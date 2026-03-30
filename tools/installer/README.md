# WingmanAI Skill Installer Builder

Generates a standalone Windows installer `.exe` for any WingmanAI custom skill.
The installer copies skill files directly into the correct WingmanAI folder on the
recipient's machine — no Python knowledge required.

---

## Requirements

```bash
pip install pyinstaller
```

---

## Usage

Run the interactive picker (recommended):

```bash
python tools/installer/build_installer.py
```

Or target a skill directly for scripted/CI use:

```bash
python tools/installer/build_installer.py skills/sc_log_reader
python tools/installer/build_installer.py sc_log_reader
```

Output is placed at:

```
skills/<skill_name>/dist/<DisplayName>_Installer.exe
```

---

## Adding installer support to a skill

**Step 1** — Copy the template into the skill folder:

```bash
cp tools/installer/skill_config_template.json skills/my_skill/skill_installer_config.json
```

**Step 2** — Edit `skill_installer_config.json`:

```json
{
  "skill_name": "sc_my_skill",
  "display_name": "SC My Skill",
  "version": "1.0.0",
  "files": [
    "__init__.py",
    "default_config.yaml",
    "logo.png",
    "main.py"
  ],
  "dirs": [
    "my_skill_ui"
  ],
  "preserve_on_update": [
    "default_config.yaml"
  ]
}
```

| Field | Description |
|---|---|
| `skill_name` | Folder name under `custom_skills/` — must match the skill's directory name in WingmanAI |
| `display_name` | Human-readable name shown in the installer window |
| `version` | Current skill version — shown to the user and written to the install location for future update detection |
| `files` | Flat files to copy from `release_version/` |
| `dirs` | Subdirectories to copy from `release_version/` (e.g. UI folders, data folders) |
| `preserve_on_update` | Files that will **not** be overwritten when updating an existing install — use this for user-configurable files like `default_config.yaml` |

**Step 3** — Refresh the release folder, then build:

```bash
python skills/my_skill/update_release.py
python tools/installer/build_installer.py skills/my_skill
```

---

## How the installer works

1. Checks that WingmanAI has been installed and launched at least once
2. Detects any existing installation and its version
3. If updating — shows a confirmation screen with old/new version and lists which files will be preserved
4. Copies all skill files and directories to:
   `%APPDATA%\ShipBit\WingmanAI\custom_skills\<skill_name>\`
5. On failure — saves all skill files to `Downloads\<skill_name>\` and displays
   numbered manual install steps with Explorer shortcuts

---

## Antivirus false positives

PyInstaller bundles a Python runtime into the `.exe`, which some antivirus tools
flag as suspicious. This is a well-known false positive. Include a note in your
release post asking users to allow the file in Windows Security if it is blocked.
