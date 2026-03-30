# DEVLOG — sc_mining_assistant

## 2026-03-13 — Session 1: Scaffold + In-Memory Capture + Keybind Design

**Developer:** Mallachi

### Context
Regolith.Rocks shutting down June 1, 2026. SC 4.7 mining overhaul resets all data.
Building full Regolith replacement as WingmanAI skill with community scan pipeline.

### Decisions Made
- r_displayinfo **mandatory** for all scans — provides auto game version, server ID, server timestamp
- BYOK model for Claude API (scan OCR) — no central cost
- SQLite local DB only for Phase 1; MCP community sync deferred to Phase 2
- Append-only records, version-tagged, JSON `extra` column for extensibility
- OpenCV CPU pipeline (no VRAM impact on SC)
- EasyOCR CPU for text extraction
- Full-image panel search (no fixed region — HUD shifts with head tracking)
- **mss used for in-memory screen capture** — no disk write required, no dependency on SC screenshot system
  - sha256 hash computed from raw BGRA bytes before any processing
  - `save_debug_screenshots` config flag for QA/template calibration when needed
  - Kills the SC screenshot bug as a blocker entirely
- **Keybind toggle mode chosen** over single-shot keybind
  - Scanning every 10 seconds makes repeated voice commands impractical
  - `F9` (configurable) starts auto-scan loop at configurable interval
  - `F9` again stops the loop
  - Last voice-set location stored in skill state and reused by keybind scans
  - keyboard.add_hotkey() available via bundled `keyboard/keyboard/` library in WingmanAI
  - asyncio bridge required: callback runs in keyboard hook thread → asyncio.run_coroutine_threadsafe()

### Files Created / Modified
- `preparations.md` — full planning archive (updated with keybind design)
- `DEVLOG.md` — this file
- `__init__.py` — module exports
- `default_config.yaml` (v0.2.0) — added monitor_index, save_debug_screenshots
- `database.py` — SQLite schema + CRUD layer
- `scanner.py` (v0.2.0) — mss in-memory capture; process_capture() replaces process_screenshot()
- `ocr.py` — EasyOCR extraction + structured parser
- `main.py` (v0.2.0) — uses capture_screen() + process_capture(); no file path handling
- `clean.py` — standard cleanup utility

### Pending Implementation
- `main.py` v0.3.0: keybind toggle mode
  - register hotkey in validate() or on_skill_ready()
  - _scan_loop_running flag + asyncio task
  - scan_interval (seconds) from config
  - scan_keybind (key combo) from config
  - last_location stored from voice tool calls, reused by loop
- `default_config.yaml` v0.3.0: scan_keybind, scan_interval fields

### Other Open Items
- Reference screenshots still needed at 1080p, 1440p, 5120×1440 for template generation
  - Use `save_debug_screenshots: true` to capture from live game
- Build templates/ dir and generate scan_results_<width>.png template images
- Implement detect_panel() full template match + deskew logic in scanner.py
- Seed refinery data (static JSON for 4.7 post-launch)
- Phase 2: MCP server integration

## 2026-03-13 — Session 2: Import Fix + DevKit Database Browser

**Developer:** Mallachi

### Changes

**Import fix (runtime safety):**
- Converted relative imports (`from .database`, `from .scanner`, `from .ocr`) to
  `sys.path.insert` + bare imports pattern — matches SC_Accountant/SC_Navigator
- Prevents `ModuleNotFoundError` on live Wingman AI release (skill loader doesn't
  guarantee package-style relative imports work at runtime)
- Database path now defaults to skill directory (`current_dir / sc_mining_assistant.db`)
  instead of relative to CWD

**DevKit database browser:**
- `devkit/devkit.py` — standalone entry point (port 7868, auto-opens browser)
- `devkit/server.py` — FastAPI REST API with 8 endpoints:
  - `/api/stats` — summary counts
  - `/api/scans` — paginated scan list with filters (location, version)
  - `/api/scans/{id}` — scan detail with minerals
  - `/api/locations` — all locations with scan counts
  - `/api/locations/{id}/composition` — mineral breakdown with bar chart
  - `/api/minerals` — aggregate mineral stats
  - `/api/versions` — game version registry
- `devkit/static/` — dark-theme SPA (gold/amber accent, matching SC UI aesthetic)
  - 4 tabs: Dashboard, Scans, Locations, Minerals
  - Composition bar chart with min/max range overlay on location click
  - Mineral badges color-coded by category (raw/refined/inert)
  - Location/version filter dropdowns on Scans tab
  - Pagination, auto-refresh toggle (15s)
- Reads SQLite database directly — no dependency on skill runtime

