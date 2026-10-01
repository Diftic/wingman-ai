# Skill Environments — Wingman AI

Canonical locations for skill development, packaging, and deployment.

---

## Developer test environment

**Path:** `D:\PycharmProjects\wingman-ai\skills\`

The working source tree under version control. Edits are made here and the dev-mode Wingman AI loads skills from this location when running from the repo.

## Skill live release folder

**Path:** `D:\PycharmProjects\wingman-ai\skills\<skill_name>\release_version\`

Per-skill packaged copy inside the repo. Example: `skills\sc_log_reader\release_version\`. Contains `install.bat` and mirrors the skill files. `update_release.py` syncs dev source → `release_version/`.

## Live test environment

**Path:** `C:\Users\larse\AppData\Roaming\ShipBit\WingmanAI\custom_skills\`

Where the installed Wingman AI desktop app loads custom skills from. `install.bat` copies from a `release_version/` into this folder. This is the production install on the user's machine — what runs during real Star Citizen play sessions.

## Live core reference tree

**Path:** `D:\PycharmProjects\wingman-ai-live\`

A clone of ShipBit upstream at tag `2.1.1` on local branch `live/2.1.1`: the core source that the installed app was built from. It is a read-only reference, never a place to edit skills. Use it to answer "how does the version users actually run behave", which the dev tree cannot answer because it is ahead.

Verified 2026-07-25: dev tree `LOCAL_VERSION = "3.1.2"`, live tree `LOCAL_VERSION = "2.1.1"` (both in `services/system_manager.py`). `skills/skill_base.py` is byte-identical between the two, so the skill base API has not moved; `api/interface.py` does differ, so anything a skill touches there needs checking against the live tree before release.

Its `skills/` folder holds untracked copies of the SC skills from a 2026-07-07 snapshot. They are stale (accountant 4.8.0.0, log reader 4.8.2.0, no sc_navpoint) and are not maintained. Never read them as current and never edit them.

---

## Flow

```
edit in dev tree  ──►  update_release.py  ──►  release_version/  ──►  install.bat  ──►  AppData\...\custom_skills\
(git-tracked)                                  (git-tracked)                              (live test)
       │
       └── validate against wingman-ai-live core source before each release
```

## Rules

- **Edits originate only in the dev tree.** Never hand-edit `release_version/` or `custom_skills/` — those are downstream copies and hand-edits create sync drift.
- **`release_version/` is regenerated**, not maintained. Treat it as build output that happens to be committed.
- **`custom_skills/` is the live target.** When the user says "live test," they mean this install running against real Star Citizen.
- **Author in the dev tree, validate against the live tree.** Skills are written and tested in the 3.1.2 dev tree, but they ship to users running 2.1.1. Before a release, any core behavior a skill depends on gets confirmed in `wingman-ai-live` source, not in the dev tree. The dev tree passing is not evidence that the shipped app behaves the same way.
- **A dev-tree dependency is not a live-runtime dependency.** `requirements.txt` describes the dev venv; the shipped app is a frozen build that bundles only what the core imports. Check `C:\Program Files\WingmanAI\_internal\<package>` before trusting any external dep. This cost a live skill load once (pydirectinput, 2026-07-16).
