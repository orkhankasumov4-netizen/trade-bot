#!/usr/bin/env python3
"""
main.py — BTC/USDT Trading Bot entry point.

Usage:
    python main.py                  # default: testnet mode
    python main.py --mode testnet   # explicit testnet
    python main.py --mode live      # ⚠️  real money
    python main.py --paper          # paper-trade (no real orders)

Loop:
    1. Fetch/refresh OHLCV data every 15 min
    2. Compute indicators on 3 timeframes
    3. Detect market regime
    4. Generate BUY / SELL / HOLD signal
    5. Execute orders (or simulate in paper mode)
    6. Print dashboard + log trades
"""

from __future__ import annotations

import argparse
import os
import signal
import sys
import time
import logging

import schedule

# ── Project imports ──────────────────────────────────────────────────────────
from trading_bot.logger import setup_logging, print_dashboard, log_trade
from trading_bot.config import (
    build_exchange,
    verify_connection,
    get_mode,
    REFRESH_INTERVAL_MIN,
    SYMBOL,
)
from trading_bot.data import refresh_all, get_candles, MIN_CANDLES
from trading_bot.indicators import compute_all
from trading_bot.strategy import (
    generate_signal,
    detect_regime,
    overall_regime,
    calc_stop_loss,
    calc_take_profit,
)
from trading_bot.risk import (
    position_size_usdt,
    check_safety,
    record_trade,
    kelly_fraction,
    win_rate,
    max_drawdown,
    sharpe_ratio,
    avg_hold_hours,
    get_trade_count,
    is_halted,
    halt_reason,
    get_daily_pnl,
    get_daily_limit,
)
from trading_bot.executor import (
    init as executor_init,
    open_position,
    close_position,
    get_position,
    is_position_open,
    should_halt_on_api_errors,
)

log = logging.getLogger("bot.main")

# ── Global state ─────────────────────────────────────────────────────────────
_exchange = None
_start_balance = 0.0
_running = True


def parse_args():
    parser = argparse.ArgumentParser(description="BTC/USDT Trading Bot — Binance")
    parser.add_argument(
        "--mode",
        choices=["testnet", "live"],
        default=None,
        help="Override MODE env var (testnet|live)",
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="Paper-trade mode — simulate orders without real execution",
    )
    return parser.parse_args()


def _sigint_handler(signum, frame):
    """Graceful shutdown on Ctrl+C — do NOT close positions."""
    global _running
    log.info("\n⚠️  Ctrl+C received — shutting down gracefully…")
    log.info("Open positions are LEFT OPEN (manual management required)")

    pos = get_position()
    if pos.is_open:
        log.info(
            "📌  Active position: %.5f BTC | Entry $%.2f | SL $%.2f | TP $%.2f",
            pos.size_btc, pos.entry_price, pos.stop_loss, pos.take_profit,
        )

    _running = False


def _get_balance() -> float:
    """Fetch current USDT balance."""
    try:
        bal = _exchange.fetch_balance()
        return float(bal.get("USDT", {}).get("free", 0))
    except Exception as exc:
        log.error("Failed to fetch balance: %s", exc)
        return 0.0


# ── Main trading cycle ──────────────────────────────────────────────────────

