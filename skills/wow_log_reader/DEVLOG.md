# DEVLOG - wow_log_reader

## 2026-04-26 - Scaffold initialized

- Folder created with README, DEVLOG, TODO. No code yet.
- Architecture decided: dual-channel (combat log tail + addon SavedVariables polling), both emitting the shared cross-game JSONL envelope.
- Test fixture in hand: 36 MB / 116k-line clean Den of Nalorakk run with full encounter markers, zone bookends, position data, and SimC-quality character coverage.
- Battle.net launcher logs ruled out as a data source (launcher-only telemetry).
- Confirmed via audit: zero loot / currency / quest events anywhere in the persistent log files. The WoW addon is mandatory for that data.

## 2026-04-26 - Decision: WoW addon lives inside the skill folder

- The Lua source for the WoW addon will sit inside this skill at `wow_log_reader/addon/`.
- Reasoning: the addon and the skill are two halves of one contract (SavedVariables schema). Keeping them in the same folder makes the coupling visible, makes schema changes atomic across both sides, and avoids a second repo for what is functionally one feature.
- Naming note: do not call this a "bridge" anywhere in code, docs, or chat. `sc_bridge` already exists in this project space, and the term collides. Always "the WoW addon".
- Trade-off accepted: mixing Lua and Python under one skill directory.

## 2026-04-26 - Phase 1 implementation: combat-channel skill end to end

Skill is now structurally complete for the combat-log channel only. The WoW addon channel is still Phase 2. Files written:

- `__init__.py` - version (12.0.5, mirrors WoW patch), exports
- `parser.py` - Layer 3, line -> LogEvent. Phase 1 events: `COMBAT_LOG_VERSION`, `ZONE_CHANGE`, `MAP_CHANGE`, `ENCOUNTER_START`, `ENCOUNTER_END`, `UNIT_DIED`. Cheap event-name pre-filter before any csv parsing.
- `logic.py` - Layer 2, `StateLogic` aggregates events into a `SessionState` with current zone/map, in-progress encounter, rolling deques of `EncounterRecord` (50) and player-only `DeathRecord` (50).
- `watcher.py` - file tail with rotation handling. `find_active_combat_log()` resolves "newest by mtime"; `CombatLogWatcher` runs a daemon thread polling at 1.0s, line-buffers partial flushes, catches up by reading the full active file on first attach.
- `main.py` - Layer 1, `WoW_LogReader(Skill)` with three @tool methods: `get_current_wow_state`, `get_recent_encounters`, `get_recent_player_deaths`. State access guarded by a `threading.Lock`. Watcher started in `prepare()`, stopped in `unload()`. Path resolution accepts the install root, the `_retail_` folder, or the `Logs` folder; falls back to a small list of common install locations when the user leaves the path empty.
- `default_config.yaml` - skill metadata, prompt for the AI, single custom property `wow_install_path` (optional, auto-detect when blank).

**Convention deviation noted:** unlike `sc_log_reader`, this skill uses relative imports (`from .parser import ...`) for intra-skill modules instead of bare imports + `sys.path.insert`. The bare-import pattern would collide on `sys.modules['parser']` and `sys.modules['logic']` if both `sc_log_reader` and `wow_log_reader` were active in the same process. Relative imports keep modules under their fully-qualified `skills.wow_log_reader.*` names.

**Verification done outside Wingman:**
- All 5 modules pass `py_compile`.
- `parser.py` standalone: parses the 36 MB / 116k-line `Lexatus_1_WoWCombatLog.txt` fixture; counts match prior hand analysis (1 version header, 3 encounters, 8 zone, 8 map, 180 unit deaths, 0 player deaths).
- `python -m skills.wow_log_reader.logic <fixture>`: final state shows zone=Silvermoon City (correct hearth), 0 player deaths, 3 kills with fight-times Hoardmonger 86.8s / Sentinel 100.1s / Nalorakk 91.1s (matches hand-verified durations).
- `CombatLogWatcher.tick_once()` against the live `D:\Games\World of Warcraft\_retail_\Logs` directory detects the right file and emits 203 events in one tick.
- Apostrophes in zone names ("Zul'Aman", "Quel'Thalas") parse correctly.

