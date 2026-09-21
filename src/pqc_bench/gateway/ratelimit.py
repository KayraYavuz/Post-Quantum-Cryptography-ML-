"""
Rate Limiting & DoS Protection Module for PQC Gateway.
Implements Token Bucket algorithm for IP and Tenant based rate limiting.
"""

import time
from typing import Dict, Tuple, Any, Optional

class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float):
        self.capacity = capacity
        self.refill_rate = refill_rate # tokens per second
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        now = time.time()
        elapsed = now - self.last_refill
        self.last_refill = now
        
        # Refill tokens
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        
        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def get_info(self) -> Dict[str, Any]:
        now = time.time()
        elapsed = now - self.last_refill
        current_tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        return {
            "tokens": current_tokens,
            "capacity": self.capacity,
            "refill_rate": self.refill_rate
        }


class RateLimiterManager:
    def __init__(self, default_rate: float = 10.0, default_capacity: int = 20):
        # default_rate: tokens per second (e.g. 10 req/sec)
        # default_capacity: burst capacity (e.g. 20 tokens)
        self.default_rate = default_rate
        self.default_capacity = default_capacity
        self.buckets: Dict[str, TokenBucket] = {}
        self.tenant_limits: Dict[str, Tuple[float, int]] = {} # tenant_id -> (rate, capacity)
        self.ip_limits: Dict[str, Tuple[float, int]] = {} # ip -> (rate, capacity)

    def set_tenant_limit(self, tenant_id: str, rate: float, capacity: int):
        self.tenant_limits[tenant_id] = (rate, capacity)

    def set_ip_limit(self, ip: str, rate: float, capacity: int):
        self.ip_limits[ip] = (rate, capacity)

    def _get_or_create_bucket(self, key: str, custom_limit: Optional[Tuple[float, int]] = None) -> TokenBucket:
        if key not in self.buckets:
            rate, capacity = custom_limit if custom_limit else (self.default_rate, self.default_capacity)
            self.buckets[key] = TokenBucket(capacity=float(capacity), refill_rate=float(rate))
        else:
            # Update bucket parameters if custom limit changed
            if custom_limit:
                bucket = self.buckets[key]
                if bucket.refill_rate != custom_limit[0] or bucket.capacity != custom_limit[1]:
                    bucket.refill_rate = float(custom_limit[0])
                    bucket.capacity = float(custom_limit[1])
                    bucket.tokens = min(bucket.tokens, bucket.capacity)
        return self.buckets[key]

    def check_rate_limit(self, identifier: str, is_tenant: bool = False, tokens: int = 1) -> Tuple[bool, Dict[str, Any]]:
        """
        Check if request is allowed under rate limits.
        identifier: tenant_id or client IP address.
        """
        custom_limit = None
        if is_tenant and identifier in self.tenant_limits:
            custom_limit = self.tenant_limits[identifier]
        elif not is_tenant and identifier in self.ip_limits:
            custom_limit = self.ip_limits[identifier]

        bucket = self._get_or_create_bucket(identifier, custom_limit)
        allowed = bucket.consume(tokens)
        info = bucket.get_info()
        
        # Calculate retry-after if not allowed
        retry_after = 0.0
        if not allowed:
            needed = tokens - info["tokens"]
            if bucket.refill_rate > 0:
                retry_after = needed / bucket.refill_rate

        return allowed, {
            "allowed": allowed,
            "remaining": max(0.0, info["tokens"]),
            "capacity": bucket.capacity,
            "retry_after": retry_after
        }

    def reset(self):
        self.buckets.clear()
        self.tenant_limits.clear()
        self.ip_limits.clear()
