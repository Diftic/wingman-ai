"""
wow_log_reader - Layer 2: Session State Aggregator

Consumes parsed LogEvent records and maintains an in-memory snapshot of the
current session: log version, build, current zone and map, in-progress and
completed encounters, and player deaths. The Layer 1 skill queries this state
to answer the AI's tool calls.

Module name is `session_state` (not `logic`) to avoid sys.modules collisions
with sibling skills that bare-import their own `logic` module.

Author: Mallachi
"""

from __future__ import annotations

import logging
import os
import sys
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from combat_log_parser import LogEvent  # noqa: E402


logger = logging.getLogger(__name__)


@dataclass
class EncounterRecord:
    """A completed encounter (boss fight)."""

    encounter_id: int
    name: str
    difficulty_id: int
    group_size: int
    success: bool
    fight_time_ms: int
    started_at: datetime
    ended_at: datetime

    def to_dict(self) -> dict:
        return {
            "encounter_id": self.encounter_id,
            "name": self.name,
            "difficulty_id": self.difficulty_id,
            "group_size": self.group_size,
            "success": self.success,
            "fight_time_ms": self.fight_time_ms,
            "started_at": self.started_at.isoformat(),
            "ended_at": self.ended_at.isoformat(),
        }


@dataclass
class DeathRecord:
    """A player death (non-player deaths are not retained)."""

    timestamp: datetime
    dest_name: str
    dest_guid: str
    source_name: str
    zone_name: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "dest_name": self.dest_name,
            "dest_guid": self.dest_guid,
            "source_name": self.source_name,
            "zone_name": self.zone_name,
        }


@dataclass
class SessionState:
    """In-memory snapshot of the current WoW session."""

    log_version: Optional[int] = None
    build_version: str = ""
    current_zone: str = ""
    current_zone_id: int = 0
    current_zone_difficulty: int = 0
    current_map: str = ""
    current_map_id: int = 0
    in_progress_encounter: Optional[dict] = None
    encounters: deque[EncounterRecord] = field(default_factory=lambda: deque(maxlen=50))
    player_deaths: deque[DeathRecord] = field(default_factory=lambda: deque(maxlen=50))


@dataclass
class NotificationEvent:
    """A derived event ready to be dispatched to the AI as a proactive update.

    `event_type` is one of the keys in main.py's _EVENT_TOGGLE_MAP and is used
    to gate dispatch on a per-event config toggle. `message` is the human-
    readable narration the AI sees (prefixed with "[Game Event]" by main.py).
    """

    event_type: str
    message: str
    timestamp: datetime


class StateLogic:
    """Updates a SessionState in response to parsed LogEvent records.

    `apply` returns the list of NotificationEvent records derived from the
    incoming LogEvent. The caller decides whether to dispatch them (live)
    or discard them (initial catch-up).
    """

    def __init__(self) -> None:
        self.state = SessionState()

    def apply(self, ev: LogEvent) -> list[NotificationEvent]:
        """Apply a single event and return the notifications it derives."""
        notifications: list[NotificationEvent] = []
        handler = _HANDLERS.get(ev.event_type)
        if handler is not None:
            handler(self.state, ev, notifications)
        return notifications

    def apply_many(self, events) -> list[NotificationEvent]:
        """Apply an iterable of events; returns concatenated notifications."""
        all_notifications: list[NotificationEvent] = []
        for ev in events:
            all_notifications.extend(self.apply(ev))
        return all_notifications


def _handle_combat_log_version(
    state: SessionState, ev: LogEvent, notifications: list[NotificationEvent]
) -> None:
    state.log_version = ev.data.get("version")
    state.build_version = ev.data.get("build_version", "")
    notifications.append(
        NotificationEvent(
            event_type="session_started",
            message=(
                f"Combat logging started "
                f"(WoW build {state.build_version}, log v{state.log_version})."
            ),
            timestamp=ev.timestamp,
        )
    )


def _handle_zone_change(
    state: SessionState, ev: LogEvent, notifications: list[NotificationEvent]
) -> None:
    new_zone = ev.data.get("zone_name", "")
    new_difficulty = ev.data.get("difficulty_id", 0)

    was_in_instance = state.current_zone_difficulty != 0
    will_be_in_instance = new_difficulty != 0

    # Decide which derived event (if any) to emit before mutating state, so we
    # have access to both the previous and the new zone.
    if was_in_instance and not will_be_in_instance:
        notifications.append(
            NotificationEvent(
                event_type="instance_exited",
                message=f"Left {state.current_zone}.",
                timestamp=ev.timestamp,
            )
        )
    elif will_be_in_instance and not was_in_instance:
        notifications.append(
            NotificationEvent(
                event_type="instance_entered",
                message=(
                    f"Stepped into {new_zone} (difficulty {new_difficulty})."
                ),
                timestamp=ev.timestamp,
            )
        )
    elif new_zone and new_zone != state.current_zone:
        notifications.append(
            NotificationEvent(
                event_type="zone_entered",
                message=f"Entered {new_zone}.",
                timestamp=ev.timestamp,
            )
        )

    state.current_zone = new_zone
    state.current_zone_id = ev.data.get("instance_id", 0)
    state.current_zone_difficulty = new_difficulty


