# TODO - wow_wowhead

## Drafting phase (next)

- [ ] Survey wago.tools exports: which DBC tables we actually need (Items, ItemSparse, Quests, QuestV2, Creatures, AreaTable, MapDifficulty, etc.)
- [ ] Decide caching/refresh strategy for static dumps (download cadence, storage location, version pinning)
- [ ] Decide query API surface (functions exposed to the persona)
- [ ] Investigate tooltip endpoint stability and rate limits

## Lookups required by the six questions

- [ ] Item by ID -> stats, slot, ilvl, source(s), socket count, requirements, drop locations, vendor sources
- [ ] Item by name -> ID resolution (fuzzy match)
- [ ] Quest by ID -> objectives, rewards, prerequisites, follow-up quest IDs, faction, level
- [ ] Quest by name -> ID resolution (fuzzy match)
- [ ] NPC by name or ID -> coords, zone, role (vendor / trainer / quest giver), services
- [ ] Zone / area lookup -> map ID, level range, instance flag, parent zone
- [ ] Talent tree by spec -> tree structure, talent IDs, talent string encode/decode
- [ ] Instance / dungeon by ID -> boss list, difficulty options, area linkage
- [ ] Enchant / gem by ID -> stats, slot eligibility, source
- [ ] Recipe / profession lookup -> recipe trees, materials, source
- [ ] Currency / reputation -> hierarchy, rewards, requirements

## Cross-cutting

- [ ] Patch staleness handling: how does the skill report "data may be outdated" when a new WoW patch ships before wago.tools refreshes?
- [ ] Localization: WoW supports many locales; user is likely enUS, but design for locale awareness from the start

## Out of scope for v0.1

- Per-character recommendations (those need raidbots + log_reader)
- Live AH prices (no good public source)
- Performance / simulation data: DPS, item upgrade math, sim results (lives in `wow_raidbots`)
- Talent build *recommendations* (lives in `wow_raidbots`); this skill owns the talent tree *structure* itself
