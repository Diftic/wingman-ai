"""
wow_log_reader - Combat Log Tail Watcher

Watches the WoW Logs directory for the active WoWCombatLog-*.txt file, tails
it, and feeds parsed events to a callback. Handles file rotation (a new
combat-log file is created each WoW session) and partial-line buffering
(combat-log writes may be flushed mid-line).

On startup, the watcher reads the entire current file from the beginning so
the session-state aggregator can catch up on history that happened before
Wingman was launched.

Module name is `combat_log_watcher` (not `watcher`) to avoid sys.modules
collisions with sibling skills that bare-import their own `watcher` module.

Author: Mallachi
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from combat_log_parser import LogEvent, LogParser  # noqa: E402


logger = logging.getLogger(__name__)


_COMBAT_LOG_GLOB = "WoWCombatLog-*.txt"


def find_active_combat_log(logs_dir: Path) -> Optional[Path]:
    """Return the most recently modified WoWCombatLog file in logs_dir, or None.

    "Active" is defined as "highest mtime". WoW creates a new file at the start
    of each combat-log session, so the most recently modified file is the one
    being written to right now (or was last written to).
    """
    if not logs_dir.is_dir():
        return None
    candidates = list(logs_dir.glob(_COMBAT_LOG_GLOB))
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.stat().st_mtime)


class CombatLogWatcher:
    """Tails the active WoW combat log file and emits parsed LogEvent records.

    Handles file rotation, partial-line buffering, and initial catch-up by
    reading the entire current file when first attached to it. Errors during
    a tick are logged and the loop continues so transient I/O failures do not
    kill the watcher.

    Usage:
        watcher = CombatLogWatcher(logs_dir, on_event=callback)
        watcher.start()
        ...
        watcher.stop()
    """

    def __init__(
        self,
        logs_dir: Path,
        on_event: Callable[[LogEvent, bool], None],
        poll_interval: float = 0.5,
    ) -> None:
        """Construct the watcher.

        `on_event` is called for every parsed event with a second positional
        argument `is_live`: True for events read in incremental tail mode
        (after the watcher's first attach to the file), False for events
        read during the initial catch-up of an already-existing file. The
        consumer typically wants to update state for both but only dispatch
        notifications for live events.
        """
        self._logs_dir = Path(logs_dir)
        self._on_event = on_event
        self._poll_interval = poll_interval
        self._parser = LogParser()
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._current_path: Optional[Path] = None
        self._current_pos: int = 0
        self._line_buffer: str = ""
        self._first_read_done: bool = False

    @property
    def current_path(self) -> Optional[Path]:
        """The combat log file currently being tailed, or None if not attached yet."""
        return self._current_path

    def start(self) -> None:
        """Start the watcher thread (idempotent)."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run, name="WoWCombatLogWatcher", daemon=True
        )
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the watcher to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)

    def tick_once(self) -> int:
        """Run a single watch iteration synchronously. Returns events emitted.

        Useful for tests and for one-shot catch-up parsing without the thread.
        """
        return self._tick()

    def _run(self) -> None:
        """Main watch loop. Runs in the watcher thread."""
        while not self._stop_event.is_set():
            try:
                self._tick()
            except Exception:
                logger.exception("Combat log watcher tick failed; continuing")
            self._stop_event.wait(self._poll_interval)

    def _tick(self) -> int:
        """One iteration: detect rotation, read new bytes, parse, emit. Returns event count."""
        active = find_active_combat_log(self._logs_dir)
        if active is None:
            return 0

        if active != self._current_path:
            logger.info("Combat log active file: %s", active)
            self._current_path = active
            self._current_pos = 0
            self._line_buffer = ""
            self._first_read_done = False

        try:
            with open(active, "r", encoding="utf-8", errors="replace") as f:
                f.seek(self._current_pos)
                chunk = f.read()
                self._current_pos = f.tell()
        except FileNotFoundError:
            # File was rotated/deleted between detection and read; retry next tick.
            self._current_path = None
            return 0

        if not chunk:
            return 0

        self._line_buffer += chunk
        # split returns at least one element. The last element is either ""
        # (if the chunk ended with \n) or a partial line that must be carried.
        lines = self._line_buffer.split("\n")
        self._line_buffer = lines.pop()

        is_live = self._first_read_done
        emitted = 0
        for line in lines:
            ev = self._parser.parse_line(line)
            if ev is not None:
                try:
                    self._on_event(ev, is_live)
                    emitted += 1
                except Exception:
                    logger.exception("on_event callback raised; continuing")
        # First tick after attach has finished; subsequent reads are live.
        self._first_read_done = True
        return emitted


def _main() -> None:
    """CLI helper: watch a Logs directory and print events as they arrive.

    Usage:
        python combat_log_watcher.py <path/to/WoW/_retail_/Logs>
    """
    if len(sys.argv) != 2:
        print(
            "Usage: python combat_log_watcher.py <wow_logs_dir>",
            file=sys.stderr,
        )
        sys.exit(2)

    logs_dir = Path(sys.argv[1])

    def on_event(ev: LogEvent, is_live: bool) -> None:
        flag = "LIVE" if is_live else "CATCH"
        print(f"{ev.timestamp.isoformat()}  [{flag}]  {ev.event_type:<20} {ev.data}")

    watcher = CombatLogWatcher(logs_dir, on_event=on_event, poll_interval=1.0)
    watcher.start()
    print(f"Watching {logs_dir} (Ctrl+C to stop)...", file=sys.stderr)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...", file=sys.stderr)
        watcher.stop()


if __name__ == "__main__":
    _main()