### File Structure After
```
sc_mining_assistant/
├── main.py
├── scanner.py
├── ocr.py
├── database.py
├── default_config.yaml
├── __init__.py
├── clean.py
├── DEVLOG.md
├── preparations.md
└── devkit/
    ├── devkit.py
    ├── server.py
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

### Version
`0.2.1` — import fix + devkit database browser
`0.2.0` — in-memory screen capture via mss

## 2026-03-13 — Session 3: Keybind Toggle Scan Loop + Joystick Support

**Developer:** Mallachi

### Changes

**Keybind toggle scan loop (v0.3.0):**
- `input_handler.py` — standalone input polling module
  - Keyboard: uses bundled `keyboard.keyboard` library (`add_hotkey()`)
  - Joystick: uses Windows Multimedia API (`winmm.joyGetPosEx`) via ctypes
  - No pygame dependency — no conflict with WingmanCore's joystick system
  - Rising-edge detection on joystick (fires on press, not hold)
  - 50ms poll interval for joystick, keyboard uses native hook
- `main.py` v0.3.0:
  - `prepare()` registers keyboard hotkey + starts joystick polling thread
  - `unload()` stops scan loop + unregisters inputs
  - `_on_toggle_sync()` bridges sync callback → async via `asyncio.run_coroutine_threadsafe()`
  - `_scan_loop()` captures at configurable interval, logs results to Wingman UI
  - Both voice-triggered and keybind-triggered scans use same `_execute_capture_scan()` path

**Config additions:**
- `scan_keybind` (string, default "f9") — keyboard key to toggle auto-scan loop
- `scan_interval` (number, default 10) — seconds between auto-scans
- `joystick_device_id` (number, default -1) — Windows joystick index (0-15), -1 = disabled
- `joystick_button` (number, default -1) — joystick button number (0-based), -1 = disabled
- r_displayinfo activation instructions added to monitor_index hint and skill description

### Design decisions
- **winmm over pygame**: Skills must be standalone — can't share pygame instance with WingmanCore's joystick thread
- **Rising-edge detection**: Prevents repeated toggles from held buttons
- **Daemon thread**: Joystick polling thread auto-dies with process — no leak risk
- **No location from voice**: Location comes exclusively from r_displayinfo OCR (mining happens away from designated locations)

### File Structure After
```
sc_mining_assistant/
├── main.py              (v0.3.0)
├── input_handler.py     (v0.3.0) — NEW
├── scanner.py
├── ocr.py
├── database.py
├── default_config.yaml
├── __init__.py
├── clean.py
├── DEVLOG.md
├── preparations.md
└── devkit/
    ├── devkit.py
    ├── server.py
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

### Version
`0.3.0` — keybind toggle scan loop + joystick support via winmm (superseded by 0.4.0)

## 2026-03-13 — Session 4: Screenshot Folder Watcher (replaces keybind approach)

**Developer:** Mallachi

### Context
SC screenshots now working — player uses in-game keybind (PrintScreen) to take screenshots.
Keybind/joystick approach replaced with folder watcher. Simpler, no input conflicts, no mss dependency.

### Changes

**Screenshot folder watcher (v0.4.0):**
- `folder_watcher.py` — NEW: polls SC screenshot folders for new images
  - Monitors LIVE, PTU, and HOTFIX channels simultaneously
  - Seeds existing files on start (only new screenshots trigger processing)
  - 0.5s settle delay after detecting new file (let SC finish writing)
  - Configurable poll interval (default 2s)
  - `get_latest_file()` for manual voice-triggered processing
- `scanner.py` v0.4.0:
  - Removed `capture_screen()` (mss dependency eliminated)
  - Added `load_screenshot(file_path)` — loads image via OpenCV, hashes file bytes
  - `CaptureResult` simplified: removed `raw_bytes`, added `source_path`
- `main.py` v0.4.0:
  - `prepare()` builds folder list from SC install path, starts watcher
  - `_on_new_screenshot()` callback processes each new file automatically
  - `_process_screenshot()` core pipeline shared by watcher and voice tool
  - `_execute_capture_scan()` now processes latest file from watcher (voice fallback)
  - Scan `extra` field includes `screenshot_filename` for traceability
- `default_config.yaml` v0.4.0:
  - Added `sc_install_path` (default `C:\Roberts Space Industries\StarCitizen`)
  - Added `poll_interval` (default 2s)
  - Removed: `monitor_index`, `scan_keybind`, `scan_interval`, `joystick_device_id`, `joystick_button`, `save_debug_screenshots`
  - Hint on `sc_install_path` explains: create Screenshots folder manually if it doesn't exist

**Deleted files:**
- `input_handler.py` — dead code (keybind/joystick approach replaced)

### Design decisions
- **Folder watcher over keybind**: SC screenshots work reliably, player already has muscle memory for the keybind. No need for custom input handling.
- **No mss dependency**: Screenshot files are already on disk — no reason to grab the screen again
- **Multi-channel monitoring**: LIVE/PTU/HOTFIX all watched simultaneously, auto-discovers which exist
- **Settle delay**: 0.5s after file detection prevents reading partially-written files

