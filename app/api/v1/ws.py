from __future__ import annotations

import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from app.core.redis_client import CHANNEL_NOTIFICATIONS, CHANNEL_PRICES, CHANNEL_SYSTEM, get_redis
from app.core.security import safe_decode_token
from app.websocket.manager import manager

router = APIRouter(tags=["WebSocket"])


async def _auth_user_id(token: str | None) -> UUID | None:
    if not token:
        return None
    payload = safe_decode_token(token)
    if payload is None or payload.get("type") != "access":
        return None
    sub = payload.get("sub")
    if not sub:
        return None
    return UUID(sub)


@router.websocket("/ws")
async def websocket_gateway(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    user_id = await _auth_user_id(token)
    if user_id is None:
        await websocket.close(code=4401)
        return

    await manager.connect(websocket, user_id)
    await websocket.send_text(
        json.dumps({"type": "system.connected", "user_id": str(user_id), "channels": ["prices", "notifications", "system"]})
    )

    stop = asyncio.Event()

    async def redis_listener() -> None:
        try:
            r = get_redis()
            pubsub = r.pubsub(ignore_subscribe_messages=True)
            pubsub.subscribe(CHANNEL_PRICES, CHANNEL_NOTIFICATIONS, CHANNEL_SYSTEM)
            while not stop.is_set():
                message = pubsub.get_message(timeout=1.0)
                if not message or message.get("type") != "message":
                    await asyncio.sleep(0.05)
                    continue
                data = message.get("data")
                if not isinstance(data, str):
                    continue
                try:
                    event = json.loads(data)
                except json.JSONDecodeError:
                    continue
                # user-scoped notifications
                if event.get("type") == "notification.created":
                    if event.get("user_id") == str(user_id):
                        await manager.send_user(user_id, event)
                    continue
                # prices / system are global
                await manager.send_user(user_id, event)
        except Exception:  # noqa: BLE001
            # Redis optional in local dev
            pass

    listener_task = asyncio.create_task(redis_listener())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "detail": "invalid json"}))
                continue
            if msg.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif msg.get("type") == "subscribe":
                await websocket.send_text(json.dumps({"type": "subscribed", "channels": msg.get("channels", [])}))
    except WebSocketDisconnect:
        pass
    finally:
        stop.set()
        listener_task.cancel()
        await manager.disconnect(websocket, user_id)
