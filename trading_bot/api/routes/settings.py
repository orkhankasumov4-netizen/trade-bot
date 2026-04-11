import os
import json
from fastapi import APIRouter
from ..models import SettingsUpdate

router = APIRouter(redirect_slashes=False)
BOT_SETTINGS_FILE = "bot_settings.json"

@router.get("/")
async def get_settings():
    if not os.path.exists(BOT_SETTINGS_FILE):
        return {
            "stopLossPct": 4.0,
            "takeProfitPct": 10.0,
            "maxPositionSizePct": 20.0
        }
    try:
        with open(BOT_SETTINGS_FILE, "r") as f:
            data = json.load(f)
            return {
                "stopLossPct": data.get("stop_loss_pct", 4.0),
                "takeProfitPct": data.get("take_profit_pct", 10.0),
                "maxPositionSizePct": data.get("max_position_pct", 20.0)
            }
    except Exception as e:
        return {"error": "Failed to read settings", "detail": str(e)}

@router.put("/")
async def update_settings(settings: SettingsUpdate):
    try:
        data = {}
        if os.path.exists(BOT_SETTINGS_FILE):
            try:
                with open(BOT_SETTINGS_FILE, "r") as f:
                    data = json.load(f)
            except Exception:
                pass
                
        data["stop_loss_pct"] = settings.stop_loss_pct
        data["take_profit_pct"] = settings.take_profit_pct
        data["max_position_pct"] = settings.max_position_pct
        
        with open(BOT_SETTINGS_FILE, "w") as f:
            json.dump(data, f, indent=4)
            
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}