### File Structure After
```
sc_mining_assistant/
├── main.py              (v0.4.0)
├── folder_watcher.py    (v0.4.0) — NEW
├── scanner.py           (v0.4.0)
├── ocr.py
├── database.py
├── default_config.yaml  (v0.4.0)
├── __init__.py
├── clean.py
├── DEVLOG.md
├── preparations.md
└── devkit/
    ├── devkit.py
    ├── server.py
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

### Version
`0.4.0` — screenshot folder watcher replaces keybind/mss approach

## 2026-03-13 — Session 5: Mining Interface (DevKit → Skill-Integrated UI)

**Developer:** Mallachi

### Context
Repurpose the standalone devkit database browser into a skill-integrated "Mining Interface"
that activates automatically with the skill, following the SC_Accountant UI pattern.

### Changes

**Restructured `devkit/` → `ui/` (skill-integrated):**
- `ui/app.py` — `MiningServer` class (FastAPI + uvicorn background thread, port 7862)
  - All 8 REST endpoints preserved from devkit
  - Added `/api/version` endpoint for version-counter auto-refresh polling
  - Server receives `db_path` string, creates own sqlite3 connections per request
  - `start()`/`stop()`/`notify_refresh()` lifecycle methods (same pattern as `AccountantServer`)
- `ui/window.py` — `MiningWindow` class (browser opener, same pattern as `AccountantWindow`)
- `ui/static/` — SPA frontend with branding updated from "DevKit" to "Mining Interface"
  - Replaced manual auto-refresh checkbox with 2s version-counter polling
  - Added green status dot (pulsing) to indicate auto-refresh is active
  - 4 tabs preserved: Dashboard, Scans, Locations, Minerals
- `ui/__init__.py` — empty package marker

**Skill lifecycle integration (`main.py` v0.5.0):**
- `prepare()` starts `MiningServer` + creates `MiningWindow` (wrapped in try/except ImportError)
- `unload()` stops server + closes window
- `_on_new_screenshot()` calls `notify_refresh()` so browser auto-updates on new scans
- `execute_tool()` calls `notify_refresh()` after `capture_mining_scan` tool

**New voice tool: `show_mining_interface`**
- Opens the Mining Interface dashboard in the default browser
- Triggers: "show mining interface", "mining dashboard", "mining HUD", "mining module",
  "mining data", "mining information"
- Conditionally registered — only appears if FastAPI/uvicorn are available

**Config updated (`default_config.yaml`):**
- Added `show_mining_interface` tool to prompt with trigger phrases
- Updated skill description to mention Mining Interface

**Deleted files:**
- `devkit/devkit.py` (standalone entry point — replaced by skill-integrated activation)
- `devkit/server.py` (replaced by `ui/app.py`)
- `devkit/static/` (moved to `ui/static/`)

### File Structure After
```
sc_mining_assistant/
├── main.py              (v0.5.0)
├── folder_watcher.py
├── scanner.py
├── ocr.py
├── database.py
├── default_config.yaml
├── __init__.py
├── clean.py
├── DEVLOG.md
├── preparations.md
└── ui/
    ├── __init__.py
    ├── app.py           — MiningServer (FastAPI + background thread)
    ├── window.py        — MiningWindow (browser opener)
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

### Version
`0.5.0` — Mining Interface (skill-integrated UI replaces standalone devkit)

## 2026-03-13 — Session 5b: OCR Parser Update (Verified Scan Panel Format)

**Developer:** Mallachi

### Context
Reference screenshot from SC 4.7 revealed the actual scan panel format differs from
the original assumptions. Mineral lines have percent on the LEFT, name+category in the
CENTER, and quality on the RIGHT.

### Verified Format (SC 4.7, ref screenshot 2026-03-13)
```
SCAN RESULTS
LINDINIUM (ORE)                    ← rock type + category
MASS:           28465              ← raw number (NOT SCU)
RESISTANCE:     65%                ← green = module-modified
INSTABILITY:    195.48             ← green = module-modified
[bar] IMPOSSIBLE                   ← difficulty level
COMPOSITION     22.73 SCU
47.42%  LINDINIUM (ORE)    367     ← percent | name (category) | quality
17.28%  TUNGSTEN (ORE)     352
35.28%  INERT MATERIALS      0     ← no category tag, quality = 0
```

### Changes

**`ocr.py` v0.2.0:**
- `MineralEntry`: added `quality: int | None` field
- `ScanPanelData`: added `rock_category`, `difficulty` fields
- `_parse_name_with_category()`: extracts "LINDINIUM (ORE)" → ("Lindinium", "ORE")
- `DIFFICULTY_LEVELS` frozenset for detecting difficulty bar text
- New mineral regex `_RE_MINERAL_LINE`: matches `47.42% LINDINIUM (ORE) 367`
  - Handles multi-word names (INERT MATERIALS)
  - Optional parenthesized category
  - Quality as trailing integer (any digits, not just 3)
- Fallback regex `_RE_MINERAL_FALLBACK`: percent-left, no quality
- Legacy regex `_RE_MINERAL_LEGACY`: name-left percent-right (backwards compat)
- Rock type parsing now extracts category from parenthesized suffix

**`database.py` v0.2.0:**
- Schema v1 → v2 migration: adds `quality` to `scan_minerals`, `rock_category` + `difficulty` to `rock_scans`
- `insert_scan()`: includes `rock_category`, `difficulty`, mineral `quality`
- `get_recent_scans()`: mineral query includes `sm.quality`
- `get_location_composition()`: includes quality aggregates (avg/min/max)

**`main.py`:**
- Passes `rock_category`, `difficulty`, mineral `quality` to `insert_scan()`
- Voice output includes quality (Q367) and difficulty in result message
- Mass displayed as formatted integer (28,465) not decimal

**`ui/app.py`:**
- Scan list query includes `rock_category`, `difficulty`
- All mineral queries include `sm.quality`
- Composition and minerals aggregate queries include quality stats

**`ui/static/app.js`:**
- `mineralBadge()` shows quality as `[367]` suffix
- Scans table: added Difficulty column, rock type shows category, mass as integer
- Composition bars: show avg quality (Q: 367)
- Minerals tab: added Avg Quality column
- Removed Submitted By column from scans table (less useful, saves space)

### Version
`0.5.0` — includes OCR parser update for verified SC 4.7 scan panel format

## 2026-03-14 — Session 6: Live Testing Fixes + Debug Infrastructure

**Developer:** Mallachi

### Context
First live testing session. Multiple issues discovered and fixed during iterative testing.

### Fixes

**Tool registration timing (critical):**
- `show_mining_interface` was invisible to the LLM — never called despite prompt instructions
- Root cause: `get_tools()` conditionally registered the tool with `if self._ui_window`,
  but `get_tools()` is called at registration time BEFORE `prepare()` runs, so `_ui_window`
  was always None
- Fix: always register all tools unconditionally; handle "not ready" in execution method
- Saved as critical memory rule for all Wingman AI skills

