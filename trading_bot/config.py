"""
config.py — API connection & parameter management.

Loads credentials from .env, connects to Binance (testnet or live),
and verifies that the account and BTC/USDT pair are accessible.
"""

from __future__ import annotations

import os
import sys
import logging

import ccxt
from dotenv import load_dotenv

# ── Load .env ────────────────────────────────────────────────────────────────
load_dotenv()

log = logging.getLogger("bot.config")

# ── Trading Parameters ───────────────────────────────────────────────────────
SYMBOL = "BTC/USDT"
TIMEFRAMES = ["1h", "4h", "1d"]
CANDLE_LIMIT = 200            # candles to fetch per timeframe
REFRESH_INTERVAL_MIN = 15     # data refresh every N minutes

# Risk defaults (overridden dynamically by risk.py)
BOOTSTRAP_WIN_RATE = 0.50
BOOTSTRAP_REWARD_RISK = 2.0
MAX_POSITION_FRACTION = 0.20  # 20 % of balance
MIN_POSITION_USDT = 11.0      # Binance minimum
MAX_OPEN_POSITIONS = 1
DAILY_LOSS_FRACTION = 0.05    # 5 % daily loss limit
MIN_CAPITAL_USDT = 50.0       # halt below this

# Retry
MAX_API_RETRIES = 3
BACKOFF_BASE = 2              # exponential backoff multiplier


def get_mode() -> str:
    """Return 'testnet' or 'live' from the MODE env var."""
    mode = os.getenv("MODE", "testnet").strip().lower()
    if mode not in ("testnet", "live"):
        log.warning("Invalid MODE=%r — defaulting to testnet", mode)
        mode = "testnet"
    return mode


def build_exchange() -> ccxt.binance:
    """
    Build and return a configured ccxt.binance instance.
    Testnet uses Binance Spot Testnet URLs.
    """
    mode = get_mode()

    if mode == "testnet":
        api_key = os.getenv("BINANCE_TESTNET_API_KEY", "")
        api_secret = os.getenv("BINANCE_TESTNET_API_SECRET", "")
    else:
        api_key = os.getenv("BINANCE_API_KEY", "")
        api_secret = os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        log.critical(
            "API credentials missing for MODE=%s. "
            "Set them in your .env file (see .env.example).",
            mode,
        )
        sys.exit(1)

    exchange = ccxt.binance(
        {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "spot"},
        }
    )

    if mode == "testnet":
        exchange.set_sandbox_mode(True)
        log.info("🧪  Binance TESTNET mode enabled")
    else:
        log.warning("🔴  Binance LIVE mode — real money at risk!")

    return exchange


def verify_connection(exchange: ccxt.binance) -> dict:
    """
    Verify exchange connectivity:
    1. Fetch account balance
    2. Confirm BTC/USDT market exists
    Returns the balance dict.
    """
    mode = get_mode()
    log.info("Verifying connection (mode=%s)…", mode)

    try:
        balance = exchange.fetch_balance()
    except ccxt.AuthenticationError:
        log.critical("Authentication failed — check your API key/secret.")
        sys.exit(1)
    except ccxt.NetworkError as exc:
        log.critical("Network error: %s", exc)
        sys.exit(1)

    usdt_free = float(balance.get("USDT", {}).get("free", 0))
    btc_free = float(balance.get("BTC", {}).get("free", 0))
    log.info("💰  Balance → USDT: %.4f | BTC: %.8f", usdt_free, btc_free)

    # Confirm market
    exchange.load_markets()
    if SYMBOL not in exchange.markets:
        log.critical("%s not available on this exchange!", SYMBOL)
        sys.exit(1)
    log.info("✅  %s market confirmed", SYMBOL)

    return balance
