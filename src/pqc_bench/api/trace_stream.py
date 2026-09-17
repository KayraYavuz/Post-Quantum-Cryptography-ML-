"""Bounded, synthetic-only WebSocket oscilloscope telemetry.

This is visualization data, not hardware acquisition or evidence of leakage.
Clients send one validated request to select a mode. Live Play sends ``live``;
Pause sends ``pause`` or closes the connection. No filesystem paths are accepted.
"""
from __future__ import annotations

import asyncio
import json
import time
from typing import Literal

import numpy as np
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from pqc_bench.visualize.waveform import generate_power_trace
from pqc_bench.telemetry_alerts import AlertEngine, AlertPolicy, TelemetrySample


class WsTraceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trace_type: Literal["synthetic", "playback", "live", "pause"] = "synthetic"
    model: Literal["unprotected", "protected", "masked"] = "unprotected"
    n_samples: int = Field(256, ge=8, le=1024, strict=True)
    sample_rate: float = Field(1e9, gt=0, le=1e12, allow_inf_nan=False)
    butterfly_markers: bool = True
    n_chunks: int = Field(10, ge=1, le=100, strict=True)
    fps: int = Field(10, ge=1, le=60, strict=True)
    session_id: str | None = Field(None, max_length=128)
    # Connection-local JSON only; clients cannot configure external delivery.
    alerts: AlertPolicy | None = None


def _frame(request: WsTraceRequest, rng: np.random.Generator, index: int) -> dict:
    info = generate_power_trace(
        n_samples=request.n_samples, leakage_model=request.model,
        add_noise=False, butterfly_markers=request.butterfly_markers,
    )
    # The shared generator intentionally has repeatable noise. A connection-local
    # RNG provides fresh visual frames without altering global simulation state.
    trace = info["trace"] + rng.normal(0, info["labels"]["noise_std"], request.n_samples)
    peak = info["labels"]["butterfly_amplitude"]
    score = float(peak / max(float(np.max(np.abs(trace))), 1e-12))
    return {
        "type": {"live": "live_trace", "playback": "playback_chunk"}.get(
            request.trace_type, "trace"
        ),
        "source": "synthetic",
        "trace": trace.tolist(),
        "time": info["time"].tolist(),
        "time_unit": "sample_index",
        "sample_rate": request.sample_rate,
        "leakage_score": round(min(1.0, score), 4),
        "labels": info["labels"],
        "chunk_index": index,
        "timestamp": time.time(),
    }


def _evaluated_frame(
    request: WsTraceRequest, rng: np.random.Generator, index: int,
    engine: AlertEngine | None,
) -> dict:
    frame = _frame(request, rng, index)
    if engine is not None:
        # Legacy leakage_score is a synthetic visual ratio, not a leakage test.
        frame["telemetry_alert"] = engine.evaluate(TelemetrySample(
            source="synthetic", metric="visual_score", value=frame["leakage_score"],
        ))
    return frame


async def websocket_traces(ws: WebSocket) -> None:
    await ws.accept()
    rng = np.random.default_rng()
    active: WsTraceRequest | None = None
    alert_engine: AlertEngine | None = None
    alert_policy: AlertPolicy | None = None
    index = 0
    try:
        while True:
            try:
                # Read controls between frames; pause and disconnect remain
                # responsive even during continuous or chunked playback.
                if active is None:
                    data = await ws.receive_json()
                else:
                    data = await asyncio.wait_for(ws.receive_json(), timeout=1 / active.fps)
                request = WsTraceRequest.model_validate(data)
            except asyncio.TimeoutError:
                await ws.send_json(_evaluated_frame(active, rng, index, alert_engine))
                index += 1
                if active.trace_type == "playback" and index >= active.n_chunks:
                    active = None
                continue
            except (ValidationError, json.JSONDecodeError):
                active = None
                await ws.send_json({"type": "error", "message": "Invalid trace request"})
                continue

            # Pause preserves dedup; new connections/policies start a new scope.
            if request.trace_type != "pause" and request.alerts != alert_policy:
                alert_policy = request.alerts
                alert_engine = AlertEngine(alert_policy) if alert_policy is not None else None
            if request.trace_type == "pause":
                active = None
                await ws.send_json({"type": "paused"})
            elif request.trace_type == "synthetic":
                active = None
                await ws.send_json(_evaluated_frame(request, rng, 0, alert_engine))
            else:
                active, index = request, 1
                await ws.send_json(_evaluated_frame(request, rng, 0, alert_engine))
                if request.trace_type == "playback" and request.n_chunks == 1:
                    active = None
    except WebSocketDisconnect:
        return