**UI package namespace collision:**
- Both `sc_accountant/ui/` and `sc_mining_assistant/ui/` had bare `ui` package names
- When both skills' dirs were on `sys.path`, `from ui.app import AccountantServer`
  resolved to the mining assistant's `ui.app` instead
- Fix: renamed to `accountant_ui/` and `mining_ui/` respectively
- Updated imports in both skills' main.py, release_version, and update_release.py

**Folder watcher rewrite (watchdog):**
- Original asyncio polling loop never detected new screenshots
- Rewrote `folder_watcher.py` using watchdog (OS-native filesystem events)
- Initial async bridge via `asyncio.run_coroutine_threadsafe()` failed — event loop
  goes stale when Wingman framework reinitializes wingmen
- Final approach: fully synchronous callback on watchdog thread, no asyncio bridge needed
- Added `_process_screenshot_sync()` and `_do_process_screenshot()` shared pipeline

**Dependency fixes:**
- `opencv-python` not installed → added to requirements.txt
- `easyocr 1.7.0` incompatible with `Pillow 12` (removed `ANTIALIAS`) → upgraded to 1.7.2
- `torchvision 0.25.0` incompatible with `torch 2.8.0` → pinned to 0.23.0
- Added all mining skill deps to requirements.txt: `watchdog>=3.0.0`, `opencv-python>=4.8.0`, `easyocr>=1.7.2`

**Skill auto-activation:**
- Added `auto_activate: true` to config — skill now starts folder watcher + UI server
  immediately on wingman boot, not only after voice interaction

**r_displayinfo crop region:**
- Was `(0.0, 0.0, 1.0, 0.85)` — full width, 85% height — captured entire game HUD
- Changed to `(0.67, 0.0, 1.0, 0.33)` — top-right third (3x3 grid) — isolates r_displayinfo

**OCR line reconstruction:**
- EasyOCR shatters r_displayinfo lines into random fragments (e.g., "Server" + "ptu-uselb" +
  "5C-alpha" + "470-11450623" as 4 separate results)
- Added `extract_text_lines()` — groups OCR fragments by Y-coordinate proximity, joins
  left-to-right within each line, reconstructs coherent text lines
- Info crop now uses `extract_text_lines()`, panel crop still uses `extract_text()`

**Version parser robustness:**
- Added standalone `470-NNNNN` pattern matching (OCR may split "alpha" and "470")
- Regex: `\b(\d)(\d)(\d)-\d{5,}` → e.g., `470-11450623` → `4.7.0`
- Also loosened alpha prefix match to `alpha[_\s-]+` (handles OCR space/dash variation)

**Debug scan logging:**
- New `debug_scan_logging` boolean config property (default false)
- When enabled, saves per-scan debug folder to `debug_scans/`:
  - `original.jpg` — copy of source screenshot
  - `crop_panel.png` — preprocessed scan panel crop
  - `crop_info.png` — preprocessed r_displayinfo crop
  - `scan_log.txt` — raw OCR output with confidence scores + all parsed fields

**Pipeline logging:**
- Added INFO-level logging at every pipeline stage: load, crop, raw OCR lines, parsed
  panel data, each mineral, parsed info data

**Removed stale config:**
- Removed `poll_interval` custom property (no longer used after watchdog rewrite)

