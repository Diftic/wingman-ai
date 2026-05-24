"""
wow_log_reader - Layer 1: WingmanAI Skill

AI interface for World of Warcraft combat-log monitoring. Owns a CombatLogWatcher
(Layer 0 - I/O), feeds parsed events into a StateLogic aggregator (Layer 2),
and exposes the resulting session snapshot to the AI through @tool methods.

Also derives proactive notifications from live combat-log events and dispatches
them to the wingman as `[Game Event] X` messages so the AI persona can react in
character without the user having to ask.

Sibling-module imports use the bare-import + sys.path pattern so this skill
loads correctly both from the dev tree (as a package) and from custom_skills/
(as a standalone module). Module names (`combat_log_parser`, `session_state`,
`combat_log_watcher`) are deliberately unique to avoid sys.modules collisions
with other skills that may bare-import their own `parser` / `logic` / `watcher`.

Author: Mallachi
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import threading
from pathlib import Path
from threading import Thread
from typing import Optional

from api.enums import LogType
from skills.skill_base import Skill, tool


_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
if _THIS_DIR not in sys.path:
    sys.path.insert(0, _THIS_DIR)

from combat_log_parser import LogEvent  # noqa: E402
from combat_log_watcher import CombatLogWatcher  # noqa: E402
from session_state import NotificationEvent, StateLogic  # noqa: E402


logger = logging.getLogger(__name__)


# Common WoW install roots. Used as a fallback when the user has not configured
# wow_install_path. First match wins.
_DEFAULT_INSTALL_PATHS: tuple[str, ...] = (
    "D:/Games/World of Warcraft",
    "C:/Program Files (x86)/World of Warcraft",
    "C:/Program Files/World of Warcraft",
)


# Maps each derivable notification event type to its per-event toggle key in
# default_config.yaml. A notification only fires if the master switch
# (`proactive_notifications`) is on AND the per-event toggle is on.
_EVENT_TOGGLE_MAP: dict[str, str] = {
    "session_started": "notify_session_started",
    "zone_entered": "notify_zone_entered",
    "instance_entered": "notify_instance_entered",
    "instance_exited": "notify_instance_exited",
    "encounter_started": "notify_encounter_started",
    "encounter_ended_kill": "notify_encounter_ended_kill",
    "encounter_ended_wipe": "notify_encounter_ended_wipe",
    "player_died": "notify_player_died",
    "map_changed": "notify_map_changed",
}


# After this many auto-notifications without any user input, dispatch pauses
# to avoid flooding when the user is AFK. Resumes on next user message.
_MAX_AUTO_MESSAGES_WITHOUT_USER = 8


def _resolve_logs_dir(install_path_str: str) -> Optional[Path]:
    """Resolve a configured path to a usable WoW Logs directory.

    Accepts the install root (containing `_retail_`), the `_retail_` folder
    directly, or the `Logs` folder directly. Returns None if no Logs dir can
    be located under the given path.
    """
    if not install_path_str:
        return None
    p = Path(install_path_str)
    if not p.exists():
        return None

    if p.name.lower() == "logs" and p.is_dir():
        return p

    for candidate in (p / "_retail_" / "Logs", p / "Logs"):
        if candidate.is_dir():
            return candidate
    return None


class WoW_LogReader(Skill):
    """WingmanAI skill that exposes live WoW combat-log state to the AI."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._logic = StateLogic()
        self._lock = threading.Lock()
        self._watcher: Optional[CombatLogWatcher] = None
        self._logs_dir: Optional[Path] = None

        # Auto-pause bookkeeping for proactive notifications.
        self._auto_messages_since_user_input = 0
        self._notifications_paused = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def validate(self) -> list:
        errors = await super().validate()
        # Touch the property so the framework records its presence; empty value
        # is acceptable (auto-detect path) so we do not append errors here.
        self.retrieve_custom_property_value("wow_install_path", errors)
        return errors

    async def prepare(self) -> None:
        await super().prepare()

        configured_path = (
            self.retrieve_custom_property_value("wow_install_path", []) or ""
        )
        self._logs_dir = _resolve_logs_dir(configured_path)

        if self._logs_dir is None:
            for default in _DEFAULT_INSTALL_PATHS:
                resolved = _resolve_logs_dir(default)
                if resolved is not None:
                    self._logs_dir = resolved
                    self.printr.print(
                        f"WoW_LogReader: auto-detected WoW Logs directory at {resolved}",
                        color=LogType.INFO,
                        server_only=True,
                    )
                    break

        if self._logs_dir is None:
            self.printr.print(
                "WoW_LogReader: no WoW install path configured and no default location found. "
                "Set 'WoW Install Path' in skill settings, then reload the skill.",
                color=LogType.WARNING,
                server_only=True,
            )
            return

        self._watcher = CombatLogWatcher(
            logs_dir=self._logs_dir,
            on_event=self._on_event,
            poll_interval=1.0,
        )
        self._watcher.start()
        self.printr.print(
            f"WoW_LogReader: tailing combat log in {self._logs_dir}",
            color=LogType.INFO,
            server_only=True,
        )

    async def unload(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None
        await super().unload()

    # ------------------------------------------------------------------
    # Watcher callback
    # ------------------------------------------------------------------

    def _on_event(self, ev: LogEvent, is_live: bool) -> None:
        """Apply event to state; dispatch derived notifications only if live."""
        # Runs on the watcher thread; serialise mutation through the lock.
        with self._lock:
            notifications = self._logic.apply(ev)
        if not is_live:
            return
        for n in notifications:
            self._dispatch_notification(n)

    # ------------------------------------------------------------------
    # Proactive notification pipeline
    # ------------------------------------------------------------------

    def _dispatch_notification(self, event: NotificationEvent) -> None:
        """Gate on master switch + per-event toggle + auto-pause, then send."""
        # Master switch
        master = bool(self.retrieve_custom_property_value("proactive_notifications", []))
        if not master:
            return

        # Per-event toggle
        toggle_key = _EVENT_TOGGLE_MAP.get(event.event_type)
        if toggle_key is None:
            return  # unknown event type
        if not bool(self.retrieve_custom_property_value(toggle_key, [])):
            return

        # Auto-pause bookkeeping
        if self._notifications_paused:
            return
        self._auto_messages_since_user_input += 1
        if self._auto_messages_since_user_input > _MAX_AUTO_MESSAGES_WITHOUT_USER:
            self._notifications_paused = True
            self.printr.print(
                f"WoW_LogReader: pausing notifications (sent "
                f"{_MAX_AUTO_MESSAGES_WITHOUT_USER} without user input). "
                "Resumes on next user message.",
                color=LogType.WARNING,
                server_only=True,
            )
            return

        message = f"[Game Event] {event.message}"
        # Dedicated thread + throwaway event loop, mirroring sc_log_reader.
        Thread(
            target=self._run_notification,
            args=(message,),
            daemon=True,
        ).start()

    def _run_notification(self, message: str) -> None:
        """Send a notification on a dedicated thread with its own event loop."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._send_notification(message))
        except Exception:
            self.printr.print(
                "WoW_LogReader: notification delivery failed - see log",
                color=LogType.ERROR,
                server_only=True,
            )
            logger.exception("WoW_LogReader: notification delivery failed")
        finally:
            loop.close()

    async def _send_notification(self, message: str) -> None:
        """Push the message through the wingman's full personality pipeline."""
        if not self.wingman:
            return
        await self.wingman.process(transcript=message)

    # ------------------------------------------------------------------
    # User-input hook (resumes paused notifications)
    # ------------------------------------------------------------------

    async def on_add_user_message(self, message: str) -> None:
        # Any user utterance resets the auto-pause counter and unpauses.
        self._auto_messages_since_user_input = 0
        if self._notifications_paused:
            self._notifications_paused = False
            self.printr.print(
                "WoW_LogReader: notifications resumed (user spoke).",
                color=LogType.INFO,
                server_only=True,
            )

    # ------------------------------------------------------------------
    # Tools exposed to the AI
    # ------------------------------------------------------------------

    @tool()
    def get_current_wow_state(self) -> str:
        """Return the current WoW session state: zone, map, build version, in-progress encounter, and recent activity counts. Use this when the player asks where they are or for a session overview."""
        with self._lock:
            s = self._logic.state
            data = {
                "log_version": s.log_version,
                "build_version": s.build_version,
                "current_zone": s.current_zone,
                "current_zone_id": s.current_zone_id,
                "current_zone_difficulty": s.current_zone_difficulty,
                "current_map": s.current_map,
                "current_map_id": s.current_map_id,
                "in_progress_encounter": s.in_progress_encounter,
                "encounter_count": len(s.encounters),
                "player_death_count": len(s.player_deaths),
                "logs_dir": str(self._logs_dir) if self._logs_dir else None,
                "active_log_file": (
                    str(self._watcher.current_path)
                    if self._watcher is not None and self._watcher.current_path is not None
                    else None
                ),
            }
        return json.dumps(data)

    @tool()
    def get_recent_encounters(self, count: int = 5) -> str:
        """Return the most recent boss encounters (kills and wipes), newest first.

        Args:
            count: How many recent encounters to return. Default 5, max 50.
        """
        n = max(1, min(int(count), 50))
        with self._lock:
            recent = list(self._logic.state.encounters)[-n:]
        recent.reverse()  # newest first
        return json.dumps([e.to_dict() for e in recent])

    @tool()
    def get_recent_player_deaths(self, count: int = 5) -> str:
        """Return the most recent player deaths, newest first.

        Args:
            count: How many recent deaths to return. Default 5, max 50.
        """
        n = max(1, min(int(count), 50))
        with self._lock:
            recent = list(self._logic.state.player_deaths)[-n:]
        recent.reverse()
        return json.dumps([d.to_dict() for d in recent])
