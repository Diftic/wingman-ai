"""
clean.py — Remove build artifacts for sc_mining_assistant
Author: Mallachi
"""

import shutil
from pathlib import Path

SKILL_DIR = Path(__file__).parent

TARGETS = [
    "__pycache__",
    "build",
    "dist",
    "*.egg-info",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
]

EXTENSIONS = [".pyc", ".pyo"]

# Dead files from previous versions — safe to remove
DEAD_FILES = [
    "input_handler.py",  # v0.3.0 keybind approach, replaced by folder_watcher in v0.4.0
]

# Data directories/files that can be wiped for a fresh start
DATA_TARGETS = [
    "debug_scans",
    "sc_mining_assistant.db",
]


def clean():
    removed = []

    for target in TARGETS:
        for path in SKILL_DIR.rglob(target):
            if path.is_dir():
                shutil.rmtree(path)
                removed.append(str(path))
            elif path.is_file():
                path.unlink()
                removed.append(str(path))

    for ext in EXTENSIONS:
        for path in SKILL_DIR.rglob(f"*{ext}"):
            path.unlink()
            removed.append(str(path))

    for dead in DEAD_FILES:
        path = SKILL_DIR / dead
        if path.exists():
            path.unlink()
            removed.append(str(path))

    if removed:
        print(f"Removed {len(removed)} item(s):")
        for r in removed:
            print(f"  {r}")
    else:
        print("Nothing to clean.")


def clean_data():
    """Remove scan database and debug screenshots for a fresh start."""
    removed = []
    for target in DATA_TARGETS:
        path = SKILL_DIR / target
        if path.is_dir():
            shutil.rmtree(path)
            removed.append(str(path))
        elif path.is_file():
            path.unlink()
            removed.append(str(path))

    if removed:
        print(f"Removed {len(removed)} data item(s):")
        for r in removed:
            print(f"  {r}")
    else:
        print("No data to clean.")


if __name__ == "__main__":
    import sys

    if "--data" in sys.argv:
        clean_data()
    elif "--all" in sys.argv:
        clean()
        clean_data()
    else:
        clean()
        print("\nUse --data to also remove scan database + debug screenshots.")
        print("Use --all to remove everything.")
