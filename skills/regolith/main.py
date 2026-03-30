"""
Regolith Skill for Wingman AI.

Provides Star Citizen mining data from Regolith.Rocks API including:
- Ore information and prices
- Refinery locations and bonuses
- Mining locations
- Ship mining capabilities
- Refinery job calculations
"""

import functools
import json
import logging
import os
import sys
import time
from typing import TYPE_CHECKING, Literal

from api.enums import LogType, WingmanInitializationErrorType
from api.interface import SettingsConfig, SkillConfig, WingmanInitializationError
from services.file import get_writable_dir
from skills.skill_base import Skill, tool

if TYPE_CHECKING:
    from wingmen.open_ai_wingman import OpenAiWingman

# Add the current directory to sys.path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from regolith_api import RegolithAPI

logger = logging.getLogger(__name__)


def _requires_data(func):
    """Decorator ensuring Regolith data is loaded before tool execution."""

    @functools.wraps(func)
    async def wrapper(self, *args, **kwargs):
        error = self._ensure_data_loaded()
        if error:
            return error
        return await func(self, *args, **kwargs)

    return wrapper


class Regolith(Skill):
    """Wingman AI Skill for Star Citizen mining data from Regolith.Rocks."""

    def __init__(
        self,
        config: SkillConfig,
        settings: SettingsConfig,
        wingman: "OpenAiWingman",
    ) -> None:
        super().__init__(config=config, settings=settings, wingman=wingman)
        self.api: RegolithAPI | None = None
        self.data_loaded = False
        self.cache_status: str = ""

    def _get_api_key(self) -> str | None:
        """Retrieve the API key fresh from config."""
        errors: list[WingmanInitializationError] = []
        value = self.retrieve_custom_property_value("regolith_api_key", errors)
        if value and value.strip():
            return value.strip()
        return None

    def _init_api(self, api_key: str) -> bool:
        """Create the API client and verify the connection.

        Returns True if successful.
        """
        cache_dir = get_writable_dir("skills/regolith/cache")
        self.api = RegolithAPI(api_key, cache_dir=cache_dir)
        if not self.api.verify_connection():
            self.api = None
            return False
        return True

    async def validate(self) -> list[WingmanInitializationError]:
        errors = await super().validate()

        # Validate the property exists in config
        self.retrieve_custom_property_value(
            "regolith_api_key",
            errors,
            "Get your API key from https://regolith.rocks",
        )

        api_key = self._get_api_key()
        if api_key:
            if not self._init_api(api_key):
                errors.append(
                    WingmanInitializationError(
                        wingman_name=self.wingman.name,
                        message="Failed to connect to Regolith API. Check your API key.",
                        error_type=WingmanInitializationErrorType.INVALID_CONFIG,
                    )
                )
        else:
            # Activate without API — tools will inform the user via _ensure_data_loaded
            logger.warning("Regolith: No API key configured. Mining tools will be unavailable until a key is set.")

        return errors

    async def prepare(self) -> None:
        await super().prepare()

        if self.api and not self.data_loaded:
            # Load data in background (uses cache if available)
            self.threaded_execution(self._load_data)

    async def update_config(self, new_config: SkillConfig) -> None:
        # Capture the old key before super() updates self.config
        old_key = self._get_api_key()
        await super().update_config(new_config)
        new_key = self._get_api_key()

        if new_key and new_key != old_key:
            # API key was just entered or changed — init and start cache build
            if self._init_api(new_key):
                self.data_loaded = False
                self.threaded_execution(self._load_data)

    def _load_data(self) -> None:
        """Load data from cache or API (runs in background thread)."""
        try:
            # Check if cache exists and is valid
            cache_age = self.api.get_cache_age_hours()
            if cache_age is not None and cache_age < 24:
                self.printr.print(
                    f"Loading Regolith data from cache ({cache_age:.1f}h old)...",
                    color=LogType.INFO,
                    server_only=True,
                )
            else:
                self.printr.print(
                    "Building Regolith data cache (this may take a few seconds)...",
                    color=LogType.INFO,
                    server_only=True,
                )

            # Load all data (uses cache if valid, otherwise fetches from API)
            success, status_message = self.api.load_all_data()

            if success:
                self.data_loaded = True
                self.cache_status = status_message
                self.printr.print(
                    f"Regolith data ready. {status_message}",
                    color=LogType.POSITIVE,
                    server_only=True,
                )
            else:
                self.printr.print(
                    f"Failed to load Regolith data: {status_message}",
                    color=LogType.ERROR,
                    server_only=True,
                )

        except Exception:
            logger.exception("Failed to load Regolith data")
            self.printr.print(
                "Failed to load Regolith data. Check logs for details.",
                color=LogType.ERROR,
                server_only=True,
            )

    def _ensure_data_loaded(self, timeout_seconds: float = 30.0) -> str:
        """Check if data is loaded, waiting with timeout if necessary."""
        if not self.api:
            return "Regolith API not initialized. Check your API key."

        # If cache is being built, wait longer and inform the user
        if self.api.is_cache_building():
            return "CACHE_BUILDING: Mining data cache is being built. Please wait a few seconds and try again."

        # Wait for data to load with timeout
        if not self.data_loaded:
            start_time = time.time()
            while not self.data_loaded and (time.time() - start_time) < timeout_seconds:
                # Check if cache building started
                if self.api.is_cache_building():
                    return "CACHE_BUILDING: Mining data cache is being built. Please wait a few seconds and try again."
                time.sleep(0.5)

            if not self.data_loaded:
                return "Mining data is still loading. Please try again in a moment."

        return ""

    # =========================================================================
    # Tools
    # =========================================================================

    @tool(
        description="Clear the mining data cache. Use this if the user asks to clear cache, reset data, or if there are data errors."
    )
    async def clear_cache(self) -> str:
        """Clear the mining data cache completely."""
        if not self.api:
            return "Regolith API not initialized."

        cache_path = self.api._get_cache_path()
        if cache_path and cache_path.exists():
            try:
                cache_path.unlink()
                self.data_loaded = False
                self.printr.print(
                    "Regolith cache cleared.",
                    color=LogType.INFO,
                    server_only=True,
                )
                return "Cache cleared successfully. Data will be reloaded from APIs on next use."
            except Exception as e:
                return f"Failed to clear cache: {e}"
        else:
            return "No cache file found to clear."

    @tool(
        description="Refresh the mining data cache. Use this if the user asks to update or refresh mining data, or if data seems stale."
    )
    async def refresh_cache(self) -> str:
        """Force refresh the mining data cache from the APIs."""
        if not self.api:
            return "Regolith API not initialized. Check your API key."

        self.printr.print(
            "Refreshing Regolith data cache...",
            color=LogType.INFO,
            server_only=True,
        )

        # Run in background to not block
        self.data_loaded = False
        success, status_message = self.api.load_all_data(force_refresh=True)

        if success:
            self.data_loaded = True
            self.cache_status = status_message
            return f"Cache refreshed successfully. {status_message}"
        else:
            return f"Failed to refresh cache: {status_message}"

    @tool(
        description="Get detailed information about a specific ore including density, processing values, and current prices."
    )
    @_requires_data
    async def get_ore_info(self, ore_name: str) -> str:
        """
        Get information about a specific ore.

        Args:
            ore_name: The name of the ore (e.g., Quantanium, Gold, Agricium)
        """
        info = self.api.get_ore_info(ore_name)
        if not info:
            ores = self.api.get_all_ores()
            return (
                f"Ore '{ore_name}' not found. Available ores: {', '.join(sorted(ores))}"
            )

        return json.dumps(info, indent=2)

    @tool(description="List all available ores in Star Citizen with their densities.")
    @_requires_data
    async def list_all_ores(self) -> str:
        """List all available ores."""
        ores = []
        for ore_name, density in sorted(self.api.data.ore_densities.items()):
            ores.append({"name": ore_name, "density": density})

        return json.dumps(ores, indent=2)

    @tool(
        description="Get information about all refinery methods with evaluation of yield, time, and cost. Use this when user asks about refinery methods or which method to use."
    )
    @_requires_data
    async def get_refinery_methods(self) -> str:
        """Get information about all refinery processing methods with evaluation."""
        methods = self.api.get_refinery_methods_info()

        # Add evaluation and sort by yield bonus
        evaluated_methods = []
        for name, data in methods.items():
            yield_bonus = data.get("yield_bonus", 0) or 0
            time_mult = data.get("time_multiplier", 1) or 1
            cost_mult = data.get("cost_multiplier", 1) or 1

            # Evaluate each factor
            yield_rating = (
                "excellent"
                if yield_bonus >= 0.10
                else "good"
                if yield_bonus >= 0.05
                else "standard"
                if yield_bonus >= 0
                else "poor"
            )
            time_rating = (
                "fast"
                if time_mult <= 0.8
                else "moderate"
                if time_mult <= 1.2
                else "slow"
            )
            cost_rating = (
                "cheap"
                if cost_mult <= 0.8
                else "moderate"
                if cost_mult <= 1.2
                else "expensive"
            )

            evaluated_methods.append(
                {
                    "method": name,
                    "yield_bonus_pct": round(yield_bonus * 100, 1),
                    "yield_rating": yield_rating,
                    "time_multiplier": time_mult,
                    "time_rating": time_rating,
                    "cost_multiplier": cost_mult,
                    "cost_rating": cost_rating,
                }
            )

        # Sort by yield bonus descending
        evaluated_methods.sort(key=lambda x: x["yield_bonus_pct"], reverse=True)

        # Add recommendations
        best_yield = evaluated_methods[0]["method"] if evaluated_methods else None
        fastest = (
            min(evaluated_methods, key=lambda x: x["time_multiplier"])["method"]
            if evaluated_methods
            else None
        )
        cheapest = (
            min(evaluated_methods, key=lambda x: x["cost_multiplier"])["method"]
            if evaluated_methods
            else None
        )

        result = {
            "recommendations": {
                "best_yield": best_yield,
                "fastest": fastest,
                "cheapest": cheapest,
            },
            "methods": evaluated_methods,
        }

        return json.dumps(result, indent=2)

    @tool(
        description="Get all refinery locations in Star Citizen with their system and planet."
    )
    @_requires_data
    async def get_refinery_locations(self) -> str:
        """Get all refinery locations."""
        refineries = self.api.get_refineries()
        # Simplify for output
        result = []
        for r in refineries:
            result.append(
                {
                    "name": r["name"],
                    "location": r["name_short"],
                    "system": r["system"],
                    "planet": r["planet"],
                }
            )

        return json.dumps(result, indent=2)

    @tool(
        description="Get refinery bonuses for a specific ore at all refineries, sorted by best bonus."
    )
    @_requires_data
    async def get_refinery_bonuses(self, ore_name: str) -> str:
        """
        Get refinery bonuses for a specific ore.

        Args:
            ore_name: The name of the ore (e.g., Quantanium, Gold)
        """
        bonuses = self.api.get_refinery_bonuses_for_ore(ore_name)
        if not bonuses:
            return f"No refinery bonus data found for ore '{ore_name}'."

        return json.dumps(bonuses, indent=2)

    @tool(
        description="Find the best refinery to process one or more ores based on yield bonus. Use this when the user asks where to refine an ore or combination of ores."
    )
    @_requires_data
    async def find_best_refinery(self, ore_names: str) -> str:
        """
        Find the best refinery for one or more ores.

        Args:
            ore_names: One or more ore names, comma-separated (e.g., "Quantanium" or "Gold, Laranite, Agricium")
        """
        # Parse ore names (handle comma-separated list)
        ores = [o.strip() for o in ore_names.split(",") if o.strip()]

        if not ores:
            return "Please specify at least one ore name."

        if len(ores) == 1:
            # Single ore - simple lookup
            ore_name = ores[0]
            all_bonuses = self.api.get_refinery_bonuses_for_ore(ore_name)[:3]

            if not all_bonuses:
                return f"No refinery data found for ore '{ore_name}'."

            # Format results with summary strings
            formatted_results = []
            for b in all_bonuses:
                formatted_results.append(
                    {
                        "summary": f"{b['refinery_name']} at {b['location']} with +{b['bonus_percent']}% bonus for {ore_name.upper()}",
                        "refinery": b["refinery_name"],
                        "location": b["location"],
                        "bonus_pct": b["bonus_percent"],
                    }
                )

            result = {
                "query_type": "refinery_recommendation",
                "ore": ore_name.upper(),
                "results": formatted_results,
            }
        else:
            # Multiple ores - calculate combined/average bonus per refinery
            refinery_scores = {}

            for ore_name in ores:
                bonuses = self.api.get_refinery_bonuses_for_ore(ore_name)
                for b in bonuses:
                    ref_code = b["refinery_code"]
                    if ref_code not in refinery_scores:
                        refinery_scores[ref_code] = {
                            "refinery_name": b["refinery_name"],
                            "location": b["location"],
                            "ore_bonuses": {},
                            "total_bonus": 0,
                        }
                    refinery_scores[ref_code]["ore_bonuses"][ore_name.upper()] = b[
                        "bonus_percent"
                    ]
                    refinery_scores[ref_code]["total_bonus"] += b["bonus_percent"]

            # Sort by total bonus
            sorted_refineries = sorted(
                refinery_scores.values(), key=lambda x: x["total_bonus"], reverse=True
            )[:3]

            if not sorted_refineries:
                return f"No refinery data found for ores: {', '.join(ores)}"

            ore_list = ", ".join([o.upper() for o in ores])

            # Format results with summary strings
            formatted_results = []
            for r in sorted_refineries:
                formatted_results.append(
                    {
                        "summary": f"{r['refinery_name']} at {r['location']} with combined +{r['total_bonus']:.1f}% bonus for {ore_list}",
                        "refinery": r["refinery_name"],
                        "location": r["location"],
                        "combined_bonus_pct": round(r["total_bonus"], 1),
                        "per_ore_bonus": r["ore_bonuses"],
                    }
                )

            result = {
                "query_type": "refinery_recommendation",
                "ores": [o.upper() for o in ores],
                "results": formatted_results,
            }

        return json.dumps(result, indent=2)

    @tool(
        description="Get all locations where mining is possible (planets, moons, asteroid belts, lagrange points)."
    )
    @_requires_data
    async def get_mining_locations(self) -> str:
        """Get all bodies where mining is possible."""
        bodies = self.api.get_mining_bodies()

        # Group by type
        by_type = {}
        for b in bodies:
            body_type = b["type"]
            if body_type not in by_type:
                by_type[body_type] = []
            by_type[body_type].append(
                {
                    "name": b["label"],
                    "id": b["id"],
                    "parent": b["parent"],
                    "has_rocks": b["has_rocks"],
                    "has_gems": b["has_gems"],
                    "surface_mining": b["is_surface"],
                    "space_mining": b["is_space"],
                }
            )

        return json.dumps(by_type, indent=2)

    @tool(
        description="Get ships that have mining capabilities including cargo and mining hold capacity."
    )
    @_requires_data
    async def get_mining_ships(self) -> str:
        """Get all ships with mining capabilities."""
        ships = self.api.get_mining_ships()
        return json.dumps(ships, indent=2)

    @tool(
        description="Get the ore composition and probabilities at a specific mining location."
    )
    @_requires_data
    async def get_location_ore_composition(
        self,
        location_code: str,
        mining_type: Literal["ship", "vehicle"] = "ship",
    ) -> str:
        """
        Get all ores and their probabilities at a specific location.

        Args:
            location_code: The location code (e.g., YEL, CEL, AARON_HALO, HUR-L1)
            mining_type: "ship" for ship mining, "vehicle" for ROC/hand mining
        """
        if not self.api.data.has_survey_data():
            return "Survey data not loaded. Cannot get ore composition."

        composition = self.api.get_ore_probability_at_location(
            location_code, mining_type
        )

        if not composition.get("ores"):
            return f"No ore data found for location '{location_code}' with {mining_type} mining."

        return json.dumps(composition, indent=2)

    @tool(
        description="Get the best prices for selling raw ore. Shows min, max, and average prices with locations."
    )
    @_requires_data
    async def get_ore_prices(
        self, ore_name: str, ore_type: Literal["raw", "refined"] = "raw"
    ) -> str:
        """
        Get price information for an ore.

        Args:
            ore_name: The name of the ore
            ore_type: Whether to get raw or refined ore prices
        """
        ore_upper = ore_name.upper()
        price_key = "oreRaw" if ore_type == "raw" else "oreRefined"
        prices = self.api.data.max_prices.get(price_key, {}).get(ore_upper)

        if not prices:
            return f"No {ore_type} price data found for '{ore_name}'."

        result = {
            "ore": ore_upper,
            "type": ore_type,
            "min_price": prices.get("min", [None, []])[0],
            "min_locations": prices.get("min", [None, []])[1],
            "max_price": prices.get("max", [None, []])[0],
            "max_locations": prices.get("max", [None, []])[1],
            "average_price": prices.get("avg"),
        }

        return json.dumps(result, indent=2)

    @tool(
        description="Calculate estimated refinery job output based on ore amount, type, and refinery method."
    )
    @_requires_data
    async def calculate_refinery_job(
        self,
        ore_name: str,
        ore_amount_scu: float,
        refinery_method: str,
        refinery_location: str | None = None,
    ) -> str:
        """
        Calculate estimated refinery job results.

        Args:
            ore_name: The name of the ore to refine
            ore_amount_scu: Amount of ore in SCU
            refinery_method: The refinery method to use (e.g., Dinyx Solventation, Cormack)
            refinery_location: Optional refinery code for bonus calculation
        """
        ore_upper = ore_name.upper()
        method_upper = refinery_method.upper().replace(" ", "_")

        # Get ore processing data
        ore_proc = self.api.data.ore_processing.get(ore_upper)
        if not ore_proc:
            return f"No processing data found for ore '{ore_name}'."

        # Get method data
        method_data = self.api.data.refinery_methods.get(method_upper)
        if not method_data:
            methods = list(self.api.data.refinery_methods.keys())
            return f"Unknown refinery method '{refinery_method}'. Available: {', '.join(methods)}"

        # Extract values
        base_yield = ore_proc[0] if len(ore_proc) > 0 else 0.85  # Default 85%
        base_time_factor = ore_proc[1] if len(ore_proc) > 1 else 1.0

        method_yield_bonus = method_data[0] if len(method_data) > 0 else 0
        method_time_mult = method_data[1] if len(method_data) > 1 else 1.0
        method_cost_mult = method_data[2] if len(method_data) > 2 else 1.0

        # Get refinery bonus if location specified
        refinery_bonus = 1.0
        if refinery_location:
            ref_bonuses = self.api.data.refinery_bonuses.get(
                refinery_location.upper(), {}
            )
            refinery_bonus = ref_bonuses.get(ore_upper, 1.0)

        # Calculate
        total_yield = (base_yield + method_yield_bonus) * refinery_bonus
        total_yield = min(total_yield, 1.0)  # Cap at 100%

        refined_amount = ore_amount_scu * total_yield
        estimated_time_hours = base_time_factor * method_time_mult

        # Get price estimate
        refined_prices = self.api.data.max_prices.get("oreRefined", {}).get(
            ore_upper, {}
        )
        avg_price = refined_prices.get("avg", 0) if refined_prices else 0
        max_price = refined_prices.get("max", [0, []])[0] if refined_prices else 0

        result = {
            "input": {
                "ore": ore_upper,
                "amount_scu": ore_amount_scu,
                "method": refinery_method,
                "refinery": refinery_location,
            },
            "yield_calculation": {
                "base_yield": f"{base_yield * 100:.1f}%",
                "method_bonus": f"+{method_yield_bonus * 100:.1f}%",
                "refinery_bonus": f"{(refinery_bonus - 1) * 100:+.1f}%"
                if refinery_bonus != 1.0
                else "none",
                "total_yield": f"{total_yield * 100:.1f}%",
            },
            "output": {
                "refined_amount_scu": round(refined_amount, 2),
                "estimated_time_hours": round(estimated_time_hours, 2),
                "cost_multiplier": method_cost_mult,
            },
            "estimated_value": {
                "at_average_price": round(refined_amount * avg_price)
                if avg_price
                else "N/A",
                "at_max_price": round(refined_amount * max_price)
                if max_price
                else "N/A",
            },
        }

        return json.dumps(result, indent=2)

    @tool(description="Search for locations, refineries, or bodies by name.")
    @_requires_data
    async def search_location(self, search_term: str) -> str:
        """
        Search for a location by name.

        Args:
            search_term: The search term (partial match supported)
        """
        term_lower = search_term.lower()
        results = {
            "refineries": [],
            "bodies": [],
            "tradeports": [],
        }

        # Search refineries
        for r in self.api.data.refineries:
            if (
                term_lower in r.get("name", "").lower()
                or term_lower in r.get("name_short", "").lower()
            ):
                results["refineries"].append(
                    {
                        "name": r["name"],
                        "code": r["code"],
                        "location": r["name_short"],
                        "planet": r["planet"],
                    }
                )

        # Search bodies
        for b in self.api.data.bodies:
            if (
                term_lower in b.get("label", "").lower()
                or term_lower in b.get("id", "").lower()
            ):
                results["bodies"].append(
                    {
                        "name": b["label"],
                        "id": b["id"],
                        "type": b["wellType"],
                        "has_rocks": b.get("hasRocks"),
                        "has_gems": b.get("hasGems"),
                    }
                )

        # Search other tradeports
        for tp in self.api.data.tradeports:
            if not tp.get("refinery"):
                if (
                    term_lower in tp.get("name", "").lower()
                    or term_lower in tp.get("name_short", "").lower()
                ):
                    results["tradeports"].append(
                        {
                            "name": tp["name"],
                            "code": tp["code"],
                            "location": tp["name_short"],
                        }
                    )

        # Filter empty categories
        results = {k: v for k, v in results.items() if v}

        if not results:
            return f"No locations found matching '{search_term}'."

        return json.dumps(results, indent=2)

    @tool(
        description="Find where to mine a SPECIFIC ore by name (e.g., Gold, Quantanium, Agricium). Returns the best deposit type and locations. USE THIS when user asks where to find a specific mineral."
    )
    @_requires_data
    async def find_best_mining_location_by_value(
        self,
        ore_name: str,
        system: Literal["STANTON", "PYRO", "NYX"] = "STANTON",
    ) -> str:
        """
        Find which deposit types contain a specific ore and where to find them.

        Args:
            ore_name: The ore to search for (e.g., Quantanium, Gold)
            system: Star system to search (STANTON, PYRO, NYX)
        """
        if not self.api.data.has_rock_class_data():
            return "Survey data not loaded. Cannot find deposit types."

        # Get complete deposit info including locations
        deposit_info = self.api.find_ore_deposit_info(ore_name, system)

        if not deposit_info:
            return f"No deposit data found for ore '{ore_name}' in {system}."

        # Get price info for context
        price_info = self.api.get_uex_price_for_ore(ore_name)
        price_per_scu = price_info["best_price"] if price_info else 0

        # Get top 3 locations (ranked by weighted score across top 3 deposit types)
        top_locations = deposit_info.get("top_locations", [])[:3]
        top_3_deposits = deposit_info.get("top_3_deposit_types", [])

        # Format results showing weighted score and contributing deposits
        formatted_results = []
        for loc in top_locations:
            location_name = loc.get("location_name", loc.get("location_code"))
            weighted_score = loc.get("weighted_score_pct", 0)
            breakdown = loc.get("deposit_breakdown", [])

            # Build breakdown summary showing deposit proportion AND expected ore content
            # e.g., "C-Type 53.8% (2.56% gold), Q-Type 20% (1.8% gold)"
            breakdown_parts = [
                f"{d['deposit_type']} {d['proportion_pct']}% ({d['expected_content_pct']}% {deposit_info['ore'].lower()})"
                for d in breakdown[:3]
            ]
            breakdown_str = ", ".join(breakdown_parts) if breakdown_parts else "N/A"

            formatted_results.append(
                {
                    "summary": f"{deposit_info['ore']} at {location_name}: {weighted_score}% weighted score - {breakdown_str}",
                    "mineral": deposit_info["ore"],
                    "price_per_scu": price_per_scu,
                    "location": location_name,
                    "weighted_score_pct": weighted_score,
                    "deposit_breakdown": breakdown,
                }
            )

        result = {
            "query_type": "specific_mineral",
            "mineral": deposit_info["ore"],
            "price_per_scu": price_per_scu,
            "best_sell_location": price_info["best_location"] if price_info else "N/A",
            "system": system,
            "top_3_deposit_types": top_3_deposits,
            "results": formatted_results[:3],
        }

        return json.dumps(result, indent=2)

    @tool(
        description="Find the BEST mining locations overall based on TOTAL expected deposit value of ALL ores at each location. Uses REAL rock size data from surveys. Use this when the user asks 'where should I go mining today?' or wants to know the most profitable locations overall."
    )
    @_requires_data
    async def find_most_valuable_locations(
        self,
        mining_type: Literal["ship", "vehicle"] = "ship",
        limit: int = 3,
        system: Literal["STANTON", "PYRO", "NYX"] = "STANTON",
    ) -> str:
        """
        Find the most valuable mining locations based on total expected deposit value
        of ALL ores combined at each location, using real rock mass data from surveys.

        Each deposit/asteroid contains multiple minerals. This calculates:
        Deposit Value = sum (ore_price x ore_content_pct x rock_size_scu) for ALL ores
        Rock size is calculated from actual survey data (median mass / 50 = SCU).

        Args:
            mining_type: "ship" for ship mining, "vehicle" for ROC/hand mining
            limit: Number of results to return (default 3)
            system: Star system to search (STANTON, PYRO, NYX)
        """
        if not self.api.data.has_survey_data():
            return "Survey data not loaded. Cannot calculate location values."

        if not self.api.data.has_uex_prices():
            return "UEX price data not loaded. Cannot calculate values."

        locations = self.api.find_most_valuable_mining_locations(
            mining_type, limit, system
        )

        if not locations:
            return (
                f"No mining location data found for {mining_type} mining in {system}."
            )

        # Format recommendations in the specified format:
        # "Deposit A at location B, valued at C aUEC, expected yield D SCU"
        formatted_locations = []
        for loc in locations:
            deposit_type = loc.get("primary_deposit_type", "Mixed")
            location_name = loc.get("location_name", loc.get("location_code"))
            value = loc.get("total_deposit_value_auec", 0)
            expected_scu = loc.get("expected_yield_scu", 0)

            formatted_locations.append(
                {
                    "summary": f"{deposit_type} deposit at {location_name}, valued at {value:,.0f} aUEC, expected yield {expected_scu:.1f} SCU",
                    "deposit_type": deposit_type,
                    "location": location_name,
                    "value_auec": value,
                    "expected_yield_scu": expected_scu,
                    "primary_ore": loc.get("primary_ore"),
                    "ore_breakdown": loc.get("ore_breakdown", []),
                }
            )

        result = {
            "query_type": "best_mining_locations",
            "mining_type": mining_type,
            "system": system,
            "results": formatted_locations,
        }

        return json.dumps(result, indent=2)

    @tool(
        description="Get current UEX market prices for all minerals, sorted by value. Use this to see which ores are most valuable."
    )
    @_requires_data
    async def get_mineral_prices(self) -> str:
        """Get all mineral prices from UEX Corp, sorted by value."""
        if not self.api.data.has_uex_prices():
            return "UEX price data not loaded. Cannot get mineral prices."

        prices = self.api.get_all_mineral_prices()

        if not prices:
            return "No mineral price data available."

        # Format for readability
        result = {
            "source": "UEX Corp",
            "note": "Prices show best sell location for each mineral",
            "minerals": prices,
        }

        return json.dumps(result, indent=2)

    @tool(
        description="Get current UEX market price for a specific ore. Shows best sell price and location."
    )
    @_requires_data
    async def get_ore_market_price(self, ore_name: str) -> str:
        """
        Get UEX market price for a specific ore.

        Args:
            ore_name: The ore name (e.g., Quantanium, Gold, Hadanite)
        """
        if not self.api.data.has_uex_prices():
            return "UEX price data not loaded."

        price_info = self.api.get_uex_price_for_ore(ore_name)

        if not price_info:
            return f"No UEX price data found for '{ore_name}'."

        result = {
            "ore": ore_name.upper(),
            "best_price_per_scu": price_info["best_price"],
            "best_sell_location": price_info["best_location"],
            "top_sell_locations": price_info.get("all_prices", []),
            "source": "UEX Corp",
        }

        return json.dumps(result, indent=2)

    @tool(
        description="Debug tool to inspect Regolith API schema and available data fields. Use this to see what data is available from the API."
    )
    async def debug_inspect_api(
        self,
        inspect_type: Literal[
            "schema", "survey_sample", "rock_class_sample"
        ] = "schema",
    ) -> str:
        """
        Inspect the Regolith API to see available data fields.

        Args:
            inspect_type: What to inspect - "schema" for GraphQL schema, "survey_sample" for survey data structure, "rock_class_sample" for rock class data
        """
        if not self.api:
            return "Regolith API not initialized."

        if inspect_type == "schema":
            schema = self.api.introspect_schema()
            if schema:
                return json.dumps(schema, indent=2)
            return "Failed to introspect schema."

        elif inspect_type == "survey_sample":
            # Get a sample of shipOreByRockClassProb to see its structure
            sample = self.api.get_survey_data_sample("shipOreByRockClassProb", "4.4")
            if sample and sample.get("data"):
                # Get first entry to show structure
                data = sample["data"]
                if isinstance(data, dict):
                    # Get first system (e.g., STANTON)
                    for system, system_data in data.items():
                        if isinstance(system_data, dict):
                            # Get first rock class
                            for rock_class, rock_data in system_data.items():
                                return json.dumps(
                                    {
                                        "system": system,
                                        "rock_class": rock_class,
                                        "sample_data": rock_data,
                                        "all_rock_classes": list(system_data.keys())[
                                            :10
                                        ],
                                    },
                                    indent=2,
                                )
            return "No survey data available."

        elif inspect_type == "rock_class_sample":
            # Get shipRockClassByGravProb to see location/rock data
            sample = self.api.get_survey_data_sample("shipRockClassByGravProb", "4.4")
            if sample and sample.get("data"):
                data = sample["data"]
                if isinstance(data, dict):
                    for location, loc_data in data.items():
                        return json.dumps(
                            {
                                "location": location,
                                "sample_data": loc_data,
                                "all_locations": list(data.keys())[:10],
                            },
                            indent=2,
                        )
            return "No rock class data available."

        return "Unknown inspect type."
