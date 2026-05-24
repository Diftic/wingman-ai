# WoW Log Reader

Game-state ingestion for the WoW Wingman persona. Tails the combat log and polls the WoW addon's SavedVariables, normalizes both into the shared cross-game JSONL envelope.

## Status

Scaffold. No implementation yet. Test fixtures available (Den of Nalorakk session, 2026-04-26).

## Data channels

**Combat channel (live)**

Tails `<install>\_retail_\Logs\WoWCombatLog-*.txt`. Enabled in-game via `/combatlog` or `LoggingCombat(true)`. Carries combat events only: encounters, deaths, zone changes, positions, casts, damage, heals, dispels, interrupts. No loot, currency, or quest data by Blizzard design.

**Addon channel (state)**

The WoW addon writes character state to `<install>\_retail_\WTF\Account\<acct>\SavedVariables\<addon>.lua`. Blizzard flushes the file only on `/reload`, zone change, and logout. Skill polls file mtime and parses the appended tail. Carries everything outside combat: loot, currency, quests, gear, talents, reputation, SimC export.

## Output

Shared JSONL envelope. See `project_cross_game_event_log.md` in user memory for the spec. `source` field is `"log"` or `"mod"` to differentiate channels.

## Sibling skills (same WoW persona)

- `wow_wowhead`: external knowledge base lookups
- `wow_raidbots`: SimC submission and DPS sims

## Reference

- Full architecture: see user memory `project_wow_companion.md`
- Game build at scaffold time: WoW 12.0.5, combat log version 22
- Confirmed character: Lexatus-Draenor-EU
