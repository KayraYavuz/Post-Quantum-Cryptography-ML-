"""Isolated loopback-only synthetic demo; no legacy attack/API integration.

Importing this module opens no socket. Use create_local_telemetry_app() with an
in-process ASGI client. Each app owns its registry and untrained CPU ResNet.
"""
from __future__ import annotations

import ipaddress
import math
import os
from pathlib import Path
from threading import Lock
from time import perf_counter

import torch
from fastapi import FastAPI, HTTPException, Request, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from prometheus_client.core import GaugeMetricFamily
from prometheus_client.exposition import CONTENT_TYPE_LATEST
from starlette.concurrency import run_in_threadpool

from pqc_bench.models.resnet1d import SideChannelResNet1D

_INIT_LOCK = Lock()
_UNMEASURED = ("hardware_cycles", "gpu_duration_seconds", "gpu_memory_bytes",
               "model_only_memory_bytes", "accuracy")


def read_process_rss_bytes() -> int | None:
    """Linux current resident pages * host page size, for the entire process.

    Not peak RSS, a per-model allocation, container total, or GPU memory.
    Unsupported/failed observations return None, never a fabricated zero.
    """
    try:
        with Path('/proc/self/statm').open('r', encoding='ascii') as stream:
            fields = stream.read(256).split()
        pages = int(fields[1])
        page_size = os.sysconf('SC_PAGE_SIZE')
        if pages < 0 or page_size <= 0:
            return None
        return pages * page_size
    except (OSError, ValueError, IndexError, AttributeError):
        return None


class ProcessRSSCollector:
    """Fresh samples on scrape: omit unavailable bytes, expose availability."""

    def describe(self):
        yield GaugeMetricFamily('pqc_local_process_resident_memory_bytes',
                                'Current entire-process Linux RSS in bytes; not model memory.')
        yield GaugeMetricFamily('pqc_local_process_rss_measured',
                                '1 if current entire-process RSS was sampled, otherwise 0.')

    def collect(self):
        rss = read_process_rss_bytes()
        valid = type(rss) is int and rss >= 0
        yield GaugeMetricFamily('pqc_local_process_rss_measured',
                                '1 if current entire-process RSS was sampled, otherwise 0.',
                                value=int(valid))
        if valid:
            yield GaugeMetricFamily('pqc_local_process_resident_memory_bytes',
                                    'Current entire-process Linux RSS in bytes; not model memory.',
                                    value=rss)


def create_local_telemetry_app() -> FastAPI:
    """Create an independent, non-listening synthetic-only ASGI application.

    The three fixed rows are sine, cosine and seeded noise. The model has random
    untrained weights. No request-provided traces, paths, model IDs or labels.
    """
    registry = CollectorRegistry()
    duration = Histogram(
        'pqc_local_synthetic_inference_duration_seconds',
        'Successful fixed batch CPU forward and argmax host wall time; excludes setup and HTTP.',
        buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.5, 1, 5), registry=registry,
    )
    successes = Counter('pqc_local_synthetic_inference_successes',
                        'Successful fixed synthetic batches, not individual samples.', registry=registry)
    failures = Counter('pqc_local_synthetic_inference_failures',
                       'Failed fixed synthetic batches; no exception labels.', registry=registry)
    registry.register(ProcessRSSCollector())
    # fork_rng restores CPU RNG; never reset global thread settings or load checkpoints.
    with _INIT_LOCK, torch.random.fork_rng(devices=[]):
        torch.manual_seed(812)
        model = SideChannelResNet1D(
            input_length=64, num_classes=3, stem_channels=4, stage_channels=(8,),
            blocks_per_stage=1, fc_dim=8, dropout_p=0.0,
        ).cpu().eval()
    t = torch.linspace(0, 1, 64)
    generator = torch.Generator(device='cpu').manual_seed(812)
    batch = torch.stack((torch.sin(2 * torch.pi * t), torch.cos(2 * torch.pi * t),
                         torch.randn(64, generator=generator)))
    inference_lock = Lock()
    app = FastAPI(title='Local synthetic telemetry', docs_url=None, redoc_url=None,
                  openapi_url=None)

    @app.middleware('http')
    async def local_only(request: Request, call_next):
        try:
            local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
        except ValueError:
            local = False
        if not local:
            return Response('Loopback client required', status_code=403)
        # No request labels or user waveforms; reject inputs rather than silently ignore.
        if request.url.query:
            return Response('Query parameters are not accepted', status_code=400)
        async for chunk in request.stream():
            if chunk:
                return Response('Request bodies are not accepted', status_code=400)
        return await call_next(request)

    def infer():
        if not inference_lock.acquire(blocking=False):
            raise HTTPException(status_code=409, detail='Synthetic inference busy')
        try:
            start = perf_counter()
            with torch.inference_mode():
                logits = model(batch)
                if logits.shape != (3, 3) or not torch.isfinite(logits).all():
                    raise ValueError('Invalid model output')
                predictions = logits.argmax(dim=1).tolist()
            elapsed = perf_counter() - start
            if not math.isfinite(elapsed) or elapsed < 0:
                raise ValueError('Invalid host duration')
            duration.observe(elapsed)
            successes.inc()
            return {
                'scope': 'fixed_general_synthetic_cpu', 'model': 'untrained_resnet1d',
                'batch_size': 3, 'classes': ['sine', 'cosine', 'noise'],
                'predictions': predictions, 'host_duration_seconds': elapsed,
                'unmeasured': {name: None for name in _UNMEASURED},
            }
        except Exception:
            failures.inc()
            raise HTTPException(status_code=500, detail='Synthetic inference failed') from None
        finally:
            inference_lock.release()

    @app.post('/synthetic/infer')
    async def synthetic_infer():
        return await run_in_threadpool(infer)

    @app.get('/metrics', include_in_schema=False)
    def metrics():
        return Response(generate_latest(registry), headers={
            'Content-Type': CONTENT_TYPE_LATEST, 'Cache-Control': 'no-store',
        })

    return app