**Known limitation (Phase 1):** the combat log does not advertise the player's own character GUID/name from any of the Phase 1 events. `SessionState.player_name` is unknown until the WoW addon channel lands in Phase 2 (or until SPELL_* parsing is added and we lazy-detect from source name on cast events).

**Not done in Wingman venv:** runtime load of the skill, @tool registration, end-to-end voice query. The system Python used here lacks `platformdirs` (a Wingman runtime dep that lives in their venv); same error reproduces against `sc_log_reader`. Final integration check happens when the user next launches Wingman.

## 2026-04-26 - Module rename + live install fix

First live install attempt failed with `attempted relative import with no known parent package`. Cause: when Wingman loads from `custom_skills/`, it loads `main.py` directly as a standalone module, not as part of a package, so `from .session_state import ...` had no parent context to resolve against.

**Two changes made together:**

1. **Switched to bare imports + `sys.path.insert(0, _THIS_DIR)`** in main.py, session_state.py, and combat_log_watcher.py. This is the same pattern `sc_log_reader` uses and it works in both the dev-tree (package) load and the custom_skills (standalone) load.

2. **Renamed three modules to unique names** to avoid `sys.modules` collisions with sibling skills under the bare-import pattern:
   - `parser.py` -> `combat_log_parser.py`
   - `logic.py` -> `session_state.py`
   - `watcher.py` -> `combat_log_watcher.py`

   Without the rename, if both `wow_log_reader` and `sc_log_reader` were ever loaded together, whichever was imported second would silently end up holding the first's classes (since `sys.modules['parser']` only holds one entry). Unique names eliminate that risk and also read more clearly than the generic ones.

`__init__.py` reduced to version metadata only, since Wingman never evaluates it in the live install (main.py is loaded directly).

`skill_installer_config.json` and `update_release.py` updated with the new filenames.

**Live install sequence:**
1. `python update_release.py` -> 8 files in `release_version/`
2. `robocopy release_version/ %AppData%/.../custom_skills/wow_log_reader/ /E /IS /IT /XF install.bat TESTER_README.txt` -> 6 runtime files installed
3. Stale `parser.py`, `logic.py`, `watcher.py` from the previous install removed from AppData before robocopy

## 2026-04-26 - Live test: skill loads cleanly, no errors

User confirmed: with the renamed modules in place, the WoW_LogReader skill loads in Wingman without errors. Hearthwarden has the skill enabled (`wow_install_path` left empty for auto-detection). Phase 1 runtime objective met: parser + watcher + state aggregator + @tool methods are all live. End-to-end voice queries against the captured fixture data are next.

## 2026-04-26 - Phase 1.5: proactive notification pipeline

Added derived-event notifications, mirroring `sc_log_reader`'s approach.

**New types in `session_state.py`:**
- `NotificationEvent(event_type, message, timestamp)` dataclass
- `StateLogic.apply()` now returns `list[NotificationEvent]`
- Each handler appends notifications when applicable (uses pre-mutation state to detect transitions like instance enter/exit)

**Nine derivable notification types:**
- `session_started` (from COMBAT_LOG_VERSION)
- `zone_entered` (ZONE_CHANGE to a non-instance zone, only if it differs from the current zone)
- `instance_entered` (ZONE_CHANGE where difficulty_id != 0, when leaving non-instance)
- `instance_exited` (ZONE_CHANGE to non-instance, when leaving an instance)
- `encounter_started` (ENCOUNTER_START)
- `encounter_ended_kill` (ENCOUNTER_END with success=True)
- `encounter_ended_wipe` (ENCOUNTER_END with success=False)
- `player_died` (UNIT_DIED filtered to is_player=True)
- `map_changed` (MAP_CHANGE; default OFF, too noisy)

