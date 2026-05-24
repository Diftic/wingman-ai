# TODO - wow_log_reader

## Drafting phase

- [x] Draft full skill design: parser modules, watcher, config schema (Phase 1 done 2026-04-26; envelope writer deferred to Phase 2)
- [x] Decide on shared utility lib vs. duplicated scaffolding from `sc_log_reader` (chose duplicated scaffolding for now; can extract a shared lib later if duplication grows)
- [ ] Lock the JSONL envelope spec for WoW (which combat-log events become which envelope events; payload shape per event family) — deferred to Phase 2

## Combat channel (Phase 1 - implementation status)

- [x] Tail-watcher with rotation handling (`watcher.py::CombatLogWatcher`)
- [x] Parser for COMBAT_LOG_VERSION header (build/version captured into SessionState)
- [x] Event handlers (Phase 1 priority): ENCOUNTER_START, ENCOUNTER_END, ZONE_CHANGE, MAP_CHANGE, UNIT_DIED (player-only filter)
- [ ] PARTY_KILL, ENVIRONMENTAL_DAMAGE, SPELL_INTERRUPT, SPELL_DISPEL (Phase 1.x, not blocking)
- [ ] SPELL_DAMAGE / SPELL_HEAL aggregation for per-encounter DPS / HPS rollups (Phase 2+)
- [ ] Player GUID/name detection from SPELL_CAST_SUCCESS source (Phase 2 — combat log alone cannot tell us our own character without parsing SPELL_* events; the WoW addon will fill this in cleanly via SavedVariables)
- [x] Runtime smoke test inside Wingman venv: skill loads, no errors (confirmed 2026-04-26 after rename + bare-import fix)
- [ ] End-to-end voice query test: ask "where am I in WoW?" and confirm `get_current_wow_state` returns a sensible answer; ask "tell me about my last boss fight" and confirm `get_recent_encounters` returns the Den of Nalorakk run
- [ ] End-to-end live notification test: enable `/combatlog` in WoW, change zones / kill a mob / pull a boss; confirm `[Game Event]` messages reach Hearthwarden and trigger in-character reactions
- [ ] Decide on production defaults for `proactive_notifications` master switch and per-event toggles (currently all ON for testing)
- [ ] Time-based zone-change debouncer to suppress portal/hearth transit flicker (Phase 2 if it becomes a real annoyance)

## Addon channel

- [x] Decided: WoW addon source lives at `wow_log_reader/addon/` (same skill folder)
- [ ] Pick the addon's published name (the folder users drop into `Interface\AddOns\`); must not contain "bridge" since `sc_bridge` already exists. Candidates: `Wingman`, `WingmanWoW`, `WingmanForWoW`
- [ ] Author the `.toc` file (interface version pinned to current WoW build)
- [ ] Pick addon load model: standalone or LibStub-based
- [ ] Decide event coverage on the addon side: CHAT_MSG_LOOT, CHAT_MSG_MONEY, CHAT_MSG_CURRENCY, LOOT_OPENED, QUEST_TURNED_IN, QUEST_ACCEPTED, PLAYER_EQUIPMENT_CHANGED, PLAYER_TALENT_UPDATE, PLAYER_LEVEL_UP, etc.
- [ ] SavedVariables schema: rolling buffer with sequence number, flushed segment markers
- [ ] SimC export emitter (call SimulationCraft addon if present, or replicate the exporter)
- [ ] Mtime-based polling on the companion side

## Cross-cutting

- [ ] Sibling-skill comms: how does `wow_wowhead` query state ("did I do quest X?") - in-process API, shared event bus, or via the persona LLM?
- [ ] Test harness fed by the captured Den of Nalorakk fixture

## Out of scope for v0.1

- Loot upgrades (lives in raidbots + log_reader integration)
- Wowhead lookups (lives in wow_wowhead)
- DPS sims (lives in wow_raidbots)
