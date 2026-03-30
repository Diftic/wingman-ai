# SC_Accountant — Development Log

**Author:** Mallachi
**Skill Version:** 2.4.0

---

## 2026-03-10 — v2.4.0: Live Refresh, Ledger Integrity, Bug Fixes

### Live Dashboard Refresh
- Added `/api/version` endpoint with data version counter
- Browser polls every 2s, refreshes only when version changes
- `execute_tool` override bumps version on every voice tool call
- HTTP middleware bumps version on every POST/PUT/DELETE (cross-browser sync)
- Static files served with `Cache-Control: no-cache, no-store, must-revalidate`
- Fetch uses `cache: "no-store"` + cache-buster query param for Opera compatibility

### Ledger Integrity — Commodity Trades Route Through Portfolio
- `record_transaction` now blocks `commodity_purchase` and `commodity_sale` categories
- New `record_commodity_purchase` tool: creates ledger entry + opens portfolio position
- New `record_commodity_sale` tool: creates ledger entry + closes positions via FIFO
- Ledger is now a receipt — populated only by movements from domain tools

### New Voice Tool: `delete_asset`
- Removes asset record without creating a sale transaction
- Prevents AI from using `sell_asset` at 0 aUEC when user says "delete"

### Removed: `set_balance` Voice Tool
- LLM confused "add X to balance" with "set balance to X" — too risky
- Balance can only be set manually via the web dashboard now
- Removed `starting_balance` config property (balance init via web only)

### Bug Fix: `update_asset` String Coercion
- LLM passed `estimated_market_value` as string despite `float` type hint
- Added `float()` coercion at tool boundary for `purchase_price` and `estimated_market_value`

### Improved: Market Data Feedback
- Empty cache now tells AI to use `refresh_market_data` instead of vague "still loading"
- Commodity not found now suggests refreshing cache or checking spelling

### Config: Min Profit per SCU
- Renamed "Minimum Opportunity Profit" → "Minimum Profit per SCU"
- Wired `futures_min_profit` config to `generate_opportunities(min_margin=)` — was unused
- Default changed from 1000 to 0

### Files Changed
- **Modified:** `main.py`, `ui/app.py`, `ui/static/app.js`, `default_config.yaml`, `clean.py`

---

## 2026-03-08 — v2.3.1: Trade Opportunity Announcements

### Proactive Trade Alerts
- New feature: announces top 5 trade opportunities when player arrives at a location with commodity trading
- Triggered by location change detection in `_sync_loop` (every 30s via SC_LogReader)
- Uses `get_best_trades(location=, limit=5)` to query UEX market data
- Speaks via `wingman.play_to_user()` — uses wingman's TTS voice, no LLM round-trip
- Deduplicates with `_last_announced_location` to avoid repeating on same location
- Silently skips locations without commodity trading (empty result = no announcement)

### Configuration
- New custom property: `announce_trade_opportunities` (boolean, default `false`)
- Toggleable on/off in wingman settings menu
- Requires SC_LogReader sibling skill for location data

---

## 2026-03-07 — v2.3.0: Transaction Display & Group Events Consistency

### Transaction Description/Location Fix
- SC_LogReader synced transactions no longer concatenate shop name into description
- Description: just `"Item Purchase: item_name"` (no `" at shop"`)
- Location: uses shop_name (more specific than game location)

### Date Format — All Tabs
- All transaction dates now show `YYYY:MM:DD - HH:MM` (was date-only on Ledger, locale format on Group)
- Updated `formatTimestamp()` to produce consistent format
- Applied to: Ledger tab, Group Events tab, fulfillment history

### Group Events Tab — Ledger Parity
- Same 7 columns as Ledger: Date, Type, Category, Amount, Description, Notes, Location
- `buildFilterRow` + `wireTableFilters` for per-column text filtering
- Clickable rows open edit form (same as Ledger tab)
- API: added `id`, `notes`, `tags` to group session transaction response

### Group Session History
- When no session is active, past sessions are listed in a filterable table
- Click any past session to view full detail: transactions + split summary
- New API endpoint: `GET /api/group-session/{session_id}` returns full session detail
- Detail view includes back button, clickable/editable transaction rows

### Files Changed
- `main.py` — removed shop name from description, shop_name preferred as location
- `ui/app.py` — added session detail endpoint, `id`/`notes`/`tags` to transaction dict
- `ui/static/app.js` — group table rebuild, date format, clickable rows, session history + detail view

