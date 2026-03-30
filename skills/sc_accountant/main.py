"""
SC_Accountant — Company Accountant for Star Citizen

Full business accounting system for Star Citizen traders. Tracks income,
expenses, trade orders, budgets, trading sessions, investment positions,
trade opportunities (futures), and standalone accounting dashboard.

Sibling skill integrations (all optional):
  - SC_LogReader: auto-captures trades from game log
  - UEXCorp: auto-populates ship purchase prices

Author: Mallachi
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from api.interface import (
    SettingsConfig,
    SkillConfig,
    WingmanInitializationError,
)
from services.benchmark import Benchmark
from skills.skill_base import Skill, tool

# Add skill directory to sys.path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from assets import AssetManager  # noqa: E402
from credits import CreditManager  # noqa: E402
from futures import FuturesManager  # noqa: E402
from guid_resolver import GuidResolver  # noqa: E402
from hauling import HaulManager  # noqa: E402
from inventory import InventoryManager  # noqa: E402
from market_data import MarketData  # noqa: E402
from models import (  # noqa: E402
    ALL_CATEGORIES,
    CATEGORY_ACTIVITY,
    CATEGORY_LABELS,
    EXPENSE_CATEGORIES,
    INCOME_CATEGORIES,
    Activity,
    Budget,
    GroupSession,
    PlannedOrder,
    TradeOrder,
    TradingSession,
    Transaction,
)
from planning import PlanningEngine  # noqa: E402
from positions import PositionManager  # noqa: E402
from production import ProductionManager  # noqa: E402
from reports import generate_budget_vs_actual, generate_pnl  # noqa: E402
from statements import (  # noqa: E402
    generate_balance_sheet,
    generate_cash_flow,
    generate_income_statement,
)
from store import AccountantStore  # noqa: E402

if TYPE_CHECKING:
    from wingmen.open_ai_wingman import OpenAiWingman

logger = logging.getLogger(__name__)


class SC_Accountant(Skill):
    def __init__(
        self,
        config: SkillConfig,
        settings: SettingsConfig,
        wingman: "OpenAiWingman",
    ) -> None:
        super().__init__(config=config, settings=settings, wingman=wingman)
        self._store: AccountantStore | None = None
        self._guid_resolver: GuidResolver | None = None
        self._market: MarketData | None = None
        self._futures: FuturesManager | None = None
        self._positions: PositionManager | None = None
        self._credits: CreditManager | None = None
        self._hauling: HaulManager | None = None
        self._inventory: InventoryManager | None = None
        self._production: ProductionManager | None = None
        self._assets: AssetManager | None = None
        self._planning: PlanningEngine | None = None
        self._ui_server = None
        self._ui_window = None
        self._sync_active = False
        self._market_refresh_active = False
        self._last_announced_location: str | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def validate(self) -> list[WingmanInitializationError]:
        errors = await super().validate()
        self.retrieve_custom_property_value("auto_sync_interval", errors)
        self.retrieve_custom_property_value("default_currency_format", errors)
        self.retrieve_custom_property_value("complexity_layer", errors)
        self.retrieve_custom_property_value("announce_trade_opportunities", errors)
        self.retrieve_custom_property_value("futures_min_profit", errors)
        return errors

    async def prepare(self) -> None:
        await super().prepare()

        base_dir = Path(self.get_generated_files_dir())
        self._store = AccountantStore(base_dir)
        self._guid_resolver = GuidResolver(base_dir / "guid_map.json")

        # Initialize market data cache
        self._market = MarketData(base_dir / "market_cache.db")
        self._market.open()

        # Initialize domain managers
        self._futures = FuturesManager(self._store, self._market)
        self._positions = PositionManager(self._store, self._market)
        self._credits = CreditManager(self._store)
        self._hauling = HaulManager(self._store)
        self._inventory = InventoryManager(self._store)
        self._production = ProductionManager(self._store)
        self._assets = AssetManager(self._store, self._format_auec)
        self._planning = PlanningEngine(self._store, self._format_auec)

        # Initialize standalone accounting UI (optional — requires fastapi extras)
        try:
            from accountant_ui.app import AccountantServer  # noqa: E402
            from accountant_ui.window import AccountantWindow  # noqa: E402

            self._ui_server = AccountantServer(
                store=self._store,
                format_fn=self._format_auec,
            )
            self._ui_server.set_managers(
                positions=self._positions,
                futures=self._futures,
                assets=self._assets,
                credits=self._credits,
                market=self._market,
                get_player_location=self._get_player_location,
            )
            self._ui_server.start()

            self._ui_window = AccountantWindow(url=self._ui_server.url)
        except ImportError:
            logger.warning(
                "Accounting dashboard unavailable — missing dependencies "
                "(fastapi[standard] or pywebview). Core accounting tools still work."
            )

        # Background: initial market data load (non-blocking)
        self._market_refresh_active = True
        self.threaded_execution(self._market_refresh_loop)

        # Start background sync timer
        sync_interval = self._get_sync_interval()
        if sync_interval > 0:
            self._sync_active = True
            self.threaded_execution(self._sync_loop)

    async def unload(self) -> None:
        self._sync_active = False
        self._market_refresh_active = False
        if self._ui_window:
            try:
                self._ui_window.close()
            except OSError:
                logger.debug("Failed to close accounting window")
            self._ui_window = None
        if self._ui_server:
            try:
                self._ui_server.stop()
            except OSError:
                logger.debug("Failed to stop accounting server")
            self._ui_server = None
        if self._market:
            self._market.close()
            self._market = None
        self._futures = None
        self._positions = None
        self._credits = None
        self._hauling = None
        self._inventory = None
        self._production = None
        self._assets = None
        self._planning = None
        await super().unload()

    # ------------------------------------------------------------------
    # Config helpers (just-in-time retrieval)
    # ------------------------------------------------------------------

    def _get_sync_interval(self) -> int:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("auto_sync_interval", errors)
        return int(value) if value else 15

    def _get_currency_format(self) -> str:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("default_currency_format", errors)
        return value if value else "full"

    def _get_futures_min_profit(self) -> float:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("futures_min_profit", errors)
        return float(value) if value else 0.0

    def _get_futures_auto_generate(self) -> bool:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("futures_auto_generate", errors)
        if value is None:
            return True
        return str(value).lower() in ("true", "1", "yes")

    def _get_position_auto_track(self) -> bool:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("position_auto_track", errors)
        if value is None:
            return True
        return str(value).lower() in ("true", "1", "yes")

    def _get_complexity_layer(self) -> str:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("complexity_layer", errors)
        if value and value in ("casual", "engaged", "industrial"):
            return value
        return "engaged"

    def _get_announce_trades(self) -> bool:
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value(
            "announce_trade_opportunities", errors
        )
        if value is None:
            return False
        return str(value).lower() in ("true", "1", "yes")

    # ------------------------------------------------------------------
    # Sibling skill detection (all optional)
    # ------------------------------------------------------------------

    def _find_sibling_skill(self, class_name: str):
        """Find a sibling skill by class name on this wingman.

        Returns the skill instance if loaded and prepared, else None.
        """
        for skill in self.wingman.skills:
            if skill.__class__.__name__ == class_name and skill.is_prepared:
                return skill
        return None

    def _has_logreader(self) -> bool:
        """Check if SC_LogReader is loaded on this wingman."""
        return self._find_sibling_skill("SC_LogReader") is not None

    def _has_uexcorp(self) -> bool:
        """Check if UEXCorp is loaded on this wingman."""
        return self._find_sibling_skill("UEXCorp") is not None

    def _get_player_location(self) -> dict | None:
        """Get current player location from SC_LogReader if available.

        Returns:
            Dict with 'location_name' and 'star_system' keys, or None.
        """
        lr = self._find_sibling_skill("SC_LogReader")
        if not lr:
            return None
        try:
            state = lr._logic.get_combined_state()
            location_name = state.get("location_name") or state.get("location", "")
            star_system = state.get("star_system", "")
            if location_name or star_system:
                return {
                    "location_name": location_name,
                    "star_system": star_system,
                }
        except (AttributeError, KeyError):
            logger.debug("Failed to read player location from SC_LogReader")
        return None

    def _lookup_ship_price(self, ship_name: str) -> float | None:
        """Look up in-game purchase price via UEXCorp if available.

        Tries multiple name matching strategies:
          1. Exact match on vehicle_name in purchase price table
          2. Exact match on vehicle name/name_full, then lookup prices by ID
          3. Case-insensitive partial match on vehicle name

        Returns the lowest purchase price across terminals, or None.
        """
        if not self._has_uexcorp():
            return None

        try:
            from skills.uexcorp.uexcorp.data_access.vehicle_data_access import (
                VehicleDataAccess,
            )
            from skills.uexcorp.uexcorp.data_access.vehicle_purchase_price_data_access import (
                VehiclePurchasePriceDataAccess,
            )

            # Strategy 1: direct match on purchase price table vehicle_name
            prices = (
                VehiclePurchasePriceDataAccess()
                .add_filter_by_vehicle_name(ship_name)
                .load()
            )
            if prices:
                valid = [p.get_price_buy() for p in prices if p.get_price_buy()]
                if valid:
                    return min(valid)

            # Strategy 2: find vehicle by name, then look up prices by ID
            vehicle = VehicleDataAccess().load_by_property("name", ship_name)
            if not vehicle:
                vehicle = VehicleDataAccess().load_by_property("name_full", ship_name)
            if vehicle:
                prices = (
                    VehiclePurchasePriceDataAccess()
                    .add_filter_by_id_vehicle(vehicle.get_id())
                    .load()
                )
                if prices:
                    valid = [p.get_price_buy() for p in prices if p.get_price_buy()]
                    if valid:
                        return min(valid)

            # Strategy 3: load all vehicles and do case-insensitive partial match
            all_vehicles = VehicleDataAccess().load()
            name_lower = ship_name.lower()
            for v in all_vehicles:
                v_name = (v.get_value("name") or "").lower()
                v_full = (v.get_value("name_full") or "").lower()
                if name_lower in v_name or name_lower in v_full:
                    prices = (
                        VehiclePurchasePriceDataAccess()
                        .add_filter_by_id_vehicle(v.get_id())
                        .load()
                    )
                    if prices:
                        valid = [p.get_price_buy() for p in prices if p.get_price_buy()]
                        if valid:
                            return min(valid)

        except (ImportError, AttributeError, KeyError, TypeError, ValueError):
            logger.debug("UEXCorp ship price lookup failed for '%s'", ship_name)

        return None

    # ------------------------------------------------------------------
    # Dynamic prompt injection
    #
    # Injecting live state (balance, fleet, orders) into the system prompt
    # lets the AI answer "how much do I have?" without a tool call. The
    # token cost is small (~200 tokens) vs. the UX gain of instant answers.
    # ------------------------------------------------------------------

    async def get_prompt(self) -> str | None:
        parts = [self.config.prompt or ""]

        if self._store:
            balance = self._store.get_balance()
            if balance.last_updated:
                parts.append(
                    f"\n**Current Balance:** {self._format_auec(balance.current_balance)}"
                )

            session = self._store.get_active_session()
            if session:
                parts.append(
                    f"\n**Active Trading Session:** Started {session.started_at}"
                )

            open_orders = self._store.query_trade_orders(status="open", limit=100)
            if open_orders:
                parts.append(f"\n**Open Trade Orders:** {len(open_orders)}")

            # Opportunities summary
            available_opps = self._store.query_opportunities(
                status="available", limit=100
            )
            if available_opps:
                best = max(available_opps, key=lambda o: o.estimated_profit)
                parts.append(
                    f"\n**Trade Opportunities:** {len(available_opps)} available"
                    f" (best: {best.commodity_name},"
                    f" ~{self._format_auec(best.estimated_profit)} profit)"
                )

            # Open positions summary
            open_positions = self._store.query_positions(status="open", limit=100)
            if open_positions:
                total_unrealized = sum(p.unrealized_pnl for p in open_positions)
                total_invested = sum(p.buy_total for p in open_positions)
                parts.append(
                    f"\n**Open Positions:** {len(open_positions)}"
                    f" (invested: {self._format_auec(total_invested)},"
                    f" unrealized P&L: {self._format_auec(total_unrealized)})"
                )

            # Outstanding credits summary
            outstanding_credits = self._store.query_credits(
                status="outstanding", limit=100
            )
            partial_credits = self._store.query_credits(status="partial", limit=100)
            active_credits = outstanding_credits + partial_credits
            if active_credits:
                total_recv = sum(
                    c.remaining_amount
                    for c in active_credits
                    if c.credit_type == "receivable"
                )
                total_pay = sum(
                    c.remaining_amount
                    for c in active_credits
                    if c.credit_type == "payable"
                )
                credit_parts = []
                if total_recv > 0:
                    credit_parts.append(f"owed to you: {self._format_auec(total_recv)}")
                if total_pay > 0:
                    credit_parts.append(f"you owe: {self._format_auec(total_pay)}")
                parts.append(
                    f"\n**Outstanding Credits:** {len(active_credits)}"
                    f" ({', '.join(credit_parts)})"
                )

            # Active hauls
            active_hauls = self._store.query_hauls(status="in_transit", limit=100)
            if active_hauls:
                parts.append(f"\n**Active Hauls:** {len(active_hauls)} in transit")

            # Inventory summary
            all_inventory = self._store.query_inventory(limit=200)
            if all_inventory:
                total_value = sum(i.estimated_value for i in all_inventory)
                locations = len({i.location for i in all_inventory if i.location})
                parts.append(
                    f"\n**Inventory:** {len(all_inventory)} items"
                    f" across {locations} locations"
                    + (
                        f" (~{self._format_auec(total_value)} est. value)"
                        if total_value > 0
                        else ""
                    )
                )

            # Active production
            active_production = self._store.query_production_runs(
                status="in_progress", limit=100
            )
            if active_production:
                parts.append(
                    f"\n**Production:** {len(active_production)} runs in progress"
                )

            # Fleet/asset summary
            active_assets = self._store.query_assets(status="active", limit=200)
            if active_assets:
                ships = [a for a in active_assets if a.asset_type == "ship"]
                total_value = sum(
                    a.estimated_market_value or a.purchase_price for a in active_assets
                )
                parts.append(
                    f"\n**Fleet:** {len(ships)} ships, "
                    f"{len(active_assets)} total assets "
                    f"(~{self._format_auec(total_value)} value)"
                )

            # Planned orders
            open_orders = self._store.query_planned_orders(
                status_in=["open", "partial"], limit=100
            )
            if open_orders:
                po_count = sum(1 for o in open_orders if o.order_type == "purchase")
                so_count = sum(1 for o in open_orders if o.order_type == "sale")
                order_parts = []
                if po_count:
                    order_parts.append(f"{po_count} purchase")
                if so_count:
                    order_parts.append(f"{so_count} sale")
                parts.append(
                    f"\n**Planned Orders:** {', '.join(order_parts)} "
                    f"({len(open_orders)} total open/partial)"
                )

        if self._market and self._market.is_data_available():
            parts.append(
                "\n**Market Data:** UEX commodity prices available. "
                "Use `get_best_trades` or `get_commodity_prices` for market intelligence."
            )

        # Sibling skill availability
        sibling_parts = []
        if self._has_logreader():
            sibling_parts.append(
                "SC_LogReader is active — trades are auto-captured from the game log."
            )
        else:
            sibling_parts.append(
                "SC_LogReader is not installed — use `record_transaction` for manual entry."
            )
        if self._has_uexcorp():
            sibling_parts.append(
                "UEXCorp is active — ship prices are auto-populated when registering assets."
            )
        else:
            sibling_parts.append(
                "UEXCorp is not installed — ask the user for ship prices when registering assets."
            )
        parts.append("\n**Integrations:** " + " ".join(sibling_parts))

        # Complexity tier gating
        tier = self._get_complexity_layer()
        if tier == "casual":
            parts.append(
                "\n**Complexity: Casual** — Focus on basic income/expense tracking. "
                "Use: record_transaction, query_transactions, get_balance, "
                "get_income_statement (simple P&L only), set_budget, check_budget. "
                "Do NOT suggest fleet, planning, or advanced tools."
            )
        elif tier == "engaged":
            parts.append(
                "\n**Complexity: Engaged** — Full trading and fleet management. "
                "Use all core, trade, market, position, credit, hauling tools "
                "plus fleet management, break-even analysis, and activity ROI. "
                "Do NOT suggest what-if tools."
            )
        else:
            parts.append(
                "\n**Complexity: Industrial** — All features enabled including "
                "what-if scenarios."
            )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    def _format_auec(self, amount: float) -> str:
        """Format an aUEC amount according to user preference."""
        fmt = self._get_currency_format()
        if fmt == "short":
            if abs(amount) >= 1_000_000:
                return f"{amount / 1_000_000:.1f}M aUEC"
            elif abs(amount) >= 1_000:
                return f"{amount / 1_000:.1f}K aUEC"
        return f"{amount:,.0f} aUEC"

    def _now_iso(self) -> str:
        """Current UTC time as ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()

    def _period_start(self, period: str) -> datetime:
        """Calculate the start datetime for a named period."""
        now = datetime.now(timezone.utc)
        if period == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            return now - timedelta(days=7)
        elif period == "month":
            return now - timedelta(days=30)
        elif period == "quarter":
            return now - timedelta(days=90)
        elif period == "year":
            return now - timedelta(days=365)
        # "all" — return epoch
        return datetime(2020, 1, 1, tzinfo=timezone.utc)

    # ------------------------------------------------------------------
    # SC_LogReader ledger sync
    #
    # Sync imports from SC_LogReader's JSONL ledger using a line-number
    # cursor. This avoids duplicate imports without requiring transaction
    # ID dedup — the cursor just tracks "last processed line."
    # ------------------------------------------------------------------

    def _get_logreader_ledger_path(self) -> Path:
        """Resolve the SC_LogReader's trade ledger path."""
        from services.file import get_generated_files_dir

        logreader_dir = get_generated_files_dir("SC_LogReader")
        return Path(logreader_dir) / "sc_logreader_ledger.jsonl"

    async def _sync_from_logreader(self) -> int:
        """Sync new entries from SC_LogReader's trade ledger.

        Returns the number of new transactions imported.
        """
        if not self._store:
            return 0

        ledger_path = self._get_logreader_ledger_path()
        if not ledger_path.exists():
            return 0

        cursor = self._store.get_sync_cursor()
        imported = 0

        try:
            with open(ledger_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    if line_num <= cursor:
                        continue
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        txn = self._convert_ledger_entry(data)
                        if txn:
                            self._store.append_transaction(txn)
                            self._update_balance_for_transaction(txn)
                            imported += 1
                            # Trigger per-commodity market price refresh
                            self._refresh_commodity_on_trade(txn)
                            # Auto-manage positions on commodity trades
                            self._handle_position_on_trade(txn)
                            # Auto-fulfill accepted opportunities
                            self._handle_opportunity_fulfillment(txn)
                            # Auto-fulfill planned orders
                            self._check_planned_orders_on_trade(txn)
                    except (json.JSONDecodeError, TypeError, KeyError):
                        logger.warning(
                            "Skipping malformed SC_LogReader ledger line %d",
                            line_num,
                        )

            # Count total lines for cursor (re-read is cheap for JSONL)
            with open(ledger_path, "r", encoding="utf-8") as f:
                total_lines = sum(1 for _ in f)
            self._store.save_sync_cursor(total_lines)

        except OSError:
            logger.exception("Failed to sync from SC_LogReader ledger")

        if imported > 0:
            logger.info("Synced %d new transactions from SC_LogReader", imported)

        return imported

    def _convert_ledger_entry(self, data: dict) -> Transaction | None:
        """Convert an SC_LogReader LedgerEntry dict to a Transaction."""
        txn_type = data.get("transaction", "")
        category_raw = data.get("category", "")

        # Map SC_LogReader's (transaction, category) to our category
        if txn_type == "purchase" and category_raw == "item":
            category = "item_purchase"
        elif txn_type == "purchase" and category_raw == "commodity":
            category = "commodity_purchase"
        elif txn_type == "sale" and category_raw == "item":
            category = "item_sale"
        elif txn_type == "sale" and category_raw == "commodity":
            category = "commodity_sale"
        else:
            logger.warning("Unknown ledger entry type: %s/%s", txn_type, category_raw)
            return None

        transaction_type = "expense" if category in EXPENSE_CATEGORIES else "income"

        # Resolve commodity name
        item_name = data.get("item_name")
        item_guid = data.get("item_guid", "")
        if not item_name and item_guid and self._guid_resolver:
            item_name = self._guid_resolver.resolve(item_guid)

        description = (
            f"{CATEGORY_LABELS.get(category, category)}: {item_name or item_guid}"
        )
        shop = data.get("shop_name", "")

        # Attach to active session if one exists
        session = self._store.get_active_session()

        # Attach to active group session if one exists
        group_session = self._store.get_active_group_session()

        return Transaction(
            id=str(uuid.uuid4()),
            timestamp=data.get("timestamp", self._now_iso()),
            category=category,
            transaction_type=transaction_type,
            amount=abs(float(data.get("price", 0))),
            description=description,
            location=shop or data.get("location", ""),
            tags=["auto"],
            source="auto_log",
            session_id=session.id if session else None,
            item_name=item_name,
            item_guid=item_guid,
            quantity=data.get("quantity"),
            quantity_unit=data.get("quantity_unit"),
            shop_name=shop,
            player_id=data.get("player_id"),
            group_session_id=group_session.id if group_session else None,
        )

    def _update_balance_for_transaction(self, txn: Transaction) -> None:
        """Update the running balance after a new transaction."""
        if not self._store:
            return
        balance = self._store.get_balance()
        if txn.transaction_type == "income":
            balance.current_balance += txn.amount
            balance.total_lifetime_income += txn.amount
        else:
            balance.current_balance -= txn.amount
            balance.total_lifetime_expenses += txn.amount
        balance.last_updated = self._now_iso()
        self._store.save_balance(balance)

    async def _sync_loop(self) -> None:
        """Background sync loop that periodically imports from SC_LogReader."""
        while self._sync_active:
            try:
                await self._sync_from_logreader()
            except (OSError, json.JSONDecodeError, KeyError, ValueError):
                logger.exception("Error in sync loop")

            # Check for location change → announce trade opportunities
            try:
                await self._check_trade_announcements()
            except (OSError, KeyError, ValueError, TypeError):
                logger.exception("Error checking trade announcements")

            interval = self._get_sync_interval()
            if interval <= 0:
                break
            await asyncio.sleep(interval)

    async def _check_trade_announcements(self) -> None:
        """Announce top trade opportunities when the player arrives at a new location."""
        if not self._get_announce_trades():
            return
        if not self._market or not self._market.is_data_available():
            return

        location = self._get_player_location()
        if not location:
            return

        location_name = location.get("location_name", "")
        if not location_name:
            return

        # Only announce on location change
        if location_name == self._last_announced_location:
            return
        self._last_announced_location = location_name

        # Generate fresh opportunities for this location
        if self._futures:
            self._futures.generate_opportunities(
                location=location_name,
                min_margin=self._get_futures_min_profit(),
            )

        # Query available opportunities whose buy terminal matches this location
        all_opps = self._store.query_opportunities(status="available", limit=500)
        loc_lower = location_name.lower()
        opps = [
            o
            for o in all_opps
            if loc_lower in o.buy_terminal.lower()
            or loc_lower in o.buy_location.lower()
        ]
        # Take top 5 by score
        opps.sort(key=lambda o: o.score, reverse=True)
        opps = opps[:5]

        if not opps:
            return

        # Format like SC_LogReader game events for chat log visibility
        lines = [f"[Trade Opportunities at {location_name}]"]
        for o in opps:
            lines.append(
                f"- {o.commodity_name} to {o.sell_terminal}, "
                f"{self._format_auec(o.margin_per_scu)} per SCU"
            )

        message = "\n".join(lines)

        if self.wingman:
            await self.wingman.process(transcript=message)

    # ------------------------------------------------------------------
    # Market data refresh
    # ------------------------------------------------------------------

    async def _market_refresh_loop(self) -> None:
        """Background loop: refresh market data every 24 hours."""
        while self._market_refresh_active:
            try:
                if self._market:
                    results = self._market.refresh_all()
                    total = sum(results.values())
                    if total > 0:
                        logger.info("Market data refreshed: %s", results)
                        self._update_guid_map_from_market()

                    # Auto-generate trade opportunities from fresh data
                    if self._futures and self._get_futures_auto_generate():
                        try:
                            new_count = self._futures.generate_opportunities(
                                min_margin=self._get_futures_min_profit(),
                            )
                            if new_count > 0:
                                logger.info(
                                    "Generated %d new trade opportunities", new_count
                                )
                            expired = self._futures.expire_stale_opportunities()
                            if expired > 0:
                                logger.info("Expired %d stale opportunities", expired)
                        except (OSError, KeyError, ValueError, TypeError):
                            logger.exception("Error generating opportunities")

                    # Update unrealized P&L for open positions
                    if self._positions:
                        try:
                            updated = self._positions.update_unrealized_pnl()
                            if updated > 0:
                                logger.info(
                                    "Updated unrealized P&L for %d positions", updated
                                )
                        except (OSError, KeyError, ValueError, TypeError):
                            logger.exception("Error updating position valuations")
            except (OSError, json.JSONDecodeError, KeyError, ValueError):
                logger.exception("Error in market refresh loop")
            # Sleep 24 hours before next full refresh
            for _ in range(24 * 60):
                if not self._market_refresh_active:
                    return
                await asyncio.sleep(60)

    def _refresh_commodity_on_trade(self, txn: Transaction) -> None:
        """Trigger a targeted price refresh for a traded commodity."""
        if not self._market or not self._market.is_data_available():
            return
        # Only refresh for trade categories
        if txn.category not in (
            "commodity_purchase",
            "commodity_sale",
            "item_purchase",
            "item_sale",
        ):
            return
        name = txn.item_name
        if name:
            try:
                self._market.refresh_for_commodity_name(name)
            except (OSError, KeyError, ValueError):
                logger.debug("Could not refresh market data for %s", name)

    def _update_guid_map_from_market(self) -> None:
        """Use market commodity names to improve GUID resolver."""
        if not self._market or not self._guid_resolver:
            return
        name_index = self._market.build_name_index()
        if name_index:
            logger.info(
                "Market data provides %d commodity names for GUID resolution",
                len(name_index),
            )

    def _handle_position_on_trade(self, txn: Transaction) -> None:
        """Open/close positions based on commodity trades."""
        if not self._positions or not self._get_position_auto_track():
            return
        try:
            if txn.category == "commodity_purchase":
                self._positions.open_position_from_purchase(txn)
            elif txn.category == "commodity_sale":
                self._positions.close_position_from_sale(txn)
        except (OSError, KeyError, ValueError, TypeError):
            logger.exception("Error managing position for trade")

    def _handle_opportunity_fulfillment(self, txn: Transaction) -> None:
        """Check if a trade fulfills an accepted opportunity."""
        if not self._futures:
            return
        try:
            fulfilled = self._futures.check_fulfillment(txn)
            if fulfilled:
                logger.info(
                    "Opportunity fulfilled: %s %s",
                    fulfilled.commodity_name,
                    fulfilled.id[:8],
                )
        except (OSError, KeyError, ValueError, TypeError):
            logger.exception("Error checking opportunity fulfillment")

    # ------------------------------------------------------------------
    # Planned order fulfillment matching
    # ------------------------------------------------------------------

    _PURCHASE_CATEGORIES = {
        "commodity_purchase",
        "item_purchase",
        "player_trade_buy",
        "ship_purchase",
        "component_purchase",
        "capital_investment",
    }
    _SALE_CATEGORIES = {
        "commodity_sale",
        "item_sale",
        "player_trade_sell",
        "salvage_income",
    }

    def _fuzzy_match(self, order_name: str, txn_name: str) -> bool:
        """Case-insensitive partial match for planned order fulfillment.

        Uses substring containment (not Levenshtein) because SC commodity names
        have predictable suffixes like "(Raw)" that make exact match too strict
        while edit distance would over-match across unrelated commodities.
        """
        if not order_name or not txn_name:
            return False
        a = order_name.lower().strip()
        b = txn_name.lower().strip()
        return a in b or b in a

    def _check_planned_orders_on_trade(self, txn: Transaction) -> None:
        """Check if a transaction fulfills an open planned order."""
        if not self._store:
            return

        if txn.category in self._PURCHASE_CATEGORIES:
            order_type = "purchase"
        elif txn.category in self._SALE_CATEGORIES:
            order_type = "sale"
        else:
            return

        orders = self._store.query_planned_orders(
            order_type=order_type,
            status_in=["open", "partial"],
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
                order.fulfilled_at = self._now_iso()
            else:
                order.status = "partial"

            self._store.save_planned_order(order)
            logger.info(
                "Planned order %s fulfilled %.0f/%.0f %s",
                order.id[:8],
                order.fulfilled_quantity,
                order.ordered_quantity,
                order.item_name,
            )
            # Only match the first matching order — prevents one transaction
            # from fulfilling multiple orders for the same item
            break

    # ==================================================================
    # Tool execution hook — notify dashboard on every tool call
    # ==================================================================

    async def execute_tool(
        self, tool_name: str, parameters: dict[str, any], benchmark: Benchmark
    ) -> tuple[str, str]:
        function_response, instant_response = await super().execute_tool(
            tool_name, parameters, benchmark
        )
        if self._ui_server:
            self._ui_server.notify_refresh()
        return function_response, instant_response

    # ==================================================================
    # Phase 1 Tools — Core Accounting
    #
    # All @tool methods must live on this class because the framework's
    # @tool decorator only scans dir(self) on the Skill subclass. Domain
    # logic is delegated to manager classes to keep each method a thin
    # wrapper despite the large method count.
    # ==================================================================

    # Categories that must go through dedicated tools, not record_transaction
    _BLOCKED_CATEGORIES = {"commodity_purchase", "commodity_sale"}

    @tool(
        description=(
            "Record a manual financial transaction. Use for expenses, income, "
            "or P2P trades not automatically captured from the game log. "
            "Do NOT use this for commodity purchases or sales — use "
            "record_commodity_purchase or record_commodity_sale instead."
        )
    )
    async def record_transaction(
        self,
        category: str,
        amount: float,
        description: str,
        location: str = "",
        tags: str = "",
        linked_asset_id: str = "",
    ) -> str:
        """Record a manual financial transaction.

        Args:
            category: Transaction category (e.g. fuel, repairs, mission_reward,
                      ship_purchase, component_purchase).
            amount: Amount in aUEC (always positive).
            description: What this transaction was for.
            location: Where it happened (optional).
            tags: Comma-separated tags for filtering (optional).
            linked_asset_id: ID of the ship/asset this expense is for (optional).
                             Links the transaction for per-ship P&L tracking.
        """
        if not self._store:
            return "Accountant not initialized."

        # Validate category
        cat = category.lower().strip().replace(" ", "_")
        if cat in self._BLOCKED_CATEGORIES:
            return (
                "Use 'record_commodity_purchase' or 'record_commodity_sale' "
                "for commodity trades — they also track portfolio positions."
            )
        if cat not in ALL_CATEGORIES:
            available = ", ".join(sorted(ALL_CATEGORIES))
            return f"Unknown category '{category}'. Available: {available}"

        transaction_type = "income" if cat in INCOME_CATEGORIES else "expense"
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
        activity = CATEGORY_ACTIVITY.get(cat, Activity.GENERAL).value

        session = self._store.get_active_session()

        txn = Transaction(
            id=str(uuid.uuid4()),
            timestamp=self._now_iso(),
            category=cat,
            transaction_type=transaction_type,
            amount=abs(amount),
            description=description,
            location=location,
            tags=tag_list,
            source="manual",
            session_id=session.id if session else None,
            linked_asset_id=linked_asset_id or None,
            activity=activity,
        )

        self._store.append_transaction(txn)
        self._update_balance_for_transaction(txn)
        self._check_planned_orders_on_trade(txn)

        balance = self._store.get_balance()
        return json.dumps(
            {
                "status": "recorded",
                "transaction_type": transaction_type,
                "category": CATEGORY_LABELS.get(cat, cat),
                "amount": f"{amount:,.0f} aUEC",
                "new_balance": self._format_auec(balance.current_balance),
            }
        )

    @tool(
        description=(
            "Record a commodity purchase. Creates a ledger transaction AND "
            "opens a portfolio position for tracking. Use when the player "
            "says they bought a commodity (e.g. 'I bought 100 SCU of Laranite')."
        )
    )
    async def record_commodity_purchase(
        self,
        commodity_name: str,
        quantity_scu: float,
        price_per_scu: float,
        location: str = "",
    ) -> str:
        """Record a commodity purchase with position tracking.

        Args:
            commodity_name: Name of the commodity (e.g. Laranite, Quantanium).
            quantity_scu: Quantity in SCU.
            price_per_scu: Price per SCU in aUEC.
            location: Where the purchase happened (optional).
        """
        if not self._store:
            return "Accountant not initialized."
        if not self._positions:
            return "Position manager not initialized."

        quantity_scu = float(quantity_scu)
        price_per_scu = float(price_per_scu)
        total_cost = quantity_scu * price_per_scu
        activity = CATEGORY_ACTIVITY.get("commodity_purchase", Activity.GENERAL).value
        session = self._store.get_active_session()

        txn = Transaction(
            id=str(uuid.uuid4()),
            timestamp=self._now_iso(),
            category="commodity_purchase",
            transaction_type="expense",
            amount=total_cost,
            description=f"Purchased {quantity_scu:.0f} SCU of {commodity_name}",
            location=location,
            source="manual",
            item_name=commodity_name,
            quantity=quantity_scu,
            quantity_unit="scu",
            activity=activity,
            session_id=session.id if session else None,
        )

        self._store.append_transaction(txn)
        self._update_balance_for_transaction(txn)
        self._check_planned_orders_on_trade(txn)

        pos = self._positions.open_position_from_purchase(txn)

        balance = self._store.get_balance()
        result = {
            "status": "recorded",
            "commodity": commodity_name,
            "quantity_scu": quantity_scu,
            "price_per_scu": self._format_auec(price_per_scu),
            "total_cost": self._format_auec(total_cost),
            "new_balance": self._format_auec(balance.current_balance),
        }
        if pos:
            result["position_id"] = pos.id[:8]
        return json.dumps(result, indent=2)

    @tool(
        description=(
            "Record a commodity sale. Creates a ledger transaction AND "
            "closes portfolio positions via FIFO. Use when the player "
            "says they sold a commodity (e.g. 'I sold 50 SCU of Quantanium')."
        )
    )
    async def record_commodity_sale(
        self,
        commodity_name: str,
        quantity_scu: float,
        price_per_scu: float,
        location: str = "",
    ) -> str:
        """Record a commodity sale with position closure.

        Args:
            commodity_name: Name of the commodity (e.g. Laranite, Quantanium).
            quantity_scu: Quantity in SCU.
            price_per_scu: Price per SCU in aUEC.
            location: Where the sale happened (optional).
        """
        if not self._store:
            return "Accountant not initialized."
        if not self._positions:
            return "Position manager not initialized."

        quantity_scu = float(quantity_scu)
        price_per_scu = float(price_per_scu)
        total_revenue = quantity_scu * price_per_scu
        activity = CATEGORY_ACTIVITY.get("commodity_sale", Activity.GENERAL).value
        session = self._store.get_active_session()

        txn = Transaction(
            id=str(uuid.uuid4()),
            timestamp=self._now_iso(),
            category="commodity_sale",
            transaction_type="income",
            amount=total_revenue,
            description=f"Sold {quantity_scu:.0f} SCU of {commodity_name}",
            location=location,
            source="manual",
            item_name=commodity_name,
            quantity=quantity_scu,
            quantity_unit="scu",
            activity=activity,
            session_id=session.id if session else None,
        )

        self._store.append_transaction(txn)
        self._update_balance_for_transaction(txn)
        self._check_planned_orders_on_trade(txn)

        pos = self._positions.close_position_from_sale(txn)

        balance = self._store.get_balance()
        result = {
            "status": "recorded",
            "commodity": commodity_name,
            "quantity_scu": quantity_scu,
            "price_per_scu": self._format_auec(price_per_scu),
            "total_revenue": self._format_auec(total_revenue),
            "new_balance": self._format_auec(balance.current_balance),
        }
        if pos:
            result["position_closed"] = pos.id[:8]
            result["realized_pnl"] = self._format_auec(pos.realized_pnl or 0)
        return json.dumps(result, indent=2)

    @tool(
        description=(
            "Show the player's transaction ledger / transaction history. "
            "Use this for any request about recent transactions, last purchases, "
            "sales, expenses, income, or financial activity. Filter by time range, "
            "category, tags, or location. Returns most recent first."
        )
    )
    async def query_transactions(
        self,
        days_back: int = 7,
        category: str = "",
        tags: str = "",
        location: str = "",
        limit: int = 20,
    ) -> str:
        """Query financial transactions with filters.

        Args:
            days_back: Number of days to look back (default 7).
            category: Filter by category (optional).
            tags: Comma-separated tags to filter by (optional).
            location: Filter by location (partial match, optional).
            limit: Maximum results to return (default 20).
        """
        if not self._store:
            return "Accountant not initialized."

        start = datetime.now(timezone.utc) - timedelta(days=days_back)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
        cat = category.lower().strip().replace(" ", "_") if category else None

        txns = self._store.query_transactions(
            start=start,
            category=cat,
            tags=tag_list,
            location=location if location else None,
            limit=limit,
        )

        if not txns:
            return json.dumps({"transactions": [], "message": "No transactions found."})

        results = []
        for t in txns:
            results.append(
                {
                    "timestamp": t.timestamp,
                    "type": t.transaction_type,
                    "category": CATEGORY_LABELS.get(t.category, t.category),
                    "amount": f"{t.amount:,.0f}",
                    "description": t.description,
                    "location": t.location,
                    "tags": t.tags,
                    "source": t.source,
                }
            )

        return json.dumps({"transactions": results, "count": len(results)}, indent=2)

    @tool(
        description="Get current aUEC balance, lifetime totals, and financial position."
    )
    async def get_balance(self) -> str:
        """Get current financial position."""
        if not self._store:
            return "Accountant not initialized."

        balance = self._store.get_balance()
        return json.dumps(
            {
                "current_balance": self._format_auec(balance.current_balance),
                "total_lifetime_income": self._format_auec(
                    balance.total_lifetime_income
                ),
                "total_lifetime_expenses": self._format_auec(
                    balance.total_lifetime_expenses
                ),
                "last_updated": balance.last_updated or "Never",
            },
            indent=2,
        )

    @tool(
        description=(
            "Sync trades from the Star Citizen game log. Requires the SC_LogReader "
            "skill to be installed. If SC_LogReader is not available, use "
            "record_transaction for manual entry instead."
        )
    )
    async def sync_trade_log(self) -> str:
        """Force sync from SC_LogReader ledger."""
        if not self._store:
            return "Accountant not initialized."

        ledger_path = self._get_logreader_ledger_path()
        if not ledger_path.exists():
            return json.dumps(
                {
                    "status": "no_ledger",
                    "message": (
                        "SC_LogReader trade ledger not found. "
                        "Install and enable the SC_LogReader skill to auto-capture trades."
                    ),
                }
            )

        imported = await self._sync_from_logreader()
        balance = self._store.get_balance()

        return json.dumps(
            {
                "status": "synced",
                "new_transactions": imported,
                "current_balance": self._format_auec(balance.current_balance),
            }
        )

    # ==================================================================
    # Phase 2 Tools — Trade Orders, Sessions, Budgets
    # ==================================================================

    async def create_trade_order(
        self,
        order_type: str,
        item_name: str,
        quantity: float,
        quantity_unit: str = "scu",
        target_price: float = 0,
        target_location: str = "",
        notes: str = "",
    ) -> str:
        """Create a planned trade order.

        Args:
            order_type: Either "buy" or "sell".
            item_name: What commodity or item to trade.
            quantity: How many units.
            quantity_unit: Unit type (scu, cscu, or units).
            target_price: Target price per unit in aUEC (optional).
            target_location: Where to execute the trade (optional).
            notes: Any additional notes (optional).
        """
        if not self._store:
            return "Accountant not initialized."

        otype = order_type.lower().strip()
        if otype not in ("buy", "sell"):
            return "Order type must be 'buy' or 'sell'."

        order = TradeOrder(
            id=str(uuid.uuid4()),
            created_at=self._now_iso(),
            status="open",
            order_type=otype,
            item_name=item_name,
            quantity=quantity,
            quantity_unit=quantity_unit,
            target_price=target_price if target_price > 0 else None,
            target_location=target_location or None,
            notes=notes,
        )

        self._store.save_trade_order(order)

        result = {
            "status": "order_created",
            "order_id": order.id[:8],
            "type": otype,
            "item": item_name,
            "quantity": f"{quantity} {quantity_unit}",
        }
        if target_price > 0:
            total = target_price * quantity
            result["target_price_per_unit"] = self._format_auec(target_price)
            result["estimated_total"] = self._format_auec(total)
        if target_location:
            result["location"] = target_location

        return json.dumps(result, indent=2)

    async def complete_trade_order(
        self,
        order_id: str,
        actual_price: float,
    ) -> str:
        """Mark a trade order as completed.

        Args:
            order_id: The order ID (or first 8 characters).
            actual_price: The actual total price paid/received in aUEC.
        """
        if not self._store:
            return "Accountant not initialized."

        # Find order by full or partial ID
        order = self._find_order_by_id(order_id)
        if not order:
            return f"Trade order '{order_id}' not found."

        if order.status != "open":
            return f"Order is already {order.status}."

        # Determine category and create transaction
        if order.order_type == "buy":
            category = "commodity_purchase"
        else:
            category = "commodity_sale"

        transaction_type = "expense" if category in EXPENSE_CATEGORIES else "income"
        session = self._store.get_active_session()

        txn = Transaction(
            id=str(uuid.uuid4()),
            timestamp=self._now_iso(),
            category=category,
            transaction_type=transaction_type,
            amount=abs(actual_price),
            description=f"Trade order completed: {order.order_type} {order.quantity} {order.quantity_unit} {order.item_name}",
            location=order.target_location or "",
            tags=["trade_order"],
            source="trade_order",
            trade_order_id=order.id,
            session_id=session.id if session else None,
            item_name=order.item_name,
            quantity=order.quantity,
            quantity_unit=order.quantity_unit,
        )

        self._store.append_transaction(txn)
        self._update_balance_for_transaction(txn)

        # Update the order
        order.status = "completed"
        order.completed_at = self._now_iso()
        order.actual_price = actual_price
        order.transaction_id = txn.id
        self._store.save_trade_order(order)

        result = {
            "status": "order_completed",
            "order_id": order.id[:8],
            "item": order.item_name,
            "actual_price": self._format_auec(actual_price),
        }
        if order.target_price:
            expected = order.target_price * order.quantity
            diff = actual_price - expected
            result["expected_total"] = self._format_auec(expected)
            result["difference"] = self._format_auec(diff)

        return json.dumps(result, indent=2)

    async def cancel_trade_order(self, order_id: str) -> str:
        """Cancel an open trade order.

        Args:
            order_id: The order ID (or first 8 characters).
        """
        if not self._store:
            return "Accountant not initialized."

        order = self._find_order_by_id(order_id)
        if not order:
            return f"Trade order '{order_id}' not found."

        if order.status != "open":
            return f"Order is already {order.status}."

        order.status = "cancelled"
        self._store.save_trade_order(order)

        return json.dumps(
            {
                "status": "order_cancelled",
                "order_id": order.id[:8],
                "item": order.item_name,
            }
        )

    async def list_trade_orders(
        self,
        status: str = "open",
        limit: int = 10,
    ) -> str:
        """List trade orders.

        Args:
            status: Filter by status — open, completed, cancelled, or all.
            limit: Maximum results (default 10).
        """
        if not self._store:
            return "Accountant not initialized."

        st = status.lower().strip() if status and status != "all" else None
        orders = self._store.query_trade_orders(status=st, limit=limit)

        if not orders:
            return json.dumps({"orders": [], "message": "No trade orders found."})

        results = []
        for o in orders:
            entry = {
                "order_id": o.id[:8],
                "status": o.status,
                "type": o.order_type,
                "item": o.item_name,
                "quantity": f"{o.quantity} {o.quantity_unit}",
                "created": o.created_at,
            }
            if o.target_price:
                entry["target_price_per_unit"] = self._format_auec(o.target_price)
            if o.target_location:
                entry["location"] = o.target_location
            if o.actual_price is not None:
                entry["actual_price"] = self._format_auec(o.actual_price)
            results.append(entry)

        return json.dumps({"orders": results, "count": len(results)}, indent=2)

    def _find_order_by_id(self, order_id: str) -> TradeOrder | None:
        """Find a trade order by full or partial ID."""
        if not self._store:
            return None
        # Try exact match first
        order = self._store.get_trade_order(order_id)
        if order:
            return order
        # Try partial match (first N chars)
        for o in self._store.query_trade_orders(limit=500):
            if o.id.startswith(order_id):
                return o
        return None

    # -- Sessions --

    async def start_trading_session(self, notes: str = "") -> str:
        """Start a new trading session.

        Args:
            notes: Optional notes about this session's goals.
        """
        if not self._store:
            return "Accountant not initialized."

        existing = self._store.get_active_session()
        if existing:
            return json.dumps(
                {
                    "status": "session_already_active",
                    "session_id": existing.id[:8],
                    "started_at": existing.started_at,
                    "message": "End the current session before starting a new one.",
                }
            )

        balance = self._store.get_balance()
        session = TradingSession(
            id=str(uuid.uuid4()),
            started_at=self._now_iso(),
            starting_balance=balance.current_balance,
            notes=notes,
        )
        self._store.save_session(session)

        return json.dumps(
            {
                "status": "session_started",
                "session_id": session.id[:8],
                "starting_balance": self._format_auec(session.starting_balance),
            }
        )

    async def end_trading_session(self) -> str:
        """End the current trading session."""
        if not self._store:
            return "Accountant not initialized."

        session = self._store.get_active_session()
        if not session:
            return "No active trading session."

        session.ended_at = self._now_iso()
        self._store.save_session(session)

        # Calculate session P&L
        balance = self._store.get_balance()
        session_profit = balance.current_balance - session.starting_balance

        # Get session transactions
        session_txns = self._store.query_transactions(
            session_id=session.id, limit=10000
        )
        pnl = generate_pnl(session_txns)

        return json.dumps(
            {
                "status": "session_ended",
                "session_id": session.id[:8],
                "duration": session.started_at + " → " + session.ended_at,
                "starting_balance": self._format_auec(session.starting_balance),
                "ending_balance": self._format_auec(balance.current_balance),
                "session_profit": self._format_auec(session_profit),
                "transactions": pnl["transaction_count"],
                "income": self._format_auec(pnl["total_income"]),
                "expenses": self._format_auec(pnl["total_expenses"]),
            },
            indent=2,
        )

    async def get_session_status(self) -> str:
        """Get the active trading session's status."""
        if not self._store:
            return "Accountant not initialized."

        session = self._store.get_active_session()
        if not session:
            return "No active trading session."

        balance = self._store.get_balance()
        running_pnl = balance.current_balance - session.starting_balance

        session_txns = self._store.query_transactions(
            session_id=session.id, limit=10000
        )
        pnl = generate_pnl(session_txns)

        return json.dumps(
            {
                "session_id": session.id[:8],
                "started_at": session.started_at,
                "running_pnl": self._format_auec(running_pnl),
                "current_balance": self._format_auec(balance.current_balance),
                "transactions": pnl["transaction_count"],
                "income": self._format_auec(pnl["total_income"]),
                "expenses": self._format_auec(pnl["total_expenses"]),
            },
            indent=2,
        )

    # -- Group Sessions --

    @tool(
        description=(
            "Start a group session for multi-player profit splitting. "
            "All trades captured during the session are tagged to the group ledger. "
            "Only one group session can be active at a time."
        )
    )
    async def start_group_session(self, notes: str = "") -> str:
        """Start a new group session.

        Args:
            notes: Optional notes about this group session.
        """
        if not self._store:
            return "Accountant not initialized."

        existing = self._store.get_active_group_session()
        if existing:
            return json.dumps(
                {
                    "status": "group_session_already_active",
                    "session_id": existing.id[:8],
                    "started_at": existing.started_at,
                    "message": "Stop the current group session before starting a new one.",
                }
            )

        gs = GroupSession(
            id=str(uuid.uuid4()),
            started_at=self._now_iso(),
            status="active",
            notes=notes,
        )
        self._store.save_group_session(gs)

        return json.dumps(
            {
                "status": "group_session_started",
                "session_id": gs.id[:8],
                "started_at": gs.started_at,
            }
        )

    @tool(description="Stop the active group session.")
    async def stop_group_session(self) -> str:
        """Stop the current group session."""
        if not self._store:
            return "Accountant not initialized."

        gs = self._store.get_active_group_session()
        if not gs:
            return "No active group session."

        gs.status = "ended"
        gs.ended_at = self._now_iso()
        self._store.save_group_session(gs)

        # Summarize session transactions
        txns = self._store.query_transactions(group_session_id=gs.id, limit=10000)
        total_income = sum(t.amount for t in txns if t.transaction_type == "income")
        total_expenses = sum(t.amount for t in txns if t.transaction_type == "expense")

        return json.dumps(
            {
                "status": "group_session_ended",
                "session_id": gs.id[:8],
                "duration": gs.started_at + " → " + gs.ended_at,
                "transactions": len(txns),
                "total_income": self._format_auec(total_income),
                "total_expenses": self._format_auec(total_expenses),
                "net": self._format_auec(total_income - total_expenses),
            },
            indent=2,
        )

    # ==================================================================
    # Planned Orders (Purchase/Sales Orders)
    # ==================================================================

    @tool(
        description=(
            "Create a planned purchase or sales order for future investment "
            "planning. Tracks fulfillment progress as items are bought or sold. "
            "Sales orders can only be created for items you already own — "
            "registered assets, open commodity positions, or inventory items."
        )
    )
    async def create_planned_order(
        self,
        order_type: str,
        item_name: str,
        quantity: float,
        quantity_unit: str = "units",
        target_price_per_unit: float = 0,
        target_location: str = "",
        notes: str = "",
    ) -> str:
        """Create a planned purchase or sales order.

        Args:
            order_type: Either "purchase" or "sale".
            item_name: What to buy or sell (e.g. "Prospector", "Laranite").
            quantity: How many units to acquire or sell.
            quantity_unit: Unit type (units, scu, cscu).
            target_price_per_unit: Expected price per unit in aUEC (optional).
            target_location: Where to execute (optional).
            notes: Additional notes (optional).
        """
        if not self._store:
            return "Accountant not initialized."

        otype = order_type.lower().strip()
        if otype not in ("purchase", "sale"):
            return "Order type must be 'purchase' or 'sale'."

        if quantity <= 0:
            return "Quantity must be greater than 0."

        # Sales orders: validate item exists in assets, positions, or inventory
        if otype == "sale":
            found_source = None
            assets = self._store.query_assets(status="active", limit=500)
            for a in assets:
                if self._fuzzy_match(item_name, a.name):
                    found_source = f"asset: {a.name}"
                    break

            if not found_source:
                positions = self._store.query_positions(status="open", limit=500)
                for p in positions:
                    if self._fuzzy_match(item_name, p.commodity_name):
                        found_source = f"position: {p.commodity_name}"
                        break

            if not found_source:
                inventory = self._store.query_inventory(limit=500)
                for inv in inventory:
                    if self._fuzzy_match(item_name, inv.item_name):
                        found_source = f"inventory: {inv.item_name}"
                        break

            if not found_source:
                return (
                    f"Cannot create a sale order for '{item_name}' — "
                    "no matching asset, position, or inventory item found. "
                    "You can only plan sales for items you already own."
                )

        order = PlannedOrder(
            id=str(uuid.uuid4()),
            created_at=self._now_iso(),
            order_type=otype,
            status="open",
            item_name=item_name,
            ordered_quantity=quantity,
            quantity_unit=quantity_unit,
            target_price_per_unit=target_price_per_unit
            if target_price_per_unit > 0
            else 0.0,
            target_location=target_location,
            notes=notes,
        )
        self._store.save_planned_order(order)

        result = {
            "status": "order_created",
            "order_id": order.id[:8],
            "type": otype,
            "item": item_name,
            "quantity": f"{quantity} {quantity_unit}",
        }
        if target_price_per_unit > 0:
            total = target_price_per_unit * quantity
            result["target_price_per_unit"] = self._format_auec(target_price_per_unit)
            result["estimated_total"] = self._format_auec(total)
        if target_location:
            result["location"] = target_location

        return json.dumps(result, indent=2)

    @tool(
        description=(
            "List planned purchase and sales orders. Shows fulfillment progress "
            "(e.g. 3/4 delivered). Filter by order type or status."
        )
    )
    async def list_planned_orders(
        self,
        order_type: str = "",
        status: str = "",
        limit: int = 20,
    ) -> str:
        """List planned orders with fulfillment progress.

        Args:
            order_type: Filter by "purchase" or "sale" (optional, shows all).
            status: Filter by "open", "partial", "fulfilled", "cancelled"
                    (optional, shows open and partial by default).
            limit: Maximum results to return (default 20).
        """
        if not self._store:
            return "Accountant not initialized."

        otype = order_type.lower().strip() if order_type else None
        st = status.lower().strip() if status else None
        status_in = None
        if not st:
            status_in = ["open", "partial"]

        orders = self._store.query_planned_orders(
            order_type=otype,
            status=st,
            status_in=status_in,
            limit=limit,
        )

        if not orders:
            return json.dumps({"orders": [], "message": "No planned orders found."})

        results = []
        for o in orders:
            entry = {
                "order_id": o.id[:8],
                "type": o.order_type,
                "status": o.status,
                "item": o.item_name,
                "progress": f"{o.fulfilled_quantity:.0f}/{o.ordered_quantity:.0f} {o.quantity_unit}",
                "created": o.created_at[:10],
            }
            if o.target_price_per_unit > 0:
                entry["target_price"] = self._format_auec(o.target_price_per_unit)
                entry["estimated_total"] = self._format_auec(
                    o.target_price_per_unit * o.ordered_quantity
                )
            if o.target_location:
                entry["location"] = o.target_location
            if o.notes:
                entry["notes"] = o.notes
            results.append(entry)

        return json.dumps({"orders": results, "count": len(results)}, indent=2)

    # -- Budgets --

    async def set_budget(
        self,
        category: str,
        amount: float,
        period_type: str = "monthly",
        notes: str = "",
    ) -> str:
        """Set a budget for a spending category.

        Args:
            category: The expense category to budget (e.g. fuel, repairs).
            amount: Budget amount in aUEC.
            period_type: Budget period — daily, weekly, monthly, quarterly, or yearly.
            notes: Optional notes about this budget.
        """
        if not self._store:
            return "Accountant not initialized."

        cat = category.lower().strip().replace(" ", "_")
        if cat not in ALL_CATEGORIES:
            available = ", ".join(sorted(ALL_CATEGORIES))
            return f"Unknown category '{category}'. Available: {available}"

        now = datetime.now(timezone.utc)
        period_days = {
            "daily": 1,
            "weekly": 7,
            "monthly": 30,
            "quarterly": 90,
            "yearly": 365,
        }
        days = period_days.get(period_type, 30)
        period_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_end = period_start + timedelta(days=days)

        budget = Budget(
            id=str(uuid.uuid4()),
            category=cat,
            period_type=period_type,
            period_start=period_start.isoformat(),
            period_end=period_end.isoformat(),
            allocated_amount=abs(amount),
            notes=notes,
        )
        self._store.save_budget(budget)

        return json.dumps(
            {
                "status": "budget_set",
                "category": CATEGORY_LABELS.get(cat, cat),
                "allocated": self._format_auec(amount),
                "period": period_type,
                "start": budget.period_start,
                "end": budget.period_end,
            }
        )

    async def check_budget(self, category: str = "") -> str:
        """Check budget vs actual spending.

        Args:
            category: Filter by category (optional, shows all if empty).
        """
        if not self._store:
            return "Accountant not initialized."

        cat = category.lower().strip().replace(" ", "_") if category else None
        budgets = self._store.get_budgets(category=cat)

        if not budgets:
            return json.dumps(
                {
                    "budgets": [],
                    "message": "No budgets configured. Use set_budget to create one.",
                }
            )

        # Get all transactions for comparison
        all_txns = self._store.query_transactions(limit=10000)
        results = generate_budget_vs_actual(budgets, all_txns)

        formatted = []
        for r in results:
            formatted.append(
                {
                    "category": r["category"],
                    "period": r["period_type"],
                    "allocated": self._format_auec(r["allocated"]),
                    "spent": self._format_auec(r["spent"]),
                    "remaining": self._format_auec(r["remaining"]),
                    "used": f"{r['percentage_used']}%",
                    "status": r["status"],
                }
            )

        return json.dumps({"budgets": formatted}, indent=2)

    # ==================================================================
    # Market Data Tools
    # ==================================================================

    @tool(
        description=(
            "Get the most profitable trade routes from UEX market data. "
            "Filters out routes where origin is out of stock or destination "
            "has full inventory. Optionally constrained by cargo capacity and budget."
        ),
        wait_response=True,
    )
    async def get_best_trades(
        self,
        limit: int = 10,
        cargo_scu: float = 0,
        budget_auec: float = 0,
        star_system: str = "",
    ) -> str:
        """Get the top most profitable trade routes.

        Args:
            limit: Number of results to return (default 10).
            cargo_scu: Your cargo capacity in SCU (0 = unconstrained).
            budget_auec: Your available budget in aUEC (0 = unconstrained).
            star_system: Filter to routes within this star system (optional).
        """
        if not self._market:
            return "Market data not initialized."

        if not self._market.is_data_available():
            return json.dumps(
                {
                    "status": "no_data",
                    "message": (
                        "Market data is still loading. "
                        "Try again in a moment, or use refresh_market_data to force a refresh."
                    ),
                }
            )

        trades = self._market.get_best_trades(
            limit=limit,
            cargo_scu=cargo_scu if cargo_scu > 0 else None,
            budget_auec=budget_auec if budget_auec > 0 else None,
            star_system=star_system if star_system else None,
        )

        if not trades:
            return json.dumps({"trades": [], "message": "No profitable trades found."})

        results = []
        for t in trades:
            entry = {
                "commodity": t.get("commodity_name", "Unknown"),
                "buy_at": t.get("origin_terminal_name", ""),
                "buy_location": t.get("origin_planet_name", "")
                or t.get("origin_star_system_name", ""),
                "buy_price": self._format_auec(t.get("price_origin", 0)),
                "sell_at": t.get("destination_terminal_name", ""),
                "sell_location": t.get("destination_planet_name", "")
                or t.get("destination_star_system_name", ""),
                "sell_price": self._format_auec(t.get("price_destination", 0)),
                "profit_per_scu": self._format_auec(
                    t.get("price_destination", 0) - t.get("price_origin", 0)
                ),
                "score": t.get("score", 0),
            }

            # Include adjusted values if player constraints were given
            if cargo_scu > 0 or budget_auec > 0:
                entry["adjusted_profit"] = self._format_auec(
                    t.get("adjusted_profit", 0)
                )
                entry["adjusted_scu"] = t.get("adjusted_scu", 0)
                entry["investment"] = self._format_auec(t.get("adjusted_investment", 0))

            results.append(entry)

        return json.dumps(
            {"trades": results, "count": len(results)},
            indent=2,
        )

    @tool(
        description=(
            "Get current commodity prices at all terminals from UEX market data. "
            "Shows where to buy and sell a specific commodity."
        )
    )
    async def get_commodity_prices(self, commodity_name: str) -> str:
        """Get terminal prices for a commodity.

        Args:
            commodity_name: Name or code of the commodity (e.g. Laranite, LARA).
        """
        if not self._market:
            return "Market data not initialized."

        if not self._market.is_data_available():
            return json.dumps(
                {
                    "status": "no_data",
                    "message": (
                        "Market data cache is empty. "
                        "Use refresh_market_data to load prices from UEX."
                    ),
                }
            )

        commodity = self._market.find_commodity(commodity_name)
        if not commodity:
            return json.dumps(
                {
                    "status": "not_found",
                    "message": (
                        f"Commodity '{commodity_name}' not found. "
                        "Try refresh_market_data to update the cache, "
                        "or check the spelling."
                    ),
                }
            )

        prices = self._market.get_commodity_prices(commodity_name)
        if not prices:
            return json.dumps(
                {
                    "commodity": commodity["name"],
                    "prices": [],
                    "message": "No price data available for this commodity.",
                }
            )

        # Separate buy and sell terminals
        buy_terminals = []
        sell_terminals = []

        for p in prices:
            if p.get("price_buy", 0) > 0:
                buy_terminals.append(
                    {
                        "terminal": p.get("terminal_name", ""),
                        "location": p.get("planet_name", "")
                        or p.get("star_system_name", ""),
                        "price": self._format_auec(p["price_buy"]),
                        "stock_scu": round(p.get("scu_buy", 0), 1),
                    }
                )
            if p.get("price_sell", 0) > 0:
                sell_terminals.append(
                    {
                        "terminal": p.get("terminal_name", ""),
                        "location": p.get("planet_name", "")
                        or p.get("star_system_name", ""),
                        "price": self._format_auec(p["price_sell"]),
                        "demand_scu": round(p.get("scu_sell_stock", 0), 1),
                    }
                )

        # Sort: cheapest buy first, most expensive sell first
        buy_terminals.sort(key=lambda x: float(x["price"].replace(",", "").split()[0]))
        sell_terminals.sort(
            key=lambda x: float(x["price"].replace(",", "").split()[0]),
            reverse=True,
        )

        return json.dumps(
            {
                "commodity": commodity["name"],
                "code": commodity.get("code", ""),
                "buy_terminals": buy_terminals[:15],
                "sell_terminals": sell_terminals[:15],
            },
            indent=2,
        )

    async def refresh_market_data(self) -> str:
        """Force refresh all market data from UEX."""
        if not self._market:
            return "Market data not initialized."

        results = self._market.refresh_all(force=True)
        total = sum(results.values())

        self._update_guid_map_from_market()

        return json.dumps(
            {
                "status": "refreshed",
                "total_records": total,
                "details": {k: v for k, v in results.items() if v > 0},
            },
            indent=2,
        )

    # ==================================================================
    # Futures / Opportunities Tools
    # ==================================================================

    async def list_opportunities(
        self,
        status: str = "available",
        commodity: str = "",
        limit: int = 10,
    ) -> str:
        """List trade opportunities.

        Args:
            status: Filter — available, accepted, fulfilled, expired, dismissed, or all.
            commodity: Filter by commodity name (optional).
            limit: Maximum results (default 10).
        """
        if not self._futures:
            return "Futures module not initialized."
        results = self._futures.list_opportunities(
            status=status, commodity=commodity, limit=limit
        )
        return json.dumps({"opportunities": results, "count": len(results)}, indent=2)

    async def accept_opportunity(
        self,
        opportunity_id: str,
        create_trade_order: bool = True,
    ) -> str:
        """Accept a trade opportunity.

        Args:
            opportunity_id: The opportunity ID (or first 8 characters).
            create_trade_order: Create a linked trade order (default True).
        """
        if not self._futures:
            return "Futures module not initialized."
        result = self._futures.accept_opportunity(
            opp_id=opportunity_id, create_trade_order=create_trade_order
        )
        return json.dumps(result, indent=2)

    async def dismiss_opportunity(
        self,
        opportunity_id: str,
        reason: str = "",
    ) -> str:
        """Dismiss a trade opportunity.

        Args:
            opportunity_id: The opportunity ID (or first 8 characters).
            reason: Why you're dismissing it (optional).
        """
        if not self._futures:
            return "Futures module not initialized."
        result = self._futures.dismiss_opportunity(opp_id=opportunity_id, reason=reason)
        return json.dumps(result, indent=2)

    # ==================================================================
    # Investment Positions Tools
    # ==================================================================

    async def list_positions(
        self,
        status: str = "open",
        commodity: str = "",
        limit: int = 20,
    ) -> str:
        """List investment positions.

        Args:
            status: Filter — open, closed, or all.
            commodity: Filter by commodity name (optional).
            limit: Maximum results (default 20).
        """
        if not self._positions:
            return "Positions module not initialized."
        results = self._positions.list_positions(
            status=status, commodity=commodity, limit=limit
        )
        return json.dumps({"positions": results, "count": len(results)}, indent=2)

    async def get_portfolio_summary(self) -> str:
        """Get aggregated portfolio summary."""
        if not self._positions:
            return "Positions module not initialized."
        summary = self._positions.get_portfolio_summary()
        return json.dumps(summary, indent=2)

    async def close_position(
        self,
        position_id: str,
        sell_price: float,
        sell_location: str = "",
    ) -> str:
        """Manually close an open position.

        Args:
            position_id: The position ID (or first 8 characters).
            sell_price: Total aUEC received for the sale.
            sell_location: Where the sale happened (optional).
        """
        if not self._positions:
            return "Positions module not initialized."
        result = self._positions.close_position_manual(
            pos_id=position_id, sell_price=sell_price, sell_location=sell_location
        )
        return json.dumps(result, indent=2)

    async def adjust_position(
        self,
        position_id: str,
        quantity: float = 0,
        buy_price_per_unit: float = 0,
        notes: str = "",
    ) -> str:
        """Adjust a position's details.

        Args:
            position_id: The position ID (or first 8 characters).
            quantity: New quantity (0 = no change).
            buy_price_per_unit: New buy price per unit (0 = no change).
            notes: Reason for adjustment (optional).
        """
        if not self._positions:
            return "Positions module not initialized."
        result = self._positions.adjust_position(
            pos_id=position_id,
            quantity=quantity if quantity > 0 else None,
            buy_price=buy_price_per_unit if buy_price_per_unit > 0 else None,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    # ==================================================================
    # ==================================================================
    # Credits / Receivables & Payables Tools
    # ==================================================================

    async def create_credit(
        self,
        credit_type: str,
        counterparty: str,
        amount: float,
        description: str,
        item_type: str = "cash",
        item_name: str = "",
        due_date: str = "",
        notes: str = "",
    ) -> str:
        """Create a receivable or payable credit record.

        Args:
            credit_type: "receivable" (they owe you) or "payable" (you owe them).
            counterparty: Player name or organization.
            amount: Amount owed in aUEC.
            description: What the credit is for.
            item_type: Type — cash, ship, cargo, or service (default cash).
            item_name: Specific item name (optional).
            due_date: When payment is expected, ISO date (optional).
            notes: Additional notes (optional).
        """
        if not self._credits:
            return "Credits module not initialized."
        result = self._credits.create_credit(
            credit_type=credit_type,
            counterparty=counterparty,
            amount=amount,
            description=description,
            item_type=item_type,
            item_name=item_name,
            due_date=due_date,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    async def record_payment(
        self,
        credit_id: str,
        amount: float,
        notes: str = "",
    ) -> str:
        """Record a payment against a credit.

        Args:
            credit_id: The credit ID (or first 8 characters).
            amount: Payment amount in aUEC.
            notes: Payment notes (optional).
        """
        if not self._credits:
            return "Credits module not initialized."
        result = self._credits.record_payment(
            credit_id=credit_id, amount=amount, notes=notes
        )
        return json.dumps(result, indent=2)

    async def list_credits(
        self,
        credit_type: str = "",
        status: str = "",
        counterparty: str = "",
        limit: int = 20,
    ) -> str:
        """List credit records.

        Args:
            credit_type: Filter — receivable, payable, or empty for all.
            status: Filter — outstanding, partial, settled, written_off, or empty.
            counterparty: Filter by counterparty name (optional, partial match).
            limit: Maximum results (default 20).
        """
        if not self._credits:
            return "Credits module not initialized."
        results = self._credits.list_credits(
            credit_type=credit_type,
            status=status,
            counterparty=counterparty,
            limit=limit,
        )
        return json.dumps({"credits": results, "count": len(results)}, indent=2)

    async def get_credit_summary(self) -> str:
        """Get aggregated credit summary."""
        if not self._credits:
            return "Credits module not initialized."
        summary = self._credits.get_credit_summary()
        return json.dumps(summary, indent=2)

    async def write_off_credit(
        self,
        credit_id: str,
        reason: str = "",
    ) -> str:
        """Write off a credit as uncollectable.

        Args:
            credit_id: The credit ID (or first 8 characters).
            reason: Why the credit is being written off (optional).
        """
        if not self._credits:
            return "Credits module not initialized."
        result = self._credits.write_off_credit(credit_id=credit_id, reason=reason)
        return json.dumps(result, indent=2)

    # ==================================================================
    # Hauling / Cargo Transport Tools
    # ==================================================================

    async def log_haul(
        self,
        origin: str,
        destination: str,
        cargo_description: str,
        quantity: float = 0.0,
        quantity_unit: str = "scu",
        ship_name: str = "",
        fuel_cost: float = 0.0,
        other_costs: float = 0.0,
        revenue: float = 0.0,
        status: str = "delivered",
        notes: str = "",
    ) -> str:
        """Log a cargo transport trip.

        Args:
            origin: Starting location.
            destination: Delivery location.
            cargo_description: What was hauled.
            quantity: Amount of cargo (default 0).
            quantity_unit: Unit of measurement (default 'scu').
            ship_name: Ship used for transport (optional).
            fuel_cost: Fuel expenses in aUEC (default 0).
            other_costs: Other expenses in aUEC (default 0).
            revenue: Payment received in aUEC (default 0).
            status: in_transit, delivered, or cancelled (default delivered).
            notes: Additional notes (optional).
        """
        if not self._hauling:
            return "Hauling module not initialized."
        result = self._hauling.log_haul(
            origin=origin,
            destination=destination,
            cargo_description=cargo_description,
            quantity=quantity,
            quantity_unit=quantity_unit,
            ship_name=ship_name,
            fuel_cost=fuel_cost,
            other_costs=other_costs,
            revenue=revenue,
            status=status,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    async def complete_haul(
        self,
        haul_id: str,
        revenue: float = 0.0,
        fuel_cost: float = 0.0,
        other_costs: float = 0.0,
        notes: str = "",
    ) -> str:
        """Complete an in-transit haul.

        Args:
            haul_id: The haul ID (or first 8 characters).
            revenue: Additional revenue in aUEC (default 0).
            fuel_cost: Additional fuel cost in aUEC (default 0).
            other_costs: Additional other costs in aUEC (default 0).
            notes: Completion notes (optional).
        """
        if not self._hauling:
            return "Hauling module not initialized."
        result = self._hauling.complete_haul(
            haul_id=haul_id,
            revenue=revenue,
            fuel_cost=fuel_cost,
            other_costs=other_costs,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    async def list_hauls(
        self,
        status: str = "",
        limit: int = 20,
    ) -> str:
        """List cargo hauls.

        Args:
            status: Filter — in_transit, delivered, cancelled, or empty for all.
            limit: Maximum results (default 20).
        """
        if not self._hauling:
            return "Hauling module not initialized."
        results = self._hauling.list_hauls(status=status, limit=limit)
        return json.dumps({"hauls": results, "count": len(results)}, indent=2)

    async def get_hauling_summary(
        self,
        days_back: int = 30,
    ) -> str:
        """Get aggregated hauling summary.

        Args:
            days_back: Number of days to look back (default 30).
        """
        if not self._hauling:
            return "Hauling module not initialized."
        summary = self._hauling.get_hauling_summary(days_back=days_back)
        return json.dumps(summary, indent=2)

    # ==================================================================
    # Inventory / Warehousing Tools (Stub)
    # ==================================================================

    async def report_inventory(
        self,
        item_name: str,
        quantity: float,
        location: str,
        quantity_unit: str = "scu",
        estimated_value: float = 0.0,
        notes: str = "",
    ) -> str:
        """Report or update inventory at a location.

        Args:
            item_name: Name of the item or commodity.
            quantity: Current quantity at that location.
            location: Where the inventory is stored.
            quantity_unit: Unit of measurement (default 'scu').
            estimated_value: Estimated total value in aUEC (default 0).
            notes: Additional notes (optional).
        """
        if not self._inventory:
            return "Inventory module not initialized."
        result = self._inventory.report_inventory(
            item_name=item_name,
            quantity=quantity,
            location=location,
            quantity_unit=quantity_unit,
            estimated_value=estimated_value,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    async def get_inventory(
        self,
        item_name: str = "",
        location: str = "",
        limit: int = 30,
    ) -> str:
        """List inventory items.

        Args:
            item_name: Filter by item name (optional, partial match).
            location: Filter by location (optional, partial match).
            limit: Maximum results (default 30).
        """
        if not self._inventory:
            return "Inventory module not initialized."
        results = self._inventory.get_inventory(
            item_name=item_name, location=location, limit=limit
        )
        return json.dumps({"inventory": results, "count": len(results)}, indent=2)

    # ==================================================================
    # Production Tools (Stub)
    # ==================================================================

    async def log_production(
        self,
        output_name: str,
        output_quantity: float,
        output_value: float = 0.0,
        inputs: str = "",
        location: str = "",
        status: str = "completed",
        notes: str = "",
    ) -> str:
        """Log a production run.

        Args:
            output_name: Name of the produced item/commodity.
            output_quantity: Amount produced.
            output_value: Estimated value of the output in aUEC (default 0).
            inputs: Comma-separated inputs as "name:qty:cost" (optional).
            location: Where production happened (optional).
            status: in_progress, completed, or cancelled (default completed).
            notes: Additional notes (optional).
        """
        if not self._production:
            return "Production module not initialized."
        result = self._production.log_production(
            output_name=output_name,
            output_quantity=output_quantity,
            output_value=output_value,
            inputs=inputs,
            location=location,
            status=status,
            notes=notes,
        )
        return json.dumps(result, indent=2)

    async def get_production_summary(self) -> str:
        """Get aggregated production summary."""
        if not self._production:
            return "Production module not initialized."
        summary = self._production.get_production_summary()
        return json.dumps(summary, indent=2)

    # ==================================================================
    # Three-Statement Financial Reports
    # ==================================================================

    @tool(
        description=(
            "Generate an Income Statement (Operations Report). Shows Revenue, "
            "Cost of Goods Sold (COGS), Gross Margin, Operating Expenses (OpEx), "
            "Net Operating Profit, and per-activity margin breakdown. "
            "Period can be 'week', 'month', 'quarter', 'year', or 'all'."
        )
    )
    async def get_income_statement(self, period: str = "month") -> str:
        """Generate income statement for the given period."""
        if not self._store:
            return "Accountant not initialized."

        cutoff = self._period_to_cutoff(period)
        txns = self._store.query_transactions(start=cutoff, limit=50000)

        result = generate_income_statement(txns, period)
        return json.dumps(result, indent=2)

    @tool(
        description=(
            "Generate a Balance Sheet (Hangar Report). Shows total assets "
            "(cash, ships, components, vehicles, cargo, inventory, "
            "receivables), liabilities (payables), and equity (net worth)."
        )
    )
    async def get_balance_sheet(self) -> str:
        """Generate current balance sheet."""
        if not self._store:
            return "Accountant not initialized."

        balance = self._store.get_balance()
        assets = self._store.query_assets(status="active", limit=500)
        positions = self._store.query_positions(status="open", limit=500)

        inventory = self._store.query_inventory(limit=500)

        credits = self._store.query_credits(status="active", limit=500)

        result = generate_balance_sheet(
            balance=balance,
            assets=assets,
            open_positions=positions,
            inventory=inventory,
            credits=credits,
        )
        return json.dumps(result, indent=2)

    async def get_cash_flow(self, period: str = "month") -> str:
        """Generate cash flow statement for the given period."""
        if not self._store:
            return "Accountant not initialized."

        cutoff = self._period_to_cutoff(period)
        txns = self._store.query_transactions(start=cutoff, limit=50000)

        result = generate_cash_flow(txns, period)
        return json.dumps(result, indent=2)

    # ==================================================================
    # Asset / Fleet Management Tools
    # ==================================================================

    @tool(
        description=(
            "Register a new capital asset — ship, vehicle, component, or equipment. "
            "Creates the asset record and an optional CAPEX transaction. "
            "For components, provide parent_asset_id to link to the parent ship. "
            "If purchase_price is 0 or omitted for a ship/vehicle, the price is "
            "automatically looked up via UEXCorp (if available)."
        )
    )
    async def register_asset(
        self,
        asset_type: str,
        name: str,
        purchase_price: float = 0,
        ship_model: str = "",
        location: str = "",
        parent_asset_id: str = "",
        notes: str = "",
    ) -> str:
        """Register a new capital asset."""
        if not self._assets:
            return "Asset manager not initialized."

        # Auto-lookup price via UEXCorp if not provided
        price_source = "manual"
        if purchase_price <= 0 and asset_type.lower().strip() in ("ship", "vehicle"):
            uex_price = self._lookup_ship_price(name)
            if uex_price:
                purchase_price = uex_price
                price_source = "uex"
                logger.info(
                    "Auto-populated price for %s: %s (UEXCorp)",
                    name,
                    self._format_auec(uex_price),
                )

        asset, txn = self._assets.register_asset(
            asset_type=asset_type.lower().strip(),
            name=name,
            purchase_price=purchase_price,
            ship_model=ship_model,
            location=location,
            parent_asset_id=parent_asset_id,
            notes=notes,
        )

        result = {
            "asset_id": asset.id,
            "name": asset.name,
            "type": asset.asset_type,
            "purchase_price": self._format_auec(asset.purchase_price),
            "status": asset.status,
        }
        if price_source == "uex":
            result["price_source"] = "UEXCorp (auto-lookup)"
        elif purchase_price <= 0:
            result["price_note"] = (
                "Price unknown. Tell me the purchase price to update it, "
                "or install UEXCorp for automatic price lookup."
            )
        if txn:
            result["transaction_id"] = txn.id
        return json.dumps(result, indent=2)

    @tool(
        description=(
            "Update an existing asset's details — name, type, price, location, "
            "market value, or notes. Only provided fields are changed. "
            "Use this when the player says 'rename my ship', 'update the price', "
            "'change location of my Prospector', etc."
        )
    )
    async def update_asset(
        self,
        asset_id: str,
        name: str | None = None,
        asset_type: str | None = None,
        ship_model: str | None = None,
        location: str | None = None,
        purchase_price: float | None = None,
        estimated_market_value: float | None = None,
        notes: str | None = None,
    ) -> str:
        """Update fields on an existing asset."""
        if not self._assets:
            return "Asset manager not initialized."

        # Coerce numeric fields — LLM may pass strings despite type hints
        if purchase_price is not None:
            purchase_price = float(purchase_price)
        if estimated_market_value is not None:
            estimated_market_value = float(estimated_market_value)

        asset, changes = self._assets.update_asset(
            asset_id=asset_id,
            name=name,
            asset_type=asset_type,
            ship_model=ship_model,
            location=location,
            purchase_price=purchase_price,
            estimated_market_value=estimated_market_value,
            notes=notes,
        )

        if not asset:
            return json.dumps({"error": f"Asset {asset_id} not found"})
        if not changes:
            return json.dumps({"message": "No changes made", "asset_id": asset_id})

        return json.dumps(
            {
                "asset_id": asset.id,
                "name": asset.name,
                "type": asset.asset_type,
                "purchase_price": self._format_auec(asset.purchase_price),
                "market_value": self._format_auec(
                    asset.estimated_market_value or asset.purchase_price
                ),
                "changes": changes,
            },
            indent=2,
        )

    @tool(
        description=(
            "Record the sale of a registered asset. Calculates realized profit "
            "or loss (sell price minus purchase price) and creates an income "
            "transaction."
        )
    )
    async def sell_asset(
        self,
        asset_id: str,
        sell_price: float,
        location: str = "",
    ) -> str:
        """Sell a registered asset."""
        if not self._assets:
            return "Asset manager not initialized."

        asset, txn, msg = self._assets.sell_asset(
            asset_id=asset_id,
            sell_price=sell_price,
            location=location,
        )
        if not asset:
            return msg

        result = {"message": msg, "asset_id": asset.id}
        if txn:
            result["transaction_id"] = txn.id
        return json.dumps(result, indent=2)

    @tool(
        description=(
            "Delete a registered asset without creating a sale transaction. "
            "Use when the player says 'delete that asset', 'remove that entry', "
            "or wants to undo an accidental registration. For actual sales, "
            "use sell_asset instead."
        )
    )
    async def delete_asset(self, asset_id: str) -> str:
        """Delete an asset record entirely.

        Args:
            asset_id: The asset ID (or first 8 characters).
        """
        if not self._store:
            return "Accountant not initialized."

        deleted = self._store.delete_asset(asset_id)
        if not deleted:
            return json.dumps({"error": f"Asset {asset_id} not found"})

        return json.dumps(
            {
                "status": "deleted",
                "asset_id": deleted.id,
                "name": deleted.name,
                "type": deleted.asset_type,
            }
        )

    async def list_fleet(
        self,
        asset_type: str = "",
        status: str = "active",
    ) -> str:
        """List registered assets with optional filters."""
        if not self._assets:
            return "Asset manager not initialized."

        assets = self._assets.list_assets(
            asset_type=asset_type.lower().strip() if asset_type else "",
            status=status.lower().strip() if status else "active",
        )

        if not assets:
            return json.dumps({"assets": [], "message": "No assets found."})

        result = []
        for a in assets:
            result.append(
                {
                    "id": a.id,
                    "name": a.name,
                    "type": a.asset_type,
                    "status": a.status,
                    "purchase_price": round(a.purchase_price, 2),
                    "market_value": round(
                        a.estimated_market_value or a.purchase_price, 2
                    ),
                    "location": a.location or "",
                }
            )

        return json.dumps({"assets": result, "count": len(result)}, indent=2)

    async def get_fleet_summary(self) -> str:
        """Get aggregated fleet summary."""
        if not self._assets:
            return "Asset manager not initialized."
        summary = self._assets.get_fleet_summary()
        return json.dumps(summary, indent=2)

    # ==================================================================
    # Accounting Dashboard Window Tools
    # ==================================================================

    @tool(
        description=(
            "Open the standalone accounting dashboard in the default browser. "
            "Interactive tabs: Ledger, Fleet, Operations (Income Statement), "
            "Cash Flow, Balance Sheet, Portfolio, and Opportunities. "
            "The user can interact directly — sorting, filtering, and "
            "navigating are built into the interface."
        )
    )
    async def open_accounting_window(self) -> str:
        """Open the accounting dashboard window."""
        if not self._ui_window:
            return "Accounting window not initialized."

        self._ui_window.open()
        lan_url = self._ui_server.lan_url if self._ui_server else ""
        result = {
            "status": "opened",
            "message": "Accounting dashboard opened in your browser.",
        }
        if lan_url and "127.0.0.1" not in lan_url:
            result["lan_url"] = lan_url
            result["message"] += (
                f" To access from a tablet or phone on the same network, "
                f"go to {lan_url} — or scan the QR code in the dashboard footer."
            )
        return json.dumps(result)

    @tool(description="Close the standalone accounting dashboard window.")
    async def close_accounting_window(self) -> str:
        """Close the accounting dashboard window."""
        if not self._ui_window:
            return "Accounting window not initialized."

        self._ui_window.close()
        return json.dumps(
            {
                "status": "closed",
                "message": "Accounting dashboard closed.",
            }
        )

    # ==================================================================
    # Planning & Forecasting Tools
    # ==================================================================

    @tool(
        description=(
            "Calculate break-even analysis for a registered asset. Shows purchase "
            "price, net profit earned so far, average daily profit, estimated days "
            "and date to break even, and current ROI percentage."
        )
    )
    async def get_break_even(self, asset_id: str) -> str:
        """Break-even analysis for an asset."""
        if not self._planning or not self._store:
            return "Planning engine not initialized."

        asset = self._store.get_asset(asset_id)
        if not asset:
            return f"Asset {asset_id} not found."

        txns = self._store.query_transactions(linked_asset_id=asset_id, limit=50000)

        result = self._planning.break_even_analysis(asset, txns)
        return json.dumps(result, indent=2)

    @tool(
        description=(
            "Compare profitability across gameplay activities (trading, "
            "bounty hunting, missions, salvage, hauling). Shows revenue, costs, "
            "net profit, and margin percentage per activity, sorted by profit. "
            "Period can be 'week', 'month', 'quarter', 'year', or 'all'."
        )
    )
    async def get_activity_roi(self, period: str = "month") -> str:
        """Activity ROI comparison."""
        if not self._planning or not self._store:
            return "Planning engine not initialized."

        cutoff = self._period_to_cutoff(period)
        txns = self._store.query_transactions(start=cutoff, limit=50000)

        result = self._planning.activity_roi_comparison(txns)
        return json.dumps({"period": period, "activities": result}, indent=2)

    @tool(
        description=(
            "Run a what-if scenario projection. Supported scenarios: "
            "'upgrade' (cost, improvement_pct, activity) — payback time for an upgrade; "
            "'ship_purchase' (price, activity) — payback time for a new ship; "
            "'trade' (buy_price, sell_price, quantity, fuel_cost, other_costs) — "
            "single trade profit calculation."
        )
    )
    async def what_if(
        self,
        scenario: str,
        parameters: str,
    ) -> str:
        """Run a what-if scenario.

        Args:
            scenario: Scenario type ('upgrade', 'ship_purchase', 'trade').
            parameters: JSON string of scenario parameters.
        """
        if not self._planning or not self._store:
            return "Planning engine not initialized."

        try:
            params = json.loads(parameters)
        except json.JSONDecodeError:
            return "Invalid parameters — provide a valid JSON string."

        txns = self._store.query_transactions(limit=50000)

        result = self._planning.what_if_scenario(
            scenario_type=scenario.lower().strip(),
            parameters=params,
            transactions=txns,
        )
        return json.dumps(result, indent=2)

    # ==================================================================
    # Internal Helpers
    # ==================================================================

    def _period_to_cutoff(self, period: str) -> datetime:
        """Convert a period label to a UTC datetime cutoff."""
        now = datetime.now(timezone.utc)
        period = period.lower().strip()
        if period == "today":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            return now - timedelta(days=7)
        elif period == "month":
            return now - timedelta(days=30)
        elif period == "quarter":
            return now - timedelta(days=90)
        elif period == "year":
            return now - timedelta(days=365)
        else:
            # "all" — go back 10 years
            return now - timedelta(days=3650)
