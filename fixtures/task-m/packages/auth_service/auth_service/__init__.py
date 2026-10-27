from typing import Dict, Any, Optional


class AuthService:
    """Authentication and identity token provider."""

    def __init__(self):
        self.valid_tokens = {
            "token-alice-123": {"user_id": "usr-alice", "tenant_id": "tenant-corp-1"},
            "token-bob-456": {"user_id": "usr-bob", "tenant_id": "tenant-corp-2"},
        }

    def authenticate_token(self, auth_header: Optional[str]) -> Dict[str, Any]:
        """Validates Bearer token and returns user context."""
        if not auth_header or not auth_header.startswith("Bearer "):
            return {"authenticated": False, "error": "Missing or malformed Authorization header"}

        token = auth_header.split(" ", 1)[1].strip()
        user_info = self.valid_tokens.get(token)
        if not user_info:
            return {"authenticated": False, "error": "Invalid token"}

        # Returns identity context
        # CONTRACT NOTE: AuthService outputs 'user_id' and 'tenant_id'
        return {
            "authenticated": True,
            "user_id": user_info["user_id"],
            "tenant_id": user_info["tenant_id"],
        }