**Watcher gained an `is_live` signal:**
- `CombatLogWatcher.on_event` callback signature is now `(LogEvent, bool)`
- First read after attaching to a file fires `is_live=False` for every event (catch-up)
- Subsequent ticks fire `is_live=True` (true tail)
- `main.py` only dispatches notifications when `is_live=True`. Without this, the entire history of the current `WoWCombatLog-*.txt` would replay as fresh narration every time the skill loads.

**`main.py` dispatch infrastructure (mirrors sc_log_reader):**
- `_EVENT_TOGGLE_MAP`: notification event type -> per-event toggle property name
- `_dispatch_notification(event)`: gates on master switch + per-event toggle + auto-pause counter
- `_run_notification(message)`: dedicated daemon thread with throwaway `asyncio.new_event_loop()` (the "PTT pattern" referenced by sc_log_reader; main event loop can be busy/stale and this still delivers reliably)
- `_send_notification(message)`: `await self.wingman.process(transcript=message)` (full personality + TTS pipeline)
- `on_add_user_message` override: any user utterance resets `_auto_messages_since_user_input` and unpauses
- `_MAX_AUTO_MESSAGES_WITHOUT_USER = 8`: dispatch pauses after 8 unanswered notifications, resumes on user input

**Config:**
- `proactive_notifications` master switch, **default ON for testing** (will be revisited before release)
- 9 per-event toggles, all default ON except `notify_map_changed` (OFF, too noisy)
- Hearthwarden prompt updated with a "Proactive Notifications" section explaining how to react to `[Game Event] X` messages (brief reactions, "good luck" on pulls, sympathy on wipes, no narration of details the player can already see)

**Smoke test against fixture:**
- 20 notifications derived from the Den of Nalorakk session: 1 session_started, 1 instance_entered, 3 encounter_started, 3 encounter_ended_kill, 1 instance_exited, 6 zone_entered, 5 map_changed.
- Wording inspection looks right: `[session_started] Combat logging started (WoW build 12.0.5, log v22).`, `[instance_entered] Stepped into Den of Nalorakk (difficulty 205).`, `[encounter_started] Pull: Nalorakk, group of 5.`, `[encounter_ended_kill] Killed Nalorakk in 91 seconds.`, `[instance_exited] Left Den of Nalorakk.`, etc.

**Known Phase 1.5 limitation - zone-change flicker:**
- The fixture's portal/hearth transit produced 4 zone_change events between Numazon and Zul'Aman in 430ms, all of which derive `zone_entered` notifications. Simple "differs from current" dedup catches Westfall->Westfall but not A->B->A->B oscillation.
- Real fix is a time-based debouncer (hold zone_entered for ~3s; reset timer on new event; emit only when stable). Deferred until live testing shows whether it actually annoys.

**Testing in real WoW (no replay needed):** enable combat logging in-game (`/combatlog`), then any zone change, mob kill, or instance entry will fire live notifications immediately.

## 2026-04-27 - Bug fix: auto_activate=false meant the watcher never started

User reported "log reader doesn't seem to be working" after a real WoW session (00:58 to 01:31, ~33 minutes of play, 17 zone changes, 66 mob kills). Wingman log confirmed: Hearthwarden loaded with WoW_LogReader as a discoverable skill, but no "validated and prepared" line and no "tailing combat log" line ever appeared. The watcher was never started.

**Root cause:** I had `auto_activate: false` in default_config.yaml. The Wingman framework only calls `prepare()` lazily on first activation. Without auto_activate, the watcher boot in prepare() is deferred until something explicitly triggers the skill (an AI tool call, etc.). For a proactive-notification skill that is the wrong default - the watcher must be running before there is anything to notify about.

**Fix:** changed to `auto_activate: true` (matches sc_log_reader). Re-packaged and re-deployed. After the next Wingman restart, the watcher will start as soon as Hearthwarden's config loads, and live combat-log events will produce notifications. Build / package tooling will need to skip `addon/` when bundling the Python skill, and a separate path will package the addon for users to drop into `<install>\_retail_\Interface\AddOns\`.
