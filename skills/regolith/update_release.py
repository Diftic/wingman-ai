"""Update the release_version folder with all runtime-necessary files.

Credit: Mallachi
"""

import shutil
from pathlib import Path


SKILL_DIR = Path(__file__).parent
RELEASE_DIR = SKILL_DIR / "release_version"

RELEASE_FILES = [
    "__init__.py",
    "default_config.yaml",
    "main.py",
    "regolith_api.py",
]


def update_release() -> None:
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir()

    for filename in RELEASE_FILES:
        src = SKILL_DIR / filename
        if not src.exists():
            print(f"  WARNING: {filename} not found, skipping")
            continue
        shutil.copy2(src, RELEASE_DIR / filename)
        print(f"  Copied {filename}")

    print(f"\nRelease folder updated: {RELEASE_DIR}")


if __name__ == "__main__":
    print("Updating regolith release_version...")
    update_release()
