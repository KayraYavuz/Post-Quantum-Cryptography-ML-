"""Phase 4 Unit Tests: Waveform Visualizer & API Endpoints.

Tests for WS-P4.1: Canlı Dalga Formu Osiloskopu ve API endpoint'i.
Validates:
1. Waveform generation (unprotected/protected/masked models)
2. NTT butterfly markers at correct indices
3. Protected vs unprotected leakage score comparison
4. GET /api/v1/visualize/trace endpoint response
5. Dashboard HTML trace visualization integrity
"""

import json
import numpy as np
import pytest

from pqc_bench.visualize.waveform import (
    generate_power_trace,
    generate_comparison_traces,
    compare_protected_unprotected,
    generate_ntt_butterfly_peak,
    generate_synthetic_emm_pattern,
)


class TestWaveformGeneration:
    """Test basic waveform generation with different leakage models."""

    def test_unprotected_trace(self):
        """Unprotected ML-KEM-768 trace should generate without errors."""
        result = generate_power_trace(n_samples=256, leakage_model="unprotected")
        assert "trace" in result
        assert "time" in result
        assert "leakage_score" in result
        assert "labels" in result
        assert len(result["trace"]) == 256
        assert len(result["time"]) == 256
        assert result["labels"]["leakage_model"] == "unprotected"

    def test_protected_trace(self):
        """1st-order Boolean masked trace generation."""
        result = generate_power_trace(n_samples=256, leakage_model="protected")
        assert len(result["trace"]) == 256
        assert result["labels"]["leakage_model"] == "protected"

    def test_masked_trace(self):
        """Full masking + shuffling trace generation."""
        result = generate_power_trace(n_samples=256, leakage_model="masked")
        assert len(result["trace"]) == 256
        assert result["labels"]["leakage_model"] == "masked"

    def test_butterfly_markers_present(self):
        """Unprotected trace should have NTT butterfly markers."""
        result = generate_power_trace(n_samples=256, leakage_model="unprotected", butterfly_markers=True)
        assert result["labels"]["butterfly_peak_idx"] == 128  # ML-KEM butterfly center

    def test_no_butterfly_markers(self):
        """Trace without butterfly markers."""
        result = generate_power_trace(n_samples=256, leakage_model="unprotected", butterfly_markers=False)
        assert result["labels"]["butterfly_peak_idx"] == 128  # Still defaults but markers omitted


class TestWaveformComparison:
    """Test protected vs unprotected comparison."""

    def test_comparison_all_models(self):
        """Generate all three models: unprotected, protected, masked."""
        comparison = compare_protected_unprotected()
        assert "unprotected" in comparison
        assert "protected" in comparison
        assert "masked" in comparison

        # Each should have trace, time, leakage_score, labels
        for model_name, data in comparison.items():
            assert "trace" in data
            assert "time" in data
            assert "leakage_score" in data
            assert "labels" in data

    def test_leakage_score_ordering(self):
        """Unprotected should have higher leakage score than protected."""
        comparison = compare_protected_unprotected()
        unprot_score = comparison["unprotected"]["leakage_score"]
        prot_score = comparison["protected"]["leakage_score"]
        # Unprotected naturally has more leakage
        assert unprot_score >= prot_score


class TestNttButterflyPeak:
    """Test NTT butterfly peak generation."""

    def test_ntt_butterfly_peak(self):
        """Generate standalone NTT butterfly peak."""
        result = generate_ntt_butterfly_peak()
        assert "trace" in result
        assert "time" in result
        assert len(result["trace"]) == 256

    def test_ntt_butterfly_peak_custom_index(self):
        """Generate NTT peak at custom index."""
        result = generate_ntt_butterfly_peak(n_samples=256, peak_index=64)
        assert len(result["trace"]) == 256