def trading_cycle():
    """One full analysis + decision + execution cycle."""
    global _exchange

    if not _running:
        return

    # Safety halt checks
    if is_halted():
        log.critical("🛑  Bot is HALTED: %s — manual restart required", halt_reason())
        return

    if should_halt_on_api_errors():
        log.critical("🛑  Too many API errors — manual restart required")
        return

    # 1. Refresh data
    try:
        candles = refresh_all(_exchange)
    except RuntimeError as exc:
        log.error("Data refresh failed: %s", exc)
        return

    # 2. Compute indicators
    compute_all(candles)

    # 3. Detect regime
    regimes = detect_regime(candles)
    regime = overall_regime(regimes)

    # 4. Get current balance & run safety checks
    balance = _get_balance()
    open_count = 1 if is_position_open() else 0
    safe = check_safety(balance, open_count)

    # 5. Generate signal
    pos = get_position()
    sig = generate_signal(
        candles,
        position_open=pos.is_open,
        entry_price=pos.entry_price,
    )

    # 6. Execute
    if sig.action == "BUY" and safe and not pos.is_open:
        size = position_size_usdt(balance)
        if size > 0:
            sl = calc_stop_loss(sig.current_price, sig.atr)
            tp = calc_take_profit(sig.current_price, sig.atr)
            open_position(_exchange, "BUY", size, sig.current_price, sl, tp)

    elif sig.action == "SELL" and pos.is_open:
        reason = "; ".join(sig.reasons) if sig.reasons else "Signal SELL"
        trade = close_position(_exchange, sig.current_price, reason)
        if trade:
            record_trade(trade["pnl_usdt"])
            log_trade(
                trade,
                signal_score=sig.score,
                regimes=sig.regimes,
                candles=candles,
            )

    # 7. Dashboard
    pos = get_position()  # re-fetch after potential changes
    print_dashboard(
        current_price=sig.current_price,
        regime_str=regime.value,
        candles=candles,
        signal_action=sig.action,
        signal_score=sig.score,
        position=pos,
        balance=balance,
        start_balance=_start_balance,
        daily_pnl=get_daily_pnl(),
        daily_limit=get_daily_limit(balance),
        kelly_frac=kelly_fraction(),
        win_rate_pct=win_rate() * 100,
        max_dd_pct=max_drawdown(),
        sharpe=sharpe_ratio(),
        avg_hold=avg_hold_hours(),
        trade_count=get_trade_count(),
    )


# ── Entry point ──────────────────────────────────────────────────────────────

def main():
    global _exchange, _start_balance

    args = parse_args()

    # Override MODE from CLI if provided
    if args.mode:
        os.environ["MODE"] = args.mode

    # Initialise logging
    setup_logging()
    log.info("=" * 60)
    log.info("  BTC/USDT Trading Bot — Starting")
    log.info("=" * 60)

    # Build exchange connection
    _exchange = build_exchange()
    balance_info = verify_connection(_exchange)
    _start_balance = float(balance_info.get("USDT", {}).get("free", 0))

    # Executor mode
    paper = args.paper or get_mode() == "testnet"
    executor_init(paper=paper)

    # Graceful shutdown handler
    signal.signal(signal.SIGINT, _sigint_handler)
    signal.signal(signal.SIGTERM, _sigint_handler)

    # Startup Data Diagnostic
    log.info("Running initial data fetch and diagnostic…")
    try:
        startup_candles = refresh_all(_exchange)
        for tf in ["1h", "4h", "1d"]:
            actual = len(startup_candles.get(tf, []))
            req = MIN_CANDLES.get(tf, 11)
            
            if actual >= req:
                if tf == "1d" and actual < 20:
                    print(f"  [DATA CHECK] {tf}: {actual} candles ⚠ (limited — using reduced windows)")
                else:
                    print(f"  [DATA CHECK] {tf}: {actual} candles ✓")
            else:
                print(f"  [DATA CHECK] {tf}: {actual} candles ❌ (needs {req})")
    except Exception as exc:
        log.error("Initial data diagnostic failed: %s", exc)

    # Run first cycle immediately
    log.info("Starting initial trading cycle…")
    trading_cycle()

    # Schedule subsequent cycles every 15 min
    schedule.every(REFRESH_INTERVAL_MIN).minutes.do(trading_cycle)
    log.info(
        "⏰  Scheduled: trading cycle every %d minutes. Press Ctrl+C to stop.",
        REFRESH_INTERVAL_MIN,
    )

    while _running:
        schedule.run_pending()
        time.sleep(1)

    log.info("Bot shut down cleanly.")


if __name__ == "__main__":
    main()
