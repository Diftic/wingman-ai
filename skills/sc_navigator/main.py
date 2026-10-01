"""
Star Citizen Navigator skill for Wingman AI.
Provides route optimization, distance lookups, and location search.
"""

import json
import os
import sys
from typing import TYPE_CHECKING

from api.interface import SettingsConfig, SkillConfig
from skills.skill_base import Skill, tool

# Add skill directory to sys.path for local imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from sc_nav_route_optimizer import AMBIGUOUS, MATCHED, RouteOptimizer

if TYPE_CHECKING:
    from wingmen.open_ai_wingman import OpenAiWingman


class SC_Navigator(Skill):
    # Versions mirror the Star Citizen patch this skill is qualified against.
    # Within-patch updates append a dotted suffix (4.8.0.2, 4.8.0.3, ...).
    # See skills/Versioning.md.
    VERSION = "4.9.0.0"
    SC_TARGET_VERSION = "4.9.0"

    def __init__(
        self,
        config: SkillConfig,
        settings: SettingsConfig,
        wingman: "OpenAiWingman",
    ) -> None:
        super().__init__(config=config, settings=settings, wingman=wingman)
        self._optimizer: RouteOptimizer | None = None

    async def validate(self) -> list:
        errors = await super().validate()
        try:
            self._optimizer = RouteOptimizer()
        except Exception as e:
            from api.interface import WingmanInitializationError
            errors.append(
                WingmanInitializationError(
                    wingman_name=self.wingman.name,
                    message=f"SC_Navigator: Failed to load location data: {e}",
                    error_type="sc_navigator_data_load",
                )
            )
        return errors

    def _resolve_or_error(self, name: str):
        """Resolve a spoken name to a location or a JSON error payload.

        Returns a (location, None) tuple on a clean match, or (None, error)
        where error is a JSON string the LLM can relay: an ambiguous name
        lists the candidate display keys and asks the player to pick a system,
        an unknown name reports it plainly.
        """
        result = self._optimizer.resolve_location(name)
        if result.status == MATCHED and result.location is not None:
            return result.location, None
        if result.status == AMBIGUOUS:
            return None, json.dumps(
                {
                    "error": f"Ambiguous location: '{name}'",
                    "candidates": result.candidates,
                    "hint": "Ask the player which one they mean (specify the system).",
                }
            )
        return None, json.dumps({"error": f"Unknown location: '{name}'"})

    @tool(
        description="Find the optimal visit order for multiple Star Citizen locations. "
        "Plans a one-way route from a start point through all waypoints in the shortest order."
    )
    def plan_route(
        self,
        waypoints: list[str],
        start_location: str = "",
        end_location: str = "",
        return_to_start: bool = False,
    ) -> str:
        """
        Find the optimal visit order for multiple locations.

        Args:
            waypoints: List of location names to visit.
            start_location: Starting location (optional). If empty, the optimizer
                evaluates every waypoint as a potential start (heuristic path).
            end_location: Force the route to end at this location (optional).
            return_to_start: Whether the route should loop back to the starting location.
        """
        if not self._optimizer:
            return json.dumps({"error": "Navigator not initialized. Check location data."})
        result = self._optimizer.optimize_route(
            waypoints=waypoints,
            start_location=start_location,
            end_location=end_location,
            return_to_start=return_to_start,
        )
        return json.dumps(result, indent=2)

    @tool(
        description="Get the travel distance between two Star Citizen locations. "
        "Works for same-system and cross-system routes (via jump point gateways)."
    )
    def get_distance(self, from_location: str, to_location: str) -> str:
        """
        Look up the distance between two locations.

        Args:
            from_location: Origin location name.
            to_location: Destination location name.
        """
        if not self._optimizer:
            return json.dumps({"error": "Navigator not initialized. Check location data."})

        origin, origin_err = self._resolve_or_error(from_location)
        if origin_err is not None:
            return origin_err
        destination, dest_err = self._resolve_or_error(to_location)
        if dest_err is not None:
            return dest_err

        a = origin.display_key
        b = destination.display_key
        dist, via = self._optimizer.get_distance(a, b)
        sys_a = origin.system
        sys_b = destination.system
        is_cross = sys_a != sys_b
        result = {
            "from": a,
            "to": b,
            "distance_gm": round(dist, 3) if dist is not None else None,
            "from_system": sys_a,
            "to_system": sys_b,
            "cross_system": is_cross,
        }
        if via:
            result["via_gateways"] = via
        if dist is None:
            result["error"] = "No route found between these locations"
        return json.dumps(result, indent=2)

    @tool(
        description="Search for Star Citizen location names by partial match. "
        "Use this to verify or resolve ambiguous location names."
    )
    def find_location(self, query: str, system: str = "") -> str:
        """
        Search for locations matching a query string.

        Args:
            query: Search string (partial name match, case-insensitive).
            system: Optional system filter (e.g. 'Stanton', 'Pyro', 'Nyx').
        """
        if not self._optimizer:
            return json.dumps({"error": "Navigator not initialized. Check location data."})
        results = self._optimizer.find_locations(query, system)
        if not results:
            return json.dumps({"matches": [], "message": f"No locations found matching '{query}'"})
        return json.dumps({"matches": results[:20], "total": len(results)})
