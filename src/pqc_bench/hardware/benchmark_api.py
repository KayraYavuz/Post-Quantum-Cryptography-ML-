"""
Hardware Benchmark and Calibration API Service.
Provides REST endpoints for architecture power profiling and side-channel trace simulations.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from pqc_bench.hardware.power_calibration import PowerCalibrationEngine

router = APIRouter(prefix="/api/v1/hardware", tags=["Hardware Power & Benchmarking"])


class CalibrationRequest(BaseModel):
    architecture: str = Field(..., description="Architecture name: x86_64, arm64, apple_silicon")
    operation: str = Field(..., description="Cryptographic operation: ntt, keccak, ml_kem_encaps, etc.")
    iterations: int = Field(1000, description="Number of benchmark iterations")


class TraceSimulationRequest(BaseModel):
    architecture: str = Field(..., description="Architecture name: x86_64, arm64, apple_silicon")
    operation: str = Field(..., description="Cryptographic operation")
    sample_points: int = Field(500, description="Number of sample points in trace")


@router.post("/calibrate", response_model=Dict[str, Any])
async def calibrate_hardware_power(req: CalibrationRequest):
    """
    Calculates estimated power consumption and energy profile for specified architecture and operation.
    """
    try:
        engine = PowerCalibrationEngine(req.architecture)
        result = engine.calibrate_operation(req.operation, req.iterations)
        return {"status": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/simulate-trace", response_model=Dict[str, Any])
async def simulate_hardware_trace(req: TraceSimulationRequest):
    """
    Generates synthetic power trace waveform points for side-channel simulation.
    """
    try:
        engine = PowerCalibrationEngine(req.architecture)
        trace = engine.simulate_power_trace(req.operation, req.sample_points)
        return {
            "status": "success",
            "architecture": req.architecture,
            "operation": req.operation,
            "sample_count": len(trace),
            "power_trace_mw": trace
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/architectures", response_model=Dict[str, Any])
async def list_supported_architectures():
    """
    Lists supported CPU architectures and their hardware baseline profiles.
    """
    return {
        "status": "success",
        "architectures": PowerCalibrationEngine.SUPPORTED_ARCHS
    }
