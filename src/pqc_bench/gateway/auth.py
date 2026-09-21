"""
Authentication and Multi-Tenant RBAC Module for PQC Gateway.
Provides API Key verification, JWT token generation/validation, and Role-Based Access Control (RBAC).
"""

import hmac
import hashlib
import time
import base64
import json
from typing import Dict, Any, Optional, List

class MultiTenantAuthManager:
    def __init__(self):
        # tenant_id -> { "api_keys": set(keys), "roles": {role: permissions}, "users": {username: {role, api_key}} }
        self.tenants: Dict[str, Dict[str, Any]] = {}
        # secret for signing tokens
        self._jwt_secret = "pqc_gateway_super_secret_key_2026"
        
        # Initialize default tenants for testing
        self.register_tenant("tenant-alpha", {
            "admin": ["read", "write", "fuzz", "admin"],
            "analyst": ["read", "fuzz"],
            "viewer": ["read"]
        })
        self.register_tenant("tenant-beta", {
            "admin": ["read", "write", "admin"],
            "viewer": ["read"]
        })
        
        # Add default API keys & users
        self.add_api_key("tenant-alpha", "key-alpha-admin", "admin", "alice")
        self.add_api_key("tenant-alpha", "key-alpha-analyst", "analyst", "bob")
        self.add_api_key("tenant-beta", "key-beta-admin", "admin", "charlie")

    def register_tenant(self, tenant_id: str, roles: Dict[str, List[str]]):
        self.tenants[tenant_id] = {
            "roles": roles,
            "api_keys": {}, # key -> {username, role}
            "users": {}
        }

    def add_api_key(self, tenant_id: str, api_key: str, role: str, username: str):
        if tenant_id not in self.tenants:
            raise ValueError(f"Tenant {tenant_id} does not exist.")
        if role not in self.tenants[tenant_id]["roles"]:
            raise ValueError(f"Role {role} not defined for tenant {tenant_id}.")
        
        self.tenants[tenant_id]["api_keys"][api_key] = {
            "username": username,
            "role": role
        }
        self.tenants[tenant_id]["users"][username] = {
            "role": role,
            "api_key": api_key
        }

    def authenticate_api_key(self, tenant_id: str, api_key: str) -> Optional[Dict[str, Any]]:
        if tenant_id not in self.tenants:
            return None
        keys = self.tenants[tenant_id]["api_keys"]
        if api_key in keys:
            info = keys[api_key]
            return {
                "tenant_id": tenant_id,
                "username": info["username"],
                "role": info["role"],
                "permissions": self.tenants[tenant_id]["roles"][info["role"]]
            }
        return None

    def generate_jwt(self, tenant_id: str, username: str, expiry_seconds: int = 3600) -> str:
        if tenant_id not in self.tenants or username not in self.tenants[tenant_id]["users"]:
            raise ValueError("Invalid tenant or username")
        
        user_info = self.tenants[tenant_id]["users"][username]
        payload = {
            "tenant_id": tenant_id,
            "username": username,
            "role": user_info["role"],
            "exp": int(time.time()) + expiry_seconds
        }
        
        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload_bytes).decode("utf-8").rstrip("=")
        
        signature = hmac.new(
            self._jwt_secret.encode("utf-8"),
            payload_b64.encode("utf-8"),
            hashlib.sha256
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
        
        return f"{payload_b64}.{sig_b64}"

    def verify_jwt(self, token: str) -> Optional[Dict[str, Any]]:
        try:
            parts = token.split(".")
            if len(parts) != 2:
                return None
            payload_b64, sig_b64 = parts
            
            # Verify signature
            expected_sig = hmac.new(
                self._jwt_secret.encode("utf-8"),
                payload_b64.encode("utf-8"),
                hashlib.sha256
            ).digest()
            expected_sig_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")
            
            if not hmac.compare_digest(sig_b64, expected_sig_b64):
                return None
            
            # Decode payload
            padding = "=" * (-len(payload_b64) % 4)
            payload_bytes = base64.urlsafe_b64decode(payload_b64 + padding)
            payload = json.loads(payload_bytes.decode("utf-8"))
            
            # Check expiration
            if payload.get("exp", 0) < time.time():
                return None
                
            tenant_id = payload.get("tenant_id")
            role = payload.get("role")
            if tenant_id in self.tenants and role in self.tenants[tenant_id]["roles"]:
                payload["permissions"] = self.tenants[tenant_id]["roles"][role]
                return payload
                
            return None
        except Exception:
            return None

    def check_permission(self, auth_context: Dict[str, Any], required_permission: str) -> bool:
        if not auth_context:
            return False
        permissions = auth_context.get("permissions", [])
        return required_permission in permissions
