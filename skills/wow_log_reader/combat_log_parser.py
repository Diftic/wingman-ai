"""
WoW_LogReader - Layer 3: Combat Log Parser

Reads WoWCombatLog-*.txt and translates lines into atomic LogEvent records.

Phase 1 scope (this file): the combat-log version header, encounter lifecycle,
zone and map transitions, and unit deaths. All other events are silently
skipped at near-zero cost via a string-prefix pre-filter before any parsing.

Author: Mallachi
"""

from __future__ import annotations

import csv
import io
import logging
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


# Splits "<timestamp>  <payload>" where the timestamp is M/D/YYYY HH:MM:SS.ffff
# and payload is a comma-separated SimC-style record. WoW writes a tab or
# multiple spaces between the two parts; \s+ tolerates either.
_LINE_RE = re.compile(r"^(?P<ts>\d+/\d+/\d+\s+\d+:\d+:\d+\.\d+)\s+(?P<payload>.+)$")

# Phase 1 events. Lines whose event name is not in this set are skipped before
# any csv parsing or timestamp parsing happens.
_PHASE_1_EVENTS: frozenset[str] = frozenset({
    "COMBAT_LOG_VERSION",
    "ZONE_CHANGE",
    "MAP_CHANGE",
    "ENCOUNTER_START",
    "ENCOUNTER_END",
    "UNIT_DIED",
})


