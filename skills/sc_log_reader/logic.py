"""
SC_LogReader - Layer 2: State Logic

Combines atomic states from Layer 3 into derived states and events.
Can run standalone or be imported by Layer 1.

Author: Mallachi
"""

from __future__ import annotations

import copy
import json
import logging
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from debug_emitter import emit as _debug_emit
from ledger import LedgerEntry, TradeLedger
from parser import LogEvent, LogParser


logger = logging.getLogger(__name__)


@dataclass
class DerivedEvent:
    """Represents a derived event produced by combining atomic states."""

    event_type: str
    timestamp: datetime
    message: str
    source_states: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "source_states": self.source_states,
        }


@dataclass
class Rule:
    """
    Declarative rule for deriving events from state combinations.

    A rule fires when:
    1. The trigger_key changes (if specified)
    2. All conditions are satisfied
    """

    name: str
    event_type: str
    message_template: str
    trigger_key: str | None = None  # State key that triggers evaluation
    conditions: list[tuple[str, str, Any]] | None = None  # [(key, op, value), ...]

    def evaluate(
        self,
        states: dict[str, Any],
        changed_key: str | None = None,
    ) -> bool:
        """Check if the rule should fire given current states."""
        # If rule has a trigger, only evaluate when that key changes
        if self.trigger_key and changed_key != self.trigger_key:
            return False

        # Check all conditions
        if self.conditions:
            for key, op, expected in self.conditions:
                actual = states.get(key)
                if not self._check_condition(actual, op, expected):
                    return False

        return True

    def _check_condition(self, actual: Any, op: str, expected: Any) -> bool:
        """Evaluate a single condition."""
        if op == "==":
            return actual == expected
        if op == "!=":
            return actual != expected
        if op == "is":
            return actual is expected
        if op == "is_not":
            return actual is not expected
        if op == "in":
            return actual in expected
        if op == "not_in":
            return actual not in expected
        if op == "exists":
            return actual is not None
        if op == "not_exists":
            return actual is None
        return False

    def format_message(self, states: dict[str, Any]) -> str:
        """Generate the event message using current states."""
        try:
            return self.message_template.format(**states)
        except KeyError:
            return self.message_template