---

## 2026-03-07 — v2.2.1: Code Quality — 15 Rules Compliance

### DRY Refactor: store.py
Replaced 14 identical `_read_all_X` / `_write_X` method pairs with two generic
methods: `_read_json_list(path, model_cls)` and `_write_json_list(path, items)`.
All public API methods unchanged — zero impact on callers. Removed ~200 lines of
boilerplate while keeping the same behavior.

### Exception Handling Specificity
Replaced 49 `except Exception` catches across `store.py`, `main.py`, and
`ui/app.py` with specific exception types:
- `OSError` for file I/O failures
- `json.JSONDecodeError` for parse errors
- `KeyError` / `TypeError` / `ValueError` for data validation
- `AttributeError` / `ImportError` for sibling skill access

Blanket `except Exception` no longer masks programming bugs (`AttributeError`,
`TypeError`) that should surface during development.

### Inline "Why" Comments
Added design decision comments to key sections:
- Why JSONL for transactions (append-only, no corruption from partial writes)
- Why substring matching for planned order fulfillment (not Levenshtein)
- Why live data is injected into get_prompt() (token cost vs UX tradeoff)
- Why all @tool methods must live on the Skill subclass (framework constraint)
- Why sync uses a line-number cursor (avoids dedup overhead)

### Group Events Tab Button Consistency
Replaced custom `action-btn` markup (which had no CSS definition) with the
standard `actionBar()` / `wireActionButton()` pattern used by Portfolio,
Banking, and Orders tabs.

### Files Changed
- **Modified:** `store.py` (generic I/O, specific exceptions), `main.py`
  (specific exceptions, "why" comments), `ui/app.py` (specific exception),
  `ui/static/app.js` (group tab buttons)

### Test Suite
138 tests across 8 modules, 100% pass rate, <1s runtime. No test changes needed.

---

## 2026-03-07 — v2.2.0: Planned Orders (Purchase/Sales Order Management)

### Feature Overview
Added purchase and sales order management with automatic partial fulfillment
tracking. When any transaction is recorded (auto-synced or manual), the system
checks for matching open planned orders and updates fulfillment progress.

### New Model: `PlannedOrder`
- Fields: `order_type` (purchase/sale), `status` (open/partial/fulfilled/cancelled),
  `item_name`, `ordered_quantity`, `fulfilled_quantity`, `fulfillments` (list of
  `{transaction_id, quantity, amount, date}` records)
- Stored in `planned_orders.json` (JSON read-modify-write, same pattern as other entities)

### Auto-Fulfillment Logic
- Hooks into both `_sync_from_logreader()` and `record_transaction()`
- Fuzzy matching: case-insensitive partial string match (e.g. "Quantanium" matches
  "Quantanium (Raw)")
- Over-fulfillment capped at ordered quantity — extra units are ignored
- Status auto-transitions: `open` -> `partial` -> `fulfilled`

### Sales Order Constraint
Sale orders can only be created for items that exist in at least one of:
- Asset registry (fleet) — for ships, vehicles, equipment
- Open commodity positions — for held commodities
- Inventory items — for stored goods

### Voice Tools (2 new, 23 total)
- `create_planned_order`: Create a purchase or sale order with quantity, price, location
- `list_planned_orders`: Show open/partial orders with fulfillment progress

### Dashboard: "Orders" Tab
- Placed after "My Assets" in tab order
- Summary cards: purchase orders, sales orders, fulfilled count, planned value
- Table with progress bars showing `fulfilled/ordered` quantity
- BUY/SELL badges for visual distinction
- Column filtering on all fields
- Create modal for new purchase/sale orders
- Edit modal with fulfillment history, field updates, cancel/delete actions

### Files Changed
- **Modified:** `models.py` (PlannedOrder), `store.py` (CRUD + status_in filter),
  `main.py` (matching logic, 2 tools, prompt injection), `ui/app.py` (4 endpoints),
  `ui/static/app.js` (Orders tab, forms, progress bars),
  `ui/static/style.css` (progress bars, badges, action bar),
  `ui/static/index.html` (Orders tab button), `default_config.yaml` (23 tools)
- **Created:** `tests/test_planned_orders.py` (20 tests)

### Test Suite
138 tests across 8 modules, 100% pass rate, <1s runtime.

---

## 2026-03-06 — v2.1.2: Group Session Split Modes + Asset Management

### Group Session: Percentage vs Flat Rate Split
The split calculator now supports two modes, toggled via a pill-style button pair:

