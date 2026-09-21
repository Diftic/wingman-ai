# SC NavPoint 4.9.0.27

Save the player's current Star Citizen position as a waypoint, view saved points
in a local dashboard, and navigate back with distance and direction guidance.
Position-dependent tools capture and read the game display themselves.

## Requirements and installation

This contribution targets Wingman Skill API v3 on Windows x64. It includes the
V8 OCR model and a patched OpenCV runtime. NumPy, ONNX Runtime, Pillow, mss,
FastAPI, and uvicorn must be available from the Wingman host environment.

Fully close Wingman, back up any existing skill folder outside `custom_skills`,
and place this entire `sc_navpoint` folder under
`%APPDATA%/ShipBit/WingmanAI/custom_skills`. Keep `_vendor`, `models`, and
`navpoint_ui` beside `main.py`. Restart Wingman and enable Star Citizen NavPoint
in your profile. Preserve existing user data and saved profile settings.

In Star Citizen, enable `r_displayinfo 2`. Select the capture display in the
skill settings. The Star Citizen window must be in the foreground for capture.
Ask Wingman to save your position, list your waypoints, or navigate to one.
When the dashboard is ready, its startup card provides the computer link and
a phone QR link. Treat a QR link as access to your dashboard session.

## Coordinate and navigation limits

Waypoints belong to their observed coordinate frame. A planet/moon surface
frame is distinct from a system-space frame; unsupported frame transitions
must not silently reuse old coordinates. Missing, ambiguous, or stale readings
can refuse a capture or suspend guidance. Syntax checks alone do not establish
OCR accuracy or safe navigation. Verify guidance against the game.

This is an existing development candidate. Package checks and synthetic model
execution do not establish live-game accuracy or qualification on the latest
Wingman develop branch. Other operating systems are not qualified by this
Windows dependency bundle.

The skill license is in LICENSE. OpenCV licenses and its loader modification
notice are under `_vendor`; QR generator attribution is retained in its source.
