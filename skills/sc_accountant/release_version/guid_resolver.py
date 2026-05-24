"""
SC_Accountant — Commodity GUID Resolver

Maps Star Citizen commodity resource GUIDs to human-readable names.
The game log only exposes GUIDs for commodity trades; this module
provides a lookup table and persistent cache.

Author: Mallachi
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Known commodity GUID-to-name mappings from Star Citizen game data.
# This table is maintained manually and extended as new GUIDs are encountered.
# Format: { "resource_guid": "Human-Readable Name" }
_BUILTIN_GUID_MAP: dict[str, str] = {
    # Metals & minerals
    "6d56a0ea-7336-41fc-9bba-fd40deaborite": "Aborite",
    # The GUID format in SC logs varies; entries will be added as real
    # GUIDs are observed in production. This stub table prevents lookup
    # failures during development.
}


class GuidResolver:
    """Resolves commodity resource GUIDs to human-readable names.

    Combines a built-in static table with a persistent user cache
    that grows as new mappings are discovered (e.g. from UEXCorp data).
    """

    def __init__(self, cache_path: Path) -> None:
        self._cache_path = cache_path
        self._cache: dict[str, str] = {}
        self._load_cache()

    def resolve(self, guid: str) -> str:
        """Resolve a GUID to a human-readable name.

        Args:
            guid: The resource GUID from the game log.

        Returns:
            Human-readable commodity name, or a truncated GUID if unknown.
        """
        if not guid:
            return "Unknown"

        # Check user cache first (may contain corrections)
        if guid in self._cache:
            return self._cache[guid]

        # Check built-in table
        if guid in _BUILTIN_GUID_MAP:
            return _BUILTIN_GUID_MAP[guid]

        # Unknown — return truncated GUID
        short = guid[:8] if len(guid) > 8 else guid
        return f"Unknown ({short}...)"

    def add_mapping(self, guid: str, name: str) -> None:
        """Add or update a GUID-to-name mapping in the persistent cache."""
        if not guid or not name:
            return
        self._cache[guid] = name
        self._save_cache()

    def add_mappings(self, mappings: dict[str, str]) -> None:
        """Bulk-add GUID-to-name mappings."""
        if not mappings:
            return
        self._cache.update(mappings)
        self._save_cache()

    def get_all_mappings(self) -> dict[str, str]:
        """Return the combined mapping table (built-in + cache)."""
        combined = dict(_BUILTIN_GUID_MAP)
        combined.update(self._cache)
        return combined

    def _load_cache(self) -> None:
        """Load the persistent GUID cache from disk."""
        if not self._cache_path.exists():
            return
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                self._cache = json.load(f)
            logger.info("Loaded %d GUID mappings from cache", len(self._cache))
        except Exception:
            logger.exception("Failed to load GUID cache from %s", self._cache_path)
            self._cache = {}

    def _save_cache(self) -> None:
        """Persist the GUID cache to disk."""
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2)
        except Exception:
            logger.exception("Failed to save GUID cache to %s", self._cache_path)
