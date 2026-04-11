"""
strategy.py — Market regime detection & multi-timeframe signal confluence.

Regime filter (4h + 1d):
    TRENDING_UP   → Price > EMA50 > EMA200 on BOTH 4h and 1d
    TRENDING_DOWN → Price < EMA50 < EMA200 on BOTH 4h and 1d
    SIDEWAYS      → EMAs within 1.5 % of each other on either

Signal scoring (0-4 per timeframe, total /12):
    BUY  → needs ≥ 6/12
    SELL → any single exit condition met
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional

import numpy as np
import pandas as pd

log = logging.getLogger("bot.strategy")


# ── Enums & Data Classes ────────────────────────────────────────────────────

class Regime(Enum):
    TRENDING_UP = "TRENDING UP"
    TRENDING_DOWN = "TRENDING DOWN"
    SIDEWAYS = "SIDEWAYS"


@dataclass
class Signal:
    action: str                 # "BUY", "SELL", "HOLD"
    score: int = 0              # 0-12
    max_score: int = 12
    regime: Regime = Regime.SIDEWAYS
    regimes: Dict[str, Regime] = field(default_factory=dict)
    scores: Dict[str, int] = field(default_factory=dict)
    reasons: list = field(default_factory=list)
    atr: float = 0.0           # ATR from 1h for stop/target calc
    current_price: float = 0.0


# ── Regime Detection ────────────────────────────────────────────────────────

def _single_regime(df: pd.DataFrame) -> Optional[Regime]:
    """Classify regime for a single timeframe using its last row."""
    row = df.iloc[-1]
    price = row["close"]
    ema50 = row.get("ema50", np.nan)
    ema200 = row.get("ema200", np.nan)

    if pd.isna(ema50) or pd.isna(ema200):
        return None

    # Sideways: EMAs within 1.5 % of each other
    ema_spread = abs(ema50 - ema200) / ema200
    if ema_spread < 0.015:
        return Regime.SIDEWAYS

    if price > ema50 > ema200:
        return Regime.TRENDING_UP
    elif price < ema50 < ema200:
        return Regime.TRENDING_DOWN

    return Regime.SIDEWAYS


def detect_regime(candles: Dict[str, pd.DataFrame]) -> Dict[str, Optional[Regime]]:
    """Compute regime per timeframe; overall regime requires 4h AND 1d agreement."""
    regimes: Dict[str, Regime] = {}
    for tf in ("1h", "4h", "1d"):
        if tf in candles and len(candles[tf]) > 0:
            regimes[tf] = _single_regime(candles[tf])
        else:
            regimes[tf] = Regime.SIDEWAYS
    return regimes


def overall_regime(regimes: Dict[str, Optional[Regime]]) -> Regime:
    """
    Overall regime: 4h AND 1d must agree on trending direction.
    If 1d is missing (due to API limits): fallback to 4h alone.
    If 4h is also missing: fallback to 1h.
    """
    r1h = regimes.get("1h")
    r4h = regimes.get("4h")
    r1d = regimes.get("1d")

    # If 1d is missing (None), use 4h only
    if r1d is None:
        if r4h is None:
            if r1h is None:
                return Regime.SIDEWAYS
            return r1h
        return r4h

    # If 4h is missing but 1d is present (rare/safety fallback)
    if r4h is None:
        return r1d

    # Normal case: both 4h and 1d exist
    if r4h == Regime.TRENDING_UP and r1d == Regime.TRENDING_UP:
        return Regime.TRENDING_UP
    if r4h == Regime.TRENDING_DOWN and r1d == Regime.TRENDING_DOWN:
        return Regime.TRENDING_DOWN

    return Regime.SIDEWAYS


# ── Signal Scoring ──────────────────────────────────────────────────────────

def _score_timeframe(df: pd.DataFrame) -> int:
    """
    Score a single timeframe 0-4 for BUY signals.
    +1 RSI < 40
    +1 Price within 1.5 % of Bollinger lower band
    +1 Bullish RSI divergence
    +1 Volume ratio > 1.3
    """
    if len(df) == 0:
        return 0

    row = df.iloc[-1]
    score = 0

    # RSI oversold
    rsi = row.get("rsi", np.nan)
    if not np.isnan(rsi) and rsi < 40:
        score += 1

    # Price near BB lower (within 1.5 %)
    close = row["close"]
    bb_lower = row.get("bb_lower", np.nan)
    if not np.isnan(bb_lower) and bb_lower > 0:
        proximity = (close - bb_lower) / bb_lower
        if proximity < 0.015:
            score += 1

    # Bullish RSI divergence
    if row.get("rsi_div_bull", False):
        score += 1

    # Volume surge
    vol_ratio = row.get("vol_ratio", np.nan)
    if not np.isnan(vol_ratio) and vol_ratio > 1.3:
        score += 1

    return score


def generate_signal(
    candles: Dict[str, pd.DataFrame],
    position_open: bool = False,
    entry_price: float = 0.0,
) -> Signal:
    """
    Master signal generator.
    Returns a Signal with action = BUY | SELL | HOLD.
    """
    regimes = detect_regime(candles)
    regime = overall_regime(regimes)

    # Current price & ATR from 1h
    df_1h = candles.get("1h")
    if df_1h is None or len(df_1h) == 0:
        return Signal(action="HOLD", regime=regime, regimes=regimes)

    current_price = float(df_1h.iloc[-1]["close"])
    atr_1h = float(df_1h.iloc[-1].get("atr", 0))

    # ── EXIT / SELL logic (checked first if we have an open position) ────
    if position_open and entry_price > 0:
        sell_reasons = _check_exit_conditions(
            candles, entry_price, current_price, atr_1h, regime
        )
        if sell_reasons:
            return Signal(
                action="SELL",
                regime=regime,
                regimes=regimes,
                reasons=sell_reasons,
                atr=atr_1h,
                current_price=current_price,
            )

    # ── BUY logic ────────────────────────────────────────────────────────
    if not position_open:
        # Never trade sideways
        if regime == Regime.SIDEWAYS:
            return Signal(
                action="HOLD",
                regime=regime,
                regimes=regimes,
                reasons=["Market is SIDEWAYS — no trade"],
                current_price=current_price,
                atr=atr_1h,
            )

        # Only BUY in uptrend
        if regime != Regime.TRENDING_UP:
            return Signal(
                action="HOLD",
                regime=regime,
                regimes=regimes,
                reasons=["Regime not TRENDING UP — BUY blocked"],
                current_price=current_price,
                atr=atr_1h,
            )

        # Score each timeframe
        scores: Dict[str, int] = {}
        total = 0
        for tf in ("1h", "4h", "1d"):
            s = _score_timeframe(candles[tf]) if tf in candles else 0
            scores[tf] = s
            total += s

        if total >= 6:
            return Signal(
                action="BUY",
                score=total,
                regime=regime,
                regimes=regimes,
                scores=scores,
                reasons=[f"Confluence score {total}/12 ≥ 6"],
                atr=atr_1h,
                current_price=current_price,
            )
        else:
            return Signal(
                action="HOLD",
                score=total,
                regime=regime,
                regimes=regimes,
                scores=scores,
                reasons=[f"Confluence score {total}/12 < 6 — not enough"],
                atr=atr_1h,
                current_price=current_price,
            )

    # Default: HOLD
    return Signal(
        action="HOLD",
        regime=regime,
        regimes=regimes,
        atr=atr_1h,
        current_price=current_price,
    )


# ── Exit condition checker ──────────────────────────────────────────────────

def _check_exit_conditions(
    candles: Dict[str, pd.DataFrame],
    entry_price: float,
    current_price: float,
    atr: float,
    regime: Regime,
) -> list[str]:
    """Return a list of triggered exit reasons (empty = hold)."""
    reasons: list[str] = []

    if atr > 0:
        # Dynamic stop-loss: entry − 2×ATR
        stop_loss = entry_price - 2 * atr
        if current_price <= stop_loss:
            reasons.append(f"Stop-loss hit: {current_price:.2f} ≤ SL {stop_loss:.2f}")

        # Take-profit: entry + 4×ATR (1:2 R/R)
        take_profit = entry_price + 4 * atr
        if current_price >= take_profit:
            reasons.append(f"Take-profit hit: {current_price:.2f} ≥ TP {take_profit:.2f}")

    # RSI > 65 on 1h AND 4h simultaneously
    rsi_1h = _last_rsi(candles, "1h")
    rsi_4h = _last_rsi(candles, "4h")
    if rsi_1h > 65 and rsi_4h > 65:
        reasons.append(f"RSI overbought: 1h={rsi_1h:.1f} 4h={rsi_4h:.1f}")

    # Bearish RSI divergence on 4h
    if "4h" in candles and len(candles["4h"]) > 0:
        if candles["4h"].iloc[-1].get("rsi_div_bear", False):
            reasons.append("Bearish RSI divergence on 4h")

    # Regime shift
    if regime in (Regime.SIDEWAYS, Regime.TRENDING_DOWN):
        reasons.append(f"Regime shifted to {regime.value}")

    return reasons


def _last_rsi(candles: Dict[str, pd.DataFrame], tf: str) -> float:
    if tf in candles and len(candles[tf]) > 0:
        v = candles[tf].iloc[-1].get("rsi", np.nan)
        return float(v) if not np.isnan(v) else 0.0
    return 0.0


# ── Helpers for Stop-Loss / Take-Profit levels ─────────────────────────────

def calc_stop_loss(entry: float, atr: float) -> float:
    return entry - 2 * atr


def calc_take_profit(entry: float, atr: float) -> float:
    return entry + 4 * atr
