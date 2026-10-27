from typing import Dict, Any, Optional


class BillingService:
    """Processes tenant billing and invoice transactions."""

    def __init__(self):
        self.accounts = {
            "tenant-corp-1": {"balance": 5000.0, "active": True},
            "tenant-corp-2": {"balance": 100.0, "active": True},
        }

    def charge_account(self, headers: Dict[str, str], amount: float, description: str) -> Dict[str, Any]:
        """Charges a tenant account.
        
        CONTRACT EXPECTATION:
        BillingService expects the tenant ID in header 'X-Tenant-Id' (case-insensitive check)
        or 'x-tenant-id', and user in 'X-User-Id'.
        """
        # Normalize header keys to lowercase
        norm_headers = {k.lower(): v for k, v in headers.items()}
        tenant_id = norm_headers.get("x-tenant-id")
        user_id = norm_headers.get("x-user-id")

        if not tenant_id:
            return {
                "success": False,
                "status_code": 400,
                "error": "Billing rejected: Missing required 'X-Tenant-Id' header in downstream request",
            }

        if not user_id:
            return {
                "success": False,
                "status_code": 400,
                "error": "Billing rejected: Missing required 'X-User-Id' header in downstream request",
            }

        account = self.accounts.get(tenant_id)
        if not account or not account["active"]:
            return {
                "success": False,
                "status_code": 404,
                "error": f"Billing account not found or inactive for tenant '{tenant_id}'",
            }

        if account["balance"] < amount:
            return {
                "success": False,
                "status_code": 402,
                "error": f"Insufficient account balance: required {amount}, available {account['balance']}",
            }

        account["balance"] -= amount
        return {
            "success": True,
            "status_code": 200,
            "transaction_id": f"tx-{tenant_id}-{int(amount*100)}",
            "billed_amount": amount,
            "remaining_balance": account["balance"],
        }
