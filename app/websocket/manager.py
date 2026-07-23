from __future__ import annotations

import asyncio
import json
from collections import defaultdict
from typing import Any
from uuid import UUID

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, user_id: UUID) -> None:
        await websocket.accept()
        async with self._lock:
            self._rooms[str(user_id)].add(websocket)

    async def disconnect(self, websocket: WebSocket, user_id: UUID) -> None:
        async with self._lock:
            room = self._rooms.get(str(user_id))
            if not room:
                return
            room.discard(websocket)
            if not room:
                self._rooms.pop(str(user_id), None)

    async def send_user(self, user_id: str | UUID, event: dict[str, Any]) -> None:
        payload = json.dumps(event)
        async with self._lock:
            sockets = list(self._rooms.get(str(user_id), set()))
        dead: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            await self.disconnect(ws, UUID(str(user_id)))

    async def broadcast(self, event: dict[str, Any]) -> None:
        payload = json.dumps(event)
        async with self._lock:
            all_sockets = [ws for room in self._rooms.values() for ws in room]
        for ws in all_sockets:
            try:
                await ws.send_text(payload)
            except Exception:  # noqa: BLE001
                pass


manager = ConnectionManager()
