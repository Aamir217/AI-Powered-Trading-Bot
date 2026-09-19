import logging
from typing import Optional

from app.config import settings

logger = logging.getLogger("metaapi_broker")

_connection = None


async def _get_connection():
    """Lazily connect to the MetaApi RPC connection for the configured account."""
    global _connection
    if _connection is not None:
        return _connection

    # Imported lazily so the package is only required when DRY_RUN is false.
    from metaapi_cloud_sdk import MetaApi

    api = MetaApi(settings.metaapi_token)
    account = await api.metatrader_account_api.get_account(settings.metaapi_account_id)
    await account.wait_connected()
    connection = account.get_rpc_connection()
    await connection.connect()
    await connection.wait_synchronized()
    _connection = connection
    return _connection


async def open_buy(symbol: str, volume: float) -> dict:
    conn = await _get_connection()
    result = await conn.create_market_buy_order(symbol, volume)
    logger.info("Opened BUY %s lot %s -> %s", volume, symbol, result)
    return result


async def open_sell(symbol: str, volume: float) -> dict:
    conn = await _get_connection()
    result = await conn.create_market_sell_order(symbol, volume)
    logger.info("Opened SELL %s lot %s -> %s", volume, symbol, result)
    return result


async def get_position(position_id: str) -> Optional[dict]:
    conn = await _get_connection()
    try:
        return await conn.get_position(position_id)
    except Exception:
        # MetaApi raises when the position no longer exists (e.g. already closed).
        return None


async def close_position(position_id: str) -> dict:
    conn = await _get_connection()
    result = await conn.close_position(position_id)
    logger.info("Closed position %s -> %s", position_id, result)
    return result
