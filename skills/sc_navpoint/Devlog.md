# SC NavPoint — Devlog

## Status: OUTDATED — pre-SC 4.7 (2026-04-25)

This skill was built before Star Citizen patch 4.7, which delivered a major overhaul
of navigation points. The Vision AI parsing of `r_displayinfo 4` and the per-server
storage assumptions were calibrated against the pre-4.7 client, and have not been
re-validated against 4.7. Treat any waypoints, bearings, and zone/planet info this
skill produces as suspect until verified.

`auto_activate` has been turned off so the skill no longer loads by default — enable
it explicitly only when re-validating.

**To revive:** re-run end-to-end against SC 4.7, confirm Vision AI still extracts the
expected fields from `r_displayinfo 4` (overlay layout may have shifted), validate
bearing math against in-game distances, update Devlog status, and remove the
"Outdated" tag from `default_config.yaml`.

---

## v1.0.0 — 2026-03-20 — Initial release

### Overview
Mark and navigate to custom waypoints in Star Citizen using r_displayinfo 4 position data.
Vision AI extracts XYZ coordinates, zone, planet, system, and server ID from the live screen.

### Architecture

**Files:**
- `main.py` — SC_NavPoint skill class; 9 @tool methods
- `scanner.py` — mss screen capture, dual-image b64 encoding, LLM message builder, JSON parser
- `database.py` — SQLite CRUD (`navpoints` table); per-server storage
- `navigation.py` — bearing math, format_distance(), turn/elevation instruction generators
- `navpoint_ui/app.py` — FastAPI server (port 7869); REST API for waypoints + nav state
- `navpoint_ui/window.py` — stdlib webbrowser opener
- `navpoint_ui/static/` — SPA: waypoint list (left panel) + navigation compass (right panel)

**Tools (voice commands):**
| Tool | Trigger phrases |
|---|---|
| `enable_displayinfo` | "enable position overlay", "activate r_displayinfo" |
| `disable_displayinfo` | "disable position overlay", "hide debug overlay" |
| `mark_location` | "mark location", "drop waypoint", "save position" |
| `navigate_to` | "navigate to X", "guide me to X" |
| `update_position` | "update position", "refresh bearing", "how far" |
| `stop_navigation` | "stop navigation", "cancel navigation" |
| `show_navpoint_hud` | "show navigation HUD", "open waypoints" |
| `list_navpoints` | "list waypoints", "show saved locations" |
| `delete_navpoint` | "delete waypoint X" |
| `rename_navpoint` | "rename X to Y" |

### Key Technical Decisions

**Dual-image Vision AI extraction**
Send two images per LLM call: full screenshot (context, low detail) + top-right 45%×55%
crop (high detail). The crop isolates r_displayinfo without noise from the rest of the screen.
Crop is upscaled to 900px wide if smaller — improves text legibility on high-res displays.
Pattern proven in old SC_MiningAssistant (solved GPT-4o-mini inconsistency on tiny overlay text).
Learning from SC_Signature_Scanner: crop to the region of interest before OCR.

**Auto-polling loop**
`navigate_to()` calls `_start_nav_polling()` which launches an `asyncio.Task`.
The task loops every N seconds (configurable 1–10s, default 5s):
- Capture screen → extract position → `ui_server.set_position()` → increment `_update_token`
- Frontend polls `/api/nav/state` every 2s → sees token change → recalculates bearing → redraws compass
Stops on: `stop_navigation()`, `delete_navpoint()` (active target), `unload()`, or target cleared.

**Console command automation**
`_send_console_command(cmd)` async helper:
```
tilde → sleep 0.5s → unicode_typewrite(cmd) → enter → sleep 0.2s → tilde
```
Uses `pydirectinput.unicode_typewrite()` (already a Wingman dependency).
All calls via `asyncio.to_thread()` to keep the event loop unblocked.
Star Citizen must be the focused window when called.

**Coordinate system**
SC uses X/Z for horizontal plane, Y for vertical. Bearing: `atan2(dx, dz)`.
Heading offset from current heading for the compass arrow direction.

**Port assignment**
7862=hud, 7863=accountant, 7864-7867=log_reader, 7868=mining, 7869=navpoint

### Configuration
| Property | Default | Description |
|---|---|---|
| `display` | 1 | Monitor to capture (1-based) |
| `poll_interval` | 5 | Auto-tracking refresh interval in seconds (1–10) |

### Known Limitations / Future Work
- Coordinate units from r_displayinfo vary by game version — navigation math works correctly
  as long as both stored and current positions use the same unit (they always will)
- No "arrived" notification when within a threshold distance of the target
- No support for multiple active targets / route waypoints
- SC console key (tilde) is hardcoded — could become a configurable property if needed