- **Percentage mode** (default): Each player gets a % of net. Warning if total ≠ 100%.
- **Flat rate mode**: Each player gets a fixed aUEC amount. Warning shows unallocated remainder.
- "Equal Split" adapts to mode — divides 100% or divides net equally.
- Split mode is persisted on the `GroupSession` model (`split_mode` field).
- Switching mode saves current players and re-renders immediately.

### Group Session: UX Improvements
- Moved "Group Buy" / "Group Sell" buttons into the status bar, to the left of
  "Stop Session", instead of being buried below the summary cards.

### Asset Delete (Web UI)
- Added `DELETE /api/fleet/{asset_id}` endpoint.
- Added `store.delete_asset()` method.
- Edit Asset modal now includes a red "Delete Asset" button with confirmation dialog.

### `update_asset` Tool Re-exposed to AI
The `update_asset` method existed but lost its `@tool` decorator during the 55→20
tool reduction. Re-added with description and routing hints. Tool count: 21.

### Files Changed
- **Modified:** `models.py` (GroupSession.split_mode), `store.py` (delete_asset),
  `ui/app.py` (split_mode in GET/POST/PUT group endpoints + DELETE fleet endpoint),
  `ui/static/app.js` (split mode toggle, flat rate inputs, status bar button layout,
  delete asset button), `ui/static/style.css` (split-mode-toggle, group-status-actions),
  `main.py` (@tool on update_asset), `default_config.yaml` (21 tools, update_asset routing)

---

## 2026-03-03 — v2.1.1: pywebview → Default Browser

**Issue:** `pywebview must be run on a main thread` — pywebview requires the main
thread on Windows, but skills run in background threads.

**Fix:** Replaced pywebview with `webbrowser.open()`. Dashboard opens in the user's
default browser instead of a native window. Removed `pywebview==6.1` from
`requirements.txt`. Deleted `hud_dashboard.py` (was still on disk from v2.0.0).

---

## 2026-03-03 — v2.1.0: Sibling Skill Independence + Standalone Dashboard

### Sibling Skill Independence
All sibling skills (SC_LogReader, UEXCorp, Regolith, SC_Navigator) are now
optional automation enhancers, not requirements. Every function works via
manual voice entry.

- Added `_find_sibling_skill(class_name)` — detects sibling skills at runtime
- Added `_has_logreader()` / `_has_uexcorp()` convenience checks
- `get_prompt()` dynamically reports which sibling skills are available
- Config language updated: "Optional: Install..." not "Recommended: Install..."
- Sync tool description explicitly states SC_LogReader requirement

### UEXCorp Ship Price Auto-Lookup
When UEXCorp is loaded, `register_asset` auto-populates ship/vehicle purchase
prices via UEXCorp's vehicle data access layer. Three-stage name matching:
exact `vehicle_name`, then `name`/`name_full`, then case-insensitive partial.
Falls back gracefully — if UEXCorp is not installed, prompts user for manual entry.

### New Tool: `update_asset`
Updates existing asset fields: name, type, ship_model, location, purchase_price,
estimated_market_value, notes. When purchase_price changes and market_value was
tracking it, market_value auto-follows.

### Standalone Accounting Dashboard
Replaced the HUD overlay (`hud_dashboard.py`) with a standalone web-based
accounting window:

- **`ui/app.py`** — FastAPI micro-server (port 7863) with 10 REST endpoints
- **`ui/window.py`** — pywebview native window with always-on-top
- **`ui/static/`** — SPA with 7 tabs: Ledger, Fleet, Operations, Cash Flow,
  Balance Sheet, Portfolio, Opportunities
- Dark theme, monospace numbers, auto-refresh every 5s
- Interactive tables, pagination, period selector
- Tools: `open_accounting_window`, `close_accounting_window`
- Removed: `show_spreadsheet`, `spreadsheet_navigate`, `hide_spreadsheet`

### Files Changed
- **Modified:** `main.py`, `assets.py`, `default_config.yaml`, `requirements.txt`
- **Created:** `ui/__init__.py`, `ui/app.py`, `ui/window.py`, `ui/static/index.html`,
  `ui/static/style.css`, `ui/static/app.js`
- **Deleted:** `hud_dashboard.py`, `tests/test_hud.py`
- **Dependency added:** `pywebview==6.1`

### Test Suite
118 tests across 7 modules (removed 21 HUD tests, added 7 update_asset tests).

