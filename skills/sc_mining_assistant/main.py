"""
main.py — WingmanAI skill class for sc_mining_assistant
Author: Mallachi
Version: 2.0.0

Star Citizen mining assistant — provides comprehensive mining data
from game-extracted data files. Replaces the Regolith WingmanAI skill
after Regolith.Rocks shutdown (June 1, 2026).

Data is extracted from Star Citizen's Data.p4k via MinersRefuge and
shipped as JSON files in the data_library/ directory.
"""

import logging
import os
import sys

from api.enums import LogType
from api.interface import WingmanInitializationError
from skills.skill_base import Skill

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

logger = logging.getLogger(__name__)

SKILL_VERSION = "2.0.0"


class SC_MiningAssistant(Skill):
    def __init__(self, config, settings, wingman) -> None:
        super().__init__(config=config, settings=settings, wingman=wingman)
        self._ui_server = None
        self._ui_window = None

    async def validate(self) -> list[WingmanInitializationError]:
        errors = await super().validate()
        return errors

    async def prepare(self) -> None:
        """Start Mining Interface on activation."""
        await super().prepare()

        try:
            from mining_ui.app import MiningServer  # noqa: E402
            from mining_ui.window import MiningWindow  # noqa: E402

            self._ui_server = MiningServer(port=7868)
            self._ui_server.start()
            self._ui_window = MiningWindow(url=self._ui_server.url)
            self.printr.print(
                f"Mining Interface available at {self._ui_server.url}",
                color=LogType.POSITIVE,
                server_only=True,
            )
        except ImportError:
            logger.warning(
                "Mining Interface unavailable — missing dependencies "
                "(pip install fastapi uvicorn)"
            )

    async def unload(self) -> None:
        """Stop Mining Interface."""
        if self._ui_window:
            try:
                self._ui_window.close()
            except OSError:
                logger.debug("Failed to close mining interface window")
            self._ui_window = None
        if self._ui_server:
            try:
                self._ui_server.stop()
            except OSError:
                logger.debug("Failed to stop mining interface server")
            self._ui_server = None
        await super().unload()

    # ------------------------------------------------------------------ #
    # Logging helper
    # ------------------------------------------------------------------ #

    def _log(self, msg: str, *args, level: str = "info") -> None:
        """Log to both Python logger and Wingman printr."""
        formatted = msg % args if args else msg
        getattr(logger, level)(msg, *args)

        color_map = {
            "info": LogType.INFO,
            "warning": LogType.WARNING,
            "error": LogType.ERROR,
        }
        try:
            self.printr.print(
                f"[Mining] {formatted}",
                color=color_map.get(level, LogType.INFO),
                server_only=True,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------ #
    # Tool definitions
    # ------------------------------------------------------------------ #

    def get_tools(self) -> list[tuple[str, dict]]:
        return [
            self._tool_show_mining_interface(),
        ]

    def _tool_show_mining_interface(self):
        return (
            "show_mining_interface",
            {
                "type": "function",
                "function": {
                    "name": "show_mining_interface",
                    "description": (
                        "Open the Mining Interface dashboard in the player's browser. "
                        "You MUST call this tool when the player wants to see, show, open, or display "
                        "anything related to mining interface, mining dashboard, mining HUD, mining module, "
                        "mining data, or mining information. This is the only way to open the browser."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {},
                        "required": [],
                    },
                },
            },
        )

    # ------------------------------------------------------------------ #
    # Tool execution
    # ------------------------------------------------------------------ #

    async def execute_tool(
        self, tool_name: str, parameters: dict[str, any], benchmark=None
    ) -> tuple[str, str]:
        if tool_name == "show_mining_interface":
            return self._execute_show_mining_interface()
        return await super().execute_tool(tool_name, parameters, benchmark)

    def _execute_show_mining_interface(self) -> tuple[str, str]:
        """Open the Mining Interface in the default browser."""
        if not self._ui_window:
            return (
                "Mining Interface not available. Missing dependencies.",
                "",
            )
        self._ui_window.open()
        return (
            f"Mining Interface opened in your browser at {self._ui_server.url}",
            "Opening Mining Interface.",
        )
