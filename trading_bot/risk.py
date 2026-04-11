"""
risk.py — Kelly Criterion position sizing & risk controls.

Uses Half-Kelly for safety, with hard caps on position size,
daily loss limit, and minimum capital protection.
Recalculates Kelly from actual trade history every 10 completed trades.
"""

from __future__ import annotations

import logging
from typing import List

from trading_bot.config import (
    BOOTSTRAP_WIN_RATE,
    BOOTSTRAP_REWARD_RISK,
    MAX_POSITION_FRACTION,
    MIN_POSITION_USDT,
    MAX_OPEN_POSITIONS,
    DAILY_LOSS_FRACTION,
    MIN_CAPITAL_USDT,
)

log = logging.getLogger("bot.risk")

# ── State ────────────────────────────────────────────────────────────────────
_trade_history: List[dict] = []   # appended by logger / executor
_daily_pnl: float = 0.0
_halted: bool = False
_halt_reason: str = ""


def reset_daily():
    """Call at midnight (or bot restart) to reset daily PnL tracking."""
    global _daily_pnl
    _daily_pnl = 0.0
    log.info("Daily PnL counter reset")


def record_trade(pnl_usdt: float):
    """Record a completed trade's PnL for Kelly recalculation."""
    global _daily_pnl
    _trade_history.append({"pnl": pnl_usdt})
    _daily_pnl += pnl_usdt


def get_trade_count() -> int:
    return len(_trade_history)


# ── Kelly Criterion ─────────────────────────────────────────────────────────

def _compute_kelly(win_rate: float, reward_risk: float) -> float:
    """
    Half-Kelly:  f* = (W − (1−W)/R) / 2
    Clamp to [0, 1].
    """
    if reward_risk <= 0:
        return 0.0
    k = (win_rate - (1 - win_rate) / reward_risk) / 2.0
    return max(0.0, min(k, 1.0))


def kelly_fraction() -> float:
    """
    Return the Kelly fraction to use.
    Bootstrap with defaults until 20+ trades, then recalculate every 10.
    """
    n = len(_trade_history)

    if n < 20:
        frac = _compute_kelly(BOOTSTRAP_WIN_RATE, BOOTSTRAP_REWARD_RISK)
        log.debug("Kelly (bootstrap): %.4f (trades=%d)", frac, n)
        return frac

    # Use most recent trades (up to last 50)
    recent = _trade_history[-50:]
    wins = [t for t in recent if t["pnl"] > 0]
    losses = [t for t in recent if t["pnl"] <= 0]

    win_rate = len(wins) / len(recent) if recent else BOOTSTRAP_WIN_RATE
    avg_win = sum(t["pnl"] for t in wins) / len(wins) if wins else 1.0
    avg_loss = abs(sum(t["pnl"] for t in losses) / len(losses)) if losses else 1.0
    reward_risk = avg_win / avg_loss if avg_loss > 0 else BOOTSTRAP_REWARD_RISK

    frac = _compute_kelly(win_rate, reward_risk)
    log.info(
        "Kelly recalc: WR=%.2f R/R=%.2f → f*=%.4f (n=%d)",
        win_rate, reward_risk, frac, n,
    )
    return frac


# ── Position Sizing ─────────────────────────────────────────────────────────

def position_size_usdt(balance: float) -> float:
    """
    Calculate position size in USDT using Kelly + hard caps.
    Returns 0.0 if trading should be halted.
    """
    if is_halted():
        return 0.0

    frac = kelly_fraction()
    raw = balance * frac

    # Hard caps
    max_pos = balance * MAX_POSITION_FRACTION
    size = min(raw, max_pos)
    size = max(size, 0.0)

    if size < MIN_POSITION_USDT:
        log.warning(
            "Position size $%.2f below Binance minimum ($%.2f) — skip trade",
            size, MIN_POSITION_USDT,
        )
        return 0.0

    return round(size, 2)


# ── Safety Checks ───────────────────────────────────────────────────────────

def check_safety(balance: float, open_positions: int) -> bool:
    """
    Run all safety checks.  Sets _halted = True and returns False
    if any check fails.
    """
    global _halted, _halt_reason

    # Minimum capital
    if balance < MIN_CAPITAL_USDT:
        _halted = True
        _halt_reason = f"Balance ${balance:.2f} below minimum ${MIN_CAPITAL_USDT}"
        log.critical("🛑  HALT: %s", _halt_reason)
        return False

    # Daily loss limit
    daily_limit = balance * DAILY_LOSS_FRACTION
    if _daily_pnl < -daily_limit:
        _halted = True
        _halt_reason = (
            f"Daily loss ${_daily_pnl:.2f} exceeds limit -${daily_limit:.2f}"
        )
        log.critical("🛑  HALT: %s", _halt_reason)
        return False

    # Max open positions
    if open_positions >= MAX_OPEN_POSITIONS:
        log.info("Max open positions (%d) reached — no new trades", MAX_OPEN_POSITIONS)
        return False

    return True


def is_halted() -> bool:
    return _halted


def halt_reason() -> str:
    return _halt_reason


def get_daily_pnl() -> float:
    return _daily_pnl


def get_daily_limit(balance: float) -> float:
    return balance * DAILY_LOSS_FRACTION


# ── Performance metrics used by the dashboard ───────────────────────────────

def win_rate(n: int = 20) -> float:
    """Win rate over the last *n* trades."""
    recent = _trade_history[-n:] if _trade_history else []
    if not recent:
        return 0.0
    wins = sum(1 for t in recent if t["pnl"] > 0)
    return wins / len(recent)


def max_drawdown() -> float:
    """Rolling max drawdown % from cumulative PnL curve."""
    if not _trade_history:
        return 0.0
    cum = 0.0
    peak = 0.0
    dd = 0.0
    for t in _trade_history:
        cum += t["pnl"]
        if cum > peak:
            peak = cum
        drawdown = (peak - cum) / peak if peak > 0 else 0.0
        dd = max(dd, drawdown)
    return dd * 100  # percent


def sharpe_ratio() -> float:
    """Annualised Sharpe (0 % risk-free) from per-trade returns."""
    if len(_trade_history) < 2:
        return 0.0
    import numpy as np

    returns = [t["pnl"] for t in _trade_history]
    mean_r = np.mean(returns)
    std_r = np.std(returns, ddof=1)
    if std_r == 0:
        return 0.0
    # Approx: assume ~2 trades/day → √730 annualisation
    return float((mean_r / std_r) * (730 ** 0.5))


def avg_hold_hours() -> float:
    """Average hold time — requires 'hold_hours' key in history."""
    holds = [t.get("hold_hours", 0) for t in _trade_history if "hold_hours" in t]
    return sum(holds) / len(holds) if holds else 0.0
