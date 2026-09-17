"""Offline checks for bounded defensive telemetry review notifications."""
import pytest
from pydantic import ValidationError
from pqc_bench.telemetry_alerts import AlertEngine, AlertPolicy, TelemetrySample


def test_negative_timing_rejected():
    with pytest.raises(ValidationError):
        TelemetrySample(source='local', metric='latency_ms', value=-1.0)


def test_above_threshold_alert():
    result = AlertEngine(clock=lambda: 0.0).evaluate(
        TelemetrySample(source='local', metric='latency_ms', value=101.0))
    assert result['status'] == 'alert'
    assert result['delivery'] == 'disabled'


def test_bounded_notification_fields():
    result = AlertEngine(clock=lambda: 0.0).evaluate(
        TelemetrySample(source='synthetic', metric='visual_score', value=0.9))
    assert set(result) == {'status', 'notification', 'delivery'}
    assert set(result['notification']) == {
        'schema_version', 'kind', 'severity', 'source', 'metric', 'value',
        'threshold', 'evidence'}

import concurrent.futures
import io
import json
import math
import urllib.error
import urllib.request
from unittest.mock import Mock
from pqc_bench.telemetry_alerts import HTTPSWebhookTransport


def sample(**kw):
    return {'source': 'local', 'metric': 'latency_ms', 'value': 101.0, **kw}


@pytest.mark.parametrize('change', [
    {'source': 'remote'}, {'metric': 'cycles'}, {'value': True},
    {'value': '1'}, {'value': -1.0}, {'value': 1e12 + 1},
    {'value': math.nan}, {'value': math.inf}, {'value': -math.inf},
    {'metric': 'visual_score', 'value': 1.01}, {'path': '/private'},
])
def test_sample_bounds(change):
    with pytest.raises(ValidationError):
        TelemetrySample(**sample(**change))


@pytest.mark.parametrize('metric,value', [
    ('latency_ms', 0.0), ('latency_ms', 1e12),
    ('visual_score', 0.0), ('visual_score', 1.0),
])
def test_sample_endpoints(metric, value):
    model = TelemetrySample(**sample(metric=metric, value=value))
    assert model.value == value
    with pytest.raises(ValidationError):
        model.value = 1.0


@pytest.mark.parametrize('field,bad', [
    ('visual_score_threshold', -0.01), ('visual_score_threshold', 1.01),
    ('latency_ms_threshold', -1.0), ('latency_ms_threshold', 1e12 + 1),
    ('cooldown_seconds', -1.0), ('cooldown_seconds', 86401.0),
    *[(field, bad) for field in ('visual_score_threshold', 'latency_ms_threshold',
                               'cooldown_seconds')
      for bad in (math.nan, math.inf, -math.inf, True, '1')],
    ('url', 'https://example.invalid'),
])
def test_policy_bounds(field, bad):
    with pytest.raises(ValidationError):
        AlertPolicy(**{field: bad})


def test_policy_defaults_endpoints_and_frozen():
    assert AlertPolicy().model_dump() == dict(visual_score_threshold=0.8,
        latency_ms_threshold=100.0, cooldown_seconds=60.0)
    AlertPolicy(visual_score_threshold=0.0, latency_ms_threshold=0.0, cooldown_seconds=0.0)
    AlertPolicy(visual_score_threshold=1.0, latency_ms_threshold=1e12, cooldown_seconds=86400.0)
    policy = AlertPolicy()
    with pytest.raises(ValidationError):
        policy.cooldown_seconds = 0.0


@pytest.mark.parametrize('value', [100.0, 0.0])
def test_threshold_strict_and_default_no_network(monkeypatch, value):
    monkeypatch.setattr(urllib.request, 'build_opener', Mock(side_effect=AssertionError))
    engine = AlertEngine(clock=lambda: 0.0)
    assert engine.evaluate(sample(value=value)) == dict(status='below_threshold',
        notification=None, delivery='not_attempted')
    assert engine.evaluate(sample())['delivery'] == 'disabled'


def test_cooldown_expiry_below_does_not_reset_and_independence():
    now = [0.0]
    engine = AlertEngine(clock=lambda: now[0])
    assert engine.evaluate(sample())['status'] == 'alert'
    now[0] = 30.0
    assert engine.evaluate(sample(value=0.0))['status'] == 'below_threshold'
    assert engine.evaluate(sample())['status'] == 'suppressed'
    for source, metric, value in [('synthetic', 'latency_ms', 101.0),
                                  ('local', 'visual_score', 0.9),
                                  ('synthetic', 'visual_score', 0.9)]:
        assert engine.evaluate(sample(source=source, metric=metric, value=value))['status'] == 'alert'
    assert len(engine._last_attempt) == 4
    now[0] = 59.999
    assert engine.evaluate(sample())['status'] == 'suppressed'
    now[0] = 60.0
    assert engine.evaluate(sample())['status'] == 'alert'
    assert AlertEngine(clock=lambda: 60.0).evaluate(sample())['status'] == 'alert'


def test_failed_delivery_reserves_cooldown_no_retry():
    now = [0.0]
    transport = Mock(side_effect=RuntimeError('/private/trace'))
    engine = AlertEngine(transport=transport, clock=lambda: now[0])
    result = engine.evaluate(sample())
    assert result['delivery'] == 'failed'
    assert '/private' not in json.dumps(result)
    assert engine.evaluate(sample())['status'] == 'suppressed'
    assert transport.call_count == 1
    now[0] = 60.0
    assert engine.evaluate(sample())['delivery'] == 'failed'
    assert transport.call_count == 2


