# DEVLOG - wow_wowhead

## 2026-04-26 - Scaffold initialized

- Folder created with README, DEVLOG, TODO. No code yet.
- Role decided: stateless knowledge layer. Does not know about the player; the persona bridges to `wow_log_reader` for state-aware questions.
- Data source priority decided: wago.tools static dumps preferred, tooltip endpoint as fallback, HTML scrape as last resort.

## 2026-04-26 - Scope expanded: owns ALL static game info

- User clarified the ownership boundary: this skill owns ALL static game data, not just NPCs / quests / areas / coords / vendors. Items, talents, instances, enchants, crafting, item curves, bonuses, item sets, item names, item limit categories, item conversions all live here.
- `wow_raidbots` is narrowed to performance / simulation metrics only and does not serve general game-data lookups even when Raidbots happens to publish dumps for them.
- Build order locked: `wow_log_reader` first, this skill second, `wow_raidbots` last.
- README and TODO expanded to cover the broader lookup surface.
