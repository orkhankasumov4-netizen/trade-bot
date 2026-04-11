"""
indicators.py — Technical indicator calculations.

Computes per-timeframe:
  • Bollinger Bands (20, ±2σ)
  • RSI-14 (Wilder's smoothing)
  • EMA-50 / EMA-200
  • ATR-14
  • Volume ratio (current vs 20-period mean)
  • Bullish / Bearish RSI divergence (5-candle lookback)
"""

from __future__ import annotations

import logging
from typing import Dict

import numpy as np
import pandas as pd
import ta

log = logging.getLogger("bot.indicators")


def compute(df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    """
    Attach all indicator columns to *df* **in-place** and return it.
    Dynamically adjusts window sizes for short DataFrames (e.g., testnet 1d).
    Expects columns: open, high, low, close, volume.
    """
    n = len(df)
    
    # Pre-fill all expected columns with NaN
    for col in ["bb_upper", "bb_mid", "bb_lower", "bb_pct", "rsi", "ema50", "ema200", "atr", "vol_ratio"]:
        df[col] = np.nan
    df["rsi_div_bull"] = False
    df["rsi_div_bear"] = False

    if n == 0:
        return df

    close = df["close"]
    high = df["high"]
    low = df["low"]
    volume = df["volume"]

    # ── Bollinger Bands ──────────────────────────────────────────────────
    bb_window = 20
    if n < 20:
        if timeframe == "1d" and n >= 10:
            bb_window = 10
        else:
            bb_window = None

    if bb_window:
        try:
            bb = ta.volatility.BollingerBands(close=close, window=bb_window, window_dev=2)
            df["bb_upper"] = bb.bollinger_hband()
            df["bb_mid"] = bb.bollinger_mavg()
            df["bb_lower"] = bb.bollinger_lband()
            df["bb_pct"] = bb.bollinger_pband()   # 0 = lower, 1 = upper
        except Exception:
            pass

    # ── RSI ─────────────────────────────────────────────────────────────
    rsi_window = 14
    if n < 14:
        if timeframe == "1d" and n >= 9:
            rsi_window = 9
        else:
            rsi_window = None
            
    if rsi_window:
        try:
            rsi_ind = ta.momentum.RSIIndicator(close=close, window=rsi_window)
            df["rsi"] = rsi_ind.rsi()
        except Exception:
            pass

    # ── EMAs ────────────────────────────────────────────────────────────
    if n >= 50:
        try:
            df["ema50"] = ta.trend.EMAIndicator(close=close, window=50).ema_indicator()
        except Exception:
            pass

    if n >= 200:
        try:
            df["ema200"] = ta.trend.EMAIndicator(close=close, window=200).ema_indicator()
        except Exception:
            pass

    # ── ATR ─────────────────────────────────────────────────────────────
    atr_window = 14
    if n < 14:
        if timeframe == "1d" and n >= 11:
            atr_window = 11
        else:
            atr_window = None

    if atr_window:
        try:
            atr_ind = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=atr_window)
            df["atr"] = atr_ind.average_true_range()
        except Exception:
            pass

    # ── Volume ratio ────────────────────────────────────────────────────
    if n >= 20:
        vol_sma = volume.rolling(window=20).mean()
        df["vol_ratio"] = volume / vol_sma.replace(0, np.nan)
    elif n >= 10 and timeframe == "1d":
        vol_sma = volume.rolling(window=10).mean()
        df["vol_ratio"] = volume / vol_sma.replace(0, np.nan)

    # ── RSI divergence ──────────────────────────────────────────────────
    if rsi_window:
        lookback = min(5, n - 1)
        if lookback >= 2:
            df["rsi_div_bull"] = _detect_divergence(close, df["rsi"], kind="bullish", lookback=lookback)
            df["rsi_div_bear"] = _detect_divergence(close, df["rsi"], kind="bearish", lookback=lookback)

    return df


def compute_all(candles: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """Compute indicators on every timeframe DataFrame."""
    for tf, df in candles.items():
        log.debug("Computing indicators for %s…", tf)
        compute(df, tf)
    return candles


# ── Internal helpers ─────────────────────────────────────────────────────────

def _detect_divergence(
    price: pd.Series,
    rsi: pd.Series,
    kind: str = "bullish",
    lookback: int = 5,
) -> pd.Series:
    """
    Simple swing-based divergence detector.

    Bullish divergence: price makes a lower low, RSI makes a higher low.
    Bearish divergence: price makes a higher high, RSI makes a lower high.

    Returns a boolean Series (True where divergence detected).
    """
    result = pd.Series(False, index=price.index)

    if len(price) < lookback + 1:
        return result

    for i in range(lookback, len(price)):
        window_price = price.iloc[i - lookback : i + 1]
        window_rsi = rsi.iloc[i - lookback : i + 1]

        if window_price.isna().any() or window_rsi.isna().any():
            continue

        if kind == "bullish":
            # Price: current low < previous low  AND  RSI: current "low" > previous "low"
            price_curr_low = window_price.iloc[-1]
            price_prev_low = window_price.iloc[:-1].min()
            rsi_at_curr = window_rsi.iloc[-1]
            rsi_at_prev_low_idx = window_price.iloc[:-1].idxmin()
            rsi_at_prev = window_rsi.loc[rsi_at_prev_low_idx] if rsi_at_prev_low_idx in window_rsi.index else np.nan

            if (
                not np.isnan(rsi_at_prev)
                and price_curr_low < price_prev_low
                and rsi_at_curr > rsi_at_prev
            ):
                result.iloc[i] = True

        elif kind == "bearish":
            price_curr_high = window_price.iloc[-1]
            price_prev_high = window_price.iloc[:-1].max()
            rsi_at_curr = window_rsi.iloc[-1]
            rsi_at_prev_high_idx = window_price.iloc[:-1].idxmax()
            rsi_at_prev = window_rsi.loc[rsi_at_prev_high_idx] if rsi_at_prev_high_idx in window_rsi.index else np.nan

            if (
                not np.isnan(rsi_at_prev)
                and price_curr_high > price_prev_high
                and rsi_at_curr < rsi_at_prev
            ):
                result.iloc[i] = True

    return result