---

## 2026-03-03 — v2.0.0: Test Suite

Built comprehensive test suite from scratch — no prior test infrastructure existed
for SC skills. 136 tests across 8 modules, 100% pass rate, <1s runtime.

### Structure
- `tests/conftest.py` — Pytest fixtures only (`store`, `format_fn`)
- `tests/factories.py` — Importable data factory functions (9 factories)
- 8 test modules covering all new v2.0.0 modules

### Test Modules

| Module | Tests | Scope |
|--------|------:|-------|
| `test_models.py` | 19 | Classification maps, enums, `from_dict` round-trips |
| `test_statements.py` | 14 | Income statement, balance sheet, cash flow, asset P&L |
| `test_store.py` | 21 | Transaction/asset/refinery CRUD, filters, persistence |
| `test_planning.py` | 11 | Break-even, activity ROI, what-if scenarios |
| `test_assets.py` | 13 | Register, sell, update, list, fleet summary |
| `test_refinery.py` | 15 | Log, complete, collect, list, pipeline summary |
| `test_hud.py` | 21 | Tab resolution, show/hide, pagination, sorting, filtering |
| `test_integration.py` | 6 | Asset lifecycle, mining pipeline, balance sheet completeness |

### Key Design Decision
Factory functions live in `factories.py`, not `conftest.py`. Pytest auto-loads
conftest as a plugin — it cannot be imported as a regular module (`from conftest
import ...` fails with `ModuleNotFoundError`). Separating factories makes them
importable by any test file.

### Bugs Found During Testing
- HUD `sort_by()` defaults to descending for new columns — tests initially
  assumed ascending-first
- Break-even ROI formula: `net_profit / purchase_price * 100` — with zero cost
  transactions, net profit equals total revenue (not revenue minus purchase price)

---

## 2026-03-02 — v2.0.0: Three-Statement Restructure

Major restructure from flat income/expense model to corporate three-statement
accounting adapted for Star Citizen. 53 tools across 15 files, ~9,700 LOC.

### Architecture Changes
- **Classification system**: `StatementClass` enum (REVENUE, COGS, OPEX, CAPEX) maps
  every transaction category to its financial statement line at query time. Zero migration.
- **Activity mapping**: `Activity` enum maps categories to gameplay loops (trading, mining,
  bounty hunting, missions, salvage, hauling, general) for per-activity margin analysis.
- **Asset registry**: `Asset` dataclass with full lifecycle (register → active → sold/destroyed).
  `linked_asset_id` on Transaction enables per-ship P&L tracking.
- **Mining pipeline**: `RefineryJob` dataclass tracks ore → refinery → refined materials → sale.

### New Files (4)
- `statements.py` — Pure computation engine: `generate_income_statement`, `generate_balance_sheet`,
  `generate_cash_flow`, `generate_asset_pnl`. Takes data in, returns dicts out. No side effects.
- `assets.py` — AssetManager: register, sell, list, fleet summary. Creates CAPEX transactions.
- `refinery.py` — RefineryManager: log, complete, collect jobs. Pipeline margin analysis by ore type.
- `planning.py` — PlanningEngine: break-even, activity ROI comparison, what-if scenarios
  (upgrade payback, ship purchase projection, trade profit calculation).

### Modified Files (4)
- `models.py` — Added enums, classification maps, 3 new categories, Asset/RefineryJob dataclasses,
  `linked_asset_id` and `activity` fields on Transaction.
- `store.py` — Added asset/refinery CRUD, `linked_asset_id` filter on `query_transactions`.
- `hud_dashboard.py` — Complete rewrite: 5 separate panels → single spreadsheet with 7 tabs
  (ledger, hangar, operations, flow, portfolio, opportunities, fleet), voice-commanded pagination,
  sorting, filtering, period selection.
- `main.py` — Removed 6 superseded tools, added 16 new tools. Updated prepare/unload/get_prompt.
  Added complexity tier gating (casual/engaged/industrial).

### Tools Delta
- **Removed (6):** get_financial_summary, get_expense_breakdown, get_revenue_breakdown,
  show_budget, show_accounting_info, hide_financial_hud
- **Added (16):** get_income_statement, get_balance_sheet, get_cash_flow, register_asset,
  sell_asset, list_fleet, get_fleet_summary, log_refinery_job, complete_refinery_job,
  get_mining_summary, show_spreadsheet, spreadsheet_navigate, hide_spreadsheet,
  get_break_even, get_activity_roi, what_if
