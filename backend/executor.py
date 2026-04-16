"""
executor.py — Order execution on Binance.

• Market orders for entries
• Limit orders for take-profit
• OCO stop-loss+take-profit after entry
• Paper-trade mode (simulates without real execution)
• Confirms fills before logging
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import ccxt

from backend.config import SYMBOL, get_mode

log = logging.getLogger("bot.executor")

# ── Current Position State ──────────────────────────────────────────────────

@dataclass
class Position:
    is_open: bool = False
    side: str = ""          # "BUY"
    entry_price: float = 0.0
    size_btc: float = 0.0
    size_usdt: float = 0.0
    stop_loss: float = 0.0
    take_profit: float = 0.0
    entry_time: float = 0.0   # time.time() of entry
    oco_order_id: Optional[str] = None


_position = Position()
_paper_mode = False
_api_error_count = 0
_MAX_API_ERRORS = 3


def init(paper: bool = False):
    global _paper_mode
    _paper_mode = paper
    if _paper_mode:
        log.info("📝  Paper-trade mode enabled — no real orders")


def get_position() -> Position:
    return _position


def is_position_open() -> bool:
    return _position.is_open


def api_error_count() -> int:
    return _api_error_count


def _increment_api_error(exc: Exception):
    global _api_error_count
    _api_error_count += 1
    log.error(
        "API error (%d/%d): %s",
        _api_error_count, _MAX_API_ERRORS, exc,
    )
    if _api_error_count >= _MAX_API_ERRORS:
        log.critical(
            "🛑  %d consecutive API errors — HALTING. Manual restart required.",
            _MAX_API_ERRORS,
        )


def should_halt_on_api_errors() -> bool:
    return _api_error_count >= _MAX_API_ERRORS


# ── Entry ────────────────────────────────────────────────────────────────────

def open_position(
    exchange: ccxt.binance,
    side: str,
    size_usdt: float,
    current_price: float,
    stop_loss: float,
    take_profit: float,
) -> bool:
    """
    Execute a market BUY, then place OCO for SL/TP.
    Returns True on success.
    """
    global _position, _api_error_count

    size_btc = size_usdt / current_price

    # Round to Binance precision
    size_btc = _round_btc(size_btc)
    if size_btc <= 0:
        log.warning("BTC size rounds to 0 — skipping")
        return False

    log.info(
        "📤  OPENING %s: %.8f BTC (~$%.2f) @ ~$%.2f  SL=$%.2f  TP=$%.2f",
        side, size_btc, size_usdt, current_price, stop_loss, take_profit,
    )

    if _paper_mode:
        _position = Position(
            is_open=True,
            side=side,
            entry_price=current_price,
            size_btc=size_btc,
            size_usdt=size_usdt,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=time.time(),
        )
        log.info("📝  [PAPER] Position opened")
        _api_error_count = 0
        return True

    # ── Real execution ──────────────────────────────────────────────────
    try:
        order = exchange.create_market_buy_order(SYMBOL, size_btc)
        fill_price = float(order.get("average", current_price) or current_price)
        filled_amount = float(order.get("filled", size_btc) or size_btc)

        log.info(
            "✅  Market BUY filled: %.8f BTC @ $%.2f (id=%s)",
            filled_amount, fill_price, order.get("id"),
        )

        # Recalculate SL/TP using actual fill price (ATR-based offsets)
        atr_offset = (take_profit - current_price) / 4  # reverse-calculate ATR
        stop_loss = fill_price - 2 * atr_offset
        take_profit = fill_price + 4 * atr_offset

        _position = Position(
            is_open=True,
            side=side,
            entry_price=fill_price,
            size_btc=filled_amount,
            size_usdt=fill_price * filled_amount,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=time.time(),
        )

        # Place OCO (stop-loss + take-profit)
        _place_oco(exchange, filled_amount, stop_loss, take_profit)
        _api_error_count = 0
        return True

    except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
        _increment_api_error(exc)
        log.error("❌  BUY order FAILED — will NOT auto-retry: %s", exc)
        return False


def _place_oco(
    exchange: ccxt.binance,
    amount_btc: float,
    stop_loss: float,
    take_profit: float,
):
    """
    Place an OCO sell order (stop-loss + limit take-profit).
    Binance OCO = stopPrice + limit price in a single order group.
    """
    global _position

    try:
        # Binance-specific OCO via create_order with params
        # The stop limit price is slightly below stop price to ensure fill
        stop_limit_price = stop_loss * 0.998

        oco = exchange.create_order(
            symbol=SYMBOL,
            type="limit",
            side="sell",
            amount=amount_btc,
            price=take_profit,
            params={
                "stopPrice": stop_loss,
                "stopLimitPrice": round(stop_limit_price, 2),
                "stopLimitTimeInForce": "GTC",
                "newOrderRespType": "FULL",
                "listClientOrderId": f"oco_{int(time.time())}",
            },
        )
        _position.oco_order_id = oco.get("id")
        log.info(
            "✅  OCO placed: SL=$%.2f  TP=$%.2f (id=%s)",
            stop_loss, take_profit, _position.oco_order_id,
        )
    except Exception as exc:
        log.error(
            "⚠️  OCO placement failed (position still open without SL/TP): %s", exc
        )


# ── Exit ─────────────────────────────────────────────────────────────────────

def close_position(
    exchange: ccxt.binance,
    current_price: float,
    reason: str,
) -> dict:
    """
    Close the current position with a market sell.
    Returns a dict with trade details for logging.
    """
    global _position, _api_error_count

    if not _position.is_open:
        log.warning("No open position to close")
        return {}

    pos = _position
    hold_seconds = time.time() - pos.entry_time
    hold_hours = hold_seconds / 3600

    log.info(
        "📥  CLOSING position: %.8f BTC  reason=%s",
        pos.size_btc, reason,
    )

    exit_price = current_price

    if _paper_mode:
        log.info("📝  [PAPER] Position closed @ $%.2f", exit_price)
    else:
        try:
            # Cancel OCO first
            if pos.oco_order_id:
                try:
                    exchange.cancel_order(pos.oco_order_id, SYMBOL)
                except Exception:
                    pass  # OCO may have already triggered

            order = exchange.create_market_sell_order(SYMBOL, pos.size_btc)
            exit_price = float(order.get("average", current_price) or current_price)
            log.info("✅  Market SELL filled @ $%.2f", exit_price)
            _api_error_count = 0

        except (ccxt.NetworkError, ccxt.ExchangeError) as exc:
            _increment_api_error(exc)
            log.error("❌  SELL order FAILED: %s", exc)
            return {}

    pnl_usdt = (exit_price - pos.entry_price) * pos.size_btc
    pnl_pct = ((exit_price - pos.entry_price) / pos.entry_price) * 100

    trade_record = {
        "side": pos.side,
        "entry_price": pos.entry_price,
        "exit_price": exit_price,
        "size_btc": pos.size_btc,
        "size_usdt": pos.size_usdt,
        "pnl_usdt": round(pnl_usdt, 4),
        "pnl_pct": round(pnl_pct, 4),
        "hold_hours": round(hold_hours, 2),
        "exit_reason": reason,
    }

    # Reset position
    _position = Position()

    log.info(
        "💰  PnL: $%.4f (%.2f%%) | Hold: %.1fh | Reason: %s",
        pnl_usdt, pnl_pct, hold_hours, reason,
    )

    return trade_record


def _round_btc(amount: float) -> float:
    """Round BTC to 5 decimal places (Binance precision for BTC)."""
    return round(amount, 5)
