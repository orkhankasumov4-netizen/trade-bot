import os
import pandas as pd
from fastapi import APIRouter

router = APIRouter(redirect_slashes=False)
TRADES_CSV = "trades.csv"

@router.get("/")
async def get_trades():
    if not os.path.exists(TRADES_CSV) or os.path.getsize(TRADES_CSV) == 0:
        return {"trades": [], "total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}
    try:
        df = pd.read_csv(TRADES_CSV)
        if df.empty:
            return {"trades": [], "total_trades": 0, "win_rate": 0.0, "total_pnl": 0.0}
        
        # Calculate summary stats based on df
        total_trades = len(df)
        winning_trades = len(df[df['pnl_pct'] > 0])
        win_rate = round((winning_trades / total_trades) * 100, 1) if total_trades > 0 else 0.0
        total_pnl = round(df['pnl_usdt'].sum(), 2)
        
        # Prepare trades list mapping to JSON
        # Sort by timestamp descending
        df = df.sort_values(by="timestamp", ascending=False)
        trades_list = []
        for _, row in df.iterrows():
            # Flutter wants 'date', 'entryPrice', 'exitPrice', 'pnlPct', 'holdTime', 'exitReason'
            # Convert timestamp to a more readable date if needed, or pass as is
            try:
                date_str = pd.to_datetime(row['timestamp']).strftime('%b %d')
            except:
                date_str = str(row['timestamp'])
                
            trades_list.append({
                "date": date_str,
                "entryPrice": row.get("entry_price", 0.0),
                "exitPrice": row.get("exit_price", 0.0),
                "pnlPct": row.get("pnl_pct", 0.0),
                "holdTime": f"{row.get('hold_hours', 0)}h",
                "exitReason": str(row.get("exit_reason", "")).replace("_", " ").title()
            })
            
        return {
            "trades": trades_list,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl
        }
    except Exception as e:
        return {"error": "Failed to read trades", "detail": str(e)}

@router.get("/stats")
async def get_trades_stats():
    if not os.path.exists(TRADES_CSV) or os.path.getsize(TRADES_CSV) == 0:
        return {}
    try:
        df = pd.read_csv(TRADES_CSV)
        if df.empty:
            return {}
            
        total_trades = len(df)
        winning_trades = len(df[df['pnl_pct'] > 0])
        losing_trades = len(df[df['pnl_pct'] <= 0])
        win_rate = round((winning_trades / total_trades) * 100, 1) if total_trades > 0 else 0.0
        total_pnl_usdt = round(df['pnl_usdt'].sum(), 2)
        total_pnl_pct = round(df['pnl_pct'].sum(), 2)
        
        best_trade_row = df.loc[df['pnl_pct'].idxmax()] if not df.empty else None
        worst_trade_row = df.loc[df['pnl_pct'].idxmin()] if not df.empty else None
        
        avg_hold_hours = round(df['hold_hours'].mean(), 1) if 'hold_hours' in df.columns else 0.0
        
        # Profit factor: gross profit / gross loss (absolute)
        gross_profit = df[df['pnl_usdt'] > 0]['pnl_usdt'].sum()
        gross_loss = abs(df[df['pnl_usdt'] < 0]['pnl_usdt'].sum())
        profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
        
        # Max drawdown simplistic based on row cumulative max over pnl
        cumulative_pnl = df['pnl_pct'].cumsum()
        running_max = cumulative_pnl.cummax()
        drawdown = running_max - cumulative_pnl
        max_drawdown_pct = round(drawdown.max(), 2) if not drawdown.empty else 0.0
        
        # Sharpe ratio approx (simplistic assuming zero risk free rate per trade)
        mean_return = df['pnl_pct'].mean()
        std_dev = df['pnl_pct'].std()
        sharpe_ratio = round(mean_return / std_dev, 2) if std_dev > 0 else 0.0
        
        def format_date(ts):
            if pd.isna(ts): return ""
            try: return pd.to_datetime(ts).strftime('%Y-%m-%d')
            except: return str(ts)
            
        return {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "total_pnl_usdt": total_pnl_usdt,
            "total_pnl_pct": total_pnl_pct,
            "best_trade": {
                "pnl_pct": round(best_trade_row['pnl_pct'], 2) if best_trade_row is not None else 0.0,
                "date": format_date(best_trade_row['timestamp']) if best_trade_row is not None else ""
            },
            "worst_trade": {
                "pnl_pct": round(worst_trade_row['pnl_pct'], 2) if worst_trade_row is not None else 0.0,
                "date": format_date(worst_trade_row['timestamp']) if worst_trade_row is not None else ""
            },
            "avg_hold_hours": avg_hold_hours,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_drawdown_pct,
            "sharpe_ratio": sharpe_ratio
        }
    except Exception as e:
        return {"error": "Failed to calculate stats", "detail": str(e)}
