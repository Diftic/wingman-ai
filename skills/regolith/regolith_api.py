"""
Regolith.Rocks GraphQL API Client for Star Citizen Mining Data.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# Cache settings
CACHE_MAX_AGE_HOURS = 24
CACHE_FILENAME = "regolith_cache.json"

# Mineral densities (kg per SCU) - datamined from Star Citizen game files
# Source: SC_Signature_Scanner project
# Formula: mineral_volume (SCU) = mineral_mass / density
MINERAL_DENSITY = {
    "AGRICIUM": 239.71,
    "ALUMINUM": 89.88,
    "BERYL": 91.41,
    "BEXALITE": 230.03,
    "BORASE": 149.60,
    "COPPER": 298.37,
    "CORUNDUM": 133.85,
    "GOLD": 643.57,
    "HEPHAESTANITE": 106.54,
    "ICE": 33.19,
    "INERTMATERIAL": 33.21,
    "IRON": 262.42,
    "LARANITE": 383.09,
    "QUANTANIUM": 681.26,
    "QUARTZ": 88.30,
    "RICCITE": 53.28,
    "SILICON": 77.82,
    "STILERON": 158.20,
    "TARANITE": 339.67,
    "TIN": 192.04,
    "TITANIUM": 149.61,
    "TUNGSTEN": 642.94,
    # NYX minerals
    "LINDINIUM": 200.00,
    "TORITE": 200.00,
    # Gems (vehicle mining) - using estimates
    "HADANITE": 100.00,
    "DOLIVINE": 100.00,
    "APHORITE": 100.00,
    "JANALITE": 100.00,
}

# Default density for unknown minerals
DEFAULT_MINERAL_DENSITY = 100.0


@dataclass
class RegolithData:
    """Container for cached Regolith lookup data."""

    # CIG data
    ore_densities: dict[str, float] | None = None
    refinery_methods: dict[str, list] | None = None
    ore_processing: dict[str, list] | None = None

    # UEX data
    bodies: list[dict] | None = None
    max_prices: dict[str, dict] | None = None
    refinery_bonuses: dict[str, dict] | None = None
    ships: list[dict] | None = None
    tradeports: list[dict] | None = None

    # Derived data
    refineries: list[dict] | None = None

    # Survey data (mining probabilities)
    ship_ore_probs: dict[str, dict] | None = None  # shipOreByGravProb
    vehicle_ore_probs: dict[str, dict] | None = None  # vehicleProbs (ROC/hand mining)
    bonus_map: dict[str, float] | None = None  # Deposit spawn multipliers by location
    bonus_map_roc: dict[str, float] | None = None  # ROC deposit spawn multipliers
    rock_class_by_location: dict[str, dict] | None = None  # shipRockClassByGravProb
    ore_by_rock_class: dict[str, dict] | None = None  # shipOreByRockClassProb

    # UEX price data (from UEX Corp API)
    uex_minerals: dict[str, dict] | None = None  # Mineral commodity data by name
    uex_prices: dict[str, dict] | None = None  # Best sell prices per mineral

    def is_loaded(self) -> bool:
        return self.ore_densities is not None

    def has_survey_data(self) -> bool:
        return self.ship_ore_probs is not None

    def has_rock_class_data(self) -> bool:
        return (
            self.rock_class_by_location is not None
            and self.ore_by_rock_class is not None
        )

    def has_uex_prices(self) -> bool:
        return self.uex_prices is not None


# Mapping from Regolith ore names to UEX commodity names
# UEX uses slightly different spellings (e.g., "Quantainium" with 'i')
REGOLITH_TO_UEX_NAME = {
    "QUANTANIUM": "Quantainium",
    "AGRICIUM": "Agricium",
    "GOLD": "Gold",
    "BEXALITE": "Bexalite",
    "TARANITE": "Taranite",
    "LARANITE": "Laranite",
    "BORASE": "Borase",
    "HEPHAESTANITE": "Hephaestanite",
    "TITANIUM": "Titanium",
    "DIAMOND": "Diamond",
    "COPPER": "Copper",
    "BERYL": "Beryl",
    "TUNGSTEN": "Tungsten",
    "CORUNDUM": "Corundum",
    "QUARTZ": "Quartz",
    "ALUMINIUM": "Aluminium",
    "INERT": "Inert Material",
    "HADANITE": "Hadanite",
    "DOLIVINE": "Dolivine",
    "APHORITE": "Aphorite",
    "JANALITE": "Janalite",
}


class RegolithAPI:
    """GraphQL client for the Regolith.Rocks API."""

    BASE_URL = "https://api.regolith.rocks"
    TIMEOUT = 30

    def __init__(self, api_key: str, cache_dir: str | None = None):
        self.api_key = api_key
        self.session = requests.Session()
        self.data = RegolithData()
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self._cache_building = False

    # =========================================================================
    # Cache Management
    # =========================================================================

    def _get_cache_path(self) -> Path | None:
        """Get the cache file path."""
        if not self.cache_dir:
            return None
        return self.cache_dir / CACHE_FILENAME

    def _is_cache_valid(self) -> bool:
        """Check if cache exists and is less than 24 hours old."""
        cache_path = self._get_cache_path()
        if not cache_path or not cache_path.exists():
            return False

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            cache_timestamp = cache_data.get("timestamp", 0)
            age_hours = (time.time() - cache_timestamp) / 3600

            return age_hours < CACHE_MAX_AGE_HOURS
        except Exception:
            logger.exception("Failed to validate cache at %s", cache_path)
            return False

    def _save_cache(self) -> bool:
        """Save current data to cache file."""
        cache_path = self._get_cache_path()
        if not cache_path:
            return False

        try:
            # Ensure cache directory exists
            cache_path.parent.mkdir(parents=True, exist_ok=True)

            cache_data = {
                "timestamp": time.time(),
                "ore_densities": self.data.ore_densities,
                "refinery_methods": self.data.refinery_methods,
                "ore_processing": self.data.ore_processing,
                "bodies": self.data.bodies,
                "max_prices": self.data.max_prices,
                "refinery_bonuses": self.data.refinery_bonuses,
                "ships": self.data.ships,
                "tradeports": self.data.tradeports,
                "refineries": self.data.refineries,
                "ship_ore_probs": self.data.ship_ore_probs,
                "vehicle_ore_probs": self.data.vehicle_ore_probs,
                "bonus_map": self.data.bonus_map,
                "bonus_map_roc": self.data.bonus_map_roc,
                "rock_class_by_location": self.data.rock_class_by_location,
                "ore_by_rock_class": self.data.ore_by_rock_class,
                "uex_minerals": self.data.uex_minerals,
                "uex_prices": self.data.uex_prices,
            }

            with open(cache_path, "w", encoding="utf-8") as f:
                json.dump(cache_data, f)

            return True
        except Exception:
            logger.exception("Failed to save cache to %s", cache_path)
            return False

    def _load_cache(self) -> bool:
        """Load data from cache file."""
        cache_path = self._get_cache_path()
        if not cache_path or not cache_path.exists():
            return False

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Restore all data from cache
            self.data.ore_densities = cache_data.get("ore_densities")
            self.data.refinery_methods = cache_data.get("refinery_methods")
            self.data.ore_processing = cache_data.get("ore_processing")
            self.data.bodies = cache_data.get("bodies")
            self.data.max_prices = cache_data.get("max_prices")
            self.data.refinery_bonuses = cache_data.get("refinery_bonuses")
            self.data.ships = cache_data.get("ships")
            self.data.tradeports = cache_data.get("tradeports")
            self.data.refineries = cache_data.get("refineries")
            self.data.ship_ore_probs = cache_data.get("ship_ore_probs")
            self.data.vehicle_ore_probs = cache_data.get("vehicle_ore_probs")
            self.data.bonus_map = cache_data.get("bonus_map")
            self.data.bonus_map_roc = cache_data.get("bonus_map_roc")
            self.data.rock_class_by_location = cache_data.get("rock_class_by_location")
            self.data.ore_by_rock_class = cache_data.get("ore_by_rock_class")
            self.data.uex_minerals = cache_data.get("uex_minerals")
            self.data.uex_prices = cache_data.get("uex_prices")

            return self.data.is_loaded()
        except Exception:
            logger.exception("Failed to load cache from %s", cache_path)
            return False

    def get_cache_age_hours(self) -> float | None:
        """Get cache age in hours, or None if no cache."""
        cache_path = self._get_cache_path()
        if not cache_path or not cache_path.exists():
            return None

        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
            cache_timestamp = cache_data.get("timestamp", 0)
            return (time.time() - cache_timestamp) / 3600
        except Exception:
            logger.exception("Failed to read cache age from %s", cache_path)
            return None

    def is_cache_building(self) -> bool:
        """Check if cache is currently being built."""
        return self._cache_building

    def load_all_data(self, force_refresh: bool = False) -> tuple[bool, str]:
        """
        Load all data, using cache if valid.

        Returns:
            Tuple of (success, status_message)
        """
        # Check if cache is valid and not forcing refresh
        if not force_refresh and self._is_cache_valid():
            if self._load_cache():
                age = self.get_cache_age_hours()
                return True, f"Loaded from cache ({age:.1f}h old)"

        # Need to build cache from API
        self._cache_building = True

        try:
            # Load lookup data
            if not self.load_lookups():
                return False, "Failed to load lookup data from API"

            # Load survey data
            if not self.load_survey_data():
                return False, "Failed to load survey data from API"

            # Load UEX prices
            if not self.load_uex_prices():
                return False, "Failed to load UEX price data"

            # Save to cache
            if self._save_cache():
                return True, "Cache built and saved successfully"
            else:
                return True, "Data loaded but cache save failed"

        finally:
            self._cache_building = False

    def _get_headers(self) -> dict[str, str]:
        return {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
        }

    def _execute_query(self, query: str) -> dict[str, Any]:
        """Execute a GraphQL query and return the response data."""
        try:
            response = self.session.post(
                self.BASE_URL,
                headers=self._get_headers(),
                json={"query": query},
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

            if "errors" in result:
                raise Exception(f"GraphQL errors: {result['errors']}")

            return result.get("data", {})
        except requests.exceptions.RequestException as e:
            raise Exception(f"API request failed: {e}")

    def verify_connection(self) -> bool:
        """Verify API key by fetching profile."""
        query = """
        {
            profile {
                userId
                scName
                plan
            }
        }
        """
        try:
            data = self._execute_query(query)
            return data.get("profile") is not None
        except Exception:
            logger.exception("Failed to verify Regolith API connection")
            return False

    def introspect_schema(self) -> dict | None:
        """Introspect the GraphQL schema to see available types and fields."""
        query = """
        {
            __schema {
                queryType {
                    fields {
                        name
                        description
                        type {
                            name
                            kind
                        }
                    }
                }
            }
        }
        """
        try:
            return self._execute_query(query)
        except Exception:
            logger.exception("Failed to introspect GraphQL schema")
            return None

    def get_survey_data_sample(self, data_name: str, epoch: str = "4.4") -> dict | None:
        """Get a sample of survey data to inspect its structure."""
        return self.get_survey_data(data_name, epoch)

    def load_lookups(self) -> bool:
        """Load all lookup data from the API."""
        query = """
        {
            lookups {
                CIG {
                    densitiesLookups
                    methodsBonusLookup
                    oreProcessingLookup
                }
                UEX {
                    bodies
                    maxPrices
                    refineryBonuses
                    ships
                    tradeports
                }
            }
        }
        """
        try:
            data = self._execute_query(query)
            lookups = data.get("lookups", {})

            # Parse CIG data
            cig = lookups.get("CIG", {})
            self.data.ore_densities = cig.get("densitiesLookups", {})
            self.data.refinery_methods = cig.get("methodsBonusLookup", {})
            self.data.ore_processing = cig.get("oreProcessingLookup", {})

            # Parse UEX data
            uex = lookups.get("UEX", {})
            self.data.bodies = uex.get("bodies", [])
            self.data.max_prices = uex.get("maxPrices", {})
            self.data.refinery_bonuses = uex.get("refineryBonuses", {})
            self.data.ships = uex.get("ships", [])
            self.data.tradeports = uex.get("tradeports", [])

            # Extract refineries from tradeports
            self.data.refineries = [
                tp for tp in self.data.tradeports if tp.get("refinery", False)
            ]

            return True
        except Exception:
            logger.exception("Failed to load lookups from Regolith API")
            raise

    def get_survey_data(self, data_name: str, epoch: str = "latest") -> dict | None:
        """
        Fetch survey data by name.

        Valid data_name values:
        - vehicleProbs
        - shipOreByGravProb
        - shipOreByRockClassProb
        - shipRockClassByGravProb
        - bonusMap
        - bonusMap.roc
        - leaderBoard
        - guildLeaderBoard
        """
        query = f"""
        {{
            surveyData(dataName: "{data_name}", epoch: "{epoch}") {{
                data
                dataName
                epoch
                lastUpdated
            }}
        }}
        """
        try:
            data = self._execute_query(query)
            return data.get("surveyData")
        except Exception:
            logger.exception(
                "Failed to fetch survey data: %s (epoch=%s)", data_name, epoch
            )
            return None

    # =========================================================================
    # Helper methods for data access
    # =========================================================================

    def get_ore_info(self, ore_name: str) -> dict | None:
        """Get comprehensive info about an ore."""
        ore_upper = ore_name.upper()

        if ore_upper not in self.data.ore_densities:
            return None

        info = {
            "name": ore_upper,
            "density": self.data.ore_densities.get(ore_upper),
            "processing": None,
            "prices": {
                "raw": None,
                "refined": None,
            },
        }

        # Add processing data [yield_factor, time_factor, base_price_factor]
        if ore_upper in self.data.ore_processing:
            proc = self.data.ore_processing[ore_upper]
            info["processing"] = {
                "yield_factor": proc[0] if len(proc) > 0 else None,
                "time_factor": proc[1] if len(proc) > 1 else None,
                "base_price_factor": proc[2] if len(proc) > 2 else None,
            }

        # Add price data
        raw_prices = self.data.max_prices.get("oreRaw", {}).get(ore_upper)
        if raw_prices:
            info["prices"]["raw"] = {
                "min": raw_prices.get("min", [None, []])[0],
                "min_locations": raw_prices.get("min", [None, []])[1],
                "max": raw_prices.get("max", [None, []])[0],
                "max_locations": raw_prices.get("max", [None, []])[1],
                "avg": raw_prices.get("avg"),
            }

        refined_prices = self.data.max_prices.get("oreRefined", {}).get(ore_upper)
        if refined_prices:
            info["prices"]["refined"] = {
                "min": refined_prices.get("min", [None, []])[0],
                "min_locations": refined_prices.get("min", [None, []])[1],
                "max": refined_prices.get("max", [None, []])[0],
                "max_locations": refined_prices.get("max", [None, []])[1],
                "avg": refined_prices.get("avg"),
            }

        return info

    def get_all_ores(self) -> list[str]:
        """Get list of all ore names."""
        return list(self.data.ore_densities.keys())

    def _get_location_label(self, location_code: str) -> str:
        """Resolve a location code to its human-readable label."""
        body = next(
            (b for b in self.data.bodies if b.get("id") == location_code),
            None,
        )
        return body.get("label") if body else location_code

    def get_refinery_methods_info(self) -> dict:
        """Get info about all refinery methods."""
        methods = {}
        for name, values in self.data.refinery_methods.items():
            # values = [yield_bonus, time_multiplier, cost_multiplier]
            methods[name] = {
                "name": name.replace("_", " ").title(),
                "yield_bonus": values[0] if len(values) > 0 else None,
                "time_multiplier": values[1] if len(values) > 1 else None,
                "cost_multiplier": values[2] if len(values) > 2 else None,
            }
        return methods

    def get_refineries(self) -> list[dict]:
        """Get all refinery locations."""
        refineries = []
        for tp in self.data.refineries:
            refineries.append(
                {
                    "code": tp.get("code"),
                    "name": tp.get("name"),
                    "name_short": tp.get("name_short"),
                    "system": tp.get("system"),
                    "planet": tp.get("planet"),
                    "prices": tp.get("prices", {}),
                }
            )
        return refineries

    def get_refinery_bonuses_for_ore(self, ore_name: str) -> list[dict]:
        """Get refinery bonuses for a specific ore, sorted by bonus."""
        ore_upper = ore_name.upper()
        bonuses = []

        for refinery_code, ore_bonuses in self.data.refinery_bonuses.items():
            if ore_upper in ore_bonuses:
                bonus = ore_bonuses[ore_upper]
                # Find refinery name
                refinery_info = next(
                    (r for r in self.data.refineries if r.get("code") == refinery_code),
                    None,
                )
                bonuses.append(
                    {
                        "refinery_code": refinery_code,
                        "refinery_name": refinery_info.get("name")
                        if refinery_info
                        else refinery_code,
                        "location": refinery_info.get("name_short")
                        if refinery_info
                        else None,
                        "bonus": bonus,
                        "bonus_percent": round((bonus - 1) * 100, 1),
                    }
                )

        # Sort by bonus descending
        bonuses.sort(key=lambda x: x["bonus"], reverse=True)
        return bonuses

    def get_mining_bodies(self, has_rocks: bool = True) -> list[dict]:
        """Get bodies where mining is possible."""
        return [
            {
                "id": b.get("id"),
                "label": b.get("label"),
                "type": b.get("wellType"),
                "system": b.get("system"),
                "parent": b.get("parent"),
                "is_space": b.get("isSpace"),
                "is_surface": b.get("isSurface"),
                "has_rocks": b.get("hasRocks"),
                "has_gems": b.get("hasGems"),
            }
            for b in self.data.bodies
            if b.get("hasRocks") == has_rocks or b.get("hasGems")
        ]

    def get_mining_ships(self) -> list[dict]:
        """Get ships with mining capabilities."""
        return [
            {
                "name": s.get("name"),
                "maker": s.get("maker"),
                "cargo": s.get("cargo"),
                "mining_hold": s.get("miningHold"),
                "role": s.get("role"),
            }
            for s in self.data.ships
            if s.get("miningHold") or s.get("role") == "MINING"
        ]

    def load_survey_data(self, epoch: str = "4.4") -> bool:
        """Load mining probability survey data from the API."""
        try:
            # Load ship ore probabilities by location (simple lookup)
            ship_ore_data = self.get_survey_data("shipOreByGravProb", epoch)
            if ship_ore_data and ship_ore_data.get("data"):
                self.data.ship_ore_probs = ship_ore_data["data"]

            # Load vehicle/ROC ore probabilities
            vehicle_data = self.get_survey_data("vehicleProbs", epoch)
            if vehicle_data and vehicle_data.get("data"):
                self.data.vehicle_ore_probs = vehicle_data["data"]

            # Load bonus maps (deposit spawn multipliers)
            bonus_data = self.get_survey_data("bonusMap", epoch)
            if bonus_data and bonus_data.get("data"):
                self.data.bonus_map = bonus_data["data"]

            bonus_roc_data = self.get_survey_data("bonusMap.roc", epoch)
            if bonus_roc_data and bonus_roc_data.get("data"):
                self.data.bonus_map_roc = bonus_roc_data["data"]

            # Load rock class data for proper ore content calculations
            rock_by_loc = self.get_survey_data("shipRockClassByGravProb", epoch)
            if rock_by_loc and rock_by_loc.get("data"):
                self.data.rock_class_by_location = rock_by_loc["data"]

            ore_by_rock = self.get_survey_data("shipOreByRockClassProb", epoch)
            if ore_by_rock and ore_by_rock.get("data"):
                self.data.ore_by_rock_class = ore_by_rock["data"]

            return self.data.has_survey_data()
        except Exception:
            logger.exception("Failed to load survey data")
            return False

    def find_best_mining_locations(
        self,
        ore_name: str,
        mining_type: str = "ship",
        limit: int = 10,
        system: str = "STANTON",
    ) -> list[dict]:
        """
        Find the best mining locations for a specific ore.

        Calculates expected ore content using:
        Score = Σ (rock_type_prob × ore_prob_in_rock × ore_median_content)

        Args:
            ore_name: The ore to search for (e.g., QUANTANIUM, GOLD)
            mining_type: "ship" for ship mining, "vehicle" for ROC/hand mining
            limit: Maximum number of results to return
            system: Star system (STANTON, PYRO, NYX)

        Returns:
            List of locations sorted by expected ore content (best first)
        """
        ore_upper = ore_name.upper()
        results = []

        # For vehicle/ROC mining, use the simpler probability data
        if mining_type == "vehicle":
            return self._find_best_vehicle_mining_locations(ore_upper, limit)

        # For ship mining, use rock class data for accurate calculation
        if not self.data.has_rock_class_data():
            # Fallback to simple probability if rock class data not loaded
            return self._find_best_mining_locations_simple(ore_upper, limit)

        rock_by_location = self.data.rock_class_by_location or {}
        ore_by_rock = self.data.ore_by_rock_class.get(system, {})
        bonus_map = self.data.bonus_map or {}

        for location, loc_data in rock_by_location.items():
            rock_types = loc_data.get("rockTypes", {})
            total_scans = loc_data.get("scans", 0)

            # Calculate expected ore content across all rock types
            expected_content = 0.0
            contributing_rocks = []

            for rock_type, rock_data in rock_types.items():
                rock_prob = rock_data.get("prob", 0)

                # Get ore data for this rock type
                rock_info = ore_by_rock.get(rock_type)
                if not rock_info:
                    continue
                rock_ore_data = rock_info.get("ores", {})
                if not rock_ore_data or ore_upper not in rock_ore_data:
                    continue

                ore_data = rock_ore_data[ore_upper]
                ore_prob = ore_data.get("prob", 0)
                ore_med_pct = ore_data.get("medPct", 0)

                # Calculate contribution: rock_prob × ore_prob × median_content
                contribution = rock_prob * ore_prob * ore_med_pct
                expected_content += contribution

                if contribution > 0:
                    contributing_rocks.append(
                        {
                            "rock_type": rock_type,
                            "rock_prob": round(rock_prob * 100, 1),
                            "ore_prob": round(ore_prob * 100, 1),
                            "ore_median_pct": round(ore_med_pct * 100, 1),
                            "contribution": round(contribution * 100, 3),
                        }
                    )

            if expected_content <= 0:
                continue

            # Get bonus (deposit spawn multiplier)
            bonus = bonus_map.get(location, 1.0)

            results.append(
                {
                    "location_code": location,
                    "location_name": self._get_location_label(location),
                    "expected_ore_content_pct": round(expected_content * 100, 3),
                    "deposit_spawn_bonus": bonus,
                    "sample_size": total_scans,
                    "contributing_rock_types": sorted(
                        contributing_rocks,
                        key=lambda x: x["contribution"],
                        reverse=True,
                    ),
                }
            )

        # Sort by expected ore content descending
        results.sort(key=lambda x: x["expected_ore_content_pct"], reverse=True)
        return results[:limit]

    def _find_best_mining_locations_simple(
        self, ore_upper: str, limit: int
    ) -> list[dict]:
        """Fallback: find locations using simple probability data."""
        ore_probs = self.data.ship_ore_probs or {}
        results = []

        for location, loc_data in ore_probs.items():
            ores = loc_data.get("ores", {})
            if ore_upper not in ores:
                continue

            ore_data = ores[ore_upper]
            probability = ore_data.get("prob", 0)

            results.append(
                {
                    "location_code": location,
                    "location_name": self._get_location_label(location),
                    "expected_ore_content_pct": round(probability * 100, 1),
                    "note": "Simple probability (rock class data not available)",
                }
            )

        results.sort(key=lambda x: x["expected_ore_content_pct"], reverse=True)
        return results[:limit]

    def _find_best_vehicle_mining_locations(
        self, ore_upper: str, limit: int
    ) -> list[dict]:
        """Find best locations for ROC/hand mining."""
        ore_probs = self.data.vehicle_ore_probs or {}
        bonus_map = self.data.bonus_map_roc or {}
        results = []

        for location, loc_data in ore_probs.items():
            ores = loc_data.get("ores", {})
            if ore_upper not in ores:
                continue

            ore_data = ores[ore_upper]
            probability = ore_data.get("prob", 0)
            finds = ore_data.get("finds", 0)
            median_rocks = ore_data.get("medianRocks", 0)
            bonus = bonus_map.get(location, 1.0)

            results.append(
                {
                    "location_code": location,
                    "location_name": self._get_location_label(location),
                    "probability_pct": round(probability * 100, 1),
                    "deposit_spawn_bonus": bonus,
                    "sample_size": finds,
                    "median_rocks_per_cluster": median_rocks,
                }
            )

        results.sort(key=lambda x: x["probability_pct"], reverse=True)
        return results[:limit]

    def get_ore_probability_at_location(
        self, location_code: str, mining_type: str = "ship"
    ) -> dict:
        """Get all ore probabilities at a specific location."""
        if mining_type == "ship":
            ore_probs = self.data.ship_ore_probs or {}
        else:
            ore_probs = self.data.vehicle_ore_probs or {}

        loc_data = ore_probs.get(location_code, {})
        ores = loc_data.get("ores", {})

        results = []
        for ore_name, ore_data in ores.items():
            results.append(
                {
                    "ore": ore_name,
                    "probability": round(ore_data.get("prob", 0) * 100, 1),
                    "finds": ore_data.get("finds", 0),
                    "median_rocks": ore_data.get("medianRocks", 0),
                }
            )

        # Sort by probability descending
        results.sort(key=lambda x: x["probability"], reverse=True)

        return {
            "location": location_code,
            "total_surveys": loc_data.get("finds", 0),
            "users": loc_data.get("users", 0),
            "ores": results,
        }

    # =========================================================================
    # UEX Price API Integration
    # =========================================================================

    UEX_BASE_URL = "https://api.uexcorp.space/2.0"

    def load_uex_prices(self) -> bool:
        """Load mineral prices from UEX Corp API."""
        try:
            # Fetch commodities to get mineral IDs
            commodities = self._fetch_uex_commodities()
            if not commodities:
                return False

            # Fetch all prices
            prices = self._fetch_uex_prices()
            if not prices:
                return False

            # Process minerals and their prices
            self.data.uex_minerals = {}
            self.data.uex_prices = {}

            # Index minerals by name
            for commodity in commodities:
                if commodity.get("is_mineral") == 1:
                    name = commodity.get("name", "")
                    self.data.uex_minerals[name] = {
                        "id": commodity.get("id"),
                        "code": commodity.get("code"),
                        "name": name,
                        "is_raw": commodity.get("is_raw", 0) == 1,
                    }

            # Find best sell prices for each mineral
            for price_entry in prices:
                commodity_name = price_entry.get("commodity_name", "")
                if commodity_name not in self.data.uex_minerals:
                    continue

                price_sell = price_entry.get("price_sell", 0)
                if not price_sell:
                    continue

                terminal_name = price_entry.get("terminal_name", "Unknown")

                # Track best price per mineral
                if commodity_name not in self.data.uex_prices:
                    self.data.uex_prices[commodity_name] = {
                        "name": commodity_name,
                        "best_price": price_sell,
                        "best_location": terminal_name,
                        "all_prices": [],
                    }

                self.data.uex_prices[commodity_name]["all_prices"].append(
                    {
                        "price": price_sell,
                        "location": terminal_name,
                    }
                )

                if price_sell > self.data.uex_prices[commodity_name]["best_price"]:
                    self.data.uex_prices[commodity_name]["best_price"] = price_sell
                    self.data.uex_prices[commodity_name]["best_location"] = (
                        terminal_name
                    )

            # Sort price lists for each mineral
            for mineral_data in self.data.uex_prices.values():
                mineral_data["all_prices"].sort(key=lambda x: x["price"], reverse=True)
                mineral_data["all_prices"] = mineral_data["all_prices"][
                    :5
                ]  # Keep top 5

            return True
        except Exception:
            logger.exception("Failed to load UEX prices")
            return False

    def _fetch_uex_commodities(self) -> list[dict] | None:
        """Fetch commodity data from UEX API."""
        try:
            response = self.session.get(
                f"{self.UEX_BASE_URL}/commodities",
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "ok":
                return result.get("data", [])
            return None
        except Exception:
            logger.exception("Failed to fetch UEX commodities")
            return None

    def _fetch_uex_prices(self) -> list[dict] | None:
        """Fetch all commodity prices from UEX API."""
        try:
            response = self.session.get(
                f"{self.UEX_BASE_URL}/commodities_prices_all",
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

            if result.get("status") == "ok":
                return result.get("data", [])
            return None
        except Exception:
            logger.exception("Failed to fetch UEX prices")
            return None

    def get_uex_price_for_ore(self, regolith_ore_name: str) -> dict | None:
        """
        Get UEX price for an ore using Regolith naming.

        Args:
            regolith_ore_name: Ore name in Regolith format (e.g., QUANTANIUM)

        Returns:
            Price info dict or None if not found
        """
        if not self.data.has_uex_prices():
            return None

        # Map Regolith name to UEX name
        ore_upper = regolith_ore_name.upper()
        uex_name = REGOLITH_TO_UEX_NAME.get(ore_upper)

        if not uex_name:
            # Try direct name match with title case
            uex_name = ore_upper.title()

        # Check for refined version first (higher value)
        refined_name = f"{uex_name} (refined)"
        if refined_name in self.data.uex_prices:
            return self.data.uex_prices[refined_name]

        # Fall back to raw ore
        if uex_name in self.data.uex_prices:
            return self.data.uex_prices[uex_name]

        return None

    def find_ore_deposit_info(self, ore_name: str, system: str = "STANTON") -> dict:
        """
        Find complete info about where to mine a specific ore.

        Returns:
            - Best deposit type(s) containing the ore
            - Median content percentage
            - Locations where these deposits are found
        """
        ore_upper = ore_name.upper()

        if not self.data.has_rock_class_data():
            return {}

        ore_by_rock = self.data.ore_by_rock_class.get(system, {})
        rock_by_location = self.data.rock_class_by_location or {}

        # Find deposit types containing this ore
        deposit_types = []
        for rock_type, rock_info in ore_by_rock.items():
            if not rock_info:
                continue
            rock_ore_data = rock_info.get("ores", {})
            if not rock_ore_data or ore_upper not in rock_ore_data:
                continue

            ore_data = rock_ore_data[ore_upper]
            ore_prob = ore_data.get("prob", 0)  # Spawn probability (e.g., 8%)
            ore_med_pct = ore_data.get(
                "medPct", 0
            )  # Median content when present (e.g., 32%)

            if ore_med_pct <= 0:
                continue

            # Expected content = spawn probability × median content
            # e.g., 8% × 32% = 2.56%
            expected_content_pct = ore_prob * ore_med_pct * 100

            deposit_types.append(
                {
                    "deposit_type": rock_type,
                    "spawn_probability_pct": round(ore_prob * 100, 1),
                    "median_content_pct": round(ore_med_pct * 100, 1),
                    "expected_content_pct": round(expected_content_pct, 2),
                }
            )

        if not deposit_types:
            return {}

        # Sort by expected content percentage (highest first)
        deposit_types.sort(key=lambda x: x["expected_content_pct"], reverse=True)

        # Take top 3 deposit types for the mineral
        top_3_deposits = deposit_types[:3]

        # Build a lookup for quick access: deposit_type -> expected_content
        deposit_expected = {
            d["deposit_type"]: d["expected_content_pct"]
            / 100  # Convert back to decimal
            for d in top_3_deposits
        }

        # Find best locations by calculating weighted score across top 3 deposit types
        # Score = sum of (deposit_proportion_at_location × deposit_expected_content)
        location_scores = []
        for location, loc_data in rock_by_location.items():
            rock_types = loc_data.get("rockTypes", {})

            weighted_score = 0
            deposit_breakdown = []

            for deposit in top_3_deposits:
                deposit_type = deposit["deposit_type"]
                if deposit_type in rock_types:
                    # Proportion of asteroids at this location that are this deposit type
                    deposit_proportion = rock_types[deposit_type].get("prob", 0)
                    # Expected ore content in this deposit type
                    deposit_expected_content = deposit_expected[deposit_type]

                    # Contribution = proportion × expected content
                    contribution = deposit_proportion * deposit_expected_content
                    weighted_score += contribution

                    if deposit_proportion > 0:
                        deposit_breakdown.append(
                            {
                                "deposit_type": deposit_type,
                                "proportion_pct": round(deposit_proportion * 100, 1),
                                "expected_content_pct": deposit["expected_content_pct"],
                                "contribution_pct": round(contribution * 100, 3),
                            }
                        )

            if weighted_score > 0:
                location_scores.append(
                    {
                        "location_name": self._get_location_label(location),
                        "location_code": location,
                        "weighted_score_pct": round(weighted_score * 100, 3),
                        "deposit_breakdown": deposit_breakdown,
                    }
                )

        # Sort by weighted score (highest first)
        location_scores.sort(key=lambda x: x["weighted_score_pct"], reverse=True)

        # Get the best deposit info for summary
        best_deposit = top_3_deposits[0] if top_3_deposits else {}

        return {
            "ore": ore_upper,
            "best_deposit_type": best_deposit.get("deposit_type", ""),
            "spawn_probability_pct": best_deposit.get("spawn_probability_pct", 0),
            "median_content_pct": best_deposit.get("median_content_pct", 0),
            "expected_content_pct": best_deposit.get("expected_content_pct", 0),
            "top_3_deposit_types": top_3_deposits,
            "top_locations": location_scores[:5],
        }

    def get_all_mineral_prices(self) -> list[dict]:
        """Get all mineral prices from UEX, sorted by value."""
        if not self.data.has_uex_prices():
            return []

        result = []
        for name, price_data in self.data.uex_prices.items():
            result.append(
                {
                    "name": name,
                    "best_price": price_data["best_price"],
                    "best_location": price_data["best_location"],
                }
            )

        result.sort(key=lambda x: x["best_price"], reverse=True)
        return result

    def find_most_valuable_mining_locations(
        self,
        mining_type: str = "ship",
        limit: int = 3,
        system: str = "STANTON",
    ) -> list[dict]:
        """
        Find the most valuable mining locations based on total expected deposit value
        across ALL ores at each location, using REAL rock mass data from surveys.

        Value calculation per Lazarr Bandara's research:
        1. mineral_mass = deposit_mass × medPct × probability
        2. mineral_volume (SCU) = mineral_mass / density (per mineral!)
        3. value = mineral_volume × price

        Args:
            mining_type: "ship" for ship mining, "vehicle" for ROC/hand mining
            limit: Maximum number of results to return (default 3)
            system: Star system (STANTON, PYRO, NYX)

        Returns:
            List of locations sorted by total expected deposit value (best first)
        """
        if not self.data.has_rock_class_data() or not self.data.has_uex_prices():
            return []

        rock_by_location = self.data.rock_class_by_location or {}
        ore_by_rock = self.data.ore_by_rock_class.get(system, {})
        results = []

        for location, loc_data in rock_by_location.items():
            rock_types = loc_data.get("rockTypes", {})
            total_scans = loc_data.get("scans", 0)

            # Calculate expected value for each ore at this location
            ore_breakdown = []
            total_deposit_value = 0.0
            total_expected_scu = 0.0

            # Track deposit type contributions for identifying primary deposit
            deposit_type_values = {}
            deposit_type_masses = {}  # Track median mass per deposit type

            # Get all unique ores that can appear at this location
            all_ores_at_location = set()
            for rock_type in rock_types.keys():
                rock_info = ore_by_rock.get(rock_type)
                if not rock_info:
                    continue
                rock_ore_info = rock_info.get("ores", {})
                if rock_ore_info:
                    all_ores_at_location.update(rock_ore_info.keys())

            # Calculate expected content and value for each ore
            for ore_name in all_ores_at_location:
                if ore_name == "INERTMATERIAL":
                    continue  # Skip inert material - worthless

                best_deposit_for_ore = None
                best_deposit_contribution = 0.0
                ore_total_value = 0.0
                ore_total_scu = 0.0

                # Get mineral density for this ore
                ore_density = MINERAL_DENSITY.get(
                    ore_name.upper(), DEFAULT_MINERAL_DENSITY
                )

                # Get price for this ore
                price_info = self.get_uex_price_for_ore(ore_name)
                ore_price_per_scu = price_info["best_price"] if price_info else 0

                if ore_price_per_scu <= 0:
                    continue

                for rock_type, rock_data in rock_types.items():
                    rock_prob = rock_data.get("prob", 0)
                    rock_info = ore_by_rock.get(rock_type)
                    if not rock_info:
                        continue
                    rock_ore_info = rock_info.get("ores", {})
                    if not rock_ore_info or ore_name not in rock_ore_info:
                        continue

                    ore_data = rock_ore_info[ore_name]
                    ore_prob = ore_data.get("prob", 0)
                    ore_med_pct = ore_data.get("medPct", 0)

                    # Get rock mass for this deposit type
                    mass_data = rock_data.get("mass", {})
                    rock_median_mass = mass_data.get("med", 0)

                    if (
                        rock_prob <= 0
                        or ore_prob <= 0
                        or ore_med_pct <= 0
                        or rock_median_mass <= 0
                    ):
                        continue

                    # Step 1: mineral_mass = deposit_mass × medPct × probability
                    mineral_mass = rock_median_mass * ore_med_pct * rock_prob * ore_prob

                    # Step 2: mineral_volume (SCU) = mineral_mass / density
                    mineral_scu = mineral_mass / ore_density

                    # Step 3: value = mineral_volume × price
                    mineral_value = mineral_scu * ore_price_per_scu

                    ore_total_value += mineral_value
                    ore_total_scu += mineral_scu

                    # Track best deposit type for this ore
                    contribution = rock_prob * ore_prob * ore_med_pct
                    if contribution > best_deposit_contribution:
                        best_deposit_contribution = contribution
                        best_deposit_for_ore = rock_type

                    # Store deposit type mass for later
                    if rock_type not in deposit_type_masses and rock_median_mass > 0:
                        deposit_type_masses[rock_type] = rock_median_mass

                if ore_total_value > 0:
                    ore_breakdown.append(
                        {
                            "ore": ore_name,
                            "deposit_type": best_deposit_for_ore,
                            "density": ore_density,
                            "price_per_scu": ore_price_per_scu,
                            "expected_ore_yield_scu": round(ore_total_scu, 2),
                            "ore_deposit_value_auec": round(ore_total_value, 0),
                        }
                    )
                    total_deposit_value += ore_total_value
                    total_expected_scu += ore_total_scu

                    # Track total value contributed by each deposit type
                    if best_deposit_for_ore:
                        deposit_type_values[best_deposit_for_ore] = (
                            deposit_type_values.get(best_deposit_for_ore, 0)
                            + ore_total_value
                        )

            if total_deposit_value <= 0:
                continue

            # Sort ore breakdown by value contribution
            ore_breakdown.sort(key=lambda x: x["ore_deposit_value_auec"], reverse=True)

            # Determine primary deposit type (highest value contribution)
            primary_deposit_type = None
            primary_deposit_mass = 0
            if deposit_type_values:
                primary_deposit_type = max(
                    deposit_type_values.keys(), key=lambda k: deposit_type_values[k]
                )
                primary_deposit_mass = deposit_type_masses.get(primary_deposit_type, 0)

            # Get primary ore (most valuable)
            primary_ore = ore_breakdown[0]["ore"] if ore_breakdown else None

            results.append(
                {
                    "location_code": location,
                    "location_name": self._get_location_label(location),
                    "primary_deposit_type": primary_deposit_type,
                    "primary_ore": primary_ore,
                    "total_deposit_value_auec": round(total_deposit_value, 0),
                    "expected_yield_scu": round(total_expected_scu, 1),
                    "primary_deposit_mass": primary_deposit_mass,
                    "sample_size": total_scans,
                    "ore_breakdown": ore_breakdown[:5],  # Top 5 contributing ores
                    "total_ore_types": len(ore_breakdown),
                }
            )

        # Sort by total deposit value descending
        results.sort(key=lambda x: x["total_deposit_value_auec"], reverse=True)
        return results[:limit]
