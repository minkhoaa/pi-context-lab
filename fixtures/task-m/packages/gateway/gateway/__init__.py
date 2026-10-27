from typing import Dict, Any, Optional
import uuid

from auth_service import AuthService
from inventory_service import InventoryService
from billing_service import BillingService


class ApiGateway:
    """Entrypoint API Gateway dispatching requests to microservices."""

    def __init__(
        self,
        auth_svc: Optional[AuthService] = None,
        inventory_svc: Optional[InventoryService] = None,
        billing_svc: Optional[BillingService] = None,
    ):
        self.auth_svc = auth_svc or AuthService()
        self.inventory_svc = inventory_svc or InventoryService()
        self.billing_svc = billing_svc or BillingService()

    def handle_checkout(self, request_headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
        """Orchestrates checkout:
        1. Authenticates request via AuthService.
        2. Injects downstream identity headers.
        3. Reserves items via InventoryService.
        4. Charges account via BillingService.
        """
        # Step 1: Auth
        auth_header = request_headers.get("Authorization") or request_headers.get("authorization")
        auth_res = self.auth_svc.authenticate_token(auth_header)
        if not auth_res.get("authenticated"):
            return {
                "status_code": 401,
                "error": auth_res.get("error", "Unauthorized"),
                "data": {},
            }

        user_id = auth_res["user_id"]
        tenant_id = auth_res["tenant_id"]

        # Step 2: Contract drift / header naming bug here!
        # The gateway forwards user_id as 'X-User-Id', but forwards tenant_id as 'X-Account-Id'
        # instead of 'X-Tenant-Id' when talking to billing/downstream services!
        downstream_headers = {
            "X-User-Id": user_id,
            "X-Account-Id": tenant_id,  # BUG: Contract drift. Billing service expects 'X-Tenant-Id'.
            "X-Correlation-Id": request_headers.get("X-Correlation-Id", str(uuid.uuid4())),
        }

        # Step 3: Inventory
        item_id = payload.get("item_id")
        qty = payload.get("quantity", 1)
        inv_res = self.inventory_svc.check_and_reserve(item_id=item_id, quantity=qty, tenant_id=tenant_id)
        if not inv_res.get("success"):
            return {
                "status_code": 400,
                "error": inv_res.get("error", "Inventory reservation failed"),
                "data": {},
            }

        # Step 4: Billing
        total_amount = payload.get("amount", 0.0)
        billing_res = self.billing_svc.charge_account(
            headers=downstream_headers,
            amount=total_amount,
            description=f"Purchase {qty}x {item_id}",
        )

        if not billing_res.get("success"):
            return {
                "status_code": billing_res.get("status_code", 500),
                "error": billing_res.get("error", "Billing transaction failed"),
                "data": {"billing_details": billing_res},
            }

        return {
            "status_code": 200,
            "data": {
                "transaction_id": billing_res.get("transaction_id"),
                "reserved_units": inv_res.get("reserved_units"),
                "user_id": user_id,
                "tenant_id": tenant_id,
            },
            "error": None,
        }