def _handle_map_change(
    state: SessionState, ev: LogEvent, notifications: list[NotificationEvent]
) -> None:
    new_map = ev.data.get("map_name", "")
    if new_map and new_map != state.current_map:
        notifications.append(
            NotificationEvent(
                event_type="map_changed",
                message=f"Subzone: {new_map}.",
                timestamp=ev.timestamp,
            )
        )
    state.current_map = new_map
    state.current_map_id = ev.data.get("ui_map_id", 0)


def _handle_encounter_start(
    state: SessionState, ev: LogEvent, notifications: list[NotificationEvent]
) -> None:
    state.in_progress_encounter = {
        "encounter_id": ev.data.get("encounter_id"),
        "encounter_name": ev.data.get("encounter_name"),
        "difficulty_id": ev.data.get("difficulty_id"),
        "group_size": ev.data.get("group_size"),
        "started_at": ev.timestamp.isoformat(),
    }
    name = ev.data.get("encounter_name", "the boss")
    group_size = ev.data.get("group_size", 0)
    group_str = f", group of {group_size}" if group_size else ""
    notifications.append(
        NotificationEvent(
            event_type="encounter_started",
            message=f"Pull: {name}{group_str}.",
            timestamp=ev.timestamp,
        )
    )


def _handle_encounter_end(
    state: SessionState, ev: LogEvent, notifications: list[NotificationEvent]
) -> None:
    started_at = ev.timestamp
    if state.in_progress_encounter:
        try:
            started_at = datetime.fromisoformat(
                state.in_progress_encounter["started_at"]
            )
        except (KeyError, TypeError, ValueError):
            pass

    record = EncounterRecord(
        encounter_id=ev.data.get("encounter_id", 0),
        name=ev.data.get("encounter_name", ""),
        difficulty_id=ev.data.get("difficulty_id", 0),
        group_size=ev.data.get("group_size", 0),
        success=ev.data.get("success", False),
        fight_time_ms=ev.data.get("fight_time_ms", 0),
        started_at=started_at,
        ended_at=ev.timestamp,
    )
    state.encounters.append(record)
    state.in_progress_encounter = None

    secs = record.fight_time_ms / 1000 if record.fight_time_ms else 0
    if record.success:
        notifications.append(
            NotificationEvent(
                event_type="encounter_ended_kill",
                message=f"Killed {record.name} in {secs:.0f} seconds.",
                timestamp=ev.timestamp,
            )
        )
    else:
        notifications.append(
            NotificationEvent(
                event_type="encounter_ended_wipe",
                message=f"Wiped to {record.name} after {secs:.0f} seconds.",
                timestamp=ev.timestamp,
            )
        )


def _handle_unit_died(
    state: SessionState, ev: LogEvent, notifications: list[NotificationEvent]
) -> None:
    if not ev.data.get("is_player"):
        return
    record = DeathRecord(
        timestamp=ev.timestamp,
        dest_name=ev.data.get("dest_name", ""),
        dest_guid=ev.data.get("dest_guid", ""),
        source_name=ev.data.get("source_name", ""),
        zone_name=state.current_zone,
    )
    state.player_deaths.append(record)

    where = state.current_zone or "an unknown zone"
    killer = ev.data.get("source_name", "")
    if killer:
        msg = f"You died in {where}. Source: {killer}."
    else:
        msg = f"You died in {where}."
    notifications.append(
        NotificationEvent(
            event_type="player_died",
            message=msg,
            timestamp=ev.timestamp,
        )
    )


_HANDLERS = {
    "combat_log_version": _handle_combat_log_version,
    "zone_change": _handle_zone_change,
    "map_change": _handle_map_change,
    "encounter_start": _handle_encounter_start,
    "encounter_end": _handle_encounter_end,
    "unit_died": _handle_unit_died,
}


def _main() -> None:
    """CLI helper: run parser + state aggregator against a fixture and print state.

    Usage:
        python session_state.py <path/to/WoWCombatLog.txt>
    """
    from pathlib import Path

    from combat_log_parser import LogParser

    if len(sys.argv) != 2:
        print("Usage: python session_state.py <combat_log_path>", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    parser = LogParser()
    logic = StateLogic()

    logic.apply_many(parser.parse_file(path))
    s = logic.state

    print(f"Log version       : {s.log_version}")
    print(f"Build version     : {s.build_version}")
    print(f"Current zone      : {s.current_zone} (instance {s.current_zone_id}, difficulty {s.current_zone_difficulty})")
    print(f"Current map       : {s.current_map} (id {s.current_map_id})")
    print(f"In-progress fight : {s.in_progress_encounter}")
    print(f"Player deaths     : {len(s.player_deaths)}")
    print()
    print(f"Encounters ({len(s.encounters)}):")
    for e in s.encounters:
        result = "kill" if e.success else "wipe"
        secs = e.fight_time_ms / 1000
        print(f"  {e.started_at.strftime('%H:%M:%S')} - {e.name:<25} {secs:>6.1f}s  {result}")


if __name__ == "__main__":
    _main()
