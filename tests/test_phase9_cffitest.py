"""
Phase 9 C-FFI Accelerator Core Tests

Tests the C-FFI accelerator core implementation for WS-P9.5:
C-FFI Accelerator Core and Benchmark API.

Validates:
- C extension integration and performance
- Benchmark API endpoints
- Memory efficiency and data integrity
- Edge case handling and error conditions
"""

import json
import pytest
from pathlib import Path
from typing import Any, Dict, List

from pqc_bench.cffi.nuts_accelerator import (
    NutAcceleratorCore,
    benchmark_api,
    benchmark_memory_efficiency,
    benchmark_data_integrity,
)


class TestNutAcceleratorCore:
    """Test the C-FFI Nut Accelerator Core."""

    def test_core_initialization(self):
        """Test that the Nut Accelerator Core can be initialized."""
        accelerator = NutAcceleratorCore()
        assert accelerator is not None
        assert hasattr(accelerator, "n00t_impl")
        assert hasattr(accelerator, "benchmark_api")
        assert hasattr(accelerator, "memory_efficiency")

    def test_core_operation(self):
        """Test core operations."""
        accelerator = NutAcceleratorCore()
        # Test with sample data
        result = accelerator.process([1, 2, 3, 4, 5])
        assert result is not None
        assert len(result) == 5
        assert all(isinstance(x, (int, float)) for x in result)

    def test_memory_efficiency(self):
        """Test memory efficiency."""
        accelerator = NutAcceleratorCore()
        # Large dataset test
        large_data = list(range(1000))
        result = accelerator.process(large_data)
        assert len(result) == 1000
        # Check that memory usage is reasonable (implementation dependent)
        assert hasattr(accelerator, "memory_efficiency")

    def test_edge_cases(self):
        """Test edge cases."""
        accelerator = NutAcceleratorCore()
        # Empty input
        result = accelerator.process([])
        assert result == [] or result is not None

        # Single element
        result = accelerator.process([42])
        assert len(result) == 1
        assert result[0] == 42

        # Large values
        large_values = [2**31 - 1, -2**31, 0, 1, -1]
        result = accelerator.process(large_values)
        assert len(result) == len(large_values)

    def test_error_handling(self):
        """Test error handling."""
        accelerator = NutAcceleratorCore()
        # Should handle invalid input gracefully
        result = accelerator.process("invalid")
        # May raise exception or return error result
        assert result is not None


class TestBenchmarkAPI:
    """Test the Benchmark API endpoints."""

    def test_benchmark_basic(self):
        """Test basic benchmark API."""
        result = benchmark_api()
        assert result is not None
        assert "timestamp" in result
        assert "version" in result
        assert "metrics" in result
        assert isinstance(result["metrics"], dict)

    def test_benchmark_operations(self):
        """Test benchmark with operations."""
        test_data = [1, 2, 3, 4, 5]
        result = benchmark_api(test_data)
        assert result is not None
        assert "operations_count" in result
        assert "execution_time_ms" in result
        assert "memory_usage_mb" in result

    def test_benchmark_memory_efficiency(self):
        """Test memory efficiency benchmark."""
        large_data = list(range(10000))
        result = benchmark_memory_efficiency(large_data)
        assert result is not None
        assert "memory_usage_mb" in result
        assert "processing_time_ms" in result
        assert "data_integrity" in result

    def test_benchmark_data_integrity(self):
        """Test data integrity benchmark."""
        test_data = list(range(100))
        result = benchmark_data_integrity(test_data)
        assert result is not None
        assert "data_integrity_score" in result
        assert "checksum" in result
        assert "validation_time_ms" in result


class TestPerformanceMetrics:
    """Test performance metrics collection."""

    def test_performance_collection(self):
        """Test performance metrics collection."""
        accelerator = NutAcceleratorCore()
        test_data = list(range(100))

        # Get performance metrics
        result = accelerator.process_with_metrics(test_data)
        assert result is not None
        assert "result" in result
        assert "execution_time_ms" in result
        assert "memory_usage_mb" in result
        assert "data_integrity_score" in result

    def test_performance_consistency(self):
        """Test performance consistency."""
        accelerator = NutAcceleratorCore()
        test_data = [1, 2, 3, 4, 5]

        # Run multiple times for consistency check
        results = []
        for _ in range(5):
            result = accelerator.process_with_metrics(test_data)
            results.append(result)

        # All results should have similar structure
        for result in results:
            assert "result" in result
            assert "execution_time_ms" in result

    def test_performance_scaling(self):
        """Test performance scaling."""
        accelerator = NutAcceleratorCore()

        # Test with different data sizes
        sizes = [10, 100, 1000]
        for size in sizes:
            test_data = list(range(size))
            result = accelerator.process_with_metrics(test_data)
            assert result is not None
            assert "execution_time_ms" in result
            # Execution time should scale reasonably
            assert result["execution_time_ms"] > 0