@dataclass
class LogEvent:
    """A parsed combat-log event."""

    event_type: str
    timestamp: datetime
    raw_line: str
    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serialisable dictionary."""
        return {
            "event_type": self.event_type,
            "timestamp": self.timestamp.isoformat(),
            "raw_line": self.raw_line,
            "data": self.data,
        }


def _parse_timestamp(raw: str) -> datetime:
    """Parse a WoW combat-log timestamp (M/D/YYYY HH:MM:SS.ffff)."""
    return datetime.strptime(raw, "%m/%d/%Y %H:%M:%S.%f")


def _split_csv(payload: str) -> list[str]:
    """CSV-split a payload, respecting double-quoted strings.

    WoW combat log uses double quotes for string fields; the csv module
    handles quote-stripping and embedded commas-in-quotes correctly.
    """
    reader = csv.reader(io.StringIO(payload), quotechar='"', skipinitialspace=False)
    return next(reader)


def _build_data_combat_log_version(args: list[str]) -> dict[str, Any]:
    """COMBAT_LOG_VERSION,N,ADVANCED_LOG_ENABLED,F,BUILD_VERSION,B,PROJECT_ID,P

    First arg is the version number; remaining args are alternating key/value
    pairs (ADVANCED_LOG_ENABLED, BUILD_VERSION, PROJECT_ID, ...).
    """
    data: dict[str, Any] = {"version": int(args[0])}
    pairs = args[1:]
    for i in range(0, len(pairs) - 1, 2):
        data[pairs[i].lower()] = pairs[i + 1]
    return data


def _build_data_zone_change(args: list[str]) -> dict[str, Any]:
    """ZONE_CHANGE,instanceID,zoneName,difficultyID"""
    return {
        "instance_id": int(args[0]) if args[0] else 0,
        "zone_name": args[1] if len(args) > 1 else "",
        "difficulty_id": int(args[2]) if len(args) > 2 and args[2] else 0,
    }


def _build_data_map_change(args: list[str]) -> dict[str, Any]:
    """MAP_CHANGE,uiMapID,mapName,x0,y0,x1,y1"""
    return {
        "ui_map_id": int(args[0]),
        "map_name": args[1],
        "x0": float(args[2]),
        "y0": float(args[3]),
        "x1": float(args[4]),
        "y1": float(args[5]),
    }


def _build_data_encounter_start(args: list[str]) -> dict[str, Any]:
    """ENCOUNTER_START,encounterID,encounterName,difficultyID,groupSize,instanceID"""
    return {
        "encounter_id": int(args[0]),
        "encounter_name": args[1],
        "difficulty_id": int(args[2]),
        "group_size": int(args[3]),
        "instance_id": int(args[4]) if len(args) > 4 else 0,
    }


def _build_data_encounter_end(args: list[str]) -> dict[str, Any]:
    """ENCOUNTER_END,encounterID,encounterName,difficultyID,groupSize,success,fightTimeMs"""
    return {
        "encounter_id": int(args[0]),
        "encounter_name": args[1],
        "difficulty_id": int(args[2]),
        "group_size": int(args[3]),
        "success": bool(int(args[4])),
        "fight_time_ms": int(args[5]) if len(args) > 5 else 0,
    }


def _build_data_unit_died(args: list[str]) -> dict[str, Any]:
    """UNIT_DIED,sourceGUID,sourceName,sourceFlags,sourceRaidFlags,destGUID,destName,destFlags,destRaidFlags

    The dying unit is the destination side. Source is often empty/zero
    (environmental deaths) or the killer's GUID.
    """
    dest_guid = args[4] if len(args) > 4 else ""
    return {
        "source_guid": args[0] if args else "",
        "source_name": args[1] if len(args) > 1 else "",
        "dest_guid": dest_guid,
        "dest_name": args[5] if len(args) > 5 else "",
        "is_player": dest_guid.startswith("Player-"),
    }


_BUILDERS = {
    "COMBAT_LOG_VERSION": _build_data_combat_log_version,
    "ZONE_CHANGE": _build_data_zone_change,
    "MAP_CHANGE": _build_data_map_change,
    "ENCOUNTER_START": _build_data_encounter_start,
    "ENCOUNTER_END": _build_data_encounter_end,
    "UNIT_DIED": _build_data_unit_died,
}


class LogParser:
    """Parses WoW combat log files line-by-line.

    Phase 1: only events in `_PHASE_1_EVENTS` produce a `LogEvent`. All other
    lines are silently skipped after a cheap event-name prefix check, so the
    parser stays fast on dense combat logs (where 99%+ of lines are SPELL_*
    events we do not yet care about).
    """

    def parse_line(self, line: str) -> LogEvent | None:
        """Parse one combat-log line. Returns None for skipped or malformed lines."""
        line = line.strip()
        if not line:
            return None

        m = _LINE_RE.match(line)
        if not m:
            return None

        ts_raw = m.group("ts")
        payload = m.group("payload")

        # Cheap pre-filter: peek at the event name before doing csv parsing.
        first_comma = payload.find(",")
        event_name = payload[:first_comma] if first_comma != -1 else payload
        if event_name not in _PHASE_1_EVENTS:
            return None

        try:
            fields = _split_csv(payload)
        except (csv.Error, StopIteration):
            logger.debug("Failed to CSV-split payload: %s", payload[:200])
            return None
        if not fields:
            return None

        try:
            timestamp = _parse_timestamp(ts_raw)
        except ValueError:
            logger.debug("Failed to parse timestamp: %s", ts_raw)
            return None

        builder = _BUILDERS[fields[0]]
        try:
            data = builder(fields[1:])
        except (IndexError, ValueError) as exc:
            logger.debug("Failed to build data for %s: %s", fields[0], exc)
            return None

        return LogEvent(
            event_type=fields[0].lower(),
            timestamp=timestamp,
            raw_line=line,
            data=data,
        )

    def parse_file(self, path: Path) -> Iterator[LogEvent]:
        """Iterate over all Phase 1 events in a combat-log file."""
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                ev = self.parse_line(line)
                if ev is not None:
                    yield ev


def _main() -> None:
    """CLI helper: parse a combat-log file and print Phase 1 events.

    Usage:
        python parser.py <path/to/WoWCombatLog.txt>
    """
    import sys

    if len(sys.argv) != 2:
        print("Usage: python parser.py <combat_log_path>", file=sys.stderr)
        sys.exit(2)

    path = Path(sys.argv[1])
    parser = LogParser()

    counts: dict[str, int] = {}
    for ev in parser.parse_file(path):
        counts[ev.event_type] = counts.get(ev.event_type, 0) + 1
        # Print everything except non-player UNIT_DIED events (too noisy).
        if ev.event_type != "unit_died" or ev.data.get("is_player"):
            print(f"{ev.timestamp.isoformat()}  {ev.event_type:<20} {ev.data}")

    print()
    print("Event counts (Phase 1 events only):")
    for k, v in sorted(counts.items()):
        print(f"  {k}: {v}")


if __name__ == "__main__":
    _main()
