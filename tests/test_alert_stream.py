"""Offline integration tests: optional JSON telemetry review, not leakage evidence."""
import pytest
from fastapi.testclient import TestClient
from pqc_bench.api.main import app

POLICY = {"visual_score_threshold": 0.0, "cooldown_seconds": 86400.0}


def test_default_frames_unchanged():
    with TestClient(app).websocket_connect('/ws/traces') as ws:
        ws.send_json({})
        assert 'telemetry_alert' not in ws.receive_json()


def test_playback_alert_then_suppression():
    with TestClient(app).websocket_connect('/ws/traces') as ws:
        ws.send_json({'trace_type': 'playback', 'n_chunks': 2, 'fps': 60, 'alerts': POLICY})
        first, second = ws.receive_json(), ws.receive_json()
        alert = first['telemetry_alert']
        assert alert['status'] == 'alert'
        assert alert['delivery'] == 'disabled'
        assert alert['notification']['source'] == 'synthetic'
        assert alert['notification']['metric'] == 'visual_score'
        assert alert['notification']['value'] == first['leakage_score']
        assert 'trace' not in alert['notification']
        assert second['telemetry_alert']['status'] == 'suppressed'


def test_pause_preserves_cooldown_and_policy_change_resets_scope():
    with TestClient(app).websocket_connect('/ws/traces') as ws:
        ws.send_json({'alerts': POLICY})
        assert ws.receive_json()['telemetry_alert']['status'] == 'alert'
        ws.send_json({'trace_type': 'pause'})
        assert ws.receive_json()['type'] == 'paused'
        ws.send_json({'alerts': POLICY})
        assert ws.receive_json()['telemetry_alert']['status'] == 'suppressed'
        ws.send_json({'alerts': {'visual_score_threshold': 1.0}})
        assert ws.receive_json()['telemetry_alert']['status'] == 'below_threshold'
        ws.send_json({})
        assert 'telemetry_alert' not in ws.receive_json()


def test_new_connections_have_independent_cooldown():
    for _ in range(2):
        with TestClient(app).websocket_connect('/ws/traces') as ws:
            ws.send_json({'alerts': POLICY})
            assert ws.receive_json()['telemetry_alert']['status'] == 'alert'


@pytest.mark.parametrize('alerts', [
    {'visual_score_threshold': -0.1}, {'visual_score_threshold': 1.1},
    {'visual_score_threshold': True}, {'visual_score_threshold': '0.8'},
    {'cooldown_seconds': -1}, {'cooldown_seconds': 86401},
    {'webhook_url': 'https://example.invalid'}, {'static_findings': ['idiv']},
    [], False,
])
def test_invalid_alert_policy_is_recoverable(alerts):
    with TestClient(app).websocket_connect('/ws/traces') as ws:
        ws.send_json({'alerts': alerts})
        assert ws.receive_json()['type'] == 'error'
        ws.send_json({})
        assert ws.receive_json()['type'] == 'trace'
