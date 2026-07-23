from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import decrypt_secret, encrypt_secret
from app.exchange.base import OrderRequest
from app.exchange.binance import BinanceExchangeAdapter
from app.exchange.simulated import SimulatedExchangeAdapter
from app.models.exchange import ExchangeAccount
from app.repositories.exchange_repository import ExchangeRepository
from app.schemas.exchange import (
    ExchangeAccountOut,
    ExchangeConnectRequest,
    ExchangeSyncOut,
    PlaceOrderOut,
    PlaceOrderRequest,
)


def _to_out(row: ExchangeAccount) -> ExchangeAccountOut:
    return ExchangeAccountOut(
        id=row.id,
        exchange=row.exchange,
        label=row.label,
        key_prefix=row.key_prefix,
        permissions=row.permissions,
        is_active=row.is_active,
        is_testnet=row.is_testnet,
        last_sync_at=row.last_sync_at,
        last_sync_status=row.last_sync_status,
        last_sync_error=row.last_sync_error,
        balances_cache=row.balances_cache or {},
        created_at=row.created_at,
    )


class ExchangeService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = ExchangeRepository(session)

    def _adapter_for(self, row: ExchangeAccount):
        key = decrypt_secret(row.api_key_encrypted)
        secret = decrypt_secret(row.api_secret_encrypted)
        if key.startswith("sim_") or secret.startswith("sim_"):
            return SimulatedExchangeAdapter()
        if row.exchange.lower() == "binance":
            return BinanceExchangeAdapter(key, secret, testnet=row.is_testnet)
        return SimulatedExchangeAdapter()

    async def list_accounts(self, user_id: UUID) -> list[ExchangeAccountOut]:
        rows = await self.repo.list_accounts(user_id)
        return [_to_out(r) for r in rows]

    async def connect(self, user_id: UUID, payload: ExchangeConnectRequest) -> ExchangeAccountOut:
        prefix = payload.api_key[:6] + "..."
        row = ExchangeAccount(
            user_id=user_id,
            exchange=payload.exchange.lower(),
            label=payload.label.strip(),
            api_key_encrypted=encrypt_secret(payload.api_key.strip()),
            api_secret_encrypted=encrypt_secret(payload.api_secret.strip()),
            key_prefix=prefix,
            permissions=payload.permissions,
            is_active=True,
            is_testnet=payload.is_testnet,
            last_sync_status="never",
            balances_cache={},
        )
        await self.repo.add(row)
        # quick ping; on failure keep account but mark error
        try:
            adapter = self._adapter_for(row)
            ok = await adapter.ping()
            row.last_sync_status = "connected" if ok else "ping_failed"
        except Exception as exc:  # noqa: BLE001
            row.last_sync_status = "error"
            row.last_sync_error = str(exc)[:500]
        await self.repo.flush()
        return _to_out(row)

    async def disconnect(self, user_id: UUID, account_id: UUID) -> None:
        row = await self.repo.get(user_id, account_id)
        if row is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exchange account not found")
        row.is_active = False
        await self.repo.flush()

    async def sync(self, user_id: UUID, account_id: UUID | None = None) -> ExchangeSyncOut:
        row = await self.repo.get(user_id, account_id) if account_id else await self.repo.get_active(user_id)
        if row is None:
            # no credentials → simulated sync for desk continuity
            adapter = SimulatedExchangeAdapter()
            balances = await adapter.get_balances()
            return ExchangeSyncOut(account=None, balances=balances, source="simulated")
        try:
            adapter = self._adapter_for(row)
            balances = await adapter.get_balances()
            row.balances_cache = balances
            row.last_sync_at = datetime.now(timezone.utc)
            row.last_sync_status = "ok"
            row.last_sync_error = None
            await self.repo.flush()
            return ExchangeSyncOut(account=_to_out(row), balances=balances, source=adapter.name)
        except Exception as exc:  # noqa: BLE001
            row.last_sync_status = "error"
            row.last_sync_error = str(exc)[:500]
            await self.repo.flush()
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Exchange sync failed: {row.last_sync_error}",
            ) from exc

    async def place_order(self, user_id: UUID, payload: PlaceOrderRequest, account_id: UUID | None = None) -> PlaceOrderOut:
        row = await self.repo.get(user_id, account_id) if account_id else await self.repo.get_active(user_id)
        adapter = self._adapter_for(row) if row else SimulatedExchangeAdapter()
        source = adapter.name
        result = await adapter.place_order(
            OrderRequest(
                symbol=payload.symbol,
                side=payload.side,
                quantity=payload.quantity,
                order_type=payload.order_type,
                price=payload.price,
            )
        )
        return PlaceOrderOut(
            order_id=result.order_id,
            status=result.status,
            symbol=result.symbol,
            side=result.side,
            quantity=result.quantity,
            source=source,
            detail=result.detail,
        )
