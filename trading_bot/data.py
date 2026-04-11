"""
data.py — Multi-timeframe OHLCV data fetching with retry logic.

Fetches BTC/USDT candles on 1h, 4h, and 1d from Binance and
stores them as pandas DataFrames.  Includes exponential-backoff
retry on API failures (3 attempts).
"""

from __future__ import annotations

import time
import logging
from typing import Dict

import ccxt
import pandas as pd

from trading_bot.config import (
    SYMBOL,
    TIMEFRAMES,
    CANDLE_LIMIT,
    MAX_API_RETRIES,
    BACKOFF_BASE,
)

log = logging.getLogger("bot.data")

MIN_CANDLES = {
    "1h": 200,
    "4h": 100,
    "1d": 11
}

# In-memory cache: { "1h": DataFrame, "4h": DataFrame, "1d": DataFrame }
_candle_cache: Dict[str, pd.DataFrame] = {}


def _fetch_ohlcv(exchange: ccxt.binance, timeframe: str) -> pd.DataFrame:
    """
    Fetch OHLCV data for a single timeframe with exponential backoff.
    Returns a DataFrame with columns:
        timestamp, open, high, low, close, volume
    """
    last_exc: Exception | None = None

    for attempt in range(1, MAX_API_RETRIES + 1):
        try:
            raw = exchange.fetch_ohlcv(
                SYMBOL, timeframe=timeframe, limit=CANDLE_LIMIT
            )
            df = pd.DataFrame(
                raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
            )
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            df.set_index("timestamp", inplace=True)

            # Ensure numeric
            for col in ("open", "high", "low", "close", "volume"):
                df[col] = pd.to_numeric(df[col], errors="coerce")

            log.debug(
                "Fetched %d candles for %s [%s]", len(df), SYMBOL, timeframe
            )
            return df

        except (ccxt.NetworkError, ccxt.ExchangeNotAvailable) as exc:
            last_exc = exc
            wait = BACKOFF_BASE ** attempt
            log.warning(
                "Fetch %s attempt %d/%d failed (%s). Retrying in %ds…",
                timeframe,
                attempt,
                MAX_API_RETRIES,
                exc,
                wait,
            )
            time.sleep(wait)

    raise RuntimeError(
        f"Failed to fetch {timeframe} data after {MAX_API_RETRIES} retries: {last_exc}"
    )


def refresh_all(exchange: ccxt.binance) -> Dict[str, pd.DataFrame]:
    """
    Fetch/refresh OHLCV data for ALL configured timeframes.
    Updates the module-level cache and returns it.
    """
    log.info("🔄  Refreshing OHLCV data for %s across %s…", SYMBOL, TIMEFRAMES)

    for tf in TIMEFRAMES:
        _candle_cache[tf] = _fetch_ohlcv(exchange, tf)

    log.info("✅  Data refresh complete")
    return _candle_cache


def get_candles() -> Dict[str, pd.DataFrame]:
    """Return the current in-memory candle cache (read-only reference)."""
    return _candle_cache
