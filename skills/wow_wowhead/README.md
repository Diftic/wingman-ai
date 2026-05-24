# WoW Wowhead

External knowledge base for the WoW Wingman persona. Owns all static game data: items, talents, quests, NPCs, instances, enchants, areas/zones, vendors, coordinates, anything that isn't a performance simulation.

## Status

Scaffold. No implementation yet. **Second priority** after `wow_log_reader`.

## Responsibility

Stateless knowledge layer. This skill knows nothing about the player's character; it only knows the WoW universe. The Wingman persona orchestrates between this skill and `wow_log_reader` when a question needs both ("have I done X?" = wowhead resolves name to ID, log_reader checks state).

Wowhead is a complete information source for everything and anything about WoW. The ambition of this skill is to surface that completeness through a structured query API. The lookup categories listed below are illustrative, not exhaustive; if Wowhead has it and it isn't a performance simulation, this skill owns it.

Performance and simulation data is the only explicit exception and belongs to `wow_raidbots`.

## Question coverage

This skill is involved in five of the six core questions:

- Q2: Where do I go for action X? (NPCs, vendors, trainers, quest givers, coords)
- Q3 (name -> ID resolution): Have I completed quest A?
- Q4 (objectives + walkthrough): How do I complete quest B?
- Q5 (prereq chain): What do I need to access quest C?
- Q1 (item identity, sources, requirements): Is this item an upgrade for me? (Wowhead supplies what the item is; `wow_raidbots` decides whether it is an upgrade)

## Data sources (priority order)

1. **wago.tools static DBC dumps** (preferred). Free, comprehensive, lags patches by hours to days. Items, ItemSparse, Quests, QuestV2, Creatures, AreaTable, MapDifficulty, etc.
2. **Wowhead tooltip endpoint** (`nether.wowhead.com/tooltip/...`). Undocumented, used by their in-game client. Real-time but fragile.
3. **HTML scraping of wowhead.com**. Last resort, ToS gray area.

## Lookups owned by this skill

- Items: stats, slot, ilvl, sources, socket count, drop locations, vendor sources, requires, unique-equipped flags
- Talents: tree structure, talent IDs, talent strings (encode/decode), spec coverage
- Quests: name, objectives, rewards, prerequisites, follow-up quest IDs, faction restrictions, level requirements
- NPCs: name, coords, zone, role (vendor / trainer / quest giver), services offered
- Areas / zones: map ID, level range, instance flag, parent zone
- Instances and encounters: dungeon / raid identity, boss list, difficulties (this duplicates Raidbots' `instances.json` but keeps `wow_raidbots` focused on perf data only)
- Enchantments and gems: stats, slot eligibility, profession source
- Currencies, reputations, factions: hierarchy, rewards
- Recipes / professions: recipe trees, materials, sources

If it is static reference data about the WoW universe, it lives here.

## Sibling skills (same WoW persona)

- `wow_log_reader`: live game-state ingestion
- `wow_raidbots`: performance simulation client (item DPS deltas, character DPS estimates)

## Reference

- Full architecture: see user memory `project_wow_companion.md`
