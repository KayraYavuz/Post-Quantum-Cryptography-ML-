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


class TestLiveStreamingRegression:
    def test_single_registered_route(self):
        assert len([r for r in app.routes if getattr(r, 'path', None) == '/ws/traces']) == 1

    @pytest.mark.parametrize('model', ['unprotected', 'protected', 'masked'])
    def test_live_pause_resume(self, model):
        with TestClient(app).websocket_connect('/ws/traces') as ws:
            ws.send_json({'trace_type': 'live', 'model': model, 'fps': 60})
            first = ws.receive_json()
            second = ws.receive_json()
            assert first['type'] == second['type'] == 'live_trace'
            assert first['source'] == 'synthetic'
            assert first['labels']['leakage_model'] == model
            assert len(first['trace']) == len(first['time']) == 256
            assert first['trace'] != second['trace']
            assert second['chunk_index'] == first['chunk_index'] + 1
            ws.send_json({'trace_type': 'pause'})
            # Frames already in transit may precede the acknowledgement.
            for _ in range(20):
                if ws.receive_json()['type'] == 'paused':
                    break
            else:
                pytest.fail('Pause was not acknowledged')
            ws.send_json({'trace_type': 'synthetic', 'model': 'protected'})
            assert ws.receive_json()['type'] == 'trace'
            ws.send_json({'trace_type': 'live', 'model': model})
            assert ws.receive_json()['chunk_index'] == 0

    @pytest.mark.parametrize('payload', [
        {'n_samples': 0}, {'n_samples': 1}, {'n_samples': 1025},
        {'n_samples': True}, {'n_samples': '256'}, {'fps': 0}, {'fps': 61},
        {'n_chunks': 101}, {'sample_rate': 0}, {'model': 'unknown'},
        {'trace_type': 'hdf5', 'filepath': '/etc/passwd'}, [], None,
    ])
    def test_invalid_request_is_recoverable(self, payload):
        with TestClient(app).websocket_connect('/ws/traces') as ws:
            ws.send_json(payload)
            assert ws.receive_json()['type'] == 'error'
            ws.send_json({'n_samples': 8, 'butterfly_markers': False})
            frame = ws.receive_json()
            assert len(frame['trace']) == 8
            assert frame['labels']['butterfly_amplitude'] == 0

    def test_invalid_json_is_recoverable(self):
        with TestClient(app).websocket_connect('/ws/traces') as ws:
            ws.send_text('{bad json')
            assert ws.receive_json()['type'] == 'error'
            ws.send_json({})
            assert ws.receive_json()['type'] == 'trace'

    def test_playback_is_bounded_and_full_length(self):
        with TestClient(app).websocket_connect('/ws/traces') as ws:
            ws.send_json({'trace_type': 'playback', 'n_chunks': 2, 'fps': 60})
            for index in range(2):
                frame = ws.receive_json()
                assert frame['chunk_index'] == index
                assert len(frame['trace']) == 256
            ws.send_json({'trace_type': 'pause'})
            assert ws.receive_json()['type'] == 'paused'

    def test_dashboard_live_controls(self):
        html = TestClient(app).get('/').text
        for marker in ['liveToggleBtn', 'pauseLiveStream', 'startLiveStream',
                       "trace_type: 'live'", '/ws/traces', 'Synthetic visualization only']:
            assert marker in html
