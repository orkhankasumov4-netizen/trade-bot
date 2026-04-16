"""
logger.py — Console output & CSV trade logging.

• Rich console dashboard every cycle
• CSV append for every completed trade
• Separate error log file (errors.log) with full tracebacks
"""

from __future__ import annotations

import csv
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Dict, Optional

import numpy as np
import pandas as pd

from backend.config import SYMBOL

log = logging.getLogger("bot.logger")

# ── Paths ────────────────────────────────────────────────────────────────────
TRADE_CSV = "trades.csv"
ERROR_LOG = "errors.log"

CSV_HEADERS = [
    "timestamp", "side", "entry_price", "exit_price",
    "size_btc", "size_usdt", "pnl_usdt", "pnl_pct",
    "hold_hours", "exit_reason", "signal_score",
    "regime_1h", "regime_4h", "regime_1d",
    "rsi_1h", "rsi_4h", "rsi_1d",
]


def setup_logging():
    """
    Configure root logger with console + error-file handlers.
    Call once at startup.
    """
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)

    # Console handler (INFO+)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(ch)

    # Error file handler (ERROR+)
    fh = logging.FileHandler(ERROR_LOG, mode="a")
    fh.setLevel(logging.ERROR)
    fh.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s — %(message)s\n%(exc_info)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))
    root.addHandler(fh)

    log.info("Logging initialised (console=INFO, file=%s=ERROR)", ERROR_LOG)


def _ensure_csv_header():
    """Create the CSV file with headers if it doesn't exist."""
    if not os.path.exists(TRADE_CSV):
        with open(TRADE_CSV, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADERS)


def log_trade(
    trade: dict,
    signal_score: int = 0,
    regimes: Optional[Dict[str, object]] = None,
    candles: Optional[Dict[str, pd.DataFrame]] = None,
):
    """Append one completed trade row to trades.csv."""
    _ensure_csv_header()

    # Extract RSI values from candles
    def _rsi(tf: str) -> float:
        if candles and tf in candles and len(candles[tf]) > 0:
            v = candles[tf].iloc[-1].get("rsi", np.nan)
            return round(float(v), 2) if not np.isnan(v) else 0.0
        return 0.0

    def _regime(tf: str) -> str:
        if regimes and tf in regimes:
            return str(regimes[tf].value) if hasattr(regimes[tf], "value") else str(regimes[tf])
        return ""

    row = [
        datetime.now(timezone.utc).isoformat(),
        trade.get("side", ""),
        trade.get("entry_price", 0),
        trade.get("exit_price", 0),
        trade.get("size_btc", 0),
        trade.get("size_usdt", 0),
        trade.get("pnl_usdt", 0),
        trade.get("pnl_pct", 0),
        trade.get("hold_hours", 0),
        trade.get("exit_reason", ""),
        signal_score,
        _regime("1h"),
        _regime("4h"),
        _regime("1d"),
        _rsi("1h"),
        _rsi("4h"),
        _rsi("1d"),
    ]

    with open(TRADE_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(row)

    log.info("📝  Trade logged to %s", TRADE_CSV)


def print_dashboard(
    current_price: float,
    regime_str: str,
    candles: Optional[Dict[str, pd.DataFrame]],
    signal_action: str,
    signal_score: int,
    position: object,
    balance: float,
    start_balance: float,
    daily_pnl: float,
    daily_limit: float,
    kelly_frac: float,
    win_rate_pct: float,
    max_dd_pct: float,
    sharpe: float,
    avg_hold: float,
    trade_count: int,
):
    """Print the rich console dashboard."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def _rsi(tf):
        if candles and tf in candles and len(candles[tf]) > 0:
            v = candles[tf].iloc[-1].get("rsi", np.nan)
            return f"{v:.1f}" if not np.isnan(v) else "N/A"
        return "N/A"

    def _bb_pos(tf):
        if candles and tf in candles and len(candles[tf]) > 0:
            pct = candles[tf].iloc[-1].get("bb_pct", np.nan)
            if np.isnan(pct):
                return "N/A"
            if pct < 0.2:
                return "Lower"
            elif pct > 0.8:
                return "Upper"
            return "Mid"
        return "N/A"

    total_return = ((balance - start_balance) / start_balance * 100) if start_balance > 0 else 0

    print()
    print("═" * 70)
    print(f"  [{now}]  {SYMBOL}: ${current_price:,.2f}  |  Regime: {regime_str}")
    print(f"  1h: RSI={_rsi('1h')} BB={_bb_pos('1h')}  |  "
          f"4h: RSI={_rsi('4h')} BB={_bb_pos('4h')}  |  "
          f"1d: RSI={_rsi('1d')} BB={_bb_pos('1d')}")

    if signal_action == "BUY":
        print(f"  📈 Signal Score: {signal_score}/12 → BUY TRIGGERED")
    elif signal_action == "SELL":
        print(f"  📉 Signal → SELL TRIGGERED")
    else:
        print(f"  ⏸  Signal Score: {signal_score}/12 → HOLD")

    # Position info
    pos = position
    if hasattr(pos, "is_open") and pos.is_open:
        open_pnl = (current_price - pos.entry_price) * pos.size_btc
        print(f"  Position: {pos.size_btc:.5f} BTC | Entry: ${pos.entry_price:,.2f} "
              f"| SL: ${pos.stop_loss:,.2f} | TP: ${pos.take_profit:,.2f}")
        print(f"  Open PnL: ${open_pnl:,.2f}")
    else:
        print("  Position: NONE")

    print(f"  Portfolio: ${start_balance:,.2f} → ${balance:,.2f} | "
          f"Return: {total_return:+.2f}%")
    print("─" * 70)
    print(f"  Win Rate: {win_rate_pct:.1f}% (last 20) | "
          f"Kelly: {kelly_frac:.4f} | Sharpe: {sharpe:.2f}")
    print(f"  Max DD: {max_dd_pct:.2f}% | "
          f"Avg Hold: {avg_hold:.1f}h | Trades: {trade_count}")
    print(f"  Today PnL: ${daily_pnl:,.2f} / Limit: -${daily_limit:,.2f}")
    print("═" * 70)
    print()
