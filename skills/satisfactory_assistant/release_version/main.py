"""SatisfactoryAssistant - Wingman AI skill.

Helps Satisfactory players plan and maintain factories for the currently active
save only. The active save is identified strictly from the newest game log; the
skill never mixes data between saves and only writes inside a generated,
per-save workspace.

Author: ShipBit
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from api.enums import LogType
from api.interface import SettingsConfig, SkillConfig, WingmanInitializationError
from skills.skill_base import Skill, tool

# Allow importing the sibling pure-logic modules when loaded as a skill.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from satisfactory_active_save import resolve_active_save  # noqa: E402
from satisfactory_adapter import (  # noqa: E402
    _coerce_bool as _coerce_bool,
    _coerce_int as _coerce_int,
    _normalize_rate_aliases,
    _parse_rates,
    _resolve_status_target as _resolve_status_target,
    _save_file_note as _save_file_note,
    build_locate_lines,
    build_lookup_lines,
    build_plan_status_lines,
    format_docs_missing_message,
    run_factory_audit_pipeline,
    run_master_calculation,
    run_plan_calculation,
    run_scenario_comparison,
)
from satisfactory_dataset import get_docs_catalog  # noqa: E402
from satisfactory_install import discover_docs  # noqa: E402
from satisfactory_mirror import TrendConfig  # noqa: E402
from satisfactory_map_overlay import MapOverlay  # noqa: E402
from satisfactory_map import query_targets_machine_type  # noqa: E402
from satisfactory_models import (  # noqa: E402
    STATUS_NO_ACTIVE_SAVE,
    STATUS_NO_LOG_FOLDER,
    ActiveSaveResult,
)
from satisfactory_progression import load_project_assembly_phases  # noqa: E402
from satisfactory_reference import project_assembly_reference_lines  # noqa: E402
from satisfactory_workspace import (  # noqa: E402
    FLOW_STATUSES,
    STATUS_ARCHIVED,
    STATUS_DONE,
    SaveWorkspace,
    adopt_legacy_workspace,
    clip,
    format_context,
    parse_clear_fields,
    safe_save_key,
    slugify,
    stable_workspace_key,
)

# Clip titles echoed in write-tool acknowledgements (stored titles are kept in
# full); keeps tool responses short even for long natural-language titles.
_ACK_TITLE_MAX = 60

# Automatic factory-mirror refresh. The watcher checks cheaply every five
# seconds so the in-game autosave cadence controls expensive parse/audit work.
_AUTO_AUDIT_POLL_SECONDS = 5.0

_SaveTreeMarker = tuple[tuple[str, int, int], ...]
_AutoAuditObservation = tuple[str, str, str, int, int, _SaveTreeMarker]


def _save_tree_marker(root: Path | None) -> _SaveTreeMarker:
    """Return a deterministic marker for direct and per-profile save files."""
    if root is None:
        return ()
    save_games = root / "SaveGames"
    try:
        if not save_games.is_dir():
            return ()
        candidates = [path for path in save_games.glob("*.sav") if path.is_file()]
        for profile in save_games.iterdir():
            if profile.is_dir():
                candidates.extend(path for path in profile.glob("*.sav") if path.is_file())
    except OSError:
        return ()

    marker: list[tuple[str, int, int]] = []
    for path in candidates:
        try:
            stat = path.stat()
            relative = str(path.relative_to(save_games))
        except (OSError, ValueError):
            continue
        marker.append((relative, stat.st_mtime_ns, stat.st_size))
    return tuple(sorted(marker))


def _active_save_observation(result: ActiveSaveResult) -> _AutoAuditObservation | None:
    """Build the file/log marker that decides whether an audit is due."""
    if not result.confirmed or result.save_file is None:
        return None
    try:
        save_stat = result.save_file.stat()
    except OSError:
        return None

    return (
        str(result.root or ""),
        str(result.save_name or ""),
        str(result.save_file),
        save_stat.st_mtime_ns,
        save_stat.st_size,
        _save_tree_marker(result.root),
    )

if TYPE_CHECKING:
    from wingmen.open_ai_wingman import OpenAiWingman


class SatisfactoryAssistant(Skill):
    """Per-save factory planning for Satisfactory, scoped to the active save."""

    def __init__(
        self,
        config: SkillConfig,
        settings: SettingsConfig,
        wingman: "OpenAiWingman",
    ) -> None:
        super().__init__(config=config, settings=settings, wingman=wingman)
        self._audit_lock: asyncio.Lock | None = None
        self._auto_audit_task: asyncio.Task[None] | None = None
        self._auto_audit_has_run = False
        self._auto_audit_observation: _AutoAuditObservation | None = None
        self._map_overlay: MapOverlay | None = None

    async def validate(self) -> list[WingmanInitializationError]:
        errors = await super().validate()
        self.retrieve_custom_property_value("satisfactory_install_dir", errors)
        self.retrieve_custom_property_value("max_response_items", errors)
        self.retrieve_custom_property_value("allow_plan_writes", errors)
        self.retrieve_custom_property_value("mirror_trend_window_saves", errors)
        self.retrieve_custom_property_value("mirror_zero_streak_saves", errors)
        self.retrieve_custom_property_value("mirror_deviation_threshold_percent", errors)
        self.retrieve_custom_property_value("map_overlay_enabled", errors)
        self.retrieve_custom_property_value("map_overlay_display", errors)
        self.retrieve_custom_property_value("map_overlay_size", errors)
        self.retrieve_custom_property_value("map_overlay_duration_seconds", errors)
        self.retrieve_custom_property_value("map_overlay_position", errors)
        return errors

    async def prepare(self) -> None:
        await super().prepare()
        self._start_map_overlay()
        if self._auto_audit_task is None or self._auto_audit_task.done():
            self._auto_audit_task = asyncio.create_task(self._auto_audit_loop())

    async def unload(self) -> None:
        task = self._auto_audit_task
        self._auto_audit_task = None
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        overlay = self._map_overlay
        self._map_overlay = None
        if overlay is not None:
            overlay.stop()
        await super().unload()

    # --- just-in-time config accessors (never cached) ---

    def _saved_dir(self) -> str:
        return ""

    def _docs_file(self) -> str:
        return ""

    def _install_dir(self) -> str:
        return self.retrieve_custom_property_value("satisfactory_install_dir", []) or ""

    def _docs_locale(self) -> str:
        return "en-US"

    def _parser_runtime_dir(self) -> str:
        return ""

    def _max_response_items(self) -> int:
        value = self.retrieve_custom_property_value("max_response_items", [])
        return _coerce_int(value, default=12, minimum=1)

    def _mirror_trend_window_saves(self) -> int:
        value = self.retrieve_custom_property_value("mirror_trend_window_saves", [])
        return _coerce_int(value, default=5, minimum=1)

    def _mirror_zero_streak_saves(self) -> int:
        value = self.retrieve_custom_property_value("mirror_zero_streak_saves", [])
        return _coerce_int(value, default=3, minimum=1)

    def _mirror_deviation_threshold(self) -> float:
        value = self.retrieve_custom_property_value(
            "mirror_deviation_threshold_percent", []
        )
        try:
            percent = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            percent = 25.0
        return max(0.0, min(percent, 100.0)) / 100.0

    def _allow_plan_writes(self) -> bool:
        value = self.retrieve_custom_property_value("allow_plan_writes", [])
        return _coerce_bool(value, default=True)

    def _map_overlay_enabled(self) -> bool:
        value = self.retrieve_custom_property_value("map_overlay_enabled", [])
        return _coerce_bool(value, default=True)

    def _map_overlay_display(self) -> int:
        value = self.retrieve_custom_property_value("map_overlay_display", [])
        return _coerce_int(value, default=1, minimum=1)

    def _map_overlay_size(self) -> int:
        value = self.retrieve_custom_property_value("map_overlay_size", [])
        return min(1200, _coerce_int(value, default=520, minimum=240))

    def _map_overlay_duration_seconds(self) -> float:
        value = self.retrieve_custom_property_value("map_overlay_duration_seconds", [])
        try:
            duration = float(value)  # type: ignore[arg-type]
        except (TypeError, ValueError):
            duration = 15.0
        return max(0.0, min(duration, 3600.0))

    def _map_overlay_position(self) -> str:
        value = str(
            self.retrieve_custom_property_value("map_overlay_position", [])
            or "top_center"
        ).strip().lower()
        return value if value in {"top_left", "top_center", "top_right"} else "top_center"

    def _map_background_image(self) -> Path | None:
        path = Path(self.get_generated_files_dir()) / "assets" / "satisfactory_world_map.png"
        return path if path.is_file() else None

    # --- helpers ---

    def _resolve(self) -> ActiveSaveResult:
        return resolve_active_save(configured_dir=self._saved_dir())

    def _workspace_for(self, result: ActiveSaveResult) -> SaveWorkspace:
        # Identity is based on stable logical evidence (Saved root + save name),
        # never the volatile .sav path, so the same save resolves to the same
        # workspace whether or not the file is currently found on disk.
        base = Path(self.get_generated_files_dir())
        key = stable_workspace_key(result.root, result.save_name)
        # Older workspaces were keyed on the .sav path; when a concrete save
        # file exists, adopt that legacy workspace's records under the stable
        # key so plans created before this fix do not appear to vanish.
        if result.save_file is not None:
            legacy_key = safe_save_key(result.save_name or "save", str(result.save_file))
            if legacy_key != key:
                adopt_legacy_workspace(base, key, legacy_key)
        ws = SaveWorkspace(base, key)
        ws.ensure()
        return ws

    def _status_message(self, result: ActiveSaveResult) -> str | None:
        if result.status == STATUS_NO_LOG_FOLDER:
            return (
                "I couldn't find Satisfactory's save data yet. Start the game "
                "once, then try again."
            )
        if result.status == STATUS_NO_ACTIVE_SAVE:
            return (
                "Found the newest Satisfactory log, but no active save was "
                "detected. Load a save in Satisfactory first."
            )
        return None

    def _diag(self, message: str) -> None:
        self.printr.print(message, color=LogType.SYSTEM, server_only=True)

    def _start_map_overlay(self) -> None:
        if self._map_overlay is not None:
            self._map_overlay.stop()
            self._map_overlay = None
        if not self._map_overlay_enabled():
            return
        overlay = MapOverlay(
            size=self._map_overlay_size(),
            display=self._map_overlay_display(),
            duration_s=self._map_overlay_duration_seconds(),
            position=self._map_overlay_position(),
        )
        if overlay.start():
            self._map_overlay = overlay
            self._diag("[Satisfactory] standalone map popup ready.")
        else:
            self._diag(
                "[Satisfactory] map popup unavailable: "
                f"{overlay.failed_reason or 'unknown reason'}."
            )

    def _show_map_path(self, image_path: Path) -> str:
        if not self._map_overlay_enabled():
            return "Map popup is disabled in Satisfactory skill settings."
        if self._map_overlay is None:
            self._start_map_overlay()
        overlay = self._map_overlay
        if overlay is None or not overlay.show(image_path):
            reason = overlay.failed_reason if overlay is not None else "could not start"
            return f"I made the map, but couldn't open the popup ({reason})."
        return "Opened the Satisfactory map popup."

    def _latest_map_path(self, ws: SaveWorkspace) -> Path | None:
        mirror_dir = ws.dir / "mirror"
        try:
            candidates = [path for path in mirror_dir.glob("location_*.png") if path.is_file()]
            return max(candidates, key=lambda path: path.stat().st_mtime_ns) if candidates else None
        except OSError:
            return None

    def _show_locate_result(self, ws: SaveWorkspace, query: str) -> str | None:
        image_path = ws.dir / "mirror" / f"location_{slugify(query)}.png"
        if not image_path.is_file():
            return None
        return self._show_map_path(image_path)

    async def _run_factory_audit_async(
        self, result: ActiveSaveResult, ws: SaveWorkspace, phase: int = 0
    ) -> str:
        """Run one serialized audit off the event loop.

        Shielding the worker means unload waits for an in-flight save parse to
        finish instead of leaving a thread writing mirror artifacts after the
        skill has been torn down.
        """
        if self._audit_lock is None:
            self._audit_lock = asyncio.Lock()
        async with self._audit_lock:
            worker = asyncio.create_task(
                asyncio.to_thread(self._run_factory_audit, result, ws, phase)
            )
            try:
                return await asyncio.shield(worker)
            except asyncio.CancelledError:
                try:
                    await worker
                except Exception as exc:  # pragma: no cover - diagnostic on shutdown
                    self._diag(f"[Satisfactory] audit worker failed during shutdown: {exc}")
                raise

    async def _auto_audit_once(self) -> None:
        """Run an automatic audit on first detection or a save-file change."""
        result = self._resolve()
        observation = _active_save_observation(result)
        if observation is None:
            # Resetting makes a save that disappears and later returns trigger
            # immediately, even when its file marker is unchanged.
            self._auto_audit_observation = None
            return

        if not self._auto_audit_has_run:
            reason = "startup"
        elif self._auto_audit_observation is None:
            reason = "active save detected"
        elif observation != self._auto_audit_observation:
            reason = "save changed"
        else:
            return

        ws = self._workspace_for(result)
        mirror_path = ws.dir / "mirror" / "latest_mirror.json"
        try:
            before_mtime_ns = mirror_path.stat().st_mtime_ns
        except OSError:
            before_mtime_ns = None

        self._diag(
            f"[Satisfactory] automatic audit starting ({reason}) for "
            f"{result.save_name}."
        )
        try:
            output = await self._run_factory_audit_async(result, ws)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            self._diag(f"[Satisfactory] automatic audit failed: {clip(str(exc), 240)}")
        else:
            try:
                after_mtime_ns = mirror_path.stat().st_mtime_ns
            except OSError:
                after_mtime_ns = None
            if after_mtime_ns is not None and after_mtime_ns != before_mtime_ns:
                self._diag(
                    f"[Satisfactory] automatic audit completed for {result.save_name}."
                )
            else:
                compact = clip(" ".join(output.splitlines()), 240)
                self._diag(
                    f"[Satisfactory] automatic audit did not build a mirror: {compact}"
                )
        finally:
            # A failure retries on the next save update instead of flooding
            # logs on every inexpensive watcher poll.
            self._auto_audit_has_run = True
            self._auto_audit_observation = observation

    async def _auto_audit_loop(self) -> None:
        """Watch for an active save and keep its factory mirror current."""
        while True:
            try:
                await self._auto_audit_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # pragma: no cover - defensive background guard
                self._diag(f"[Satisfactory] automatic audit watcher error: {exc}")
            await asyncio.sleep(_AUTO_AUDIT_POLL_SECONDS)

    def _lookup_lines(self, query: str) -> list[str]:
        """Return bounded Docs lookup lines for ``query`` (items then recipes).

        Capped at 5 items and 5 recipes (``satisfactory_dataset``'s own
        clamp). Any failure to reach or read the Docs catalog degrades to
        one short "unavailable" line rather than raising.
        """
        discovery = discover_docs(
            configured_file=self._docs_file(),
            configured_install_dir=self._install_dir(),
            locale=self._docs_locale(),
        )
        if discovery.docs_path is None:
            return ["I couldn't look that up because I couldn't find Satisfactory's game data."]
        try:
            catalog, _ = get_docs_catalog(discovery.docs_path)
        except (OSError, ValueError) as exc:
            self._diag(f"[Satisfactory] lookup failed to load Docs: {exc}")
            return ["I couldn't look that up because Satisfactory's game data would not open."]
        return build_lookup_lines(catalog, query)

    def _plan_status_lines(self, ws: SaveWorkspace) -> list[str]:
        """Return up to 5 compact lines describing persisted master-plan stages.

        Sourced via ``SaveStore.list_stage_revisions`` and
        ``load_stage_plan`` for plan "master". Reads only; never creates a
        store. Absent store, absent master plan, or no stage revisions
        yet all degrade to no section rather than an error.
        """
        return build_plan_status_lines(ws.dir / "planning.sqlite3")

    @tool(
        description=(
            "Check the current Satisfactory save for saved jobs, notes, goals, "
            "production setups, recipes, or locations. Use lookup for general "
            "item and recipe facts. Use locate for something built in this save; "
            "it also opens the map. Prefer show_satisfactory_map for direct map requests."
        ),
        wait_response=True,
    )
    async def get_satisfactory_context(
        self, focus: str = "", lookup: str = "", locate: str = ""
    ) -> str:
        """Return the active save identity and a compact planning summary.

        Args:
            focus: Optional keyword to filter records (matched across title,
                details, inputs, and outputs) before they are capped.
            lookup: Optional item or recipe name to look up in the bundled
                Docs catalog (capped at 5 items and 5 recipes).
            locate: Optional item, recipe, or resource name to find on the
                save's factory mirror (from the last audit). Returns
                coordinates for up to 5 matches and renders a location map
                PNG for the top match; absent mirror explains how to build
                one.
        """
        result = self._resolve()
        message = self._status_message(result)
        if message:
            self._diag(f"[Satisfactory] context unavailable: {result.status}")
            return message

        ws = self._workspace_for(result)
        # Focus is applied inside summary() BEFORE capping, so a matching older
        # record is not hidden behind newer unrelated records.
        summary = ws.summary(self._max_response_items(), focus=focus)

        header_lines: list[str] = [f"Active save: {result.save_name}"]
        if result.session_name:
            header_lines.append(f"Session: {result.session_name}")
        note = _save_file_note(result)
        if note:
            header_lines.append(note)
        if result.log_mtime:
            header_lines.append(
                f"Detected from {result.log_file.name} ({result.log_mtime:%Y-%m-%d %H:%M})"
            )
        header_lines.extend(project_assembly_reference_lines(focus))
        if lookup.strip():
            header_lines.extend(self._lookup_lines(lookup.strip()))
        locate_query = locate.strip()
        # Defensive routing for model calls that put a recognized production
        # building in `focus` despite a spoken where/map request. This happened
        # live when Faster Whisper transcribed "oil extractors" as "oilless
        # extractors" and the model selected context instead of the map tool.
        if not locate_query and focus.strip() and query_targets_machine_type(focus):
            locate_query = focus.strip()
        if locate_query:
            background_getter = getattr(self, "_map_background_image", None)
            background = background_getter() if callable(background_getter) else None
            header_lines.extend(
                build_locate_lines(ws.dir, locate_query, background)
            )
            show_locate = getattr(self, "_show_locate_result", None)
            popup_status = show_locate(ws, locate_query) if callable(show_locate) else None
            if popup_status:
                header_lines.append(popup_status)
        header_lines.extend(self._plan_status_lines(ws))

        # format_context de-duplicates blocked flows and enforces a hard global
        # character budget so the return stays under the low-token target; the
        # lookup and plan-status lines above are folded into header_lines so
        # they are accounted for by that same budget, not appended around it.
        return format_context(header_lines, summary)

    @tool(
        description=(
            "Open or close the Satisfactory map popup. Use this whenever the player "
            "asks where something is. Show with a query to find it, show without a "
            "query to reopen the last map, or hide to close the popup."
        ),
        wait_response=True,
    )
    async def show_satisfactory_map(
        self,
        query: str = "",
        action: Literal["show", "hide"] = "show",
    ) -> str:
        """Control the standalone Satisfactory map popup.

        Args:
            query: Item, recipe, resource, line, or machine to locate. Omit to
                reopen the latest rendered location map.
            action: "show" to render/open the map or "hide" to close it.
        """
        if action == "hide":
            if self._map_overlay is not None:
                self._map_overlay.hide()
            return "Closed the Satisfactory map popup."

        result = self._resolve()
        message = self._status_message(result)
        if message:
            return message
        ws = self._workspace_for(result)

        locate_query = query.strip()
        if not locate_query:
            latest = self._latest_map_path(ws)
            if latest is None:
                return "I don't have a map to reopen yet. Tell me what you want to find."
            return self._show_map_path(latest)

        background_getter = getattr(self, "_map_background_image", None)
        background = background_getter() if callable(background_getter) else None
        lines = build_locate_lines(ws.dir, locate_query, background)
        popup_status = self._show_locate_result(ws, locate_query)
        if popup_status:
            lines.append(popup_status)
        return "\n".join(lines)

    @tool(
        description=(
            "Save or update a note, job, goal, or production setup for the current "
            "Satisfactory save. Use when the player asks to remember something, "
            "add a job, mark work done, or change a planned production setup."
        ),
        wait_response=True,
    )
    async def update_satisfactory_plan(
        self,
        action: Literal[
            "add_note",
            "add_todo",
            "complete_todo",
            "add_goal",
            "add_flow",
            "update_flow",
            "archive_item",
        ],
        title: str = "",
        details: str = "",
        item_id: str = "",
        inputs: str = "",
        outputs: str = "",
        status: str = "",
        area: str = "",
        recipe: str = "",
        machines: str = "",
        constraints: str = "",
        clear_fields: str = "",
        **kwargs: Any,
    ) -> str:
        """Add or update a planning record for the active save.

        Args:
            action: The operation to perform.
            title: Title for new notes, todos, goals, or flows.
            details: Optional extra detail; preserves the player's own wording.
            item_id: Id of an existing item (for complete_todo, archive_item, update_flow).
            inputs: Semicolon-separated input materials for a flow, e.g. "Iron Ore 240/min; Coal 240/min".
            outputs: Semicolon-separated output materials for a flow, e.g. "Steel Ingot 360/min".
            status: Optional flow status: planned, building, blocked, balanced, done, archived.
            area: Optional map area/location for a flow, e.g. "Northern Forest".
            recipe: Optional recipe name for a flow, e.g. "Steel Beam (Foundry)".
            machines: Optional machine list/counts for a flow, e.g. "Foundry x8; Constructor x4".
            constraints: Optional constraint note for a flow, e.g. "power<=200MW".
            clear_fields: For update_flow only. Comma/semicolon-separated fields to
                reset (empty strings otherwise mean "leave unchanged"). Allowed:
                details, area, recipe, machines, constraints, inputs, outputs.
        """
        if not self._allow_plan_writes():
            return "Saving notes and plans is turned off in the skill settings."

        result = self._resolve()
        message = self._status_message(result)
        if message:
            return message

        ws = self._workspace_for(result)
        now = datetime.now()
        inputs, outputs = _normalize_rate_aliases(inputs, outputs, kwargs)

        if action in ("complete_todo", "archive_item"):
            if not item_id:
                return "I couldn't tell which saved item you wanted to change."
            kind, target_error = _resolve_status_target(action, item_id)
            if target_error:
                return target_error
            new_status = STATUS_DONE if action == "complete_todo" else STATUS_ARCHIVED
            if not ws.set_status_for_kind(kind, item_id, new_status, now):
                return "I couldn't find that saved item."
            ws.add_item("changes", f"{action}: {item_id}", "", now)
            return "Done — I updated that saved item."

        flow_status = status.strip().lower() if status.strip() else None
        if flow_status and flow_status not in FLOW_STATUSES:
            return f"I don't recognize that progress status. Try: {', '.join(FLOW_STATUSES)}."

        if action == "update_flow":
            if not item_id:
                return "I couldn't tell which production setup you wanted to change."
            try:
                to_clear = parse_clear_fields(clear_fields)
            except ValueError as exc:
                return str(exc)
            found = ws.update_flow(
                item_id,
                now,
                title=title or None,
                details=details or None,
                inputs=_parse_rates(inputs) if inputs.strip() else None,
                outputs=_parse_rates(outputs) if outputs.strip() else None,
                status=flow_status,
                area=area or None,
                recipe=recipe or None,
                machines=machines or None,
                constraints=constraints or None,
                clear_fields=to_clear,
            )
            if not found:
                return "I couldn't find that production setup."
            ws.add_item("changes", f"update_flow: {item_id}", "", now)
            return "Done — I updated that production setup."

        if not title.strip():
            return "Tell me what you want to call it."

        # Full title is stored; only the echoed acknowledgement is clipped.
        title_disp = clip(title.strip(), _ACK_TITLE_MAX)

        if action == "add_flow":
            ws.add_item(
                "flows",
                title,
                details,
                now,
                extra={
                    "inputs": _parse_rates(inputs),
                    "outputs": _parse_rates(outputs),
                    "area": area.strip(),
                    "recipe": recipe.strip(),
                    "machines": machines.strip(),
                    "constraints": constraints.strip(),
                },
                status=flow_status or "planned",
            )
            ws.add_item("changes", f"add_flow: {title.strip()}", "", now)
            return f"Saved the production setup '{title_disp}' for {result.save_name}."

        kind = {"add_note": "notes", "add_todo": "todos", "add_goal": "goals"}[action]
        ws.add_item(kind, title, details, now)
        ws.add_item("changes", f"{action}: {title.strip()}", "", now)
        friendly_kind = {"notes": "note", "todos": "job", "goals": "goal"}[kind]
        return f"Saved the {friendly_kind} '{title_disp}' for {result.save_name}."

    def _run_factory_audit(
        self, result: ActiveSaveResult, ws: SaveWorkspace, phase: int = 0
    ) -> str:
        """Locate the Docs file, then hand off to the pure audit pipeline.

        Reachable via ``calculate_satisfactory_plan(mode="audit")``. The caller
        has already resolved the active save, confirmed its ``.sav`` file
        exists, and validated ``phase`` (0 or 1-5).
        """
        discovery = discover_docs(
            configured_file=self._docs_file(),
            configured_install_dir=self._install_dir(),
            locale=self._docs_locale(),
        )
        if discovery.docs_path is None:
            return format_docs_missing_message(discovery.searched)

        return run_factory_audit_pipeline(
            save_file=result.save_file,
            workspace_dir=ws.dir,
            docs_path=discovery.docs_path,
            parser_runtime_dir=self._parser_runtime_dir(),
            trend_config=TrendConfig(
                window_saves=self._mirror_trend_window_saves(),
                zero_streak_saves=self._mirror_zero_streak_saves(),
                deviation_threshold=self._mirror_deviation_threshold(),
            ),
            diag=self._diag,
            phase=phase,
        )

    @tool(
        description=(
            "Plan production or check the current Satisfactory factory. Use plan "
            "for a Space Elevator phase, machine counts, power, or a full build "
            "order. Use audit to read what is actually in the current save. Stage "
            "handles one phase; master handles all phases. Recipe choices, build "
            "steps, saved jobs, and pace comparisons are optional."
        ),
        wait_response=True,
    )
    async def calculate_satisfactory_plan(
        self,
        phase: int = 0,
        pace_multiplier: float = 1.0,
        include_alternates: str = "",
        persist: bool = True,
        mode: Literal["plan", "audit"] = "plan",
        scope: Literal["stage", "master"] = "stage",
        pin_recipes: str = "",
        ban_recipes: str = "",
        include_construction: bool = False,
        create_build_todos: bool = False,
        pace_scenarios: str = "",
    ) -> str:
        """Compute (and usually persist) a Project Assembly stage plan, or audit the save.

        Args:
            phase: Project Assembly phase number (1-5) for scope="stage"
                (the default); must be omitted or 0 for scope="master"
                (which plans every phase at once). For mode="audit",
                optional: 0 (default) runs the classic factory mirror only,
                1-5 additionally compares the mirror against that phase's
                latest stored master-plan revision when one exists.
            pace_multiplier: Window-hours multiplier in [1.0, 3.0]. Ignored
                for mode="audit".
            include_alternates: Semicolon-separated alternate recipe names to
                allow beyond the default gate, e.g. "Alternate: Steel Rod".
                Ignored for mode="audit".
            persist: When True (default), save the computed stage(s) as new
                revision(s) of the save's master plan and export artifacts.
                Ignored for mode="audit".
            mode: "plan" to compute a stage plan (default), or "audit" to
                mirror the current factory from the save.
            scope: "stage" to plan a single phase (default), or "master" to
                build and persist all five Project Assembly phases at once.
                Ignored for mode="audit".
            pin_recipes: Semicolon-separated recipe names to force; each
                must already be reachable via the default gate or
                include_alternates. Ignored for mode="audit".
            ban_recipes: Semicolon-separated recipe names to exclude, even
                if otherwise unlocked. Ignored for mode="audit".
            include_construction: When True, append a construction bill and
                dependency-ordered build sequence to the response and write
                a third artifact. Defaults to False (response unchanged).
                Ignored for mode="audit" and scope="master".
            create_build_todos: When True, add a journal todo per build task
                (capped at 20). Only meaningful with include_construction=True,
                persist=True, and plan writes allowed in skill settings;
                otherwise a no-op (or a refusal line when plan writes are
                disabled). Ignored for mode="audit" and scope="master".
            pace_scenarios: Semicolon-separated pace multipliers (1-4 distinct
                values, each in [1.0, 3.0]), e.g. "1.0;2.0;3.0". When set,
                computes an unpersisted side-by-side comparison across those
                paces instead of a normal plan; overrides persist (nothing is
                ever saved) and never touches the store or workspace. Works
                with scope="stage" (uses phase) or scope="master". Ignored
                for mode="audit".
        """
        result = self._resolve()
        message = self._status_message(result)
        if message:
            if mode == "audit":
                self._diag(f"[Satisfactory] factory audit unavailable: {result.status}")
            else:
                self._diag(f"[Satisfactory] plan unavailable: {result.status}")
            return message

        if mode == "audit":
            if phase != 0 and not (1 <= phase <= 5):
                return (
                    f"For a factory check, choose phase 1 to 5 or leave it at 0. "
                    f"I received {phase}."
                )
            if result.save_file is None:
                note = _save_file_note(result)
                return (
                    "I found the active game, but I couldn't read its save file. "
                    f"{note or ''}"
                ).strip()
            ws = self._workspace_for(result)
            return await self._run_factory_audit_async(result, ws, phase)

        if scope == "master" and phase != 0:
            return (
                f"A full-game plan already covers every phase, so leave the phase at 0. "
                f"I received {phase}."
            )

        discovery = discover_docs(
            configured_file=self._docs_file(),
            configured_install_dir=self._install_dir(),
            locale=self._docs_locale(),
        )
        if discovery.docs_path is None:
            return format_docs_missing_message(discovery.searched)

        try:
            catalog, dataset_info = get_docs_catalog(discovery.docs_path)
        except (OSError, ValueError) as exc:
            self._diag(f"[Satisfactory] plan failed to load Docs: {exc}")
            return f"I couldn't read Satisfactory's game data: {clip(str(exc), 240)}"

        try:
            phase_data = load_project_assembly_phases()
        except ValueError as exc:
            self._diag(f"[Satisfactory] plan phase data invalid: {exc}")
            return str(exc)

        if pace_scenarios.strip():
            return run_scenario_comparison(
                catalog=catalog,
                phase_data=phase_data,
                scope=scope,
                phase=phase,
                pace_scenarios=pace_scenarios,
                include_alternates=include_alternates,
                pin_recipes=pin_recipes,
                ban_recipes=ban_recipes,
            )

        if scope == "master":
            return run_master_calculation(
                result=result,
                get_workspace_dir=lambda: self._workspace_for(result).dir,
                catalog=catalog,
                dataset_info=dataset_info,
                phase_data=phase_data,
                pace_multiplier=pace_multiplier,
                include_alternates=include_alternates,
                persist=persist,
                pin_recipes=pin_recipes,
                ban_recipes=ban_recipes,
            )

        return run_plan_calculation(
            result=result,
            get_workspace_dir=lambda: self._workspace_for(result).dir,
            catalog=catalog,
            dataset_info=dataset_info,
            phase_data=phase_data,
            phase=phase,
            pace_multiplier=pace_multiplier,
            include_alternates=include_alternates,
            persist=persist,
            pin_recipes=pin_recipes,
            ban_recipes=ban_recipes,
            include_construction=include_construction,
            create_build_todos=create_build_todos,
            get_workspace=lambda: self._workspace_for(result),
            get_allow_plan_writes=lambda: self._allow_plan_writes(),
        )
