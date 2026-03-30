"""WingmanAI Custom Skill — Generic Installer.

Bundled by PyInstaller into a standalone .exe per skill.
Do not run this file directly — use tools/installer/build_installer.py.

At runtime inside the .exe, skill files and skill_config.json are extracted
to sys._MEIPASS by PyInstaller. This script reads the config and installs.
"""

import json
import os
import shutil
import sys
import tkinter as tk
from pathlib import Path
from tkinter import ttk


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

APPDATA = Path(os.environ.get("APPDATA", ""))
WINGMAN_BASE = APPDATA / "ShipBit" / "WingmanAI"
CUSTOM_SKILLS_DIR = WINGMAN_BASE / "custom_skills"
DOWNLOADS_DIR = Path(os.environ.get("USERPROFILE", "")) / "Downloads"

# Installed config sentinel — written after a successful install so the next
# run can detect the installed version.
CONFIG_SENTINEL = "skill_installer_config.json"

# ---------------------------------------------------------------------------
# Colours
# ---------------------------------------------------------------------------

BG = "#1a1a2e"
BG2 = "#16213e"
FG = "#e0e0e0"
FG_DIM = "#999999"
FG_WARN = "#ffb74d"
GREEN = "#4caf50"
RED = "#ef5350"
BLUE = "#5c6bc0"
BTN_NEUTRAL = "#2e2e4e"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_bundle_dir() -> Path:
    """Locate bundled skill files.

    Inside the .exe: sys._MEIPASS holds the temp extraction directory.
    In dev mode: files live in release_version/ next to this script.
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS)
    return Path(__file__).parent.parent.parent / "skills" / "_dev_bundle"


def load_config(bundle_dir: Path) -> dict:
    config_path = bundle_dir / CONFIG_SENTINEL
    if not config_path.exists():
        raise FileNotFoundError(f"skill_config.json not found in bundle: {bundle_dir}")
    with open(config_path, encoding="utf-8") as f:
        return json.load(f)


def get_installed_version(dest_dir: Path) -> str | None:
    """Read the version from a previously installed skill_config.json, if any."""
    sentinel = dest_dir / CONFIG_SENTINEL
    if not sentinel.exists():
        return None
    try:
        with open(sentinel, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("version")
    except Exception:
        return None


def open_folder(path: Path) -> None:
    os.startfile(str(path))


# ---------------------------------------------------------------------------
# Install logic
# ---------------------------------------------------------------------------

def run_install(bundle_dir: Path, config: dict, dest_dir: Path, is_update: bool) -> tuple[bool, str]:
    """Copy skill files and directories to destination.

    On updates, files listed in ``preserve_on_update`` are skipped if they
    already exist in the destination (preserves user-customised config).

    Returns:
        (success, detail_message)
    """
    preserve = set(config.get("preserve_on_update", []))
    files: list[str] = config["files"]
    dirs: list[str] = config.get("dirs", [])

    try:
        dest_dir.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        return False, (
            f"Could not create the skill folder — permission denied.\n\n"
            f"Destination:\n{dest_dir}\n\nError: {exc}"
        )

    failures: list[str] = []

    for filename in files:
        # On updates, skip files the user may have customised
        if is_update and filename in preserve and (dest_dir / filename).exists():
            continue

        src = bundle_dir / filename
        if not src.exists():
            failures.append(f"Missing from installer bundle: {filename}")
            continue

        try:
            shutil.copy2(src, dest_dir / filename)
        except Exception as exc:
            failures.append(f"{filename}: {exc}")

    for dirname in dirs:
        src = bundle_dir / dirname
        dst = dest_dir / dirname

        if not src.exists():
            failures.append(f"Missing directory from installer bundle: {dirname}/")
            continue

        try:
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        except Exception as exc:
            failures.append(f"{dirname}/: {exc}")

    if failures:
        return False, "One or more items could not be copied:\n\n" + "\n".join(
            f"  • {f}" for f in failures
        )

    # Write config sentinel so future runs can read the installed version
    try:
        shutil.copy2(bundle_dir / CONFIG_SENTINEL, dest_dir / CONFIG_SENTINEL)
    except Exception:
        pass  # Non-fatal — only affects future version detection

    return True, str(dest_dir)


def save_fallback_files(bundle_dir: Path, config: dict, fallback_dir: Path) -> bool:
    """Copy skill files and directories to Downloads as a manual-install fallback."""
    try:
        fallback_dir.mkdir(parents=True, exist_ok=True)
        for filename in config["files"]:
            src = bundle_dir / filename
            if src.exists():
                shutil.copy2(src, fallback_dir / filename)
        for dirname in config.get("dirs", []):
            src = bundle_dir / dirname
            dst = fallback_dir / dirname
            if src.exists():
                if dst.exists():
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class InstallerApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.configure(bg=BG)
        self.resizable(False, False)

        self._bundle_dir = get_bundle_dir()
        self._config: dict = {}
        self._dest_dir: Path = Path()
        self._fallback_dir: Path = Path()
        self._is_update: bool = False

        self._set_size(520, 420)
        self._build_skeleton()
        self.after(250, self._detect)

    # ------------------------------------------------------------------
    # Layout helpers
    # ------------------------------------------------------------------

    def _set_size(self, w: int, h: int) -> None:
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

    def _build_skeleton(self) -> None:
        """Static header that persists across all screens."""
        self._header_title = tk.StringVar(value="WingmanAI Skill Installer")
        self._header_sub = tk.StringVar(value="Loading…")

        tk.Label(self, textvariable=self._header_title,
                 font=("Segoe UI", 20, "bold"), bg=BG, fg=FG).pack(pady=(28, 2))
        tk.Label(self, textvariable=self._header_sub,
                 font=("Segoe UI", 10), bg=BG, fg=FG_DIM).pack()

        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=48, pady=18)

        # Body frame — swapped out per screen
        self._body = tk.Frame(self, bg=BG)
        self._body.pack(fill="both", expand=True, padx=32)

        # Button row — always at the bottom
        self._btn_row = tk.Frame(self, bg=BG)
        self._btn_row.pack(pady=20)

    def _clear_body(self) -> None:
        for w in self._body.winfo_children():
            w.destroy()
        for w in self._btn_row.winfo_children():
            w.destroy()

    def _label(self, text: str = "", font_size: int = 10, fg: str = FG,
               bold: bool = False, justify: str = "center", **kw) -> tk.Label:
        weight = "bold" if bold else "normal"
        return tk.Label(self._body, text=text,
                        font=("Segoe UI", font_size, weight),
                        bg=BG, fg=fg, wraplength=450,
                        justify=justify, **kw)

    def _btn(self, text: str, command, bg: str = BTN_NEUTRAL,
             row: tk.Frame | None = None) -> tk.Button:
        parent = row if row is not None else self._btn_row
        b = tk.Button(
            parent, text=text, command=command,
            bg=bg, fg="white", font=("Segoe UI", 9),
            padx=16, pady=6, relief="flat", cursor="hand2",
            activebackground=bg, activeforeground="white", bd=0,
        )
        b.pack(side="left", padx=6)
        return b

    # ------------------------------------------------------------------
    # Screen: Detect → route to confirm or install
    # ------------------------------------------------------------------

    def _detect(self) -> None:
        try:
            self._config = load_config(self._bundle_dir)
        except Exception as exc:
            self._show_fatal(f"Installer bundle is corrupt:\n{exc}")
            return

        display = self._config.get("display_name", self._config["skill_name"])
        version = self._config.get("version", "?")

        self.title(f"{display} — WingmanAI Skill Installer")
        self._header_title.set(display)
        self._header_sub.set(f"WingmanAI Custom Skill  ·  v{version}")

        self._dest_dir = CUSTOM_SKILLS_DIR / self._config["skill_name"]
        self._fallback_dir = DOWNLOADS_DIR / self._config["skill_name"]

        # Pre-flight: WingmanAI must exist
        if not WINGMAN_BASE.exists():
            self._show_fatal(
                f"WingmanAI not found at:\n{WINGMAN_BASE}\n\n"
                f"Please install and launch WingmanAI at least once, then run this installer again."
            )
            return

        installed_ver = get_installed_version(self._dest_dir)

        if installed_ver:
            self._is_update = True
            self._show_update_confirm(installed_ver, version)
        else:
            self._is_update = False
            self._show_installing()

    # ------------------------------------------------------------------
    # Screen: Update confirmation
    # ------------------------------------------------------------------

    def _show_update_confirm(self, old_ver: str, new_ver: str) -> None:
        self._clear_body()
        self._label("⟳", font_size=28, fg=BLUE).pack(pady=(0, 10))
        self._label(
            f"An existing installation was found.",
            font_size=11, bold=True,
        ).pack()
        self._label(
            f"Installed version:  v{old_ver}\n"
            f"This installer:       v{new_ver}",
            font_size=10, fg=FG_DIM,
        ).pack(pady=(10, 6))

        preserve = self._config.get("preserve_on_update", [])
        if preserve:
            self._label(
                f"Your existing settings will be preserved:\n"
                + ",  ".join(preserve),
                font_size=9, fg=FG_WARN,
            ).pack(pady=(4, 0))

        self._btn("Update", self._show_installing, bg=BLUE)
        self._btn("Cancel", self.destroy, bg=BTN_NEUTRAL)

    # ------------------------------------------------------------------
    # Screen: Installing (progress)
    # ------------------------------------------------------------------

    def _show_installing(self) -> None:
        self._clear_body()
        mode = "Updating…" if self._is_update else "Installing…"
        self._label(mode, font_size=12, bold=True).pack(pady=(10, 6))

        prog = ttk.Progressbar(self._body, mode="indeterminate", length=360)
        prog.pack(pady=10)
        prog.start(10)

        self.update()
        success, detail = run_install(
            self._bundle_dir, self._config, self._dest_dir, self._is_update
        )
        prog.stop()

        if success:
            self._show_success()
        else:
            self._show_failure(detail)

    # ------------------------------------------------------------------
    # Screen: Success
    # ------------------------------------------------------------------

    def _show_success(self) -> None:
        self._clear_body()
        verb = "Updated" if self._is_update else "Installed"
        self._label("✅", font_size=28, fg=GREEN).pack(pady=(0, 8))
        self._label(f"{verb} successfully!", font_size=12, bold=True, fg=GREEN).pack()
        self._label(
            f"Restart WingmanAI to activate the skill.\n\n"
            f"Installed to:\n{self._dest_dir}",
            font_size=9, fg=FG_DIM,
        ).pack(pady=(10, 0))

        self._btn("Open Install Folder", lambda: open_folder(self._dest_dir), bg=BLUE)
        self._btn("Close", self.destroy, bg=BTN_NEUTRAL)

    # ------------------------------------------------------------------
    # Screen: Failure
    # ------------------------------------------------------------------

    def _show_failure(self, detail: str) -> None:
        self._clear_body()
        self._label("❌", font_size=28, fg=RED).pack(pady=(0, 8))
        self._label("Installation failed", font_size=12, bold=True, fg=RED).pack()
        self._label(detail, font_size=9, fg=FG_DIM, justify="left").pack(
            pady=(8, 0), anchor="w"
        )

        fallback_ok = save_fallback_files(self._bundle_dir, self._config, self._fallback_dir)

        if fallback_ok:
            manual = (
                f"\n── Manual Install Steps ──\n\n"
                f"1.  Skill files have been saved to your Downloads:\n"
                f"     {self._fallback_dir}\n\n"
                f"2.  Copy ALL those files into:\n"
                f"     {self._dest_dir}\n"
                f"     (create the folder if it doesn't exist)\n\n"
                f"3.  Restart WingmanAI — the skill will appear automatically."
            )
            self._label(manual, font_size=9, fg=FG_DIM, justify="left").pack(
                pady=(6, 0), anchor="w"
            )
            self._btn("Open Source Folder", lambda: open_folder(self._fallback_dir), bg=BTN_NEUTRAL)
            self._btn("Open Destination", lambda: open_folder(self._dest_dir.parent), bg=BLUE)
        else:
            self._label(
                f"\nManually copy the skill files to:\n{self._dest_dir}",
                font_size=9, fg=FG_DIM,
            ).pack(pady=(6, 0))

        self._btn("Close", self.destroy, bg=BTN_NEUTRAL)
        self._set_size(540, 560)

    # ------------------------------------------------------------------
    # Screen: Fatal (can't even start)
    # ------------------------------------------------------------------

    def _show_fatal(self, message: str) -> None:
        self._clear_body()
        self._label("⚠", font_size=32, fg=FG_WARN).pack(pady=(0, 8))
        self._label("Cannot proceed", font_size=12, bold=True, fg=FG_WARN).pack()
        self._label(message, font_size=9, fg=FG_DIM, justify="left").pack(
            pady=(10, 0), anchor="w"
        )
        self._btn("Close", self.destroy, bg=BTN_NEUTRAL)
        self._set_size(520, 480)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    app = InstallerApp()
    app.mainloop()
