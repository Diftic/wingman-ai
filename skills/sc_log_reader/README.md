# Star Citizen Log Reader 0.5.0

Wingman Skill API v3 integration for Star Citizen game observations, optional
spoken reactions, event history, and JSON reading-instruction updates.

## Requirements and installation

This candidate includes Windows x64 CPython 3.11 native dependencies. It needs
a compatible Wingman host; it is not a macOS or Linux package.

Close Wingman completely, then place this entire `sc_log_reader` directory in
`%APPDATA%/ShipBit/WingmanAI/custom_skills`. Keep `dependencies` alongside
`main.py`. Enable Star Citizen Log Reader in the desired profile and configure:

- Star Citizen Path: the directory containing LIVE/PTU.
- Runtime Directory: a separate writable directory for history and updates.
- React to Game Events: enable when spoken reactions are wanted.

Before replacing an existing installation, back up its skill directory outside
`custom_skills`. Preserve the Wingman profile and Runtime Directory. Existing
profiles using the `SCLogReader2` class name remain supported.

## Updates and recovery

The configured instruction URL is checked at startup and every six hours.
Validated JSON updates are staged and activated on a later Wingman process
startup. Python code is not updated by this mechanism. Instruction Recovery
can restore the previous revision after a full restart. The bundled JSON
remains available as a fallback.

## SC Accountant

The reader exposes its event feed through `events.sqlite3` in the configured
Runtime Directory. Compatible Accountant versions can discover the reader's
configured database, or use an explicitly configured database path. Keep
existing history and accounting records when upgrading.

See CONTRACT.md for data semantics and compatibility limits. Licenses for the
reader and bundled regex dependency are included.
