"""WingmanAI Custom Skill — Generic Installer Builder.

Reads a skill's skill_installer_config.json, validates the release_version/
folder, then produces a self-contained .exe via PyInstaller.

Prerequisites:
    pip install pyinstaller

Usage:
    python tools/installer/build_installer.py          # interactive picker
    python tools/installer/build_installer.py <skill>  # scripted / CI

    <skill> is optional — the skill folder name or path, e.g.:
        python tools/installer/build_installer.py skills/sc_log_reader
        python tools/installer/build_installer.py sc_log_reader

Output:
    <skill_dir>/dist/<DisplayName>_Installer.exe

Notes:
    - Run update_release.py for the skill first to refresh release_version/.
    - PyInstaller .exe files may trigger antivirus false positives.
      Include a note in your release telling users to allow the file in
      Windows Security if it is flagged.
"""

import json
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

TOOLS_DIR = Path(__file__).parent
REPO_ROOT = TOOLS_DIR.parent.parent
INSTALLER_SCRIPT = TOOLS_DIR / "installer.py"
CONFIG_FILENAME = "skill_installer_config.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_skill_dir(arg: str) -> Path:
    """Accept a full path, a skills-relative name, or just the skill name."""
    p = Path(arg)
    if p.is_dir():
        return p.resolve()
    # Try relative to repo root skills/
    candidate = REPO_ROOT / "skills" / arg
    if candidate.is_dir():
        return candidate.resolve()
    print(f"ERROR: Skill directory not found: {arg}")
    sys.exit(1)


def load_config(skill_dir: Path) -> dict:
    config_path = skill_dir / CONFIG_FILENAME
    if not config_path.exists():
        print(f"ERROR: {CONFIG_FILENAME} not found in {skill_dir}")
        print(f"       Create it using the template in tools/installer/skill_config_template.json")
        sys.exit(1)
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def validate_release_files(release_dir: Path, files: list[str]) -> list[str]:
    return [f for f in files if not (release_dir / f).exists()]


def validate_release_dirs(release_dir: Path, dirs: list[str]) -> list[str]:
    return [d for d in dirs if not (release_dir / d).is_dir()]


def safe_output_name(display_name: str) -> str:
    """Convert display name to a filesystem-safe exe name."""
    return display_name.replace(" ", "_").replace("/", "_") + "_Installer"


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def build(skill_dir: Path) -> None:
    print(f"Skill directory : {skill_dir}")

    config = load_config(skill_dir)
    skill_name = config["skill_name"]
    display_name = config.get("display_name", skill_name)
    version = config.get("version", "?")
    files: list[str] = config["files"]
    dirs: list[str] = config.get("dirs", [])

    release_dir = skill_dir / "release_version"
    if not release_dir.exists():
        print(f"ERROR: release_version/ not found in {skill_dir}")
        print(f"       Run the skill's update_release.py first.")
        sys.exit(1)

    # Validate all expected files and directories are present
    missing_files = validate_release_files(release_dir, files)
    missing_dirs = validate_release_dirs(release_dir, dirs)
    if missing_files or missing_dirs:
        if missing_files:
            print("ERROR: Missing files in release_version/:")
            for f in missing_files:
                print(f"  • {f}")
        if missing_dirs:
            print("ERROR: Missing directories in release_version/:")
            for d in missing_dirs:
                print(f"  • {d}/")
        print("\nRun the skill's update_release.py to refresh the release folder.")
        sys.exit(1)

    output_name = safe_output_name(display_name)
    dist_dir = skill_dir / "dist"
    build_dir = skill_dir / "build"

    print(f"Skill           : {display_name}  v{version}")
    print(f"Output          : {dist_dir / output_name}.exe")
    print()

    # --add-data entries for flat files — destination "." = root of sys._MEIPASS
    add_data: list[str] = []
    for filename in files:
        src = release_dir / filename
        add_data += ["--add-data", f"{src};."]

    # --add-data entries for directories — destination name must match dir name
    # so installer.py can reconstruct the same structure in custom_skills/
    for dirname in dirs:
        src = release_dir / dirname
        add_data += ["--add-data", f"{src};{dirname}"]

    # Bundle the skill config so installer.py can read it at runtime
    add_data += ["--add-data", f"{skill_dir / CONFIG_FILENAME};."]

    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",
        "--windowed",          # No console window shown to end users
        "--name", output_name,
        "--distpath", str(dist_dir),
        "--workpath", str(build_dir),
        "--specpath", str(skill_dir),
        "--clean",             # Always start from a clean state
        *add_data,
        str(INSTALLER_SCRIPT),
    ]

    print("Running PyInstaller…\n")
    result = subprocess.run(cmd)

    if result.returncode == 0:
        exe = dist_dir / f"{output_name}.exe"
        print(f"\n✓  Build successful.")
        print(f"   Installer : {exe}")
        print()
        print("── Antivirus notice ─────────────────────────────────────────────────")
        print("   PyInstaller executables are sometimes flagged as suspicious by")
        print("   Windows Defender or other antivirus tools. This is a known false")
        print("   positive. Include a note in your release asking users to allow the")
        print("   file in Windows Security if it is blocked.")
        print("─────────────────────────────────────────────────────────────────────")
    else:
        print(f"\n✗  PyInstaller failed (exit code {result.returncode}).")
        sys.exit(result.returncode)


# ---------------------------------------------------------------------------
# Interactive skill picker
# ---------------------------------------------------------------------------

def discover_skills() -> list[Path]:
    """Return all skill directories that contain a skill_installer_config.json."""
    skills_root = REPO_ROOT / "skills"
    if not skills_root.exists():
        return []
    return sorted(
        p.parent
        for p in skills_root.rglob(CONFIG_FILENAME)
        if p.parent.parent == skills_root  # top-level skills only
    )


def pick_skill() -> Path:
    """Print a numbered menu of available skills and return the chosen path."""
    skills = discover_skills()

    if not skills:
        print("No skills found with a skill_installer_config.json.")
        print(f"Expected location: {REPO_ROOT / 'skills' / '<skill_name>' / CONFIG_FILENAME}")
        print(f"Use tools/installer/skill_config_template.json as a starting point.")
        sys.exit(1)

    print("┌─────────────────────────────────────────────┐")
    print("│   WingmanAI Skill Installer Builder          │")
    print("└─────────────────────────────────────────────┘")
    print()
    print("Available skills:\n")

    for i, skill_dir in enumerate(skills, start=1):
        try:
            cfg = load_config(skill_dir)
            display = cfg.get("display_name", cfg["skill_name"])
            version = cfg.get("version", "?")
            print(f"  [{i}]  {display}  (v{version})")
        except Exception:
            print(f"  [{i}]  {skill_dir.name}  (config unreadable)")

    print()

    while True:
        raw = input("Select a skill (number): ").strip()
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(skills):
                return skills[idx]
        print(f"     Please enter a number between 1 and {len(skills)}.")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Accept an optional path argument for scripted/CI use;
    # fall back to the interactive picker when run without arguments.
    if len(sys.argv) >= 2:
        skill_dir = resolve_skill_dir(sys.argv[1])
    else:
        skill_dir = pick_skill()
        print()

    build(skill_dir)
