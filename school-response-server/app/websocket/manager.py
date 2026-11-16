"""
app/websocket/manager.py
========================
WebSocket connection manager for live quiz dashboard updates.

Flow:
  Scanner → POST /api/v1/scanner/responses
         → quiz_service.process_scanner_response()
         → ws_manager.broadcast(quiz_session_id, data)
         → Teacher dashboard receives live update
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import defaultdict
from typing import Dict, List, Set

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """
    Manages WebSocket connections grouped by quiz_session_id.
    Thread-safe for concurrent async tasks.
    """

    def __init__(self):
        # quiz_session_id → set of connected WebSockets
        self._connections: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, quiz_session_id: int) -> None:
        await websocket.accept()
        async with self._lock:
            self._connections[quiz_session_id].add(websocket)
        logger.info(f"WS connected: session={quiz_session_id} total={len(self._connections[quiz_session_id])}")

    async def disconnect(self, websocket: WebSocket, quiz_session_id: int) -> None:
        async with self._lock:
            self._connections[quiz_session_id].discard(websocket)
            if not self._connections[quiz_session_id]:
                del self._connections[quiz_session_id]
        logger.info(f"WS disconnected: session={quiz_session_id}")

    async def broadcast(self, quiz_session_id: int, data: dict) -> None:
        """Send data to all clients watching this quiz session."""
        payload = json.dumps(data)
        async with self._lock:
            sockets = list(self._connections.get(quiz_session_id, set()))

        dead: List[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)

        # Clean up dead connections
        if dead:
            async with self._lock:
                for ws in dead:
                    self._connections[quiz_session_id].discard(ws)

    def connection_count(self, quiz_session_id: int) -> int:
        return len(self._connections.get(quiz_session_id, set()))


# Singleton — imported by routes
ws_manager = ConnectionManager()
