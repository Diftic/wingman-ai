# SC NavPoint — TODO

## Status
v1.0.0 complete — awaiting in-game testing.

## Verified Patterns
- sys.path.insert pattern required for all sibling imports (confirmed working)
- @tool decorator supports async methods (confirmed in vision_ai skill)
- pydirectinput.unicode_typewrite() handles space and underscore correctly
- asyncio.to_thread() wraps blocking pydirectinput calls safely
- mss screen capture + PIL.Image.frombytes("RGB", ..., "raw", "BGRX") pattern from vision_ai skill
- FastAPI explicit static route (no aiofiles) from sc_accountant pattern

## Testing Checklist
- [ ] mark_location — r_displayinfo 4 visible, captures correct XYZ
- [ ] mark_location — no r_displayinfo, returns helpful error
- [ ] navigate_to — bearing calculation, compass arrow direction
- [ ] Auto-polling — compass updates every 5s without voice command
- [ ] stop_navigation — polling task actually cancels
- [ ] enable_displayinfo — tilde opens console, command typed, console closes
- [ ] disable_displayinfo — same sequence, r_displayinfo 0 sent
- [ ] HUD — waypoint list renders, server filter works, compass draws
- [ ] HUD — click waypoint → set as nav target → compass updates
- [ ] poll_interval setting — change to 2s, confirm faster updates
- [ ] Per-server filtering — waypoints correctly tagged with server_id

## Known Issues
- None yet (untested in game)

## Planned Features
- Arrival alert: notify player when within X km of target (threshold configurable)
- Console key configurable (some SC players rebind tilde)
- Bundle MinersRefuge coordinate data to identify nearest known location to any navpoint
