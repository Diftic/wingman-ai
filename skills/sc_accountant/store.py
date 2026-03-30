"""
SC_Accountant — Persistence Layer

JSONL append-only for transactions (immutable audit trail — no corruption risk
from partial writes, and appending is atomic on most filesystems).

JSON read-modify-write for mutable entities (trade orders, budgets, sessions,
balance, opportunities, positions, credits, hauls, inventory, production runs,
assets, loans, group sessions, planned orders).

Author: Mallachi
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import TypeVar

from models import (
    AccountBalance,
    Asset,
    Budget,
    Credit,
    GroupSession,
    Haul,
    InventoryItem,
    Loan,
    Opportunity,
    PlannedOrder,
    Position,
    ProductionRun,
    TradeOrder,
    TradingSession,
    Transaction,
)

logger = logging.getLogger(__name__)

# TypeVar for generic read/write — all models implement to_dict/from_dict
T = TypeVar("T")


class AccountantStore:
    """Persistent storage for the SC_Accountant skill."""

    def __init__(self, base_dir: Path) -> None:
        self._base_dir = base_dir
        self._base_dir.mkdir(parents=True, exist_ok=True)

        self._transactions_path = base_dir / "transactions.jsonl"
        self._trade_orders_path = base_dir / "trade_orders.json"
        self._budgets_path = base_dir / "budgets.json"
        self._sessions_path = base_dir / "sessions.json"
        self._balance_path = base_dir / "balance.json"
        self._sync_cursor_path = base_dir / "sync_cursor.json"
        self._opportunities_path = base_dir / "opportunities.json"
        self._positions_path = base_dir / "positions.json"
        self._credits_path = base_dir / "credits.json"
        self._hauls_path = base_dir / "hauls.json"
        self._inventory_path = base_dir / "inventory.json"
        self._production_path = base_dir / "production_runs.json"
        self._assets_path = base_dir / "assets.json"
        self._loans_path = base_dir / "loans.json"
        self._group_sessions_path = base_dir / "group_sessions.json"
        self._planned_orders_path = base_dir / "planned_orders.json"

    # ------------------------------------------------------------------
    # Generic JSON list I/O (DRY foundation for all mutable entities)
    # ------------------------------------------------------------------

    def _read_json_list(self, path: Path, model_cls: type[T]) -> list[T]:
        """Read a JSON array file and deserialize each element via model_cls.from_dict.

        Returns an empty list if the file doesn't exist or contains invalid JSON.
        """
        if not path.exists():
            return []
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [model_cls.from_dict(d) for d in data]
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.exception("Failed to read %s: %s", path.name, exc)
            return []

    def _write_json_list(self, path: Path, items: list) -> None:
        """Serialize a list of model objects to a JSON array file."""
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump([item.to_dict() for item in items], f, indent=2)
        except OSError as exc:
            logger.exception("Failed to write %s: %s", path.name, exc)

    # ------------------------------------------------------------------
    # Transactions (JSONL append-only — immutable audit trail)
    # ------------------------------------------------------------------

    def append_transaction(self, txn: Transaction) -> None:
        """Append a single transaction to the JSONL file."""
        try:
            with open(self._transactions_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(txn.to_dict()) + "\n")
        except OSError as exc:
            logger.exception(
                "Failed to append transaction to %s: %s",
                self._transactions_path,
                exc,
            )

    def query_transactions(
        self,
        start: datetime | None = None,
        end: datetime | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        location: str | None = None,
        source: str | None = None,
        session_id: str | None = None,
        linked_asset_id: str | None = None,
        group_session_id: str | None = None,
        limit: int = 100,
    ) -> list[Transaction]:
        """Query transactions with filters. Returns most recent first."""
        entries = self._read_all_transactions()

        if start:
            start_iso = start.isoformat()
            entries = [e for e in entries if e.timestamp >= start_iso]
        if end:
            end_iso = end.isoformat()
            entries = [e for e in entries if e.timestamp < end_iso]
        if category:
            entries = [e for e in entries if e.category == category]
        if tags:
            tag_set = set(tags)
            entries = [e for e in entries if tag_set.intersection(e.tags)]
        if location:
            loc_lower = location.lower()
            entries = [e for e in entries if loc_lower in e.location.lower()]
        if source:
            entries = [e for e in entries if e.source == source]
        if session_id:
            entries = [e for e in entries if e.session_id == session_id]
        if linked_asset_id:
            entries = [e for e in entries if e.linked_asset_id == linked_asset_id]
        if group_session_id:
            entries = [e for e in entries if e.group_session_id == group_session_id]

        entries.reverse()
        return entries[:limit]

    def update_transaction(self, txn_id: str, updates: dict) -> Transaction | None:
        """Update a transaction by ID. Rewrites the JSONL file.

        Args:
            txn_id: The transaction ID to update.
            updates: Dict of field names to new values.

        Returns:
            The updated Transaction, or None if not found.
        """
        entries = self._read_all_transactions()
        updated = None
        for i, txn in enumerate(entries):
            if txn.id == txn_id:
                data = txn.to_dict()
                data.update(updates)
                entries[i] = Transaction.from_dict(data)
                updated = entries[i]
                break

        if updated is None:
            return None

        try:
            with open(self._transactions_path, "w", encoding="utf-8") as f:
                for txn in entries:
                    f.write(json.dumps(txn.to_dict()) + "\n")
        except OSError as exc:
            logger.exception("Failed to rewrite transactions file: %s", exc)

        return updated

    def delete_transaction(self, txn_id: str) -> Transaction | None:
        """Delete a transaction by ID. Rewrites the JSONL file.

        Returns:
            The deleted Transaction, or None if not found.
        """
        entries = self._read_all_transactions()
        deleted = None
        remaining = []
        for txn in entries:
            if txn.id == txn_id and deleted is None:
                deleted = txn
            else:
                remaining.append(txn)

        if deleted is None:
            return None

        try:
            with open(self._transactions_path, "w", encoding="utf-8") as f:
                for txn in remaining:
                    f.write(json.dumps(txn.to_dict()) + "\n")
        except OSError as exc:
            logger.exception("Failed to rewrite transactions file: %s", exc)

        return deleted

    def _read_all_transactions(self) -> list[Transaction]:
        """Read all transactions from the JSONL file.

        JSONL is used (not JSON) because transactions are immutable — append-only
        writes avoid read-modify-write races and survive partial writes cleanly.
        """
        if not self._transactions_path.exists():
            return []
        entries: list[Transaction] = []
        try:
            with open(self._transactions_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        entries.append(Transaction.from_dict(data))
                    except (json.JSONDecodeError, KeyError, TypeError):
                        logger.warning(
                            "Skipping malformed transaction line %d", line_num
                        )
        except OSError as exc:
            logger.exception("Failed to read transactions: %s", exc)

        return entries

    # ------------------------------------------------------------------
    # Trade Orders (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_trade_order(self, order: TradeOrder) -> None:
        """Create or update a trade order."""
        orders = self._read_json_list(self._trade_orders_path, TradeOrder)
        found = False
        for i, existing in enumerate(orders):
            if existing.id == order.id:
                orders[i] = order
                found = True
                break
        if not found:
            orders.append(order)
        self._write_json_list(self._trade_orders_path, orders)

    def query_trade_orders(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[TradeOrder]:
        """Query trade orders with optional status filter."""
        orders = self._read_json_list(self._trade_orders_path, TradeOrder)
        if status:
            orders = [o for o in orders if o.status == status]
        orders.reverse()
        return orders[:limit]

    def get_trade_order(self, order_id: str) -> TradeOrder | None:
        """Get a single trade order by ID."""
        for order in self._read_json_list(self._trade_orders_path, TradeOrder):
            if order.id == order_id:
                return order
        return None

    # ------------------------------------------------------------------
    # Budgets (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_budget(self, budget: Budget) -> None:
        """Create or update a budget."""
        budgets = self._read_json_list(self._budgets_path, Budget)
        found = False
        for i, existing in enumerate(budgets):
            if existing.id == budget.id:
                budgets[i] = budget
                found = True
                break
        if not found:
            budgets.append(budget)
        self._write_json_list(self._budgets_path, budgets)

    def get_budgets(
        self,
        period_type: str | None = None,
        category: str | None = None,
    ) -> list[Budget]:
        """Query budgets, optionally filtered."""
        budgets = self._read_json_list(self._budgets_path, Budget)
        if period_type:
            budgets = [b for b in budgets if b.period_type == period_type]
        if category:
            budgets = [b for b in budgets if b.category == category]
        return budgets

    def delete_budget(self, budget_id: str) -> bool:
        """Delete a budget by ID. Returns True if found and deleted."""
        budgets = self._read_json_list(self._budgets_path, Budget)
        original_len = len(budgets)
        budgets = [b for b in budgets if b.id != budget_id]
        if len(budgets) < original_len:
            self._write_json_list(self._budgets_path, budgets)
            return True
        return False

    # ------------------------------------------------------------------
    # Trading Sessions (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_session(self, session: TradingSession) -> None:
        """Create or update a trading session."""
        sessions = self._read_json_list(self._sessions_path, TradingSession)
        found = False
        for i, existing in enumerate(sessions):
            if existing.id == session.id:
                sessions[i] = session
                found = True
                break
        if not found:
            sessions.append(session)
        self._write_json_list(self._sessions_path, sessions)

    def get_active_session(self) -> TradingSession | None:
        """Get the currently active trading session (if any)."""
        for session in self._read_json_list(self._sessions_path, TradingSession):
            if session.ended_at is None:
                return session
        return None

    def get_session(self, session_id: str) -> TradingSession | None:
        """Get a single session by ID."""
        for session in self._read_json_list(self._sessions_path, TradingSession):
            if session.id == session_id:
                return session
        return None

    # ------------------------------------------------------------------
    # Account Balance (single JSON object — not a list)
    # ------------------------------------------------------------------

    def get_balance(self) -> AccountBalance:
        """Read the current account balance."""
        if not self._balance_path.exists():
            return AccountBalance()
        try:
            with open(self._balance_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return AccountBalance.from_dict(data)
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.exception("Failed to read balance: %s", exc)
            return AccountBalance()

    def save_balance(self, balance: AccountBalance) -> None:
        """Write the current account balance."""
        try:
            with open(self._balance_path, "w", encoding="utf-8") as f:
                json.dump(balance.to_dict(), f, indent=2)
        except OSError as exc:
            logger.exception("Failed to write balance: %s", exc)

    # ------------------------------------------------------------------
    # Sync Cursor (tracks position in SC_LogReader ledger)
    # ------------------------------------------------------------------

    def get_sync_cursor(self) -> int:
        """Get the last-synced line number in the SC_LogReader ledger."""
        if not self._sync_cursor_path.exists():
            return 0
        try:
            with open(self._sync_cursor_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("last_line", 0)
        except (OSError, json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.exception("Failed to read sync cursor: %s", exc)
            return 0

    def save_sync_cursor(self, last_line: int) -> None:
        """Save the sync cursor position."""
        try:
            with open(self._sync_cursor_path, "w", encoding="utf-8") as f:
                json.dump({"last_line": last_line}, f)
        except OSError as exc:
            logger.exception("Failed to write sync cursor: %s", exc)

    # ------------------------------------------------------------------
    # Opportunities (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_opportunity(self, opp: Opportunity) -> None:
        """Create or update a single opportunity."""
        opps = self._read_json_list(self._opportunities_path, Opportunity)
        found = False
        for i, existing in enumerate(opps):
            if existing.id == opp.id:
                opps[i] = opp
                found = True
                break
        if not found:
            opps.append(opp)
        self._write_json_list(self._opportunities_path, opps)

    def bulk_save_opportunities(self, new_opps: list[Opportunity]) -> None:
        """Save multiple new opportunities in a single write."""
        opps = self._read_json_list(self._opportunities_path, Opportunity)
        existing_ids = {o.id for o in opps}
        for opp in new_opps:
            if opp.id in existing_ids:
                # Update existing
                for i, existing in enumerate(opps):
                    if existing.id == opp.id:
                        opps[i] = opp
                        break
            else:
                opps.append(opp)
        self._write_json_list(self._opportunities_path, opps)

    def query_opportunities(
        self,
        status: str | None = None,
        commodity_name: str | None = None,
        limit: int = 50,
    ) -> list[Opportunity]:
        """Query opportunities with optional filters."""
        opps = self._read_json_list(self._opportunities_path, Opportunity)
        if status:
            opps = [o for o in opps if o.status == status]
        if commodity_name:
            name_lower = commodity_name.lower()
            opps = [o for o in opps if name_lower in o.commodity_name.lower()]
        # Sort by score descending for available; by created_at descending otherwise
        opps.sort(
            key=lambda o: o.score if o.status == "available" else 0,
            reverse=True,
        )
        return opps[:limit]

    def get_opportunity(self, opp_id: str) -> Opportunity | None:
        """Get a single opportunity by ID."""
        for opp in self._read_json_list(self._opportunities_path, Opportunity):
            if opp.id == opp_id:
                return opp
        return None

    def delete_expired_opportunities(self, before: str) -> int:
        """Remove expired/dismissed opportunities older than a timestamp."""
        opps = self._read_json_list(self._opportunities_path, Opportunity)
        original_len = len(opps)
        opps = [
            o
            for o in opps
            if o.status not in ("expired", "dismissed") or o.created_at >= before
        ]
        removed = original_len - len(opps)
        if removed > 0:
            self._write_json_list(self._opportunities_path, opps)
        return removed

    # ------------------------------------------------------------------
    # Positions (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_position(self, pos: Position) -> None:
        """Create or update a single position."""
        positions = self._read_json_list(self._positions_path, Position)
        found = False
        for i, existing in enumerate(positions):
            if existing.id == pos.id:
                positions[i] = pos
                found = True
                break
        if not found:
            positions.append(pos)
        self._write_json_list(self._positions_path, positions)

    def query_positions(
        self,
        status: str | None = None,
        commodity_name: str | None = None,
        limit: int = 50,
    ) -> list[Position]:
        """Query positions with optional filters."""
        positions = self._read_json_list(self._positions_path, Position)
        if status:
            positions = [p for p in positions if p.status == status]
        if commodity_name:
            name_lower = commodity_name.lower()
            positions = [p for p in positions if name_lower in p.commodity_name.lower()]
        # Open positions sorted by opened_at ASC, closed by closed_at DESC
        positions.sort(
            key=lambda p: p.closed_at or p.opened_at,
            reverse=True,
        )
        return positions[:limit]

    def get_position(self, pos_id: str) -> Position | None:
        """Get a single position by ID."""
        for pos in self._read_json_list(self._positions_path, Position):
            if pos.id == pos_id:
                return pos
        return None

    # ------------------------------------------------------------------
    # Credits (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_credit(self, credit: Credit) -> None:
        """Create or update a credit record."""
        credits = self._read_json_list(self._credits_path, Credit)
        found = False
        for i, existing in enumerate(credits):
            if existing.id == credit.id:
                credits[i] = credit
                found = True
                break
        if not found:
            credits.append(credit)
        self._write_json_list(self._credits_path, credits)

    def query_credits(
        self,
        credit_type: str | None = None,
        status: str | None = None,
        counterparty: str | None = None,
        limit: int = 50,
    ) -> list[Credit]:
        """Query credits with optional filters."""
        credits = self._read_json_list(self._credits_path, Credit)
        if credit_type:
            credits = [c for c in credits if c.credit_type == credit_type]
        if status:
            credits = [c for c in credits if c.status == status]
        if counterparty:
            cp_lower = counterparty.lower()
            credits = [c for c in credits if cp_lower in c.counterparty.lower()]
        # Sort by created_at descending (most recent first)
        credits.sort(key=lambda c: c.created_at, reverse=True)
        return credits[:limit]

    def get_credit(self, credit_id: str) -> Credit | None:
        """Get a single credit by ID."""
        for credit in self._read_json_list(self._credits_path, Credit):
            if credit.id == credit_id:
                return credit
        return None

    # ------------------------------------------------------------------
    # Hauls (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_haul(self, haul: Haul) -> None:
        """Create or update a haul record."""
        hauls = self._read_json_list(self._hauls_path, Haul)
        found = False
        for i, existing in enumerate(hauls):
            if existing.id == haul.id:
                hauls[i] = haul
                found = True
                break
        if not found:
            hauls.append(haul)
        self._write_json_list(self._hauls_path, hauls)

    def query_hauls(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[Haul]:
        """Query hauls with optional status filter."""
        hauls = self._read_json_list(self._hauls_path, Haul)
        if status:
            hauls = [h for h in hauls if h.status == status]
        # Sort by started_at descending (most recent first)
        hauls.sort(key=lambda h: h.started_at, reverse=True)
        return hauls[:limit]

    def get_haul(self, haul_id: str) -> Haul | None:
        """Get a single haul by ID."""
        for haul in self._read_json_list(self._hauls_path, Haul):
            if haul.id == haul_id:
                return haul
        return None

    # ------------------------------------------------------------------
    # Inventory (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_inventory_item(self, item: InventoryItem) -> None:
        """Create or update an inventory item."""
        items = self._read_json_list(self._inventory_path, InventoryItem)
        found = False
        for i, existing in enumerate(items):
            if existing.id == item.id:
                items[i] = item
                found = True
                break
        if not found:
            items.append(item)
        self._write_json_list(self._inventory_path, items)

    def query_inventory(
        self,
        item_name: str | None = None,
        location: str | None = None,
        limit: int = 50,
    ) -> list[InventoryItem]:
        """Query inventory items with optional filters."""
        items = self._read_json_list(self._inventory_path, InventoryItem)
        if item_name:
            name_lower = item_name.lower()
            items = [i for i in items if name_lower in i.item_name.lower()]
        if location:
            loc_lower = location.lower()
            items = [i for i in items if loc_lower in i.location.lower()]
        # Sort by reported_at descending
        items.sort(key=lambda i: i.reported_at, reverse=True)
        return items[:limit]

    def find_inventory_item(
        self, item_name: str, location: str
    ) -> InventoryItem | None:
        """Find an existing inventory item by exact name and location match."""
        for item in self._read_json_list(self._inventory_path, InventoryItem):
            if (
                item.item_name.lower() == item_name.lower()
                and item.location.lower() == location.lower()
            ):
                return item
        return None

    # ------------------------------------------------------------------
    # Production Runs (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_production_run(self, run: ProductionRun) -> None:
        """Create or update a production run."""
        runs = self._read_json_list(self._production_path, ProductionRun)
        found = False
        for i, existing in enumerate(runs):
            if existing.id == run.id:
                runs[i] = run
                found = True
                break
        if not found:
            runs.append(run)
        self._write_json_list(self._production_path, runs)

    def query_production_runs(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ProductionRun]:
        """Query production runs with optional status filter."""
        runs = self._read_json_list(self._production_path, ProductionRun)
        if status:
            runs = [r for r in runs if r.status == status]
        # Sort by started_at descending
        runs.sort(key=lambda r: r.started_at, reverse=True)
        return runs[:limit]

    # ------------------------------------------------------------------
    # Assets (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_asset(self, asset: Asset) -> None:
        """Create or update an asset."""
        assets = self._read_json_list(self._assets_path, Asset)
        found = False
        for i, existing in enumerate(assets):
            if existing.id == asset.id:
                assets[i] = asset
                found = True
                break
        if not found:
            assets.append(asset)
        self._write_json_list(self._assets_path, assets)

    def query_assets(
        self,
        asset_type: str | None = None,
        status: str | None = None,
        parent_asset_id: str | None = None,
        limit: int = 50,
    ) -> list[Asset]:
        """Query assets with optional filters."""
        assets = self._read_json_list(self._assets_path, Asset)
        if asset_type:
            assets = [a for a in assets if a.asset_type == asset_type]
        if status:
            assets = [a for a in assets if a.status == status]
        if parent_asset_id:
            assets = [a for a in assets if a.parent_asset_id == parent_asset_id]
        # Active assets first, then by created_at descending
        assets.sort(
            key=lambda a: (a.status != "active", a.created_at),
            reverse=True,
        )
        return assets[:limit]

    def get_asset(self, asset_id: str) -> Asset | None:
        """Get a single asset by ID."""
        for asset in self._read_json_list(self._assets_path, Asset):
            if asset.id == asset_id:
                return asset
        return None

    def delete_asset(self, asset_id: str) -> Asset | None:
        """Delete an asset by ID. Returns the deleted asset or None."""
        assets = self._read_json_list(self._assets_path, Asset)
        for i, asset in enumerate(assets):
            if asset.id == asset_id:
                deleted = assets.pop(i)
                self._write_json_list(self._assets_path, assets)
                return deleted
        return None

    # ------------------------------------------------------------------
    # Loans (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_loan(self, loan: Loan) -> None:
        """Create or update a loan record."""
        loans = self._read_json_list(self._loans_path, Loan)
        found = False
        for i, existing in enumerate(loans):
            if existing.id == loan.id:
                loans[i] = loan
                found = True
                break
        if not found:
            loans.append(loan)
        self._write_json_list(self._loans_path, loans)

    def query_loans(
        self,
        loan_type: str | None = None,
        status: str | None = None,
        counterparty: str | None = None,
        limit: int = 50,
    ) -> list[Loan]:
        """Query loans with optional filters."""
        loans = self._read_json_list(self._loans_path, Loan)
        if loan_type:
            loans = [ln for ln in loans if ln.loan_type == loan_type]
        if status:
            loans = [ln for ln in loans if ln.status == status]
        if counterparty:
            cp_lower = counterparty.lower()
            loans = [ln for ln in loans if cp_lower in ln.counterparty.lower()]
        # Sort by created_at descending (most recent first)
        loans.sort(key=lambda ln: ln.created_at, reverse=True)
        return loans[:limit]

    def get_loan(self, loan_id: str) -> Loan | None:
        """Get a single loan by ID."""
        for loan in self._read_json_list(self._loans_path, Loan):
            if loan.id == loan_id:
                return loan
        return None

    # ------------------------------------------------------------------
    # Group Sessions (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_group_session(self, gs: GroupSession) -> None:
        """Create or update a group session."""
        sessions = self._read_json_list(self._group_sessions_path, GroupSession)
        found = False
        for i, existing in enumerate(sessions):
            if existing.id == gs.id:
                sessions[i] = gs
                found = True
                break
        if not found:
            sessions.append(gs)
        self._write_json_list(self._group_sessions_path, sessions)

    def get_active_group_session(self) -> GroupSession | None:
        """Get the currently active group session (if any)."""
        for gs in self._read_json_list(self._group_sessions_path, GroupSession):
            if gs.status == "active":
                return gs
        return None

    def get_latest_group_session(self) -> GroupSession | None:
        """Get the most recent group session (active or ended)."""
        sessions = self._read_json_list(self._group_sessions_path, GroupSession)
        if not sessions:
            return None
        sessions.sort(key=lambda gs: gs.started_at, reverse=True)
        return sessions[0]

    def get_group_session(self, gs_id: str) -> GroupSession | None:
        """Get a single group session by ID."""
        for gs in self._read_json_list(self._group_sessions_path, GroupSession):
            if gs.id == gs_id:
                return gs
        return None

    def query_group_sessions(
        self,
        status: str | None = None,
        limit: int = 50,
    ) -> list[GroupSession]:
        """Query group sessions with optional status filter."""
        sessions = self._read_json_list(self._group_sessions_path, GroupSession)
        if status:
            sessions = [gs for gs in sessions if gs.status == status]
        sessions.sort(key=lambda gs: gs.started_at, reverse=True)
        return sessions[:limit]

    # ------------------------------------------------------------------
    # Planned Orders (JSON list, read-modify-write)
    # ------------------------------------------------------------------

    def save_planned_order(self, order: PlannedOrder) -> None:
        """Create or update a planned order."""
        orders = self._read_json_list(self._planned_orders_path, PlannedOrder)
        found = False
        for i, existing in enumerate(orders):
            if existing.id == order.id:
                orders[i] = order
                found = True
                break
        if not found:
            orders.append(order)
        self._write_json_list(self._planned_orders_path, orders)

    def query_planned_orders(
        self,
        order_type: str | None = None,
        status: str | None = None,
        status_in: list[str] | None = None,
        item_name: str | None = None,
        limit: int = 100,
    ) -> list[PlannedOrder]:
        """Query planned orders with optional filters."""
        orders = self._read_json_list(self._planned_orders_path, PlannedOrder)
        if order_type:
            orders = [o for o in orders if o.order_type == order_type]
        if status:
            orders = [o for o in orders if o.status == status]
        if status_in:
            orders = [o for o in orders if o.status in status_in]
        if item_name:
            name_lower = item_name.lower()
            orders = [o for o in orders if name_lower in o.item_name.lower()]
        orders.sort(key=lambda o: o.created_at, reverse=True)
        return orders[:limit]

    def get_planned_order(self, order_id: str) -> PlannedOrder | None:
        """Get a single planned order by ID."""
        for order in self._read_json_list(self._planned_orders_path, PlannedOrder):
            if order.id == order_id:
                return order
        return None

    def delete_planned_order(self, order_id: str) -> PlannedOrder | None:
        """Delete a planned order by ID. Returns the deleted order or None."""
        orders = self._read_json_list(self._planned_orders_path, PlannedOrder)
        for i, order in enumerate(orders):
            if order.id == order_id:
                deleted = orders.pop(i)
                self._write_json_list(self._planned_orders_path, orders)
                return deleted
        return None
