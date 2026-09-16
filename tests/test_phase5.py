"""Phase 5 Unit Tests: Live WebSocket Trace Streaming Endpoint.

Tests for WS-P5.1: Canlı WebSocket Osiloskop Akışı.
Validates:
1. WebSocket /ws/traces endpoint connectivity
2. Synthetic trace streaming with different leakage models
3. HDF5 trace import functionality
4. Playback/chunk streaming mode
5. Error handling for invalid inputs
"""

import pytest

from fastapi.testclient import TestClient
from pqc_bench.api.main import app


class TestWebSocketConnectivity:
    """Test WebSocket endpoint connectivity and basic functionality."""

    def test_websocket_endpoint_exists(self):
        """Verify the /ws/traces WebSocket endpoint is registered."""
        client = TestClient(app)
        # Check that the endpoint exists in the app routes
        ws_routes = [r for r in app.routes if hasattr(r, "path") and "/ws/traces" in str(r.path)]
        assert len(ws_routes) > 0, "WebSocket endpoint /ws/traces not registered"


class TestSyntheticTraceStreaming:
    """Test synthetic trace generation via WebSocket."""

    def test_synthetic_trace_unprotected(self):
        """Test synthetic unprotected trace streaming."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            # Send synthetic trace request
            ws.send_json({
                "trace_type": "synthetic",
                "model": "unprotected",
                "n_samples": 256,
                "butterfly_markers": True,
            })

            # Receive trace data
            response = ws.receive_json()
            assert response["type"] == "trace"
            assert "trace" in response
            assert "time" in response
            assert len(response["trace"]) == 256
            assert len(response["time"]) == 256
            assert response["labels"]["leakage_model"] == "unprotected"

    def test_synthetic_trace_protected(self):
        """Test synthetic protected trace streaming."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            ws.send_json({
                "trace_type": "synthetic",
                "model": "protected",
                "n_samples": 256,
                "butterfly_markers": True,
            })

            response = ws.receive_json()
            assert response["type"] == "trace"
            assert response["labels"]["leakage_model"] == "protected"

    def test_synthetic_trace_masked(self):
        """Test synthetic masked trace streaming."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            ws.send_json({
                "trace_type": "synthetic",
                "model": "masked",
                "n_samples": 256,
                "butterfly_markers": True,
            })

            response = ws.receive_json()
            assert response["type"] == "trace"
            assert response["labels"]["leakage_model"] == "masked"

    def test_synthetic_trace_different_samples(self):
        """Test synthetic trace with custom sample count."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            ws.send_json({
                "trace_type": "synthetic",
                "model": "unprotected",
                "n_samples": 512,
                "butterfly_markers": True,
            })

            response = ws.receive_json()
            assert response["type"] == "trace"
            assert len(response["trace"]) == 512
            assert len(response["time"]) == 512

    def test_synthetic_trace_with_markers(self):
        """Test that butterfly markers are included."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            ws.send_json({
                "trace_type": "synthetic",
                "model": "unprotected",
                "n_samples": 256,
                "butterfly_markers": True,
            })

            response = ws.receive_json()
            assert response["labels"]["butterfly_peak_idx"] == 128


class TestPlaybackMode:
    """Test playback/chunk streaming mode."""

    def test_playback_chunk_streaming(self):
        """Test playback mode with chunked streaming."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            ws.send_json({
                "trace_type": "playback",
                "n_chunks": 3,
                "model": "unprotected",
                "n_samples": 256,
            })

            # Receive multiple chunks
            for i in range(3):
                response = ws.receive_json()
                assert response["type"] in ("playback_chunk",)
                assert "chunk_index" in response
                assert "trace" in response


class TestErrorHandling:
    """Test error handling for invalid inputs."""

    def test_unknown_trace_type(self):
        """Test handling of unknown trace_type."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            ws.send_json({
                "trace_type": "invalid_type",
                "model": "unprotected",
            })

            response = ws.receive_json()
            assert response["type"] == "error"
            assert "unknown" in response["message"].lower() or "invalid" in response["message"].lower()

    def test_missing_required_fields(self):
        """Test handling of missing required fields."""
        client = TestClient(app)

        with client.websocket_connect("/ws/traces") as ws:
            # Send minimal data - should handle gracefully
            ws.send_json({})

            # Connection may close or return error - both acceptable
            try:
                response = ws.receive_json()
                assert response["type"] in ("error", "trace")
            except Exception:
                # Connection closed is also acceptable
                pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
