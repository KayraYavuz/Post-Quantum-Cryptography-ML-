"""WS-P4.1: Canlı Dalga Formu Osiloskopu ve API Uç Núm (Interactive Waveform Oscilloscope & API Endpoint).

Unit tests for the waveform generation module and the /api/v1/visualize/trace endpoint.
Verifies:
- Synthetic trace generation with NTT butterfly markers
- Protected vs unprotected comparison
- API endpoint response structure
- Leakage score calculations
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from pqc_bench.visualize.waveform import (
    compare_protected_unprotected,
    generate_power_trace,
    generate_synthetic_emm_pattern,
    generate_ntt_butterfly_peak,
)
from pqc_bench.api.main import app  # FastAPI app for endpoint testing


def test_generate_power_trace_unprotected():
    """Test basic unprotected trace generation."""
    result = generate_power_trace(leakage_model="unprotected")
    
    assert "trace" in result
    assert "time" in result
    assert "leakage_score" in result
    assert "labels" in result
    
    trace = result["trace"]
    time = result["time"]
    
    assert len(trace) == 256
    assert len(time) == 256
    assert trace.dtype == float
    assert time.dtype == float
    
    # Unprotected should have higher leakage score
    assert result["leakage_score"] > 0.3
    
    # Should have butterfly marker at index 128
    assert result["labels"]["butterfly_peak_idx"] == 128
    
    print("✓ Unprotected trace generation test passed")


def test_generate_power_trace_protected():
    """Test protected (masked) trace generation."""
    result = generate_power_trace(leakage_model="protected")
    
    trace = result["trace"]
    
    # Protected should have reduced leakage compared to unprotected
    assert result["leakage_score"] < 0.5  # Lower than unprotected default
    
    # Labels should reflect protected model
    assert result["labels"]["leakage_model"] == "protected"
    
    print("✓ Protected trace generation test passed")


def test_generate_power_trace_masked():
    """Test fully masked trace generation."""
    result = generate_power_trace(leakage_model="masked")
    
    trace = result["trace"]
    
    # Masked should have lowest leakage score
    assert result["leakage_score"] < 0.3
    
    assert result["labels"]["leakage_model"] == "masked"
    
    print("✓ Masked trace generation test passed")


def test_generate_power_trace_custom_noise():
    """Test trace generation with custom noise std."""
    result = generate_power_trace(leakage_model="unprotected", noise_std=0.1)
    
    assert result["labels"]["noise_std"] == 0.1
    
    print("✓ Custom noise std test passed")


def test_generate_power_trace_no_butterfly():
    """Test trace generation without butterfly markers."""
    result = generate_power_trace(leakage_model="unprotected", butterfly_markers=False)
    
    assert result["labels"]["butterfly_amplitude"] == 0.0
    # Leakage score should be lower without markers
    assert result["leakage_score"] < 0.5
    
    print("✓ No butterfly markers test passed")


def test_generate_comparison_traces():
    """Test side-by-side comparison trace generation."""
    comparison = generate_comparison_traces()
    
    # Should have all three models
    assert "unprotected" in comparison
    assert "protected" in comparison
    assert "masked" in comparison
    
    # Each should have valid trace data
    for model_name, data in comparison.items():
        assert "trace" in data
        assert "time" in data
        assert "leakage_score" in data
        assert "labels" in data
        assert len(data["trace"]) == 256
    
    # Leakage scores should decrease: unprotected > protected > masked
    up_score = comparison["unprotected"]["leakage_score"]
    prot_score = comparison["protected"]["leakage_score"]
    mask_score = comparison["masked"]["leakage_score"]
    
    assert up_score > prot_score > mask_score
    
    print("✓ Comparison traces test passed")


def test_generate_ntt_butterfly_peak():
    """Test standalone NTT butterfly peak generation."""
    peak = generate_ntt_butterfly_peak()
    
    assert "trace" in peak
    assert "time" in peak
    assert len(peak["trace"]) == 256
    assert len(peak["time"]) == 256
    
    # Peak should be centered around index 128
    peak_val = peak["trace"][128]
    assert peak_val > 0.5  # Should have significant amplitude at center
    
    print("✓ NTT butterfly peak test passed")


def test_generate_synthetic_emm_pattern_butterfly():
    """Test synthetic EM pattern generation for NTT butterfly."""
    emm = generate_synthetic_emm_pattern(pattern="ntt_butterfly")
    
    assert "trace" in emm
    assert "time" in emm
    assert len(emm["trace"]) == 256
    
    # Butterfly pattern should have peaks near index 128
    assert emm["trace"][128] > 0.3
    
    print("✓ Synthetic EM butterfly pattern test passed")


def test_generate_synthetic_emm_pattern_protected():
    """Test protected EM pattern (reduced amplitude)."""
    emm_protected = generate_synthetic_emm_pattern(pattern="ntt_butterfly", protected=True)
    emm_unprotected = generate_synthetic_emm_pattern(pattern="ntt_butterfly", protected=False)
    
    # Protected should have lower amplitude
    assert emm_protected["trace"][128] < emm_unprotected["trace"][128]
    
    print("✓ Protected EM pattern test passed")


def test_visualize_trace_endpoint():
    """Test the /api/v1/visualize/trace endpoint returns correct structure."""
    with app.test_client() as client:
        # Test unprotected model
        response = client.get("/api/v1/visualize/trace?model=unprotected")
        assert response.status_code == 200
        
        data = response.json()
        assert data["model"] == "unprotected"
        assert "trace" in data
        assert "time" in data
        assert "leakage_score" in data
        assert "labels" in data
        assert len(data["trace"]) == 256
        assert len(data["time"]) == 256
        assert data["labels"]["leakage_model"] == "unprotected"
        
        # Test protected model
        response = client.get("/api/v1/visualize/trace?model=protected")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "protected"
        assert data["labels"]["leakage_model"] == "protected"
        
        # Test masked model
        response = client.get("/api/v1/visualize/trace?model=masked")
        assert response.status_code == 200
        data = response.json()
        assert data["model"] == "masked"
        assert data["labels"]["leakage_model"] == "masked"
        
        # Test with include_markers=False
        response = client.get("/api/v1/visualize/trace?model=unprotected&include_markers=false")
        assert response.status_code == 200
        data = response.json()
        # Markers off should still return valid data
        assert "trace" in data
        
    print("✓ Visualize trace endpoint test passed")


def test_visualize_trace_endpoint_defaults():
    """Test endpoint with default parameters."""
    with app.test_client() as client:
        response = client.get("/api/v1/visualize/trace")
        assert response.status_code == 200
        
        data = response.json()
        assert data["model"] == "unprotected"  # default
        assert data["labels"]["leakage_model"] == "unprotected"
        
    print("✓ Endpoint defaults test passed")


def test_leakage_score_ordering():
    """Test that leakage scores decrease appropriately with protection."""
    comparison = generate_comparison_traces()
    
    up = comparison["unprotected"]["leakage_score"]
    prot = comparison["protected"]["leakage_score"] 
    mask = comparison["masked"]["leakage_score"]
    
    # Unprotected has highest leakage, masked has lowest
    assert up > prot > mask
    
    # Reasonable ranges
    assert 0.3 < up <= 1.0
    assert 0.1 < prot < 0.6
    assert 0.05 < mask < 0.3
    
    print("✓ Leakage score ordering test passed")


def test_trace_time_domain():
    """Test that traces are in correct time domain."""
    for model in ["unprotected", "protected", "masked"]:
        result = generate_power_trace(leakage_model=model)
        time = result["time"]
        
        # Time should be 0 to 255 (256 samples)
        assert time[0] == 0.0
        assert time[-1] == 255.0
        
        # Uniform spacing
        for i in range(1, len(time)):
            assert time[i] - time[i-1] == 1.0
    
    print("✓ Time domain test passed")


if __name__ == "__main__":
    print("Running WS-P4.1 unit tests...")
    print("=" * 70)
    
    test_generate_power_trace_unprotected()
    test_generate_power_trace_protected()
    test_generate_power_trace_masked()
    test_generate_power_trace_custom_noise()
    test_generate_power_trace_no_butterfly()
    test_generate_comparison_traces()
    test_generate_ntt_butterfly_peak()
    test_generate_synthetic_emm_pattern_butterfly()
    test_generate_synthetic_emm_pattern_protected()
    test_visualize_trace_endpoint()
    test_visualize_trace_endpoint_defaults()
    test_leakage_score_ordering()
    test_trace_time_domain()
    
    print("=" * 70)
    print("All WS-P4.1 tests passed!")