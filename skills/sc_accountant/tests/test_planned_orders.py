"""Tests for planned order (purchase/sales order) functionality.

Covers: PlannedOrder model, store CRUD, fulfillment matching logic,
sales order validation, and partial fulfillment progression.

Author: Mallachi
"""

from __future__ import annotations

import os
import sys


# Add skill directory to sys.path for local imports
_skill_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _skill_dir not in sys.path:
    sys.path.insert(0, _skill_dir)

_tests_dir = os.path.dirname(os.path.abspath(__file__))
if _tests_dir not in sys.path:
    sys.path.insert(0, _tests_dir)

from factories import _ts, make_transaction  # noqa: E402
from models import PlannedOrder  # noqa: E402
from store import AccountantStore  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_planned_order(
    *,
    id: str = "po1",
    order_type: str = "purchase",
    status: str = "open",
    item_name: str = "Laranite",
    ordered_quantity: float = 10.0,
    fulfilled_quantity: float = 0.0,
    quantity_unit: str = "scu",
    target_price_per_unit: float = 100.0,
    target_location: str = "",
    linked_asset_id: str | None = None,
    fulfillments: list | None = None,
    notes: str = "",
) -> PlannedOrder:
    """Factory for PlannedOrder instances."""
    return PlannedOrder(
        id=id,
        created_at=_ts(),
        order_type=order_type,
        status=status,
        item_name=item_name,
        ordered_quantity=ordered_quantity,
        fulfilled_quantity=fulfilled_quantity,
        quantity_unit=quantity_unit,
        target_price_per_unit=target_price_per_unit,
        target_location=target_location,
        linked_asset_id=linked_asset_id,
        fulfillments=fulfillments or [],
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Model Tests
# ---------------------------------------------------------------------------


class TestPlannedOrderModel:
    def test_round_trip(self):
        order = make_planned_order(item_name="Prospector", ordered_quantity=4)
        data = order.to_dict()
        restored = PlannedOrder.from_dict(data)
        assert restored.item_name == "Prospector"
        assert restored.ordered_quantity == 4
        assert restored.fulfilled_quantity == 0
        assert restored.status == "open"

    def test_missing_new_fields_default(self):
        minimal = {
            "id": "po-min",
            "created_at": _ts(),
            "order_type": "purchase",
            "status": "open",
            "item_name": "Gold",
            "ordered_quantity": 5,
        }
        order = PlannedOrder.from_dict(minimal)
        assert order.fulfilled_quantity == 0.0
        assert order.quantity_unit == "units"
        assert order.fulfillments == []
        assert order.fulfilled_at is None
        assert order.cancelled_at is None


# ---------------------------------------------------------------------------
# Store Tests
# ---------------------------------------------------------------------------


class TestPlannedOrderStore:
    def test_save_and_get(self, store):
        order = make_planned_order(id="po-store-1")
        store.save_planned_order(order)
        retrieved = store.get_planned_order("po-store-1")
        assert retrieved is not None
        assert retrieved.item_name == "Laranite"

    def test_get_nonexistent(self, store):
        assert store.get_planned_order("nope") is None

    def test_query_by_type(self, store):
        store.save_planned_order(make_planned_order(id="po1", order_type="purchase"))
        store.save_planned_order(make_planned_order(id="po2", order_type="sale"))
        purchases = store.query_planned_orders(order_type="purchase")
        assert len(purchases) == 1
        assert purchases[0].id == "po1"

    def test_query_by_status(self, store):
        store.save_planned_order(make_planned_order(id="po1", status="open"))
        store.save_planned_order(make_planned_order(id="po2", status="fulfilled"))
        open_orders = store.query_planned_orders(status="open")
        assert len(open_orders) == 1
        assert open_orders[0].id == "po1"

    def test_query_status_in(self, store):
        store.save_planned_order(make_planned_order(id="po1", status="open"))
        store.save_planned_order(make_planned_order(id="po2", status="partial"))
        store.save_planned_order(make_planned_order(id="po3", status="fulfilled"))
        active = store.query_planned_orders(status_in=["open", "partial"])
        assert len(active) == 2

    def test_query_by_item_name(self, store):
        store.save_planned_order(make_planned_order(id="po1", item_name="Laranite"))
        store.save_planned_order(make_planned_order(id="po2", item_name="Gold"))
        results = store.query_planned_orders(item_name="lara")
        assert len(results) == 1
        assert results[0].item_name == "Laranite"

    def test_update_existing(self, store):
        order = make_planned_order(id="po-update")
        store.save_planned_order(order)
        order.fulfilled_quantity = 5.0
        order.status = "partial"
        store.save_planned_order(order)
        updated = store.get_planned_order("po-update")
        assert updated.fulfilled_quantity == 5.0
        assert updated.status == "partial"

    def test_delete(self, store):
        order = make_planned_order(id="po-del")
        store.save_planned_order(order)
        deleted = store.delete_planned_order("po-del")
        assert deleted is not None
        assert deleted.item_name == "Laranite"
        assert store.get_planned_order("po-del") is None

    def test_delete_nonexistent(self, store):
        assert store.delete_planned_order("nope") is None

    def test_persistence_across_instances(self, store):
        order = make_planned_order(id="po-persist")
        store.save_planned_order(order)
        store2 = AccountantStore(store._base_dir)
        retrieved = store2.get_planned_order("po-persist")
        assert retrieved is not None
        assert retrieved.item_name == "Laranite"


# ---------------------------------------------------------------------------
# Fulfillment Matching Tests (using store directly)
# ---------------------------------------------------------------------------


class TestFulfillmentLogic:
    """Test the fulfillment matching logic by simulating what main.py does."""

    def _fuzzy_match(self, order_name: str, txn_name: str) -> bool:
        """Mirror of SC_Accountant._fuzzy_match."""
        if not order_name or not txn_name:
            return False
        a = order_name.lower().strip()
        b = txn_name.lower().strip()
        return a in b or b in a

    def _check_fulfillment(self, store, txn):
        """Simplified fulfillment logic matching main.py."""
        purchase_cats = {
            "commodity_purchase",
            "item_purchase",
            "player_trade_buy",
            "ship_purchase",
            "component_purchase",
            "capital_investment",
        }
        sale_cats = {
            "commodity_sale",
            "item_sale",
            "player_trade_sell",
            "salvage_income",
        }

        if txn.category in purchase_cats:
            order_type = "purchase"
        elif txn.category in sale_cats:
            order_type = "sale"
        else:
            return

        orders = store.query_planned_orders(
            order_type=order_type, status_in=["open", "partial"]
        )

        item_name = txn.item_name or txn.description
        txn_qty = txn.quantity if txn.quantity and txn.quantity > 0 else 1.0

        for order in orders:
            if not self._fuzzy_match(order.item_name, item_name):
                continue
            remaining = order.ordered_quantity - order.fulfilled_quantity
            if remaining <= 0:
                continue
            fulfill_qty = min(txn_qty, remaining)
            order.fulfilled_quantity += fulfill_qty
            order.fulfillments.append(
                {
                    "transaction_id": txn.id,
                    "quantity": fulfill_qty,
                    "amount": txn.amount,
                    "date": txn.timestamp,
                }
            )
            if order.fulfilled_quantity >= order.ordered_quantity:
                order.status = "fulfilled"
            else:
                order.status = "partial"
            store.save_planned_order(order)
            break

    def test_full_fulfillment(self, store):
        """Buying exact quantity fulfills the order."""
        store.save_planned_order(
            make_planned_order(id="po-full", ordered_quantity=10, item_name="Laranite")
        )
        txn = make_transaction(
            id="t1",
            category="commodity_purchase",
            transaction_type="expense",
            amount=1000,
            description="Laranite",
        )
        txn.item_name = "Laranite"
        txn.quantity = 10.0
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("po-full")
        assert order.status == "fulfilled"
        assert order.fulfilled_quantity == 10.0
        assert len(order.fulfillments) == 1

    def test_partial_fulfillment(self, store):
        """Buying less than ordered leaves order as partial."""
        store.save_planned_order(
            make_planned_order(id="po-part", ordered_quantity=10, item_name="Gold")
        )
        txn = make_transaction(
            id="t1",
            category="commodity_purchase",
            transaction_type="expense",
            amount=500,
            description="Gold",
        )
        txn.item_name = "Gold"
        txn.quantity = 3.0
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("po-part")
        assert order.status == "partial"
        assert order.fulfilled_quantity == 3.0

    def test_multiple_partial_fulfillments(self, store):
        """Multiple purchases incrementally fulfill the order."""
        store.save_planned_order(
            make_planned_order(
                id="po-multi", ordered_quantity=4, item_name="Prospector"
            )
        )
        for i in range(1, 4):
            txn = make_transaction(
                id=f"t{i}",
                category="ship_purchase",
                transaction_type="expense",
                amount=2_100_000,
                description="Prospector",
            )
            txn.item_name = "Prospector"
            txn.quantity = 1.0
            self._check_fulfillment(store, txn)

        order = store.get_planned_order("po-multi")
        assert order.status == "partial"
        assert order.fulfilled_quantity == 3.0
        assert len(order.fulfillments) == 3

        # Fourth purchase completes it
        txn4 = make_transaction(
            id="t4",
            category="ship_purchase",
            transaction_type="expense",
            amount=2_100_000,
            description="Prospector",
        )
        txn4.item_name = "Prospector"
        txn4.quantity = 1.0
        self._check_fulfillment(store, txn4)
        order = store.get_planned_order("po-multi")
        assert order.status == "fulfilled"
        assert order.fulfilled_quantity == 4.0

    def test_over_fulfillment_capped(self, store):
        """Buying more than ordered caps at the ordered quantity."""
        store.save_planned_order(
            make_planned_order(id="po-cap", ordered_quantity=4, item_name="Laranite")
        )
        txn = make_transaction(
            id="t1",
            category="commodity_purchase",
            transaction_type="expense",
            amount=5000,
            description="Laranite",
        )
        txn.item_name = "Laranite"
        txn.quantity = 10.0  # More than ordered
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("po-cap")
        assert order.fulfilled_quantity == 4.0
        assert order.status == "fulfilled"

    def test_fuzzy_match(self, store):
        """Fuzzy matching: 'Quantanium' matches 'Quantanium (Raw)'."""
        store.save_planned_order(
            make_planned_order(
                id="po-fuzzy", ordered_quantity=5, item_name="Quantanium"
            )
        )
        txn = make_transaction(
            id="t1",
            category="commodity_purchase",
            transaction_type="expense",
            amount=800,
            description="Quantanium (Raw)",
        )
        txn.item_name = "Quantanium (Raw)"
        txn.quantity = 5.0
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("po-fuzzy")
        assert order.status == "fulfilled"

    def test_no_match_for_wrong_item(self, store):
        """Non-matching items don't trigger fulfillment."""
        store.save_planned_order(
            make_planned_order(id="po-no", ordered_quantity=5, item_name="Laranite")
        )
        txn = make_transaction(
            id="t1",
            category="commodity_purchase",
            transaction_type="expense",
            amount=500,
            description="Gold",
        )
        txn.item_name = "Gold"
        txn.quantity = 5.0
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("po-no")
        assert order.status == "open"
        assert order.fulfilled_quantity == 0.0

    def test_sale_order_fulfillment(self, store):
        """Sales fulfill sale orders."""
        store.save_planned_order(
            make_planned_order(
                id="so-1",
                order_type="sale",
                ordered_quantity=5,
                item_name="Laranite",
            )
        )
        txn = make_transaction(
            id="t1",
            category="commodity_sale",
            transaction_type="income",
            amount=1500,
            description="Laranite",
        )
        txn.item_name = "Laranite"
        txn.quantity = 5.0
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("so-1")
        assert order.status == "fulfilled"

    def test_no_qty_defaults_to_one(self, store):
        """Transaction without quantity defaults to 1 unit fulfillment."""
        store.save_planned_order(
            make_planned_order(id="po-noqty", ordered_quantity=3, item_name="Helmet")
        )
        txn = make_transaction(
            id="t1",
            category="item_purchase",
            transaction_type="expense",
            amount=200,
            description="Helmet",
        )
        txn.item_name = "Helmet"
        # quantity is None by default
        self._check_fulfillment(store, txn)
        order = store.get_planned_order("po-noqty")
        assert order.fulfilled_quantity == 1.0
        assert order.status == "partial"
