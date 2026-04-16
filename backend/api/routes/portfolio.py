import os
import json
from fastapi import APIRouter

router = APIRouter(redirect_slashes=False)
BOT_STATE_FILE = "bot_state.json"

@router.get("/")
async def get_portfolio():
    if not os.path.exists(BOT_STATE_FILE):
        return {}
    try:
        with open(BOT_STATE_FILE, "r") as f:
            data = json.load(f)
            return {
                "portfolio_value": data.get("portfolio_value", 0.0),
                "cash": data.get("cash", 0.0),
                "btc_holdings": data.get("btc_holdings", 0.0),
                "btc_price": data.get("btc_price", 0.0),
                "btc_change_24h": data.get("btc_change_24h", 0.0),
                "total_pnl": data.get("total_pnl", 0.0),
                "total_pnl_pct": data.get("total_pnl_pct", 0.0),
                "open_pnl": data.get("open_pnl", 0.0),
                "open_position": data.get("open_position", False),
                "entry_price": data.get("entry_price", 0.0)
            }
    except Exception as e:
        return {"error": "Error reading state", "detail": str(e)}
