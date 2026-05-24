# DEVLOG - wow_raidbots

## 2026-04-26 - Scaffold initialized

- Folder created with README, DEVLOG, TODO. No code yet.
- Role decided: stateless simulation client. Takes SimC export in, returns parsed Raidbots results out.
- Pipeline decided: SimC export comes from the WoW addon via `wow_log_reader`, never collected directly here.

## 2026-04-26 - Reference site identified

- Canonical API reference: https://www.raidbots.com/developers
- Verified the page is a JS-rendered SPA; server-side HTML is empty boilerplate. Cannot be scraped with raw HTTP. Capture must come from a rendered browser session (manual paste, screenshot, or headless browser) before drafting the API client.

## 2026-04-26 - Reference site captured; access model is read-only

- User provided a PDF snapshot of the developers page; full content captured.
- Major finding: Raidbots does NOT document a public submission API. There is no programmatic "run a sim" endpoint. Original assumption that this skill would be a "stateless sim client" submitting SimC strings is wrong.
- Actual access surface (all public, no auth): static JSON data dumps, per-report file URLs, daily top-sim aggregates, URL pre-fill for the website, embeddable talent widget, DBCache binaries.
- Architectural pivot: this skill is now a **read-only Raidbots client and URL generator**. The user runs sims on the website; the skill builds the pre-filled URL beforehand and parses the report data afterwards.
- UX impact: Q1 (item upgrade) and Q6 (DPS estimate) become user-in-the-loop, not headless. Wingman facilitates and explains, but the sim run requires a click.
- Data overlap discovered: Raidbots static JSON covers items, talents, instances, enchants, crafting, item sets. Significant overlap with `wow_wowhead`'s planned remit. Decided ownership boundary: this skill owns sim-adjacent data; `wow_wowhead` owns NPCs / quests / areas / coords / vendors.
- README rewritten with full capability list and corrected data flow.

## 2026-04-26 - Scope narrowed: performance metrics only; lowest priority

- User clarified the ownership boundary: this skill owns ONLY performance and simulation metrics. All static game data (items, talents, instances, enchants, crafting, item curves, bonuses, etc.) belongs to `wow_wowhead`, regardless of whether Raidbots happens to publish dumps for it.
- Build order locked: `wow_log_reader` first, `wow_wowhead` second, `wow_raidbots` last.
- Supplier swappability noted: Raidbots may eventually be replaced by another sim supplier with a better (submission-capable) API. The skill's public interface should be designed around domain concepts ("simulate", "compare items", "fetch report") rather than Raidbots URL shapes, so a future swap touches only this skill.
- README rewritten to reflect narrowed scope. Static data fetcher and DBCache work moved out of TODO entirely.
