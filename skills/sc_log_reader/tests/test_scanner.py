"""Tests for log_donor.scanner."""

from __future__ import annotations

from pathlib import Path

import pytest

from log_donor.dedup import DedupStore
from log_donor.scanner import (
    discover_installs,
    parse_game_version,
    discover_candidates,
)


def test_discover_installs_finds_existing_dirs(fake_sc_install: Path) -> None:
    installs = discover_installs(fake_sc_install)
    assert set(installs.keys()) == {"Live", "PTU"}
    assert installs["Live"] == fake_sc_install / "Live"
    assert installs["PTU"] == fake_sc_install / "PTU"


def test_discover_installs_skips_missing_dirs(tmp_path: Path) -> None:
    root = tmp_path / "StarCitizen"
    (root / "Live").mkdir(parents=True)
    # no PTU, no HOTFIX
    installs = discover_installs(root)
    assert set(installs.keys()) == {"Live"}


def test_discover_installs_returns_empty_for_missing_root(tmp_path: Path) -> None:
    assert discover_installs(tmp_path / "nonexistent") == {}


def test_parse_game_version_reads_file_version(fake_sc_install: Path) -> None:
    version = parse_game_version(fake_sc_install / "Live" / "Game.log")
    assert version == "4.8.180.28520"


def test_parse_game_version_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert parse_game_version(tmp_path / "nope.log") is None


def test_discover_candidates_filters_by_version(
    fake_sc_install: Path, tmp_path: Path, sc_not_running
) -> None:
    store = DedupStore(db_path=tmp_path / "state.sqlite")
    cands = discover_candidates(fake_sc_install, store)
    # Expected:
    #   Live/Game.log (matches) + Live/logbackups/Game_match.log
    #   PTU/Game.log (matches) + PTU/logbackups/Game_match.log
    # Excluded:
    #   Live/logbackups/Game_old.log (version mismatch)
    paths = {c.path.name for c in cands}
    assert "Game.log" in paths
    assert "Game_match.log" in paths
    assert "Game_old.log" not in paths
    assert len(cands) == 4


def test_discover_candidates_excludes_live_gamelog_when_sc_running(
    fake_sc_install: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("log_donor.scanner.is_sc_running", lambda: True)
    store = DedupStore(db_path=tmp_path / "state.sqlite")
    cands = discover_candidates(fake_sc_install, store)
    # Game.log entries excluded; logbackups kept.
    game_log_count = sum(1 for c in cands if c.path.name == "Game.log")
    assert game_log_count == 0
    match_count = sum(1 for c in cands if c.path.name == "Game_match.log")
    assert match_count == 2  # one for Live, one for PTU


def test_discover_candidates_dedups_known_hashes(
    fake_sc_install: Path, tmp_path: Path, sc_not_running
) -> None:
    store = DedupStore(db_path=tmp_path / "state.sqlite")
    # First discovery
    first = discover_candidates(fake_sc_install, store)
    # Record all as uploaded
    for c in first:
        store.record_uploaded(c.sha256, str(c.path), "test-upload")
    # Second discovery should return zero
    second = discover_candidates(fake_sc_install, store)
    assert second == []


def test_discover_candidates_sets_renamed_with_handle(
    fake_sc_install: Path, tmp_path: Path, sc_not_running
) -> None:
    store = DedupStore(db_path=tmp_path / "state.sqlite")
    cands = discover_candidates(fake_sc_install, store)
    for c in cands:
        assert c.renamed.startswith("Mallachi_")


def test_discover_candidates_falls_back_to_unknown_when_no_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("log_donor.scanner.is_sc_running", lambda: False)
    root = tmp_path / "StarCitizen"
    live = root / "Live"
    (live / "logbackups").mkdir(parents=True)
    # Game.log with no handle line
    (live / "Game.log").write_text(
        "<2026-05-14T13:41:52.133Z> FileVersion: 4.8.180.28520\n"
    )
    (live / "logbackups" / "Game_match.log").write_text(
        "<2026-05-14T13:41:52.133Z> FileVersion: 4.8.180.28520\n"
    )
    store = DedupStore(db_path=tmp_path / "state.sqlite")
    cands = discover_candidates(root, store)
    assert all(c.detected_handle is None for c in cands)
    assert all(c.renamed.startswith("unknown_") for c in cands)