### File Structure After
```
sc_mining_assistant/
├── main.py              (v0.5.0)
├── folder_watcher.py    (v0.5.1 — watchdog, sync callback)
├── scanner.py           (v0.4.1 — updated info crop region)
├── ocr.py               (v0.2.0 — extract_text_lines, version parser)
├── database.py          (v0.2.0)
├── default_config.yaml  (auto_activate, debug_scan_logging)
├── __init__.py
├── clean.py
├── DEVLOG.md
├── preparations.md
├── debug_scans/         (generated when debug logging enabled)
└── mining_ui/
    ├── __init__.py
    ├── app.py           — MiningServer
    ├── window.py        — MiningWindow
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

### Open Items (resolved in Session 7)
- OCR line reconstruction needs live validation → resolved, replaced with Windows OCR
- Panel crop location looks good but no scan results panel tested → validated with live scan
- `line_threshold` parameter → no longer needed (Windows OCR handles line separation natively)
- Mineral regex untested → validated, works with HUD prefix stripping

## 2026-03-14 — Session 7: Live Testing, OCR Engine Swap, Parser Hardening

**Developer:** Mallachi

### Context
First live testing session with real scan data from SC 4.7 PTU. Multiple iterations
of OCR improvements, culminating in replacing EasyOCR with Windows OCR entirely.

### Changes

**Manual scan upload (Mining Interface):**
- `POST /api/scan` endpoint on `MiningServer` — accepts file upload, runs through
  existing `_do_process_screenshot()` pipeline via callback
- `scan_callback` parameter on `MiningServer.__init__()` — receives skill's pipeline
- Frontend "Upload Scan" button in header — file picker, POSTs to endpoint, shows
  result as toast notification
- Invaluable for testing without needing the folder watcher

**Scan deletion (Mining Interface):**
- `DELETE /api/scans/{scan_id}` endpoint — deletes scan + associated minerals
- "x" button on each scan row in the table
- `Database.delete_scan()` method with proper cascade (minerals first, then scan)

**Bloom subtraction (scanner.py):**
- Added heavy Gaussian blur subtraction (sigma=50) before CLAHE in `_preprocess_crop()`
- Removes low-frequency glow from star lighting while preserving text edges
- Dramatically improved OCR accuracy — difficulty went from "JMPOSSIOLE" to "IMPOSSIBLE",
  resistance from "096" to "09", overall confidence from 0.3-0.6 to 0.8-1.0

**HUD prefix stripping (ocr.py):**
- `_strip_hud_prefix()` — iteratively removes known HUD noise from merged lines:
  OVERCHARGE, OPTIMAL, SCAN, LASER IN, MINING MODULES, FRACTURE MODE, HEAD, 100%
- Applied to every line after SCAN RESULTS header before parsing
- `_HUD_STOP_WORDS` frozenset — terminates parsing at LASER RANGE, CARGO, GEAR, etc.
- Fixed rock_type: "OVERCHARGE IRON (ORE)" → "IRON (ORE)" → Iron
- Fixed minerals: "100% 69.629 IRON (OrE) 440" → "69.629 IRON (OrE) 440"
- Fixed minerals: "LASER IN 30.37% INERT MATERIALS" → "30.37% INERT MATERIALS"

**Info parser improvements (ocr.py):**
- Version detection reordered: `alpha` encoded checked first, dotted version restricted
  to single-digit segments to avoid FPS false positives (was matching "99.8199.5")
- Location: searches for `\w+System` pattern, handles merged "Current Planet" text
- Ship name: manufacturer prefix matching (MISC, AEGS, etc.) instead of generic Zone capture
- ShardId: captures multi-token IDs, normalizes spaces to underscores
- Fuzzy difficulty matching via character overlap ratio (60% threshold)

**Windows OCR replaces EasyOCR (ocr.py v0.4.0):**
- Replaced `get_reader()`, `extract_text()`, `extract_text_lines()` with `extract_text_win()`
- Uses Windows.Media.Ocr via `winocr` package + `nest_asyncio` for event loop compat
- **43x faster**: 0.23s total vs ~10s with EasyOCR
- **Accurate % signs**: reads "69.62%" correctly (EasyOCR misread as "69.629")
- **Clean line separation**: no fragment merging or line reconstruction needed
- **No GPU required**: native Windows API, zero VRAM usage
- Removed: `ocr_use_gpu` config property, `_ocr_reader` field, EasyOCR lazy loader

**Submitted by = account name:**
- Changed from `submitted_by` custom property to `self.settings.user_name`
- Automatically uses the logged-in Wingman account name
- Removed `submitted_by` from `default_config.yaml`

**Database lock fix (database.py):**
- `get_or_create_mineral()` accepts optional `conn` parameter
- `insert_scan()` passes its connection to avoid nested connection deadlock
- Added `timeout=10` to both Database and MiningServer connections

**clean.py updated:**
- `--data` flag: removes `sc_mining_assistant.db` + `debug_scans/`
- `--all` flag: removes build artifacts + data
- Default: build artifacts only (same as before)

**Qwen2-VL experiment (abandoned):**
- Cloned skill as `sc_qwen_scan` with Qwen2-VL-2B-Instruct for VLM-based OCR
- Blocked: SC uses 10-11GB of 12GB VRAM, no room for 2B model on GPU
- CPU too slow (~30-60s per crop)
- Skill and dependencies removed entirely

### Live test results (Windows OCR, same screenshot)

```
rock_type:        Iron (ORE)           ✓
mass:             36674                ✓
resistance:       0%                   (needs verification)
instability:      27.99                ✓
difficulty:       Impossible           ✓
composition_scu:  44.37                ✓
minerals:         69.62% Iron (ORE) Q440    ✓ (exact match)
                  30.37% Inert Materials    ✓ (quality TBD)
game_version:     4.7.0                ✓
server_id:        ptu-uselb-alpha      ✓
player_location:  NyxSolarSystem       ✓
ship_name:        MISC Prospector      ✓ (Windows OCR reads it correctly)
```

### File Structure After
```
sc_mining_assistant/
├── main.py              (v0.6.0)
├── folder_watcher.py
├── scanner.py           (v0.5.0 — bloom subtraction)
├── ocr.py               (v0.4.0 — Windows OCR + HUD stripping)
├── database.py          (v0.3.0 — connection reuse fix)
├── default_config.yaml  (removed ocr_use_gpu, submitted_by)
├── __init__.py
├── clean.py             (--data, --all flags)
├── DEVLOG.md
├── TODO.md
├── preparations.md
├── debug_scans/
└── mining_ui/
    ├── __init__.py
    ├── app.py           — MiningServer (+ upload, delete endpoints)
    ├── window.py        — MiningWindow
    └── static/
        ├── index.html   (+ upload button)
        ├── style.css    (+ upload/delete styles)
        └── app.js       (+ upload/delete logic)