- **Modified (1):** record_transaction (added linked_asset_id, auto-populates activity)
- **Total:** 43 → 53

### Complexity Tiers
- **Casual:** Basic income/expenses, ledger + operations tabs only
- **Engaged:** + Fleet management, positions, planning, 6 HUD tabs
- **Industrial:** Full feature set including mining pipeline, what-if, all 7 tabs

### Backwards Compatibility
- All new Transaction fields default to `None` via `from_dict.setdefault()`
- New JSON storage files (assets, refinery) created on first use
- Existing JSONL transaction data loads without modification
- Old `generate_pnl` still used by session tools (kept in reports.py)

---

## 2026-03-02 — Bug Fix: UEX Commodity Status API

**Issue:** `refresh_market_data` tool crashed with `'str' object has no attribute 'get'`
in `market_data.py:refresh_statuses()`.

**Root Cause:** The UEX `/commodities_status` endpoint returns
`{"data": {"buy": [...], "sell": [...]}}` — a dict with two nested lists — not a flat
list of dicts like the other endpoints. The code iterated over the dict directly, getting
string keys `"buy"` and `"sell"` instead of status records.

**Fix:** Flatten the nested `buy`/`sell` structure into a list of dicts with an `is_buy`
flag before inserting into SQLite. Added `isinstance(raw, dict)` check with fallback for
flat-list format.

---

## 2026-03-01/02 — Modular Restructure (Phases 1-3)

Expanded from 20 tools to 43 tools across 7 business domains.

### Phase 1: Futures + Positions + HUD Dashboard
- `futures.py` — FuturesManager: auto-generates trade opportunities from UEX market data,
  expires stale opportunities (>15% margin change), auto-fulfills on matching trades
- `positions.py` — PositionManager: auto-opens positions on commodity purchases,
  auto-closes on sales using FIFO algorithm with partial split support, updates
  unrealized P&L from market prices
- `hud_dashboard.py` — AccountantHud: in-game HUD overlay panels (balance, portfolio,
  opportunities, budget, recent transactions) via HudHttpClient
- `reports.py` — Added portfolio and opportunity report generators
- 10 new tools (3 futures + 4 positions + 3 HUD)

### Phase 2: Credits + Hauling
- `credits.py` — CreditManager: receivables/payables with payment tracking, auto
  status transitions (outstanding → partial → settled), write-offs
- `hauling.py` — HaulManager: cargo transport logging with cost/revenue tracking,
  route profitability analysis
- 9 new tools (5 credits + 4 hauling)

### Phase 3: Inventory + Production (Stubs)
- `inventory.py` — InventoryManager: manual warehouse tracking with upsert by
  item+location. Stub until CIG ships inventory rework.
- `production.py` — ProductionManager: input→output conversion logging with
  value-added analysis. Stub for future expansion.
- 4 new tools (2 inventory + 2 production)

---

## 2026-03-01 — Market Data Integration

- Built `market_data.py` — self-contained UEX API client with SQLite cache
- 5 table schema: commodity, terminal, commodity_price, commodity_route, commodity_status
- Cache tiers: 14d static data, 24h prices/routes
- Per-commodity targeted refresh on trade events
- Filters out-of-stock / full-inventory terminals from trade results
- 3 new tools (get_best_trades, get_commodity_prices, refresh_market_data)

---

## 2026-03-01 — Initial Build (Core Accounting)

- Created skill from scratch at `skills/sc_accountant/`
- `models.py` — Transaction, TradeOrder, Budget, TradingSession, AccountBalance
  dataclasses with 22 transaction category constants
- `store.py` — JSONL append-only for transactions, JSON read-modify-write for
  mutable entities
- `guid_resolver.py` — Commodity GUID-to-name mapping with persistent cache
- `reports.py` — P&L, expense/revenue breakdown, budget-vs-actual generators
- Auto-sync from SC_LogReader's game log ledger on configurable timer
- 20 tools covering core accounting, trade orders, sessions, budgets

### Architecture Decisions
- Flat file structure matching existing SC skills (not hierarchical)
- `@tool` decorator only scans `dir(self)` on Skill class — tools MUST be methods
  on SC_Accountant, delegating to module managers via thin wrappers
- JSONL for immutable transactions (append-only, no corruption risk)
- JSON read-modify-write for everything else (simple, readable)
- Uses `sys.path.insert` + `noqa: E402` for local imports (matching SC_Navigator)
