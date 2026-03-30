"""
SC Mining Assistant — Mining Interface Window

Opens the mining interface dashboard in the user's default browser.

Author: Mallachi
"""

from __future__ import annotations

import logging
import webbrowser

logger = logging.getLogger(__name__)


class MiningWindow:
    """Manages the mining interface browser tab."""

    def __init__(self, url: str = "http://127.0.0.1:7868") -> None:
        self._url = url
        self._opened = False

    def open(self) -> None:
        """Open the mining interface in the default browser."""
        webbrowser.open(self._url)
        self._opened = True
        logger.info("Mining interface opened in default browser")

    def close(self) -> None:
        """Mark the window as closed (browser tab cannot be closed programmatically)."""
        self._opened = False
        logger.info("Mining interface marked as closed")

    @property
    def is_open(self) -> bool:
        """Whether the interface has been opened."""
        return self._opened
