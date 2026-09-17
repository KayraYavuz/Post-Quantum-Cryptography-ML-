"""Bounded scalar telemetry review notifications; no evidence of an exploit."""
from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.request
from typing import Callable, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = "1.0"
EVIDENCE_DISCLAIMER = (
    "Threshold exceedance is for human review only; no proof of leakage, "
    "exploit, or constant-time violation."
)
_MAX_PAYLOAD_BYTES = 1024


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        frozen=True, extra="forbid", strict=True, allow_inf_nan=False,
        revalidate_instances="always",
    )


class TelemetrySample(_StrictModel):
    """A scalar reading, with only four possible source/metric combinations."""

    source: Literal["synthetic", "local"]
    metric: Literal["visual_score", "latency_ms"]
    value: float = Field(ge=0, le=1e12)

    @model_validator(mode="after")
    def visual_bound(self) -> TelemetrySample:
        if self.metric == "visual_score" and self.value > 1:
            raise ValueError("visual_score must be at most 1")
        return self


class AlertPolicy(_StrictModel):
    """Thresholds and cooldown; equality never raises an alert."""

    visual_score_threshold: float = Field(default=0.8, ge=0, le=1)
    latency_ms_threshold: float = Field(default=100.0, ge=0, le=1e12)
    cooldown_seconds: float = Field(default=60.0, ge=0, le=86400)


class _Notification(TelemetrySample):
    schema_version: Literal["1.0"]
    kind: Literal["telemetry_threshold_review"]
    severity: Literal["review"]
    threshold: float = Field(ge=0, le=1e12)
    evidence: Literal[
        "Threshold exceedance is for human review only; no proof of leakage, "
        "exploit, or constant-time violation."
    ]

    @model_validator(mode="after")
    def threshold_bound(self) -> _Notification:
        if self.metric == "visual_score" and self.threshold > 1:
            raise ValueError("visual_score threshold must be at most 1")
        if self.value <= self.threshold:
            raise ValueError("notification must exceed its threshold")
        return self


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be finite") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


class AlertEngine:
    """Per-instance cooldown, with atomic reservation before any transport call.

    Transport runs synchronously outside the state lock. A failed or disabled
    delivery still consumes cooldown. No retries or background work are added.
    """

    def __init__(
        self, policy: AlertPolicy | None = None, *,
        transport: Callable[[dict], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        if policy is not None and not isinstance(policy, AlertPolicy):
            raise TypeError("policy must be AlertPolicy or None")
        self._policy = AlertPolicy.model_validate(policy if policy is not None else {})
        if transport is not None and not callable(transport):
            raise TypeError("transport must be callable or None")
        if not callable(clock):
            raise TypeError("clock must be callable")
        self._transport = transport
        self._clock = clock
        self._lock = threading.Lock()
        self._last_clock: float | None = None
        self._last_attempt: dict[tuple[str, str], float] = {}

    def evaluate(self, sample: TelemetrySample | dict) -> dict:
        """Revalidate even constructed models; return only fixed bounded JSON.

        Invalid samples/clocks raise before reserving cooldown. Nonfinite and
        regressing clocks are rejected, not clamped. Exact expiry permits alert.
        """
        sample = TelemetrySample.model_validate(sample)
        threshold = (self._policy.visual_score_threshold
                     if sample.metric == "visual_score"
                     else self._policy.latency_ms_threshold)
        with self._lock:
            now = _finite_number(self._clock(), "clock")
            if self._last_clock is not None and now < self._last_clock:
                raise ValueError("clock must be nondecreasing")
            self._last_clock = now
            if sample.value <= threshold:
                return {"status": "below_threshold", "notification": None,
                        "delivery": "not_attempted"}
            key = (sample.source, sample.metric)
            last = self._last_attempt.get(key)
            if last is not None and now - last < self._policy.cooldown_seconds:
                return {"status": "suppressed", "notification": None,
                        "delivery": "not_attempted"}
            # Four literal combinations mean state can never exceed four keys.
            self._last_attempt[key] = now

        notification = {
            "schema_version": SCHEMA_VERSION,
            "kind": "telemetry_threshold_review", "severity": "review",
            "source": sample.source, "metric": sample.metric,
            "value": sample.value, "threshold": threshold,
            "evidence": EVIDENCE_DISCLAIMER,
        }
        delivery = "disabled"
        if self._transport is not None:
            try:
                # A transport cannot mutate the returned notification.
                self._transport(dict(notification))
                delivery = "sent"
            except Exception:
                # No exception details (which may contain paths/URLs) escape.
                delivery = "failed"
        return {"status": "alert", "notification": notification, "delivery": delivery}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class HTTPSWebhookTransport:
    """Explicit synchronous HTTPS-only delivery; no proxies, redirects or retry.

    Only the fixed notification schema is accepted, including when used directly.
    The timeout is urllib's socket timeout, not a total DNS/wall-clock deadline.
    """

    def __init__(self, url: str, *, timeout: float = 3) -> None:
        if not isinstance(url, str) or not url or not url.isascii():
            raise ValueError("url must be an ASCII HTTPS URL")
        if any(char.isspace() or ord(char) < 32 or ord(char) == 127 for char in url):
            raise ValueError("url cannot contain whitespace or control characters")
        if "?" in url or "#" in url or "\\" in url:
            raise ValueError("url cannot contain query, fragment or backslash")
        try:
            parts = urlsplit(url)
            port = parts.port  # Validates numeric port and range.
            valid = (parts.scheme == "https" and parts.hostname
                     and parts.username is None and parts.password is None
                     and (port is None or port > 0))
        except ValueError as exc:
            raise ValueError("invalid HTTPS URL") from exc
        if not valid:
            raise ValueError("url must be HTTPS with host and no credentials")
        timeout = _finite_number(timeout, "timeout")
        if not 0 < timeout <= 10:
            raise ValueError("timeout must be greater than 0 and at most 10")
        self._url = url
        self._timeout = timeout
        self._opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoRedirect(),
        )

    def __call__(self, notification: dict) -> None:
        checked = _Notification.model_validate(notification)
        body = json.dumps(checked.model_dump(mode="json"), allow_nan=False,
                          separators=(",", ":"), ensure_ascii=True).encode("ascii")
        if len(body) > _MAX_PAYLOAD_BYTES:
            raise ValueError("notification exceeds payload limit")
        request = urllib.request.Request(
            self._url, data=body, method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            response = self._opener.open(request, timeout=self._timeout)
        except urllib.error.HTTPError as exc:
            exc.close()  # Includes denied redirects; do not read response bodies.
            raise
        try:
            if not 200 <= response.getcode() < 300:
                raise ValueError("webhook returned non-2xx status")
        finally:
            response.close()