class StateLogic:
    """
    Combines atomic states into derived states and events.

    Subscribes to Layer 3 (LogParser) for state changes and raw events.
    Evaluates rules to produce derived events for Layer 1.
    """

    def __init__(self, parser: LogParser) -> None:
        self._parser = parser
        self._rules: list[Rule] = []
        self._derived_state: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._event_subscribers: list[Callable[[DerivedEvent], None]] = []
        self._raw_event_subscribers: list[Callable[[LogEvent], None]] = []

        # File output (optional)
        self._file_output_enabled = False
        self._file_output_path: Path | None = None
        self._event_history: list[dict[str, Any]] = []

        # Mission tracking
        self._active_missions: dict[str, dict[str, Any]] = {}

        # Hangar sequencing: tracks context when hangar_ready fires.
        # None = no pending hangar event
        self._pending_hangar: str | None = None  # unused; kept for save_state compat

        # Location arrival dedup: suppress consecutive same-location events
        # (e.g. two location_change Orison without leaving first).
        # Resets when a *different* location fires.
        self._last_arrived_location: str | None = None

        # Trade ledger: pending item shop transactions awaiting confirmation
        self._pending_transactions: list[dict] = []
        self._ledger: TradeLedger | None = None
        # Stale pending cleanup interval (seconds)
        self._pending_max_age_seconds = 10.0

        # Setup default rules
        self._setup_default_rules()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def start(self) -> None:
        """Start listening to Layer 3."""
        self._parser.subscribe(self._on_raw_event)
        self._parser.subscribe_state(self._on_state_change)
        logger.info("StateLogic started")

    def stop(self) -> None:
        """Stop and flush outputs."""
        self._flush_file_output()
        logger.info("StateLogic stopped")

    def subscribe(self, callback: Callable[[DerivedEvent], None]) -> None:
        """Subscribe to derived events."""
        self._event_subscribers.append(callback)

    def subscribe_raw(self, callback: Callable[[LogEvent], None]) -> None:
        """Subscribe to raw events from Layer 3 (pass-through)."""
        self._raw_event_subscribers.append(callback)

    def get_derived_state(self, key: str | None = None) -> dict[str, Any] | Any:
        """Get derived state. If key provided, returns that value; else returns all."""
        with self._lock:
            if key is None:
                return self._derived_state.copy()
            return self._derived_state.get(key)

    def get_combined_state(self) -> dict[str, Any]:
        """Get both atomic (from parser) and derived states combined."""
        atomic = self._parser.get_state()
        with self._lock:
            derived = self._derived_state.copy()
        return {**atomic, **derived}

    def get_active_missions(self) -> dict[str, dict[str, Any]]:
        """Get currently tracked missions (deep copy for safety)."""
        with self._lock:
            return copy.deepcopy(self._active_missions)

    def set_ledger(self, ledger: TradeLedger) -> None:
        """Inject the trade ledger (called by main.py during init)."""
        self._ledger = ledger

    def add_rule(self, rule: Rule) -> None:
        """Add a custom rule."""
        self._rules.append(rule)

    def save_state(self) -> dict[str, Any]:
        """Return logic state as a serializable dict for persistence."""
        with self._lock:
            return {
                "active_missions": copy.deepcopy(self._active_missions),
                "derived_state": self._derived_state.copy(),
                "pending_hangar": self._pending_hangar,
                "pending_transactions": copy.deepcopy(self._pending_transactions),
            }

    def load_state(self, data: dict[str, Any]) -> None:
        """Restore logic state from persisted data."""
        with self._lock:
            self._active_missions = data.get("active_missions", {})
            self._derived_state = data.get("derived_state", {})
            # Migrate legacy bool format to new str | None format
            raw = data.get("pending_hangar")
            if raw is True:
                self._pending_hangar = "hangar_access"
            elif isinstance(raw, str):
                self._pending_hangar = raw
            else:
                self._pending_hangar = None
            self._pending_transactions = data.get("pending_transactions", [])

    def on_new_session(self) -> None:
        """Clear mission-related state on new game session.

        Called when session_start is detected. Clears mission tracking,
        pending transactions, and mission-related parser states. Other state
        (location, ship, etc.) is preserved since it persists in the game
        between sessions. The trade ledger is never cleared.
        """
        with self._lock:
            self._active_missions.clear()
            self._derived_state["active_mission_count"] = 0
            self._pending_transactions.clear()

        # Clear mission-related parser states
        mission_state_keys = [
            "current_objective",
            "last_contract_accepted",
            "last_contract_accepted_id",
            "last_contract_completed",
            "last_contract_completed_id",
            "last_contract_failed",
            "last_contract_failed_id",
        ]
        for key in mission_state_keys:
            self._parser.clear_state(key)

        # Clear injury state — session_start fires on respawn, player spawns fully healed
        for key in list(self._parser.get_state().keys()):
            if key.startswith("injury_"):
                self._parser.clear_state(key)

        logger.info("New session: mission and injury state cleared")

    def enable_file_output(self, path: str | Path) -> None:
        """Enable JSON file output for debugging."""
        self._file_output_path = Path(path)
        self._file_output_enabled = True
        logger.info("StateLogic file output enabled: %s", self._file_output_path)

    def disable_file_output(self) -> None:
        """Disable JSON file output."""
        self._flush_file_output()
        self._file_output_enabled = False
        self._file_output_path = None

    # -------------------------------------------------------------------------
    # Injury Helpers
    # -------------------------------------------------------------------------

    def _has_active_injuries(self) -> bool:
        """Check if any injury_* state key has a non-None value."""
        state = self._parser.get_state()
        return any(v is not None for k, v in state.items() if k.startswith("injury_"))

    def _get_active_injuries(self) -> dict[str, str]:
        """Return {body_part: severity} for all active injuries."""
        state = self._parser.get_state()
        injuries: dict[str, str] = {}
        for k, v in state.items():
            if k.startswith("injury_") and v is not None:
                part = k[len("injury_"):]
                injuries[part] = v
        return injuries

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_raw_event(self, event: LogEvent) -> None:
        """Handle raw events from Layer 3."""
        # New session — clear mission tracking
        if event.event_type == "session_start":
            self.on_new_session()

        # Track missions
        self._track_mission(event)

        # Track trade transactions
        self._on_trade_event(event)

        # Handle event-based derived events (not state-based)
        self._handle_event_derived(event)

        # Update derived states based on events
        self._update_derived_state(event)

        # Forward to subscribers
        for callback in self._raw_event_subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception("Error in raw event callback")

    def _handle_event_derived(self, event: LogEvent) -> None:
        """Generate derived events from raw events (not state-based)."""
        if event.event_type == "hangar_ready":
            self._emit_derived_event(
                "hangar_access",
                "Hangar access granted",
                {},
            )

        # Location arrival — event-driven so leaving A → B → A still fires.
        # But consecutive same-location events (without leaving) are suppressed.
        if event.event_type == "location_change":
            location_name = self._parser.get_state("location_name")
            if location_name and location_name != "INVALID LOCATION ID":
                if location_name != self._last_arrived_location:
                    self._last_arrived_location = location_name
                    self._emit_derived_event(
                        "location_arrived",
                        f"Arrived at: {location_name}",
                        {"location_name": location_name},
                    )

        # Station departure — disabled pending reliable log signal.
        # AImodule_ATC removed in PTU; replacement fires on terminal use.
        # if event.event_type == "station_departed":
        #     self._last_arrived_location = None
        #     self._emit_derived_event(
        #         "location",
        #         "Departed station",
        #         {},
        #     )

    def _on_state_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Handle state changes from Layer 3 and evaluate rules."""
        # Injury reminder: fire whenever the player enters any armistice zone
        # (direct entry or returning from a hangar), so they don't forget to heal.
        if key == "in_armistice" and new_value is True:
            injuries = self._get_active_injuries()
            if injuries:
                parts = ", ".join(
                    f"{severity} ({part})" for part, severity in injuries.items()
                )
                self._emit_derived_event(
                    "health_injury_reminder",
                    f"Injury reminder: {parts}",
                    {"active_injuries": injuries},
                )

        current_states = self.get_combined_state()

        for rule in self._rules:
            if rule.evaluate(current_states, changed_key=key):
                self._fire_rule(rule, current_states)

    def _fire_rule(self, rule: Rule, states: dict[str, Any]) -> None:
        """Fire a rule and produce a derived event."""
        _debug_emit(
            "logic",
            "rule_fired",
            {
                "rule": rule.name,
                "event_type": rule.event_type,
                "message": rule.format_message(states),
                "conditions": [
                    {"key": k, "op": op, "expected": v, "actual": states.get(k)}
                    for k, op, v in (rule.conditions or [])
                ],
            },
        )

        event = DerivedEvent(
            event_type=rule.event_type,
            timestamp=datetime.now(),
            message=rule.format_message(states),
            source_states={k: states.get(k) for k in self._get_rule_keys(rule)},
        )

        # Record for file output
        if self._file_output_enabled:
            self._event_history.append(event.to_dict())
            if len(self._event_history) % 10 == 0:
                self._flush_file_output()

        # Notify subscribers
        for callback in self._event_subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception("Error in derived event callback")

    def _get_rule_keys(self, rule: Rule) -> list[str]:
        """Extract state keys referenced by a rule."""
        keys = []
        if rule.trigger_key:
            keys.append(rule.trigger_key)
        if rule.conditions:
            keys.extend(key for key, _, _ in rule.conditions)
        return keys

    def _emit_derived_event(
        self,
        event_type: str,
        message: str,
        source_states: dict[str, Any],
    ) -> None:
        """Emit a derived event to all subscribers."""
        event = DerivedEvent(
            event_type=event_type,
            timestamp=datetime.now(),
            message=message,
            source_states=source_states,
        )

        _debug_emit(
            "logic",
            "derived_event",
            {
                "event_type": event_type,
                "message": message,
                "source_states": source_states,
            },
        )

        # Record for file output
        if self._file_output_enabled:
            self._event_history.append(event.to_dict())
            if len(self._event_history) % 10 == 0:
                self._flush_file_output()

        # Notify subscribers
        for callback in self._event_subscribers:
            try:
                callback(event)
            except Exception:
                logger.exception("Error in derived event callback")

    # -------------------------------------------------------------------------
    # Mission Tracking
    # -------------------------------------------------------------------------

    def _track_mission(self, event: LogEvent) -> None:
        """Track mission lifecycle and generate derived events."""
        data = event.data
        mission_id = data.get("mission_id")

        if event.event_type == "contract_accepted" and mission_id:
            mission_name = data.get("mission_name", "Unknown")
            with self._lock:
                self._active_missions[mission_id] = {
                    "mission_name": mission_name,
                    "status": "active",
                    "accepted_at": event.timestamp.isoformat(),
                    "current_objective": None,
                }
                self._derived_state["active_mission_count"] = len(self._active_missions)
            # Generate derived event for notification
            self._emit_derived_event(
                "mission_accepted",
                f"Contract accepted: {mission_name}",
                {"mission_name": mission_name, "mission_id": mission_id},
            )

        elif event.event_type == "objective_new" and mission_id:
            objective = data.get("objective", "Unknown")
            with self._lock:
                if mission_id in self._active_missions:
                    self._active_missions[mission_id]["current_objective"] = objective
            # Generate derived event for notification
            self._emit_derived_event(
                "mission_objective_new",
                f"New objective: {objective}",
                {"objective": objective, "mission_id": mission_id},
            )

        elif event.event_type == "contract_complete" and mission_id:
            mission_name = data.get("mission_name", "Unknown")
            with self._lock:
                if mission_id in self._active_missions:
                    mission_name = self._active_missions[mission_id].get(
                        "mission_name", mission_name
                    )
                    del self._active_missions[mission_id]
                    self._derived_state["active_mission_count"] = len(
                        self._active_missions
                    )
            # Generate derived event for notification
            self._emit_derived_event(
                "mission_complete",
                f"Contract complete: {mission_name}",
                {"mission_name": mission_name, "mission_id": mission_id},
            )

        elif event.event_type == "contract_failed" and mission_id:
            mission_name = data.get("mission_name", "Unknown")
            with self._lock:
                if mission_id in self._active_missions:
                    mission_name = self._active_missions[mission_id].get(
                        "mission_name", mission_name
                    )
                    del self._active_missions[mission_id]
                    self._derived_state["active_mission_count"] = len(
                        self._active_missions
                    )
            # Generate derived event for notification
            self._emit_derived_event(
                "mission_failed",
                f"Contract failed: {mission_name}",
                {"mission_name": mission_name, "mission_id": mission_id},
            )

    # -------------------------------------------------------------------------
    # Trade Ledger
    # -------------------------------------------------------------------------

    def _on_trade_event(self, event: LogEvent) -> None:
        """Handle shop and commodity trade events."""
        et = event.event_type

        if et in ("shop_buy", "shop_sell"):
            # Item shop: store as pending until confirmed.
            # Use datetime.now() for staleness tracking — event.timestamp
            # is UTC from the log, but _cleanup_stale_pending compares
            # against datetime.now() (local time).
            with self._lock:
                self._cleanup_stale_pending()

                # Deduplicate: game sometimes logs the same request twice.
                # Skip if an identical pending already exists.
                shop_id = event.data.get("shop_id", "")
                kiosk_id = event.data.get("kiosk_id", "")
                item_key = event.data.get(
                    "item_guid", event.data.get("resource_guid", "")
                )
                already_pending = any(
                    p["event_type"] == et
                    and p["data"].get("shop_id") == shop_id
                    and p["data"].get("kiosk_id") == kiosk_id
                    and p["data"].get("item_guid", p["data"].get("resource_guid", ""))
                    == item_key
                    for p in self._pending_transactions
                )
                if already_pending:
                    logger.info(
                        "Trade: skipping duplicate pending %s (shop=%s kiosk=%s)",
                        et,
                        shop_id,
                        kiosk_id,
                    )
                else:
                    self._pending_transactions.append(
                        {
                            "event_type": et,
                            "received_at": datetime.now().isoformat(),
                            "event_timestamp": event.timestamp.isoformat(),
                            "data": event.data.copy(),
                        }
                    )
                    logger.info(
                        "Trade: stored pending %s (shop=%s kiosk=%s) — %d pending",
                        et,
                        shop_id,
                        kiosk_id,
                        len(self._pending_transactions),
                    )

        elif et in ("commodity_buy", "commodity_sell"):
            # Commodity: write immediately (no confirmation log pattern)
            with self._lock:
                logger.info("Trade: immediate write for %s", et)
                self._write_trade_to_ledger(et, event.data, event.timestamp)

        elif et == "shop_transaction_result":
            self._resolve_pending_transaction(event)

    def _resolve_pending_transaction(self, event: LogEvent) -> None:
        """Match a shop_transaction_result to a pending request and write to ledger."""
        data = event.data
        result = data.get("result", "")
        tx_type = data.get("transaction_type", "")
        shop_id = data.get("shop_id", "")
        kiosk_id = data.get("kiosk_id", "")

        # Map confirmation type to request event type
        expected_type = {
            "Buying": "shop_buy",
            "Selling": "shop_sell",
        }.get(tx_type)

        if not expected_type:
            logger.warning(
                "Trade: unknown transaction_type=%r in shop_transaction_result",
                tx_type,
            )
            return

        with self._lock:
            self._cleanup_stale_pending()
            logger.info(
                "Trade: resolving %s result=%s shop=%s kiosk=%s — %d pending",
                tx_type,
                result,
                shop_id,
                kiosk_id,
                len(self._pending_transactions),
            )
            # Find matching pending transaction (most recent first)
            for i in range(len(self._pending_transactions) - 1, -1, -1):
                pending = self._pending_transactions[i]
                p_data = pending["data"]
                if (
                    pending["event_type"] == expected_type
                    and p_data.get("shop_id") == shop_id
                    and p_data.get("kiosk_id") == kiosk_id
                ):
                    self._pending_transactions.pop(i)
                    if result == "Success":
                        logger.info("Trade: match found, writing to ledger")
                        self._write_trade_to_ledger(
                            pending["event_type"],
                            p_data,
                            event.timestamp,
                        )
                    else:
                        logger.info(
                            "Trade: match found but result=%s, discarding", result
                        )
                    return

            # No match found
            logger.warning(
                "Trade: no matching pending for %s shop=%s kiosk=%s",
                expected_type,
                shop_id,
                kiosk_id,
            )

    def _write_trade_to_ledger(
        self,
        event_type: str,
        data: dict,
        timestamp: datetime,
    ) -> None:
        """Create a LedgerEntry and append it to the ledger file."""
        if not self._ledger:
            logger.warning("Trade: _write_trade_to_ledger called but ledger is None")
            return

        location = self._parser.get_state("location_name") or "Unknown"

        if event_type in ("shop_buy", "shop_sell"):
            entry = LedgerEntry(
                timestamp=timestamp.isoformat(),
                location=location,
                transaction="purchase" if event_type == "shop_buy" else "sale",
                category="item",
                item_name=data.get("item_name"),
                item_guid=data.get("item_guid", ""),
                price=data.get("price", 0.0),
                quantity=data.get("quantity", 1),
                quantity_unit="units",
                player_id=data.get("player_id", ""),
                shop_id=data.get("shop_id", ""),
                kiosk_id=data.get("kiosk_id", ""),
                shop_name=data.get("shop_name", ""),
            )
        elif event_type == "commodity_buy":
            entry = LedgerEntry(
                timestamp=timestamp.isoformat(),
                location=location,
                transaction="purchase",
                category="commodity",
                item_name=None,
                item_guid=data.get("resource_guid", ""),
                price=data.get("price", 0.0),
                quantity=data.get("quantity_cscu", 0.0),
                quantity_unit="cscu",
                player_id=data.get("player_id", ""),
                shop_id=data.get("shop_id", ""),
                kiosk_id=data.get("kiosk_id", ""),
                shop_name=data.get("shop_name", ""),
            )
        elif event_type == "commodity_sell":
            entry = LedgerEntry(
                timestamp=timestamp.isoformat(),
                location=location,
                transaction="sale",
                category="commodity",
                item_name=None,
                item_guid=data.get("resource_guid", ""),
                price=data.get("price", 0.0),
                quantity=data.get("quantity", 0),
                quantity_unit="scu",
                player_id=data.get("player_id", ""),
                shop_id=data.get("shop_id", ""),
                kiosk_id=data.get("kiosk_id", ""),
                shop_name=data.get("shop_name", ""),
            )
        else:
            return

        self._ledger.append(entry)
        logger.info(
            "Trade: ledger entry written — %s %s %s at %s",
            entry.transaction,
            entry.category,
            entry.item_name or entry.item_guid,
            entry.location,
        )

    def _cleanup_stale_pending(self) -> None:
        """Remove pending transactions older than the max age.

        Must be called while self._lock is held.
        """
        if not self._pending_transactions:
            return

        cutoff_dt = datetime.now() - timedelta(seconds=self._pending_max_age_seconds)

        kept = []
        for t in self._pending_transactions:
            received_at_str = t.get("received_at")
            if not received_at_str:
                # No timestamp — discard rather than silently keep
                continue
            try:
                received_dt = datetime.fromisoformat(received_at_str)
            except ValueError:
                continue
            if received_dt >= cutoff_dt:
                kept.append(t)

        removed = len(self._pending_transactions) - len(kept)
        self._pending_transactions = kept
        if removed:
            logger.info("Trade: cleanup removed %d stale pending entries", removed)

    # -------------------------------------------------------------------------
    # Derived State Updates
    # -------------------------------------------------------------------------

    def _update_derived_state(self, event: LogEvent) -> None:
        """Update derived states based on events."""
        # No derived state updates currently needed here.
        # Death tracking was stubbed but the log pattern for player death has not been
        # confirmed — removed to avoid a permanently-zero counter misleading the AI.

    # -------------------------------------------------------------------------
    # Default Rules
    # -------------------------------------------------------------------------

    def _setup_default_rules(self) -> None:
        """Setup default state combination rules."""
        # Armistice transitions
        self.add_rule(
            Rule(
                name="entered_armistice",
                trigger_key="in_armistice",
                conditions=[("in_armistice", "==", True)],
                event_type="zone_entered_armistice",
                message_template="Entered armistice zone",
            )
        )

        self.add_rule(
            Rule(
                name="left_armistice",
                trigger_key="in_armistice",
                conditions=[("in_armistice", "==", False)],
                event_type="zone_left_armistice",
                message_template="Left armistice zone",
            )
        )

        # Ship transitions
        self.add_rule(
            Rule(
                name="entered_ship",
                trigger_key="ship",
                conditions=[("ship", "exists", None)],
                event_type="ship_entered",
                message_template="Entered ship: {ship}",
            )
        )

        self.add_rule(
            Rule(
                name="exited_ship",
                trigger_key="ship",
                conditions=[("ship", "not_exists", None)],
                event_type="ship_exited",
                message_template="Exited ship",
            )
        )

        # Location arrival handled in _handle_event_derived (event-based,
        # not state-based) so returning to the same location still fires.

        # Station departure handled in _handle_event_derived (event-based)

    # -------------------------------------------------------------------------
    # File Output
    # -------------------------------------------------------------------------

    def _flush_file_output(self) -> None:
        """Write current state and event history to JSON file."""
        if not self._file_output_enabled or not self._file_output_path:
            return

        output = {
            "timestamp": datetime.now().isoformat(),
            "atomic_state": self._parser.get_state(),
            "derived_state": self.get_derived_state(),
            "active_missions": self.get_active_missions(),
            "recent_derived_events": self._event_history[-100:],
        }

        try:
            with open(self._file_output_path, "w", encoding="utf-8") as f:
                json.dump(output, f, indent=2, default=str)
        except Exception:
            logger.exception("Failed to write file output")


# -----------------------------------------------------------------------------
# Standalone Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import time

    argparser = argparse.ArgumentParser(description="SC State Logic - Layer 2")
    argparser.add_argument(
        "log_path",
        help="Path to Star Citizen Game.log",
    )
    argparser.add_argument(
        "--output",
        "-o",
        help="Path for JSON output file (optional)",
    )
    argparser.add_argument(
        "--parser-output",
        help="Path for Layer 3 parser JSON output (optional)",
    )
    args = argparser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    # Create Layer 3
    parser = LogParser(args.log_path)
    if args.parser_output:
        parser.enable_file_output(args.parser_output)

    # Create Layer 2
    logic = StateLogic(parser)
    if args.output:
        logic.enable_file_output(args.output)

    # Print events to console
    def on_raw_event(event: LogEvent) -> None:
        print(f"\n[RAW] {event.event_type}: {event.data}")

    def on_derived_event(event: DerivedEvent) -> None:
        print(f"\n[DERIVED] {event.event_type}: {event.message}")

    logic.subscribe_raw(on_raw_event)
    logic.subscribe(on_derived_event)

    # Start both layers
    logic.start()
    parser.start()

    print(f"Monitoring: {args.log_path}")
    print("Press Ctrl+C to stop\n")

    try:
        while parser.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        parser.stop()
        logic.stop()
