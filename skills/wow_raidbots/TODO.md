# TODO - wow_raidbots

**Priority: LAST.** Build after `wow_log_reader` and `wow_wowhead` are functional.

## Drafting phase (when we get to it)

- [x] Capture the API surface from https://www.raidbots.com/developers (PDF snapshot 2026-04-26; full surface documented in README)
- [ ] Decide minimum-viable feature set for v0.1: pre-fill URL generator + report-file reader
- [ ] Decide how a user hands a report URL back to Wingman (voice "the report is X", typed paste, auto-poll a clipboard?)
- [ ] Define a supplier-agnostic public interface ("simulate", "compare items", "fetch report") so a future supplier swap is local to this skill

## Pre-fill URL generator

- [ ] Implement realm-name -> slug normalizer (lowercase, strip spaces and apostrophes)
- [ ] Build URL for `simbot/stats?region=&realm=&name=` from current character state
- [ ] Open URL via system handler (or just return the URL for the persona to speak/show)

## Report file reader

- [ ] HTTP client for `simbot/report/{ID}/data.json` (and `data.csv` when `simbot.hasCsv` is set)
- [ ] Parser for the SimC JSON output (top 200 actors + base actor structure)
- [ ] Extract per-actor DPS, gear snapshot, stat snapshot, talents
- [ ] Diff helper for Top Gear results: rank actors by DPS, surface the best item per slot
- [ ] Local report cache with TTL (avoid re-fetching the same report)

## Top-sim aggregates (lower priority)

- [ ] Fetcher for `{YYYY-MM-DD}-summary.csv` and `details.json`
- [ ] "What does a top {spec} look like" lookup
- [ ] Decide whether this is user-facing or just used internally for sanity checks

## Cross-cutting

- [ ] Failure modes: Raidbots down, report URL invalid, malformed JSON, expired report
- [ ] Result freshness: when does a previous report become invalid (gear change, talent change, patch)?
- [ ] Attribution: every result we surface should reference the original report URL (Raidbots terms request this)

## Out of scope (owned by wow_wowhead)

- Static game data: items, talents, instances, enchantments, crafting, item curves, bonuses, item sets, item conversions, item names, item limit categories
- DBCache files (irrelevant unless we run SimC ourselves, which we will not)

## Out of scope (entirely)

- Headless sim submission (Raidbots does not expose this publicly)
- Custom APL editing
- Multi-target / fight-style configurator beyond Raidbots defaults
- Comparison across multiple character snapshots over time
- Iframe embed widgets (target websites, not voice companions)
