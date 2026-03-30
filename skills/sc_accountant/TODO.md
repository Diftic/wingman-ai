# SC_Accountant — Task Tracking

**Author:** Mallachi
**Status:** v2.4.0 — Live Refresh, Ledger Integrity, Bug Fixes

---

## Completed

### v2.4.0 — Live Refresh, Ledger Integrity, Bug Fixes
- [x] Live dashboard refresh via version polling (2s interval, cross-browser)
- [x] HTTP middleware bumps version on POST/PUT/DELETE (multi-browser sync)
- [x] Static files served with no-cache headers (Opera caching fix)
- [x] `record_transaction` blocks commodity categories → dedicated tools enforce portfolio tracking
- [x] New `record_commodity_purchase` tool (ledger + position open)
- [x] New `record_commodity_sale` tool (ledger + position close via FIFO)
- [x] New `delete_asset` voice tool (remove without sale transaction)
- [x] Removed `set_balance` voice tool (LLM misuse risk)
- [x] Removed `starting_balance` config property
- [x] Bug fix: `update_asset` string coercion for numeric fields
- [x] Improved market data feedback (suggests `refresh_market_data`)
- [x] Wired `futures_min_profit` config to opportunity generation
- [x] Renamed config: "Minimum Profit per SCU (aUEC)", default 0

### v1.0.0 — Flat Accounting Model
- [x] Core accounting (8 tools): transactions, balance, P&L, expense/revenue breakdown
- [x] Trade orders & sessions (9 tools): create/complete/cancel orders, sessions, budgets
- [x] Market intelligence (3 tools): UEX market data with SQLite cache
- [x] Futures/Opportunities (3 tools): auto-generated trade opportunities from market data
- [x] Investment positions (4 tools): FIFO position tracking with unrealized P&L
- [x] HUD dashboard (3 tools): in-game overlay via HudHttpClient
- [x] Credits (5 tools): receivables/payables with payment tracking
- [x] Hauling (4 tools): cargo transport with cost/revenue tracking
- [x] Inventory (2 tools): manual warehouse tracking (stub)
- [x] Production (2 tools): input→output conversion logging (stub)
- [x] Bug fix: UEX `/commodities_status` returns nested `{buy, sell}` dict, not flat list

### v2.0.0 — Three-Statement Restructure
- [x] Phase 0: Data model foundation (StatementClass/Activity enums, Asset/RefineryJob dataclasses, category classification maps)
- [x] Phase 1: Three-statement report engine (Income Statement, Balance Sheet, Cash Flow)
- [x] Phase 2: Asset manager (register/sell/list/fleet summary) + Refinery manager (log/complete/pipeline summary)
- [x] Phase 3: HUD rewrite — single spreadsheet panel with 7 tabs (ledger, hangar, operations, flow, portfolio, opportunities, fleet)
- [x] Phase 4: Tool integration (removed 6 superseded tools, added 16 new tools = 53 total)
- [x] Phase 5: Planning & forecasting (break-even, activity ROI, what-if scenarios)
- [x] Phase 6: Layered complexity tiers (casual/engaged/industrial)
- [x] Test suite: 136 tests across 8 modules (models, statements, store, planning, assets, refinery, HUD, integration)

### v2.1.0 — Sibling Skill Independence + Standalone Dashboard
- [x] Sibling skill detection (`_find_sibling_skill`, `_has_logreader`, `_has_uexcorp`)
- [x] UEXCorp ship price auto-lookup in `register_asset`
- [x] `update_asset` tool (name, type, price, location, notes)
- [x] Prompt/config language cleanup — all sibling skills optional
- [x] Standalone accounting web UI (FastAPI + pywebview)
- [x] Removed HUD overlay (`hud_dashboard.py`, `test_hud.py`)
- [x] Test suite updated: 118 tests, 7 modules, 100% pass

### v2.1.2 — Split Modes + Asset Management
- [x] Group session split calculator: percentage vs flat rate toggle
- [x] Split mode persisted on GroupSession model
- [x] Group Buy/Sell buttons moved to status bar (UX improvement)
- [x] Delete asset from web UI (DELETE endpoint + modal button)
- [x] `update_asset` re-exposed as AI tool (was missing @tool after 55→20 reduction)
- [x] `default_config.yaml` updated: 21 tools, update_asset routing hints

