"""
Unit tests for Phase 11.1: Multi-Tenant Authentication & RBAC Middleware.
"""

import pytest
import time
from pqc_bench.gateway.auth import MultiTenantAuthManager

def test_auth_manager_initialization():
    manager = MultiTenantAuthManager()
    assert "tenant-alpha" in manager.tenants
    assert "tenant-beta" in manager.tenants

def test_api_key_authentication_success():
    manager = MultiTenantAuthManager()
    ctx = manager.authenticate_api_key("tenant-alpha", "key-alpha-admin")
    assert ctx is not None
    assert ctx["tenant_id"] == "tenant-alpha"
    assert ctx["username"] == "alice"
    assert ctx["role"] == "admin"
    assert "admin" in ctx["permissions"]
    assert "write" in ctx["permissions"]

def test_api_key_authentication_failure():
    manager = MultiTenantAuthManager()
    # Invalid key
    assert manager.authenticate_api_key("tenant-alpha", "invalid-key") is None
    # Invalid tenant
    assert manager.authenticate_api_key("tenant-gamma", "key-alpha-admin") is None

def test_jwt_token_generation_and_verification():
    manager = MultiTenantAuthManager()
    token = manager.generate_jwt("tenant-alpha", "alice", expiry_seconds=60)
    assert isinstance(token, str)
    assert "." in token

    ctx = manager.verify_jwt(token)
    assert ctx is not None
    assert ctx["tenant_id"] == "tenant-alpha"
    assert ctx["username"] == "alice"
    assert ctx["role"] == "admin"
    assert manager.check_permission(ctx, "fuzz") is True

def test_jwt_token_expiration():
    manager = MultiTenantAuthManager()
    # Create token that expires immediately
    token = manager.generate_jwt("tenant-alpha", "alice", expiry_seconds=-1)
    ctx = manager.verify_jwt(token)
    assert ctx is None

def test_rbac_permission_checks():
    manager = MultiTenantAuthManager()
    # Analyst in tenant-alpha
    ctx_analyst = manager.authenticate_api_key("tenant-alpha", "key-alpha-analyst")
    assert manager.check_permission(ctx_analyst, "read") is True
    assert manager.check_permission(ctx_analyst, "fuzz") is True
    assert manager.check_permission(ctx_analyst, "admin") is False

    # Viewer in tenant-beta (if added or default)
    # Let's add a viewer key to tenant-beta
    manager.add_api_key("tenant-beta", "key-beta-viewer", "viewer", "dave")
    ctx_viewer = manager.authenticate_api_key("tenant-beta", "key-beta-viewer")
    assert manager.check_permission(ctx_viewer, "read") is True
    assert manager.check_permission(ctx_viewer, "admin") is False
