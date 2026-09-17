# WS-P5.4 — Bounded telemetry review notifications

`pqc_bench.telemetry_alerts` is a standalone defensive threshold notifier for
project-owned synthetic or local scalar telemetry. A notification requests human
review: it is **not proof of leakage, an exploit, or a constant-time violation**.
The engine does not collect measurements or establish statistical significance.

## Scope and bounded inputs

`TelemetrySample` is a strict, frozen, extra-forbid Pydantic model:

- `source`: `synthetic` or `local` (not a hostname or identifier).
- `metric`: `visual_score` or `latency_ms`.
- `value`: finite numeric scalar from 0 through 1e12; `visual_score` is at most 1.

Strict numeric validation rejects strings and booleans; integers are accepted as
numeric floats by Pydantic. Unknown fields are rejected. There are no raw traces,
names, filesystem paths, or static findings in the schema. `evaluate` accepts a
model or dictionary and revalidates models at its boundary, including those
created using `model_construct`. Policy models are likewise revalidated.

In the existing stream integration, `visual_score` corresponds to the legacy
`leakage_score` visual ratio; the field name does not make it a leakage test.
`latency_ms` represents caller-supplied local wall-clock measurements of the
project's own functions, not modeled cycle estimates. Origin and measurement
units remain the caller's responsibility. P5.3 binary/static review findings
are not accepted as telemetry evidence.

`AlertPolicy` is also strict, frozen and extra-forbid:

| Field | Default | Inclusive bounds |
| --- | --- | --- |
| `visual_score_threshold` | 0.8 | 0–1 |
| `latency_ms_threshold` | 100.0 | 0–1e12 |
| `cooldown_seconds` | 60.0 | 0–86400 |

All policy numbers must be finite. Alerting requires **strictly greater than**
the threshold; equality is below threshold.

## API and lifecycle

```python
from pqc_bench.telemetry_alerts import AlertEngine, AlertPolicy, TelemetrySample

engine = AlertEngine(AlertPolicy(latency_ms_threshold=100.0))
result = engine.evaluate(
    TelemetrySample(source="local", metric="latency_ms", value=120.0)
)
assert result["status"] == "alert"
assert result["delivery"] == "disabled"  # No network by default.
```

The JSON result always has exactly `status`, `notification`, and `delivery`:

| Status | Notification | Delivery |
| --- | --- | --- |
| `below_threshold` | `None` | `not_attempted` |
| `suppressed` | `None` | `not_attempted` |
| `alert` | fixed-schema dict | `disabled`, `sent`, or `failed` |

Notifications contain exactly `schema_version` (`1.0`), `kind`
(`telemetry_threshold_review`), `severity` (`review`), `source`, `metric`, `value`,
`threshold`, and a fixed `evidence` disclaimer:

> Threshold exceedance is for human review only; no proof of leakage, exploit,
> or constant-time violation.

Payload size is bounded by literal strings and scalar ranges. Transport
exceptions are reduced to `failed`, with no exception text or response content
included. `sent` means the callable returned normally, not that a human received
or acknowledged the alert. For the provided webhook it means an HTTP 2xx status.

Cooldown state is per engine, keyed only by source and metric: at most four
entries, with no persistence, identifiers, or growing event history. Reservation
occurs atomically before the transport attempt. Failed and disabled deliveries
also consume cooldown; no automatic retry occurs. A below-threshold reading does
not clear cooldown. Exactly at expiry a new alert is permitted. Zero cooldown
allows every above-threshold reading. A new engine starts with empty history;
changing policy means creating a new engine. This is not a durable or distributed
rate limiter. Integrations preserving the engine across pause preserve cooldown.

An injected `clock` defaults to `time.monotonic`. Every validated evaluation
checks a finite, nondecreasing clock under the state lock. Nonfinite values,
booleans, nonnumeric values, and backward movement raise `ValueError` without
reserving an attempt. Equal readings are allowed. Sample validation errors raise
Pydantic `ValidationError`. Concurrent evaluations atomically reserve cooldown;
transport callbacks execute outside the state lock and may overlap across keys
(or with zero cooldown), so custom transports must tolerate this.

## Explicit synchronous HTTPS delivery

Only explicit caller configuration enables delivery. The module never discovers
webhook URLs from the environment or opens network connections by default.
Constructing the transport builds its opener but makes no request. Example for a
caller-authorized endpoint (not executed by tests):

```python
from pqc_bench.telemetry_alerts import HTTPSWebhookTransport

transport = HTTPSWebhookTransport("https://alerts.example.invalid/review", timeout=3)
engine = AlertEngine(transport=transport)
# Subsequent above-threshold evaluate calls synchronously POST notifications.
```

The URL must be ASCII HTTPS with a host, without credentials, query, fragment,
whitespace, control characters, or backslashes. The caller must authorize and
trust the destination: this is not a destination allowlist or a safe URL fetcher
for untrusted users. It does not prohibit private-network destinations.

The stdlib urllib transport:

- Uses a dedicated opener with proxy inheritance disabled (`ProxyHandler({})`).
- Denies redirects instead of forwarding the request to another endpoint.
- Revalidates the fixed notification schema even on direct calls, serializes
  finite JSON, and enforces a maximum request-body size of 1024 bytes.
- Makes one HTTPS POST, accepts only 2xx, closes responses, and never reads their
  bodies. Normal HTTPS certificate verification remains enabled.
- Has a finite timeout greater than 0 and at most 10 seconds (default 3).

Delivery is synchronous. The urllib timeout is a socket-operation timeout,
**not a total DNS or wall-clock deadline**. Custom transport callables have no
engine-enforced timeout. There is no worker, queue, scheduling, or retry system.

## Offline verification

No test uses real network access. Fake callables and mocked urllib openers cover
bounds, model-construction bypass, exact cooldown expiry, independent keys,
failed/disabled delivery, concurrency, clock handling, fixed payloads, URL and
timeout rejection, disabled proxy inheritance, redirect refusal, and HTTP errors.

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src python3 -m pytest \
  tests/test_telemetry_alerts.py -q -p no:cacheprovider
```
