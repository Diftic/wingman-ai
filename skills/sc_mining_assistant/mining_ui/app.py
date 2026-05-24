"""
SC Mining Assistant — Mining Interface API Server

FastAPI server for the mining interface dashboard.
Runs as a background thread within the Wingman AI skill.

Author: Mallachi
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)

_STATIC_DIR = Path(__file__).parent / "static"


class MiningServer:
    """FastAPI server for the mining interface dashboard."""

    def __init__(self, port: int = 7868) -> None:
        self._port = port
        self._thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None
        self._app = self._create_app()

    def _create_app(self) -> FastAPI:
        """Build the FastAPI application with all routes."""
        app = FastAPI(title="SC Mining Interface", docs_url=None, redoc_url=None)

        # -------------------------------------------------------------- #
        # Static files
        # -------------------------------------------------------------- #

        @app.get("/", response_class=HTMLResponse)
        async def index():
            return _STATIC_DIR.joinpath("index.html").read_text(encoding="utf-8")

        @app.get("/static/{filename:path}")
        async def static_file(filename: str):
            file_path = _STATIC_DIR / filename
            if not file_path.exists():
                return JSONResponse({"error": "Not found"}, status_code=404)
            content = file_path.read_text(encoding="utf-8")
            if filename.endswith(".css"):
                media_type = "text/css"
            elif filename.endswith(".js"):
                media_type = "application/javascript"
            else:
                media_type = "text/plain"
            return HTMLResponse(
                content=content,
                media_type=media_type,
                headers={"Cache-Control": "no-cache"},
            )

        return app

    # ------------------------------------------------------------------ #
    # Server lifecycle
    # ------------------------------------------------------------------ #

    def start(self) -> None:
        """Start the server in a background thread."""
        if self._thread and self._thread.is_alive():
            return

        config = uvicorn.Config(
            self._app,
            host="0.0.0.0",
            port=self._port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)
        self._thread = threading.Thread(
            target=self._server.run,
            name="sc-mining-ui",
            daemon=True,
        )
        self._thread.start()
        logger.info("Mining Interface server started on port %d", self._port)

    def stop(self) -> None:
        """Stop the server."""
        if self._server:
            self._server.should_exit = True
            self._server = None
        self._thread = None
        logger.info("Mining Interface server stopped")

    @property
    def url(self) -> str:
        """Base URL for local browser access."""
        return f"http://127.0.0.1:{self._port}"

    @property
    def is_running(self) -> bool:
        """Whether the server thread is alive."""
        return self._thread is not None and self._thread.is_alive()
