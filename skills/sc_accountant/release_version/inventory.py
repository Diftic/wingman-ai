"""
SC_Accountant — Inventory Manager (Stub)

Manual warehouse inventory tracking. Players report their inventory
via voice commands. This module is intentionally minimal — it will
be expanded once CIG ships the Star Citizen inventory rework.

Author: Mallachi
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

from models import InventoryItem
from store import AccountantStore

logger = logging.getLogger(__name__)


class InventoryManager:
    """Manually tracks inventory items at locations.

    Stub implementation — will be expanded when CIG ships
    the Star Citizen inventory system rework.
    """

    def __init__(self, store: AccountantStore) -> None:
        """Initialize with shared store.

        Args:
            store: AccountantStore for persistence.
        """
        self._store = store

    # ------------------------------------------------------------------
    # Tool: Report Inventory
    # ------------------------------------------------------------------

    def report_inventory(
        self,
        item_name: str,
        quantity: float,
        location: str,
        quantity_unit: str = "scu",
        estimated_value: float = 0.0,
        notes: str = "",
    ) -> dict:
        """Report or update inventory at a location.

        If an item with the same name already exists at that location,
        its quantity is replaced (not added) with the new value.

        Args:
            item_name: Name of the item or commodity.
            quantity: Current quantity at that location.
            location: Where the inventory is stored.
            quantity_unit: Unit of measurement (default 'scu').
            estimated_value: Estimated total value in aUEC.
            notes: Additional notes.

        Returns:
            Confirmation dict with inventory details.
        """
        if quantity < 0:
            return {"error": "Quantity cannot be negative."}

        now = datetime.now(timezone.utc).isoformat()

        # Check for existing item at same location (upsert)
        existing = self._store.find_inventory_item(item_name, location)

        if existing:
            old_qty = existing.quantity
            existing.quantity = quantity
            existing.quantity_unit = quantity_unit
            existing.reported_at = now
            if estimated_value > 0:
                existing.estimated_value = estimated_value
            if notes:
                existing.notes = notes
            self._store.save_inventory_item(existing)

            logger.info(
                "Updated inventory %s: %s at %s (%.1f → %.1f %s)",
                existing.id[:8],
                item_name,
                location,
                old_qty,
                quantity,
                quantity_unit,
            )

            return {
                "status": "updated",
                "inventory_id": existing.id[:8],
                "item_name": item_name,
                "quantity": quantity,
                "quantity_unit": quantity_unit,
                "location": location,
                "previous_quantity": old_qty,
            }

        # Create new inventory entry
        item = InventoryItem(
            id=str(uuid.uuid4()),
            reported_at=now,
            item_name=item_name,
            quantity=quantity,
            quantity_unit=quantity_unit,
            location=location,
            estimated_value=estimated_value,
            notes=notes,
        )

        self._store.save_inventory_item(item)

        logger.info(
            "Reported inventory %s: %.1f %s of %s at %s",
            item.id[:8],
            quantity,
            quantity_unit,
            item_name,
            location,
        )

        return {
            "status": "created",
            "inventory_id": item.id[:8],
            "item_name": item_name,
            "quantity": quantity,
            "quantity_unit": quantity_unit,
            "location": location,
        }

    # ------------------------------------------------------------------
    # Tool: Get Inventory
    # ------------------------------------------------------------------

    def get_inventory(
        self,
        item_name: str = "",
        location: str = "",
        limit: int = 30,
    ) -> list[dict]:
        """List inventory items with optional filters.

        Args:
            item_name: Filter by item name (partial match).
            location: Filter by location (partial match).
            limit: Maximum results.

        Returns:
            List of inventory item dicts.
        """
        query_name = item_name if item_name else None
        query_loc = location if location else None

        items = self._store.query_inventory(
            item_name=query_name,
            location=query_loc,
            limit=limit,
        )

        return [self._format_item(i) for i in items]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _format_item(self, item: InventoryItem) -> dict:
        """Format an inventory item for tool response."""
        result = {
            "id": item.id[:8],
            "item_name": item.item_name,
            "quantity": item.quantity,
            "quantity_unit": item.quantity_unit,
            "location": item.location,
            "reported_at": item.reported_at,
        }

        if item.estimated_value > 0:
            result["estimated_value"] = round(item.estimated_value, 2)
        if item.notes:
            result["notes"] = item.notes

        return result