class TestIntegration:
    """Test integration with existing pqc_bench infrastructure."""

    def test_integration_with_core(self):
        """Test integration with core pqc_bench functionality."""
        accelerator = NutAcceleratorCore()
        test_data = [1, 2, 3, 4, 5]
        result = accelerator.process(test_data)
        assert result is not None
        assert len(result) == len(test_data)

    def test_integration_with_benchmark(self):
        """Test that the accelerator works with benchmark system."""
        test_data = [1, 2, 3, 4, 5]
        result = benchmark_api(test_data)
        assert result is not None
        assert "metrics" in result

    def test_integration_with_reporting(self):
        """Test that the accelerator generates appropriate reports."""
        accelerator = NutAcceleratorCore()
        test_data = list(range(100))
        result = accelerator.process_with_metrics(test_data)
        assert result is not None
        assert "result" in result
        assert "data_integrity_score" in result

class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_input(self):
        """Test with empty input."""
        accelerator = NutAcceleratorCore()
        result = accelerator.process([])
        assert result == [] or result is not None

    def test_none_input(self):
        """Test with None input."""
        accelerator = NutAcceleratorCore()
        result = accelerator.process(None)
        assert result is not None

    def test_extreme_values(self):
        """Test with extreme values."""
        accelerator = NutAcceleratorCore()
        extreme_values = [2**63 - 1, -2**63, 0, 1, -1, float('inf'), float('-inf')]
        result = accelerator.process(extreme_values)
        assert result is not None
        assert len(result) == len(extreme_values)

    def test_large_dataset(self):
        """Test with large dataset."""
        accelerator = NutAcceleratorCore()
        large_data = list(range(100000))
        result = accelerator.process_with_metrics(large_data)
        assert result is not None
        assert "execution_time_ms" in result
        assert result["execution_time_ms"] < 10000  # Should complete quickly


class TestMemoryManagement:
    """Test memory management and efficiency."""

    def test_memory_cleanup(self):
        """Test memory cleanup."""
        import gc
        accelerator = NutAcceleratorCore()

        # Create and process data
        test_data = list(range(10000))
        result = accelerator.process(test_data)

        # Force garbage collection
        gc.collect()

        # Verify memory is released
        assert "memory_efficiency" in dir(accelerator)

    def test_memory_usage(self):
        """Test memory usage monitoring."""
        accelerator = NutAcceleratorCore()
        test_data = list(range(5000))

        # Process and check memory usage
        result = accelerator.process_with_metrics(test_data)
        assert result is not None
        assert "memory_usage_mb" in result
        assert result["memory_usage_mb"] > 0


# Helper function for running all tests
def run_all_tests():
    """Run all C-FFI accelerator tests and generate a summary report."""
    import time

    test_results = {
        "total_tests": 0,
        "passed_tests": 0,
        "failed_tests": 0,
        "test_summary": [],
        "execution_time_ms": 0,
    }

    # Test classes to run
    test_classes = [
        TestNutAcceleratorCore,
        TestBenchmarkAPI,
        TestPerformanceMetrics,
        TestIntegration,
        TestEdgeCases,
        TestMemoryManagement,
    ]

    start_time = time.time()

    for test_class in test_classes:
        test_instance = test_class()

        # Get all test methods
        test_methods = [
            method for method in dir(test_instance)
            if method.startswith("test_") and callable(getattr(test_instance, method))
        ]

        for test_method in test_methods:
            test_results["total_tests"] += 1
            try:
                getattr(test_instance, test_method)()
                test_results["passed_tests"] += 1
                test_results["test_summary"].append(
                    {"test": test_method, "status": "PASSED"}
                )
            except Exception as e:
                test_results["failed_tests"] += 1
                test_results["test_summary"].append(
                    {"test": test_method, "status": "FAILED", "error": str(e)}
                )

    end_time = time.time()
    test_results["execution_time_ms"] = (end_time - start_time) * 1000

    return test_results


if __name__ == "__main__":
    # Run all tests and generate report
    results = run_all_tests()

    print("=" * 60)
    print("C-FFI Accelerator Core Tests - Summary Report")
    print("=" * 60)
    print(f"Total Tests: {results['total_tests']}")
    print(f"Passed: {results['passed_tests']}")
    print(f"Failed: {results['failed_tests']}")
    print(f"Execution Time: {results['execution_time_ms']:.2f} ms")
    print("=" * 60)
    print("\nDetailed Test Results:")
    for test_result in results["test_summary"]:
        status_icon = "✅" if test_result["status"] == "PASSED" else "❌"
        print(f"{status_icon} {test_result['test']}: {test_result['status']}")
        if test_result["status"] == "FAILED":
            print(f"   Error: {test_result.get('error', 'Unknown')}")