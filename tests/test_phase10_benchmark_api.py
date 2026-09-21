"""
Tests for Hardware Benchmark API (WS-P10.4).
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from pqc_bench.hardware.benchmark_api import router

app = FastAPI()
app.include_router(router)

client = TestClient(app)


def test_list_architectures():
    response = client.get("/api/v1/hardware/architectures")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "x86_64" in data["architectures"]
    assert "apple_silicon" in data["architectures"]


def test_calibrate_endpoint():
    payload = {
        "architecture": "x86_64",
        "operation": "ntt",
        "iterations": 2000
    }
    response = client.post("/api/v1/hardware/calibrate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["operation"] == "ntt"
    assert data["data"]["estimated_power_mw"] > 0


def test_simulate_trace_endpoint():
    payload = {
        "architecture": "arm64",
        "operation": "ml_kem_encaps",
        "sample_points": 150
    }
    response = client.post("/api/v1/hardware/simulate-trace", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["sample_count"] == 150
    assert len(data["power_trace_mw"]) == 150


def test_invalid_architecture():
    payload = {
        "architecture": "quantum_cpu_99",
        "operation": "ntt",
        "iterations": 1000
    }
    response = client.post("/api/v1/hardware/calibrate", json=payload)
    assert response.status_code == 400
