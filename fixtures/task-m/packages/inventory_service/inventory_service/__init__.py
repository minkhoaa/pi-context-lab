from typing import Dict, Any, Optional


class InventoryService:
    """Manages stock items and inventory reservations."""

    def __init__(self):
        self.stock = {
            "item-widget-1": 100,
            "item-widget-2": 5,
            "item-out-of-stock": 0,
        }

    def check_and_reserve(self, item_id: str, quantity: int, tenant_id: str) -> Dict[str, Any]:
        """Checks and reserves inventory for a tenant."""
        if not tenant_id:
            return {"success": False, "error": "Missing required tenant identification"}

        available = self.stock.get(item_id, 0)
        if available < quantity:
            return {"success": False, "error": f"Insufficient stock for {item_id}"}

        self.stock[item_id] -= quantity
        return {"success": True, "reserved_units": quantity, "item_id": item_id}