### v2.2.0 — Planned Orders (Purchase/Sales Order Management)
- [x] `PlannedOrder` dataclass — purchase/sale order with partial fulfillment tracking
- [x] Store CRUD: `planned_orders.json` with status_in filter support
- [x] Auto-matching: transactions auto-fulfill open orders (fuzzy item name matching)
- [x] Hooks in `_sync_from_logreader()` and `record_transaction()` for auto-fulfillment
- [x] Over-fulfillment capped at ordered quantity
- [x] Sales order validation: can only plan sales for owned assets/positions/inventory
- [x] Voice tools: `create_planned_order`, `list_planned_orders` (23 total)
- [x] Dashboard: "Orders" tab with progress bars, create/edit modals, cancel/delete actions
- [x] Fulfillment history displayed in edit modal
- [x] `default_config.yaml` updated: 23 tools, planned order routing hints
- [x] Test suite: 20 new tests (model, store, fulfillment logic)

### v2.3.1 — Trade Opportunity Announcements
- [x] Proactive trade alert: announces top 5 trades when player arrives at a trading location
- [x] Location change detection via `_sync_loop` + SC_LogReader state
- [x] `announce_trade_opportunities` custom property toggle (default off)
- [x] Deduplication via `_last_announced_location`
- [x] Speech via `wingman.play_to_user()` (direct TTS, no LLM cost)

## Test Suite (v2.2.0) — COMPLETE

**138 tests, 8 modules, 100% pass rate**

Run: `pytest skills/sc_accountant/tests/ -v`

| Module | Tests | Coverage |
|--------|------:|----------|
| `test_models.py` | 19 | Classification maps, enums, from_dict round-trips |
| `test_statements.py` | 14 | Income statement, balance sheet, cash flow, asset P&L |
| `test_store.py` | 21 | Transaction/asset/refinery CRUD, filters, persistence |
| `test_planning.py` | 11 | Break-even, activity ROI, what-if scenarios |
| `test_assets.py` | 18 | Register, sell, update_asset, list, fleet summary |
| `test_refinery.py` | 15 | Log, complete, collect, list, pipeline summary |
| `test_planned_orders.py` | 20 | Model, store CRUD, fulfillment matching, fuzzy match, capping |
| `test_integration.py` | 6 | Asset lifecycle, mining pipeline, balance sheet completeness |

Structure: `conftest.py` (fixtures) + `factories.py` (data factories)
Dependencies: `pytest`, `pytest-asyncio`

---

## Known Issues

- Inventory module is a stub — will need expansion when CIG ships inventory rework
- Production module is a stub — will expand as production gameplay matures
- Opportunity fulfillment matching uses fuzzy name + best-effort location (game log data varies)

## Future Enhancements

- [ ] Add `cancel_haul` tool for marking in-transit hauls as cancelled
- [ ] Add trade route history (which routes have been most profitable over time)
- [ ] Add session-level P&L integration with positions (realized P&L per session)
- [ ] Add org-level accounting (multi-player shared ledger)
- [ ] Expand inventory module when CIG inventory rework ships
- [ ] Expand production module as Star Citizen production gameplay matures
- [ ] **Multi-profile / player name support** — Allow setting a player name on the main page
  that auto-tags all transactions. Support switching between multiple player names for users
  with multiple game accounts. Could range from a simple name tag on transactions to full
  separate ledger profiles per account.
- [ ] Consider SQLite migration for store.py if JSON files grow too large
- [ ] Per-ship P&L via `generate_asset_pnl` (engine exists, needs tool exposure)
- [ ] Refinery job → sale transaction linking for full mining margin automation
- [ ] **Wingman Deck** — Tablet touch-panel remote for Star Citizen (GameGlass alternative).
  Reuses SC_Accountant's FastAPI+SPA pattern. AI-generated button layouts, custom graphics
  (HTML/CSS/SVG), WebSocket keybind dispatch, ship-aware auto-switching via SC_LogReader.
  See diary entry 2026-03-08 for full architecture concept.

## Verified Patterns

- `@tool` decorator: only scans `dir(self)` — all tools must be on Skill class
- Thin wrapper pattern: @tool methods delegate to module manager classes
- UEX API: public, no auth, base URL `https://api.uexcorp.space/2.0`
- UEX `/commodities_status` returns `{"buy": [...], "sell": [...]}` not a flat list
- Sibling skill detection: `_find_sibling_skill(class_name)` checks `self.wingman.skills`
- UEXCorp price lookup: uses VehiclePurchasePriceDataAccess with 3-stage name matching
- Generated files dir: `get_generated_files_dir("SC_Accountant")` → AppData path
- Category classification: pure code-side mapping — zero data migration needed
- Complexity tiers: prompt shaping only — no tool removal, AI just won't suggest them
- Standalone UI: FastAPI on port 7863 + `webbrowser.open()` in default browser