```

### Version
`0.6.0` — Windows OCR, bloom subtraction, HUD prefix stripping, upload/delete UI

## 2026-03-14 — Session 8: OCR Pipeline Hardening (5120x1440 Ultrawide)

**Developer:** Mallachi

### Context
Iterative OCR accuracy improvements tested against a 5120x1440 superwide screenshot
(MISC Prospector, Iron ore, Nyx system, PTU 4.7.0). All previous parsing was untested
at ultrawide resolution — every field returned None or wrong values.

### Changes

**Info crop 2x upscale (scanner.py v0.5.0):**
- `crop_displayinfo()` now upscales 2x after preprocessing (default parameter)
- Fixes Windows OCR fragmentation on tiny r_displayinfo text at ultrawide resolution
- 475x1690 → 950x3380 — still fast, massive accuracy improvement

**Line reconstruction (ocr.py v0.5.0):**
- `_reconstruct_lines()` groups OCR fragments by Y-coordinate proximity (20px threshold)
- Replaces the sequential pre-merge approach — naturally merges label+value pairs
- Handles: "MASS:" + "36674" → "MASS: 36674", "COMPOSITION" + "44.37 SCU", etc.
- Non-printable/zero-width character stripping on all OCR text

**HUD prefix stripping fix (ocr.py):**
- Changed `_HUD_PREFIXES` regex from `\s+` to `(?:\s+|$)` at end of pattern
- Standalone HUD words ("OVERCHARGE", "OPTIMAL", "100%") now stripped correctly
- Previously required trailing whitespace — standalone lines were missed

**Composition matching broadened (ocr.py):**
- Changed from requiring "composition" label to matching any `(\d+\.?\d*)\s*scu` in line
- Handles OCR typos like "COHPOSITION" and reversed label/value order
- Standalone "COMPOSITION" label handled by `co\w*position` fallback regex

**ShardId regex fix (ocr.py):**
- Changed `shard\s*id` to `shard\s*[il1]d` — handles OCR I/l/1 confusion
- Simplified capture: `(.+)` after "ShardId:" instead of complex pattern

**Ship manufacturer tolerance (ocr.py):**
- Changed from exact manufacturer match to `({mfr_pattern})\w{0,2}` — allows up to 2
  extra OCR noise characters (e.g. "MISCU" → matches "MISC")

**Location normalization (ocr.py):**
- `_normalize_location()` — fuzzy matches OCR-garbled location against known SC systems
- Uses character frequency overlap (≥75% threshold), same approach as difficulty matcher
- `_KNOWN_SYSTEMS` tuple: StantonSolarSystem, NyxSolarSystem, PyroSolarSystem
- Fixes "NyxSotarSy,5tem" → "NyxSolarSystem"

**Orphaned number tracking (ocr.py):**
- Standalone numbers between mass and composition collected as orphans
- Post-loop assignment: fills missing instability/resistance from orphans
- Handles OCR placing values before their labels (common at 1x)

### Test Results (5120x1440, single screenshot)

```
game_version:     4.7.0               ✓ (was None)
server_id:        ptu_uselb_11445650  ✓ (was None)
server_timestamp: Fri Mar 13 2026     ✓ (was None, time portion dropped by OCR)
player_location:  NyxSolarSystem      ✓ (was None, fuzzy-matched from garbled OCR)
ship_name:        MISC Prospector     ✓ (was None)
rock_type:        Iron (ORE)          ✓ (was "Optimal")
mass:             36674               ✓ (was None)
instability:      27.99               ✓ (was None)
difficulty:       Impossible          ✓ (was "Very Hard")
composition_scu:  44.37               ✓ (was None)
minerals:         Iron 69.62% ORE     ✓ (was empty)
                  Inert Materials 30.37%  ✓
```

### Known OCR Limitations (not fixable by parser)
- **Resistance 0%**: green text (module-modified) invisible after grayscale preprocessing
- **Quality numbers (440, 0)**: text too small/far-right for OCR at broad crop scale
- **Timestamp time**: "21:01:08" dropped by OCR (only date captured)
- These are Phase 2 candidates (template matching for precise crops)

### Version
`0.7.0` — OCR pipeline hardening: 2x info upscale, line reconstruction, location
normalization, HUD stripping fix, broadened composition/manufacturer/ShardId matching

## 2026-03-15 — Session 9: Vision AI Pivot (Local OCR → LLM Vision)

**Developer:** Mallachi

### Context
Local OCR pipeline (EasyOCR → Windows OCR) was functional but fragile. Every resolution,
lighting condition, and HUD overlap required new workarounds (bloom subtraction, HUD prefix
stripping, line reconstruction, fuzzy matching, manufacturer tolerance, location normalization).
The wingman's configured LLM provider supports vision/image input — send the full screenshot
and let the model extract structured data directly.

### Changes

**Architecture pivot — Vision AI replaces local OCR:**
- `scanner.py` v1.0.0 — complete rewrite:
  - Removed: OpenCV, bloom subtraction, CLAHE, cropping, preprocessing
  - Now: load screenshot via PIL, compute sha256 hash, resize to max 2000px width,
    encode as base64 PNG for Vision AI
  - Single function `load_screenshot()` → `CaptureResult` with `base64_png` field
- `main.py` v1.0.0 — complete rewrite:
  - Removed: all OCR imports, `_do_process_screenshot()` OCR pipeline, debug scan logging
  - Added: `EXTRACTION_PROMPT` — structured prompt sent with screenshot image to Vision AI
  - Uses `self.llm_call(messages)` with image content (same pattern as `vision_ai` skill)
  - `_parse_vision_response()` handles markdown-wrapped and raw JSON responses
  - Queue-based processing: folder watcher queues screenshots, drained on next tool call
  - All 4 tools preserved: capture_mining_scan, get_recent_scans, get_location_composition,
    show_mining_interface

**Deleted files:**
- `ocr.py` — 28KB of Windows OCR / EasyOCR / line reconstruction / HUD stripping / fuzzy
  matching. Entire local OCR stack replaced by Vision AI prompt.

**Dependencies removed:**
- `opencv-python`, `easyocr`, `winocr`, `nest_asyncio` — no longer needed
- Only image dep is `Pillow` (already in requirements for vision_ai skill)

**Config cleanup:**
- Removed `debug_scan_logging` property (no crops/OCR logs to save with Vision AI)

### Design decisions
- **Vision AI over local OCR**: The wingman's LLM handles all resolutions, lighting
  conditions, and HUD overlap natively. No preprocessing, no fragile regex parsing,
  no per-resolution calibration. Trade-off is API token cost per scan, but the
  accuracy and robustness gain is massive.
- **Queue-based processing**: Folder watcher runs on watchdog thread, can't call
  async `llm_call()` directly. Screenshots are queued and processed on the next
  voice tool call or when `capture_mining_scan` is invoked.
- **`resistance_modified` / `instability_modified` flags**: Vision AI can detect
  green/red text color in the screenshot — something local OCR could never do
  (grayscale preprocessing destroyed color information).

### File Structure After
```
sc_mining_assistant/
├── main.py              (v1.0.0 — Vision AI)
├── scanner.py           (v1.0.0 — load + hash + base64)
├── folder_watcher.py    (unchanged)
├── database.py          (v0.2.0 — unchanged, schema already has all fields)
├── default_config.yaml  (removed debug_scan_logging)
├── __init__.py
├── clean.py
├── DEVLOG.md
├── TODO.md
├── preparations.md
└── mining_ui/
    ├── __init__.py
    ├── app.py           — MiningServer
    ├── window.py        — MiningWindow
    └── static/
        ├── index.html
        ├── style.css
        └── app.js
