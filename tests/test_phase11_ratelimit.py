"""
Unit tests for Phase 11.2: Rate Limiting & DoS Protection (Token Bucket).
"""

import pytest
import time
from pqc_bench.gateway.ratelimit import TokenBucket, RateLimiterManager

def test_token_bucket_basic():
    bucket = TokenBucket(capacity=5.0, refill_rate=1.0)
    # Initially 5 tokens
    assert bucket.consume(3) is True
    assert bucket.consume(3) is False # Only 2 tokens left
    assert bucket.consume(2) is True
    assert bucket.consume(1) is False

def test_token_bucket_refill():
    # Capacity 2, refill rate 10 tokens per second (fast refill for testing)
    bucket = TokenBucket(capacity=2.0, refill_rate=10.0)
    assert bucket.consume(2) is True
    assert bucket.consume(1) is False
    
    # Wait 0.2 seconds -> should refill ~2 tokens
    time.sleep(0.25)
    assert bucket.consume(1) is True

def test_rate_limiter_manager_defaults():
    manager = RateLimiterManager(default_rate=50.0, default_capacity=5.0)
    
    # Check IP rate limit
    allowed, info = manager.check_rate_limit("192.168.1.10", is_tenant=False, tokens=3)
    assert allowed is True
    assert info["remaining"] == pytest.approx(2.0, abs=0.1)
    
    allowed, info = manager.check_rate_limit("192.168.1.10", is_tenant=False, tokens=3)
    assert allowed is False
    assert info["retry_after"] > 0

def test_rate_limiter_manager_tenant_limits():
    manager = RateLimiterManager(default_rate=1.0, default_capacity=1.0)
    # Set high custom limit for tenant-alpha
    manager.set_tenant_limit("tenant-alpha", rate=100.0, capacity=10.0)
    
    # tenant-alpha should succeed with 5 tokens
    allowed, info = manager.check_rate_limit("tenant-alpha", is_tenant=True, tokens=5)
    assert allowed is True
    
    # tenant-beta (default limit capacity 1.0) should fail with 5 tokens
    allowed, info = manager.check_rate_limit("tenant-beta", is_tenant=True, tokens=5)
    assert allowed is False
    assert info["retry_after"] > 0
