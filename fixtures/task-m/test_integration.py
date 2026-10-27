import sys
import os
import unittest

# Ensure all packages are on sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGES_DIR = os.path.join(BASE_DIR, "packages")

sys.path.insert(0, os.path.join(PACKAGES_DIR, "shared_types"))
sys.path.insert(0, os.path.join(PACKAGES_DIR, "auth_service"))
sys.path.insert(0, os.path.join(PACKAGES_DIR, "inventory_service"))
sys.path.insert(0, os.path.join(PACKAGES_DIR, "billing_service"))
sys.path.insert(0, os.path.join(PACKAGES_DIR, "gateway"))

from gateway import ApiGateway
from auth_service import AuthService
from inventory_service import InventoryService
from billing_service import BillingService


class TestMicroMeshIntegration(unittest.TestCase):
    def setUp(self):
        self.auth = AuthService()
        self.inventory = InventoryService()
        self.billing = BillingService()
        self.gateway = ApiGateway(
            auth_svc=self.auth,
            inventory_svc=self.inventory,
            billing_svc=self.billing,
        )

    def test_direct_auth_service(self):
        """Verify AuthService independently works."""
        res = self.auth.authenticate_token("Bearer token-alice-123")
        self.assertTrue(res["authenticated"])
        self.assertEqual(res["user_id"], "usr-alice")
        self.assertEqual(res["tenant_id"], "tenant-corp-1")

    def test_direct_inventory_service(self):
        """Verify InventoryService independently works."""
        res = self.inventory.check_and_reserve("item-widget-1", 2, "tenant-corp-1")
        self.assertTrue(res["success"])
        self.assertEqual(res["reserved_units"], 2)

    def test_direct_billing_service(self):
        """Verify BillingService independently works with correct headers."""
        headers = {"X-Tenant-Id": "tenant-corp-1", "X-User-Id": "usr-alice"}
        res = self.billing.charge_account(headers=headers, amount=50.0, description="direct charge")
        self.assertTrue(res["success"])
        self.assertEqual(res["status_code"], 200)

    def test_end_to_end_checkout_flow(self):
        """End-to-end checkout through API Gateway across all microservices."""
        headers = {"Authorization": "Bearer token-alice-123"}
        payload = {
            "item_id": "item-widget-1",
            "quantity": 1,
            "amount": 99.99,
        }
        res = self.gateway.handle_checkout(request_headers=headers, payload=payload)

        # Fails currently because Gateway passes X-Account-Id instead of X-Tenant-Id to BillingService
        self.assertEqual(
            res["status_code"],
            200,
            f"Expected status 200 but got {res['status_code']} with error: {res.get('error')}",
        )
        self.assertIsNotNone(res["data"].get("transaction_id"))
        self.assertEqual(res["data"]["tenant_id"], "tenant-corp-1")


if __name__ == "__main__":
    unittest.main()