```

### Version
`1.0.0` — Vision AI replaces entire local OCR stack

## 2026-03-15 — Session 10: Live Testing + Pipeline Fixes

**Developer:** Mallachi

### Context
First live testing of Vision AI pipeline with real SC 4.7 PTU screenshot (5120x1440,
Iron ore, Nyx system, MISC Prospector). Iterative fix cycle across upload flow,
port collision, prompt tuning, and post-processing.

### Fixes

**Upload callback was queue-only (broken):**
- `MiningServer.scan_callback` was sync `_on_upload_screenshot` which just queued to
  `_scan_queue` — queue only drained on voice tool calls, so uploads never processed
- Fix: changed callback to async, pass `_do_process_screenshot` directly
- `upload_scan` endpoint now `await`s the callback — processes immediately via Vision AI
- Deleted dead `_on_upload_screenshot` method

**Port 7862 collision with hud_server:**
- Wingman's built-in `hud_server` occupies port 7862 — returned health check JSON
  instead of Mining Interface HTML
- Fix: moved Mining Interface to port 7868
- Port map: 7862=hud_server, 7863=SC_Accountant, 7864-7867=SC_LogReader, 7868=Mining

**Null string sanitization:**
- Vision AI returned `"null"` (string) instead of JSON `null` for unreadable fields
- `"null"` is truthy → passed all checks, saved literal string "null" as location/version
- Fix: `_sanitize_nulls()` recursively converts `"null"`, `"None"`, `"n/a"` → `None`

**Full-resolution screenshot (no downscaling):**
- `scanner.py` v1.1.0: removed `max_width` resize, sends native resolution as-is
- Sends original JPEG bytes (no PNG re-encoding) — smaller payload, no quality loss
- `get_media_type()` helper for correct MIME type in Vision AI message
- Full resolution critical for reading tiny r_displayinfo text in top-right corner

**Server string extraction:**
- Previous prompt asked model to decode version from "alpha-NNN-" — model got it wrong
  (returned "3.3.0" instead of "4.7.0", or raw "alpha-470-")
- New prompt asks for full server string: `"ptu-use1b-sc-alpha-470-11445650-11383139-game29"`
- `_parse_version_code()` extracts version in code: finds `alpha-(\d{3})` → "4.7.0"
- Full server string stored as `server_id` in DB — preserves environment, region, build info

**Prompt improvements:**
- Explicit spatial guidance: "TOP-RIGHT 1/9th of the image (top-right cell of a 3x3 grid)"
- Bloom warning: resistance is 0-100%, star glow creates artifacts, 0% with glow IS 0
- Server string: return full string unmodified, version extracted in code

**Wingman log output:**
- `_log()` helper writes to both Python logger and Wingman printr (server_only)
- All pipeline stages logged: load, send, raw response, extracted fields, save/error
- Color-coded: info=INFO, warning=WARNING, error=ERROR

### Test Results (GPT-4o-mini, 5120x1440)

After all fixes, GPT-4o-mini extracted every field correctly from the same screenshot
that GPT-4o-mini previously failed on entirely:
```
server_string:        ptu-use1b-sc-alpha-470-11445650-11383139-game29  ✓
game_version:         4.7.0                                            ✓
server_timestamp:     Fri Mar 13 21:01:08 2026                         ✓
player_location:      NyxSolarSystem                                   ✓
ship_name:            MISC Prospector                                  ✓
rock_type:            Iron (ORE)                                       ✓
mass:                 36674                                            ✓
resistance:           0, modified=false                                ✓
instability:          27.99, modified=true                             ✓ (color detection!)
difficulty:           Impossible                                       ✓
composition_scu:      44.37                                            ✓
minerals:             Iron 69.6% Q440, Inert Materials 30.4% Q0       ✓
```

### Key Insight
The `instability_modified=true` flag works — Vision AI detects green/red text color
directly from the screenshot. This was impossible with local OCR (grayscale preprocessing
destroyed color information). This alone justifies the Vision AI pivot.

### Version
`1.1.0` — live-tested pipeline: async upload, port fix, full-res, server string extraction, logging

## 2026-03-15 — Session 11: Dual-Image Extraction + Consistency Fix

**Developer:** Mallachi

### Context
GPT-4o-mini was inconsistent reading r_displayinfo from the full 5120x1440 image —
sometimes returned all fields, sometimes null for location/ship/timestamp. Resistance
values fluctuated (0, 2, 8, 28) due to star bloom artifacts. Same model, same image,
different results on every call.

### Changes

**Dual-image extraction (scanner.py v1.2.0):**
- `load_screenshot()` now returns both `base64_full` and `base64_crop`
- Crop = top-right 1/9th of image (PIL crop: x=2/3 width, y=0, to full width, 1/3 height)
- Crop saved as PNG (small region, lossless)
- Full image sent as native JPEG (no re-encoding)
- Removed `get_media_type()` standalone function — media type now on `CaptureResult`

**Prompt updated for dual-image:**
- IMAGE 1 (full screenshot) = scan panel data
- IMAGE 2 (zoomed crop) = r_displayinfo data
- Model told explicitly which image to use for which fields
- Bloom warning expanded: covers all fields across both images, not just resistance

**Database path (main.py):**
- Default DB path now uses `self.get_generated_files_dir()` → `AppData/Roaming/ShipBit/WingmanAI/generated_files/SC_MiningAssistant/`
- Matches SC_Accountant and SC_LogReader convention

**Skill naming:**
- Class renamed `SCMiningAssistant` → `SC_MiningAssistant`
- Config `name` field: `SCMiningAssistant` → `SC_MiningAssistant`
- `__init__.py` updated to match

### Test Results (GPT-4o-mini, 5120x1440)

Consistent 100% accuracy with dual-image approach — tested multiple times on same
screenshot that previously gave inconsistent results:
```
server_string:        ptu-use1b-sc-alpha-470-11445650-11383139-game29  ✓
game_version:         4.7.0                                            ✓
server_timestamp:     Fri Mar 13 21:01:08 2026                         ✓
player_location:      NyxSolarSystem                                   ✓
ship_name:            MISC Prospector                                  ✓
rock_type:            Iron (ORE)                                       ✓
mass:                 36674                                            ✓
resistance:           0, modified=false                                ✓
instability:          27.99, modified=true                             ✓
difficulty:           Impossible                                       ✓
composition_scu:      44.37                                            ✓
minerals:             Iron 69.6% Q440, Inert Materials 30.4% Q0       ✓
```

### Key Insight
The dual-image approach solved the consistency problem entirely. GPT-4o-mini could
always read the scan panel from the full image, but the tiny r_displayinfo text was
hit-or-miss. Sending a cropped zoom of just that corner gives the model a ~3x zoom —
consistent reads every time, same API call cost structure.

### Version
`1.2.0` — dual-image extraction, consistent GPT-4o-mini reads, AppData DB path, naming fix

## 2026-03-15 — Session 12: Scan Edit Modal + Screenshot Viewer

**Developer:** Mallachi

### Context
Mining Interface needed a way to verify and correct Vision AI extraction results.
User clicks a scan row → popup modal with all editable fields + link to the
original screenshot for visual verification.

### Changes

**Scan edit modal (app.js + style.css):**
- Click any scan row → opens edit modal popup
- Two-column layout: left = scan data (rock type, mass, resistance, instability,
  difficulty, composition), right = metadata (rock category, ship, location,
  server timestamp, server ID, version)
- Resistance/instability have inline "Modified" checkboxes
- Minerals section: editable name/percent/quality per row, add/remove buttons
- Inert Materials always present at bottom, read-only, quality=0, percent
  auto-calculated as 100% minus sum of other minerals (updates live on typing)
- Difficulty dropdown (Trivial/Easy/Moderate/Hard/Very Hard/Impossible)
- Version field disabled (parsed from server string, not user-editable)
- "View Screenshot" link opens original image in new tab (only shown if file exists)
- Save button shows "Saving..." state, error toasts on failure

**Backend endpoints (app.py):**
- `PUT /api/scans/{id}` — updates all scan fields, location (creates if new),
  minerals (full replace), ship name in extra JSON. Wrapped in try/except with
  error logging and proper HTTP error responses.
- `GET /api/scans/{id}/screenshot` — serves the original screenshot file via
  FileResponse, looks up path from scan's extra JSON field.

**Screenshot persistence:**
- Uploaded screenshots saved permanently to `generated_files/SC_MiningAssistant/screenshots/`
  with timestamped filenames (e.g. `upload_20260315_021500.jpg`)
- `screenshot_path` (full path) added to scan's extra JSON alongside filename
- Folder watcher screenshots persist in SC Screenshots folder (already permanent)

**Bug fix — PUT endpoint dead code:**
- Initial PUT implementation left the `with _get_conn` block as unreachable dead
  code after the try/except wrapper. Save button appeared to do nothing. Fixed by
  properly nesting the DB logic inside the try block.

### File Structure (unchanged)
```
sc_mining_assistant/
├── main.py              (v1.3.0 — screenshot_path in extra, screenshots_dir)
├── scanner.py           (v1.2.0 — unchanged)
├── folder_watcher.py    (unchanged)
├── database.py          (v0.2.0 — unchanged)
├── default_config.yaml  (unchanged)
├── __init__.py
├── clean.py
├── DEVLOG.md
├── TODO.md
├── preparations.md
└── mining_ui/
    ├── __init__.py
    ├── app.py           — MiningServer (+ PUT update, GET screenshot endpoints)
    ├── window.py        — MiningWindow
    └── static/
        ├── index.html   (unchanged)
        ├── style.css    (+ modal styles, two-column layout, inert row)
        └── app.js       (+ edit modal, screenshot link, inert auto-calc)
```

### Server-Side Vision AI Investigation
Evaluated moving Vision AI to a central server for community use (~1000 scans/day).
Cost analysis completed (see TODO.md Phase 3). Key finding: GPT-4.1-mini batch at
~$23/month for 1000 scans/day is the sweet spot, with ~$30-35/month total including
hosting. Decision: **defer to Phase 3** — requires a webdev lead for production-grade
auth, scalability, and reliability for thousands of users. Keep local for now.

### Version
`1.3.0` — scan edit modal, screenshot viewer, PUT/GET endpoints, Inert Materials auto-calc