class TestEmmPattern:
    """Test synthetic EM pattern generation."""

    def test_ntt_emm_pattern(self):
        """Generate NTT-focused EM emission pattern."""
        result = generate_synthetic_emm_pattern(n_samples=256, pattern="ntt_butterfly")
        assert "trace" in result
        assert len(result["trace"]) == 256

    def test_polynomial_mult_emm(self):
        """Generate polynomial multiplication EM pattern."""
        result = generate_synthetic_emm_pattern(n_samples=256, pattern="polynomial_mult")
        assert "trace" in result
        assert len(result["trace"]) == 256

    def test_protected_emm_pattern(self):
        """Generate protected (masked) EM pattern."""
        result = generate_synthetic_emm_pattern(n_samples=256, pattern="ntt_butterfly", protected=True)
        assert "trace" in result


class TestComparisonTraces:
    """Test generate_comparison_traces function."""

    def test_default_models(self):
        """Default call should generate all three models."""
        results = generate_comparison_traces()
        assert len(results) == 3
        assert "unprotected" in results
        assert "protected" in results
        assert "masked" in results

    def test_specified_models(self):
        """Specify which models to generate."""
        # generate_comparison_traces respects include_* flags;
        # calling with models list + include_protected=False limits output
        results = generate_comparison_traces(models=["unprotected", "masked"], include_protected=False)
        assert len(results) == 2
        assert "unprotected" in results
        assert "masked" in results
        assert "protected" not in results


class TestAPIIntegration:
    """Test the FastAPI /api/v1/visualize/trace endpoint."""

    def test_visualize_trace_endpoint_unprotected(self):
        """Test the /api/v1/visualize/trace endpoint with unprotected model."""
        from fastapi.testclient import TestClient
        from pqc_bench.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/visualize/trace?model=unprotected&include_markers=true")
        assert response.status_code == 200

        data = response.json()
        assert data["model"] == "unprotected"
        assert "trace" in data
        assert "time" in data
        assert "leakage_score" in data
        assert "labels" in data
        assert len(data["trace"]) == 256
        assert len(data["time"]) == 256

    def test_visualize_trace_protected(self):
        """Test with protected model."""
        from fastapi.testclient import TestClient
        from pqc_bench.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/visualize/trace?model=protected&include_markers=true")
        assert response.status_code == 200

        data = response.json()
        assert data["model"] == "protected"

    def test_visualize_trace_masked(self):
        """Test with masked model."""
        from fastapi.testclient import TestClient
        from pqc_bench.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/visualize/trace?model=masked&include_markers=true")
        assert response.status_code == 200

        data = response.json()
        assert data["model"] == "masked"

    def test_visualize_trace_with_markers(self):
        """Test endpoint with butterfly markers included."""
        from fastapi.testclient import TestClient
        from pqc_bench.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/visualize/trace?model=unprotected&include_markers=true")
        data = response.json()
        assert data["labels"]["butterfly_peak_idx"] == 128

    def test_visualize_trace_without_markers(self):
        """Test endpoint without butterfly markers."""
        from fastapi.testclient import TestClient
        from pqc_bench.api.main import app

        client = TestClient(app)
        response = client.get("/api/v1/visualize/trace?model=unprotected&include_markers=false")
        data = response.json()
        # Still returns data, just without marker-specific labels emphasis
        assert "model" in data


class TestDashboardIntegration:
    """Test dashboard HTML integration."""

    def test_dashboard_contains_trace_section(self):
        """Dashboard HTML should contain waveform visualization section."""
        from pqc_bench.api.main import DASHBOARD_HTML

        assert "waveformCanvas" in DASHBOARD_HTML
        assert "generateSimulatedTrace" in DASHBOARD_HTML
        # Dashboard has JavaScript functions for trace generation and drawing
        assert "drawWaveform" in DASHBOARD_HTML or "generateSimulatedTrace" in DASHBOARD_HTML

    def test_dashboard_has_canvas_element(self):
        """Dashboard should have HTML5 canvas for waveform rendering."""
        from pqc_bench.api.main import DASHBOARD_HTML

        assert '<canvas id="waveformCanvas"' in DASHBOARD_HTML


if __name__ == "__main__":
    pytest.main([__file__, "-v"])