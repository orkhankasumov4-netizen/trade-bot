import os
import json
from fastapi import APIRouter

router = APIRouter(redirect_slashes=False)
BOT_STATE_FILE = "bot_state.json"

@router.get("/")
async def get_status():
    if not os.path.exists(BOT_STATE_FILE):
        return {
            "bot_status": "offline",
            "uptime": "0h 0m",
            "last_update": "",
            "overall_regime": "N/A",
            "last_signal": "NONE",
            "signal_score": "0/12"
        }
    try:
        with open(BOT_STATE_FILE, "r") as f:
            data = json.load(f)
            
            uptime_sec = data.get("uptime_seconds", 0)
            hours = uptime_sec // 3600
            minutes = (uptime_sec % 3600) // 60
            
            return {
                "bot_status": data.get("status", "unknown"),
                "uptime": f"{hours}h {minutes}m",
                "last_update": data.get("last_update", ""),
                "overall_regime": data.get("overall_regime", "N/A"),
                "last_signal": data.get("last_signal", "NONE"),
                "signal_score": f"{data.get('signal_score', 0)}/{data.get('signal_score_max', 12)}"
            }
    except Exception as e:
        return {"error": "Error reading state", "detail": str(e)}
