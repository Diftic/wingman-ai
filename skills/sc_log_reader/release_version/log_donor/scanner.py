"""Scan SC installs for log files eligible for donation."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path

from log_donor.dedup import DedupStore
from log_donor.handle_extractor import extract_handle
from log_donor.types import Candidate, InstallType


logger = logging.getLogger(__name__)

_INSTALL_NAMES: tuple[InstallType, ...] = ("Live", "PTU", "HOTFIX")
# Real SC Game.log header has `FileVersion: 4.8.180.28520` (and a duplicate
# `ProductVersion:` line) within the first 40 lines. We use FileVersion as
# the canonical per-build identifier. Earlier drafts looked for BranchName /
# BuildId, but those fields do not exist in real SC Game.log output.
_FILE_VERSION_RE = re.compile(r"FileVersion:\s*(?P<version>\S+)")


def discover_installs(sc_root: Path) -> dict[InstallType, Path]:
    """Return mapping of install name to install dir for installs that exist.

    Args:
        sc_root: Root directory of the Star Citizen installation tree
            (e.g. the folder containing Live/, PTU/, HOTFIX/).

    Returns:
        Dict mapping install name to its Path. Empty if sc_root does not exist.
    """
    result: dict[InstallType, Path] = {}
    if not sc_root.is_dir():
        return result
    for name in _INSTALL_NAMES:
        candidate = sc_root / name
        if candidate.is_dir():
            result[name] = candidate
    return result


def parse_game_version(game_log: Path) -> str | None:
    """Return the SC build identifier (e.g. '4.8.180.28520') or None.

    Reads the first 40 lines of the log to locate the `FileVersion:` line,
    which SC writes near the top of every Game.log. Two logs with the same
    FileVersion are guaranteed to be from the same SC build.

    Args:
        game_log: Path to a Game.log file.

    Returns:
        The version string after `FileVersion:`, or None if the file is
        missing, unreadable, or the field is not found in the first 40 lines.
    """
    try:
        with game_log.open("r", encoding="utf-8", errors="replace") as fh:
            head = "".join(next(fh, "") for _ in range(40))
    except OSError as e:
        logger.warning("could not read Game.log: %s (%s)", game_log, e)
        return None
    m = _FILE_VERSION_RE.search(head)
    if m is None:
        return None
    return m.group("version")


def is_sc_running() -> bool:
    """Return True if StarCitizen.exe is in the process list.

    Returns False if psutil is not installed or if access is denied.
    """
    try:
        import psutil
    except ImportError:
        return False
    try:
        for proc in psutil.process_iter(attrs=["name"]):
            if (proc.info.get("name") or "").lower() == "starcitizen.exe":
                return True
    except Exception:
        # psutil can raise on Windows access-denied; assume not running.
        return False
    return False


def _hash_file(path: Path, store: DedupStore | None) -> str:
    """Return SHA-256 hex digest of a file, using DedupStore cache when available.

    Args:
        path: Path to the file to hash.
        store: Optional DedupStore for read/write hash caching. Pass None to
            always compute fresh.

    Returns:
        Lowercase hex string of the SHA-256 digest.
    """
    if store is not None:
        cached = store.cached_hash(path)
        if cached is not None:
            return cached
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    digest = h.hexdigest()
    if store is not None:
        store.put_cached_hash(path, digest)
    return digest


def discover_candidates(
    sc_root: Path,
    store: DedupStore,
) -> list[Candidate]:
    """Walk SC installs, return all log files eligible for donation.

    Filters out:
      - installs that do not exist on disk
      - the live Game.log of any install if StarCitizen.exe is running
      - logbackups whose game version does not match the install's Game.log
      - files whose SHA-256 is already in the dedup store

    Args:
        sc_root: The Star Citizen root dir (parent of Live / PTU / HOTFIX).
        store:   DedupStore for skipping already-uploaded files and caching hashes.

    Returns:
        List of Candidate, sorted by (install, path).
    """
    sc_running = is_sc_running()
    candidates: list[Candidate] = []

    for install, install_dir in discover_installs(sc_root).items():
        game_log = install_dir / "Game.log"
        version = parse_game_version(game_log)
        if version is None:
            logger.warning("install %s has no parseable version, skipping", install)
            continue

        # Live Game.log
        if not sc_running and game_log.is_file():
            cand = _build_candidate(game_log, install, version, store)
            if cand is not None and not store.is_uploaded(cand.sha256):
                candidates.append(cand)

        # logbackups/*.log filtered by version
        logbackups = install_dir / "logbackups"
        if logbackups.is_dir():
            for path in sorted(logbackups.iterdir()):
                if not path.is_file() or path.suffix.lower() != ".log":
                    continue
                file_version = parse_game_version(path)
                if file_version != version:
                    continue
                cand = _build_candidate(path, install, version, store)
                if cand is not None and not store.is_uploaded(cand.sha256):
                    candidates.append(cand)

    return candidates


def _build_candidate(
    path: Path,
    install: InstallType,
    version: str,
    store: DedupStore,
) -> Candidate | None:
    try:
        size = path.stat().st_size
        sha256 = _hash_file(path, store)
    except OSError as e:
        logger.warning("could not read candidate file: %s (%s)", path, e)
        return None
    handle = extract_handle(path)
    name_prefix = handle if handle else "unknown"
    return Candidate(
        path=path,
        install=install,
        game_version=version,
        size_bytes=size,
        sha256=sha256,
        detected_handle=handle,
        renamed=f"{name_prefix}_{path.name}",
    )