def test_sent_and_transport_mutation_isolated():
    def transport(payload):
        payload['raw_trace'] = 'bad'
        payload['value'] = math.nan
    result = AlertEngine(transport=transport).evaluate(sample())
    assert result['delivery'] == 'sent'
    assert 'raw_trace' not in result['notification']
    assert len(json.dumps(result, allow_nan=False)) < 1024
    assert 'no proof' in result['notification']['evidence']


def test_concurrent_dedup():
    transport = Mock()
    engine = AlertEngine(transport=transport, clock=lambda: 0.0)
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: engine.evaluate(sample()), range(100)))
    assert sum(r['status'] == 'alert' for r in results) == 1
    assert transport.call_count == 1


def test_zero_cooldown():
    engine = AlertEngine(AlertPolicy(cooldown_seconds=0.0), clock=lambda: 0.0)
    assert all(engine.evaluate(sample())['status'] == 'alert' for _ in range(3))


@pytest.mark.parametrize('bad', [math.nan, math.inf, -math.inf, True, '1', 10**1000])
def test_invalid_clock_does_not_reserve(bad):
    now = [bad]
    engine = AlertEngine(clock=lambda: now[0])
    with pytest.raises(ValueError):
        engine.evaluate(sample())
    now[0] = 0.0
    assert engine.evaluate(sample())['status'] == 'alert'


def test_clock_regression_rejected_without_advancing_state():
    now = [10.0]
    engine = AlertEngine(clock=lambda: now[0])
    engine.evaluate(sample())
    now[0] = 9.0
    with pytest.raises(ValueError):
        engine.evaluate(sample())
    now[0] = 69.0
    assert engine.evaluate(sample())['status'] == 'suppressed'
    now[0] = 70.0
    assert engine.evaluate(sample())['status'] == 'alert'


@pytest.mark.parametrize('change', [{'source': 'remote'}, {'value': math.nan},
    {'metric': 'visual_score', 'value': 2.0}, {'value': '101'}])
def test_construct_bypass_revalidated(change):
    with pytest.raises(ValidationError):
        AlertEngine().evaluate(TelemetrySample.model_construct(**sample(**change)))


def test_construct_policy_bypass_revalidated():
    with pytest.raises(ValidationError):
        AlertEngine(AlertPolicy.model_construct(cooldown_seconds=math.nan))
    with pytest.raises(ValidationError):
        AlertEngine().evaluate([])


@pytest.mark.parametrize('url', [
    'http://example.invalid', 'ftp://example.invalid', 'https://',
    'https://u:p@example.invalid', 'https://u@example.invalid',
    'https://example.invalid?q=1', 'https://example.invalid?',
    'https://example.invalid#f', 'https://example.invalid#',
    ' https://example.invalid', 'https://example.invalid/\n',
    'https://example.invalid:99999', 'https://example.invalid:0',
    'https://example.invalid:bad', 'https://[bad',
    'https://example.invalid\\path', None,
])
def test_webhook_url_rejections(url):
    with pytest.raises(ValueError):
        HTTPSWebhookTransport(url)


@pytest.mark.parametrize('timeout', [0, -1, 10.01, math.nan, math.inf, True, '3'])
def test_webhook_timeout_bounds(timeout):
    with pytest.raises(ValueError):
        HTTPSWebhookTransport('https://example.invalid', timeout=timeout)


@pytest.mark.parametrize('code', [200, 201, 204, 299, 300, 302, 400, 500])
def test_mock_webhook_delivery(monkeypatch, code):
    response = Mock()
    response.getcode.return_value = code
    response.read.side_effect = AssertionError('must not read body')
    opener = Mock()
    opener.open.return_value = response
    build = Mock(return_value=opener)
    monkeypatch.setattr(urllib.request, 'build_opener', build)
    transport = HTTPSWebhookTransport('https://example.invalid/alerts', timeout=10)
    handlers = build.call_args.args
    assert next(h for h in handlers if isinstance(h, urllib.request.ProxyHandler)).proxies == {}
    redirect = next(h for h in handlers if isinstance(h, urllib.request.HTTPRedirectHandler))
    assert redirect.redirect_request(None, None, 302, None, None, 'https://else.invalid') is None
    result = AlertEngine(transport=transport).evaluate(sample())
    assert result['delivery'] == ('sent' if 200 <= code < 300 else 'failed')
    request = opener.open.call_args.args[0]
    assert request.get_method() == 'POST'
    assert request.get_header('Content-type') == 'application/json'
    assert len(request.data) < 1024
    assert json.loads(request.data) == result['notification']
    assert opener.open.call_args.kwargs == {'timeout': 10.0}
    response.read.assert_not_called()
    response.close.assert_called_once()
    opener.open.assert_called_once()


@pytest.mark.parametrize('code', [302, 307, 308, 500])
def test_http_errors_closed_no_retry(monkeypatch, code):
    body = io.BytesIO(b'unread')
    error = urllib.error.HTTPError('https://example.invalid', code, 'error', {}, body)
    opener = Mock()
    opener.open.side_effect = error
    monkeypatch.setattr(urllib.request, 'build_opener', Mock(return_value=opener))
    engine = AlertEngine(transport=HTTPSWebhookTransport('https://example.invalid'))
    assert engine.evaluate(sample())['delivery'] == 'failed'
    assert body.closed
    assert engine.evaluate(sample())['status'] == 'suppressed'
    opener.open.assert_called_once()


def test_network_error_and_direct_payload_rejected(monkeypatch):
    opener = Mock()
    opener.open.side_effect = urllib.error.URLError('unavailable')
    monkeypatch.setattr(urllib.request, 'build_opener', Mock(return_value=opener))
    transport = HTTPSWebhookTransport('https://example.invalid')
    with pytest.raises(ValidationError):
        transport({'raw_trace': 'private'})
    opener.open.assert_not_called()
    assert AlertEngine(transport=transport).evaluate(sample())['delivery'] == 'failed'
