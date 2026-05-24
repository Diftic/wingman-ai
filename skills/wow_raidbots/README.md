# WoW Raidbots

Performance simulation client for the WoW Wingman persona. Builds pre-filled Raidbots URLs for the user to run sims on, then fetches and parses the resulting reports.

## Status

Scaffold. No implementation yet. **Lowest priority of the three WoW skills.** Will be built after `wow_log_reader` and `wow_wowhead` are functional.

## Responsibility

Performance metrics only. Item DPS deltas, character DPS estimates, top-sim references for "what should a strong {spec} pull". This skill does NOT serve general game data lookups even when Raidbots happens to publish them; that is `wow_wowhead`'s domain.

**Important:** Raidbots does not document a public submission API. Sims are run by the user on the Raidbots website. The user-in-the-loop flow is the intended pattern.

## Question coverage

- Q1: Is this item an upgrade for me? (user runs Top Gear on Raidbots, skill parses report)
- Q6: What approximate DPS should I do? (user runs Standard sim on Raidbots, skill parses report)

## Supplier-swappable design

Raidbots is the chosen supplier for v1, but the skill's role is "performance simulation client" rather than "Raidbots-specific client". If a sim supplier with a better (especially submission-capable) API surfaces later, this skill should be replaceable without touching `wow_log_reader` or `wow_wowhead`. Keep the public interface around concepts ("simulate this character", "compare these items", "fetch report by ID"), not Raidbots-specific URL shapes.

## Capabilities (from https://www.raidbots.com/developers)

All endpoints are public, no auth required. Cache locally; respect Raidbots terms by linking back to the original report.

### 1. Pre-filled URL generator

```
https://www.raidbots.com/simbot/stats?region={REGION}&realm={REALM_SLUG}&name={CHARACTER}
```

Realm uses the "slug" property from the WoW Realms API (lowercase, no spaces, no special chars). Works for any Raidbots tool (Quick Sim, Top Gear, Talent Compare).

### 2. Report file reader

Every sim produces files at:

```
https://www.raidbots.com/simbot/report/{REPORT_ID}/{filename}
```

| File | Always available | Notes |
|------|------------------|-------|
| `data.json` | Yes | Top 200 actors + base. Has `simbot.hasCsv` flag. |
| `data.full.json` | No | Only for large profileset sims. Tens of MB. |
| `data.csv` | Sims after 2019-04-13 | Actor name + DPS metrics |
| `input.txt` | Yes | Raw SimC input (Smart Sim may transform it) |
| `output.txt` | Not for profileset | Plain text SimC output |
| `index.html` | Not for profileset | HTML SimC report |
| `preview.png` | Yes | Discord embed image |

### 3. Top-sim daily aggregates

```
https://www.raidbots.com/.../{YYYY-MM-DD}-summary.csv
https://www.raidbots.com/.../{YYYY-MM-DD}-details.json
```

Top 100 actors per spec from the last 30 days, generated daily at ~10:30 UTC. Earliest date: 2020-06-13. Useful for "what does a top character of my spec look like".

## Out of scope

Raidbots also publishes static game data (`equippable-items.json`, `talents.json`, `instances.json`, `enchantments.json`, `crafting.json`, `item-curves.json`, `bonuses.json`, etc.) and DBCache binaries. **This skill does not use them.** All static game data lookups belong to `wow_wowhead`. If `wow_wowhead` later finds Raidbots' dumps useful as one source among several, that is `wow_wowhead`'s decision, not this skill's.

Embeds (iframe talent tree renderer) are also out of scope; they target websites, not voice companions.

## Data flow

1. User asks a sim-shaped question ("is this item an upgrade?").
2. `wow_log_reader` provides current character state (region, realm, name, gear snapshot, SimC export if relevant).
3. `wow_raidbots` builds a pre-filled URL and asks the user to run the sim.
4. User runs the sim, gets a report URL.
5. `wow_raidbots` fetches `data.json` (and `data.csv` if present) from the report URL and parses it.
6. Skill exposes the parsed result to the WoW persona for narration.

## Sibling skills (same WoW persona)

- `wow_log_reader`: live game-state ingestion (provides region, realm, name, SimC export)
- `wow_wowhead`: all static game data (items, talents, quests, NPCs, areas, vendors, ...)

## Reference

- Canonical API page: https://www.raidbots.com/developers
- Local PDF capture (snapshot): user's Downloads folder
- Full architecture: see user memory `project_wow_companion.md`
