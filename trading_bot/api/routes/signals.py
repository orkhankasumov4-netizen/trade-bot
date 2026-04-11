import os
import json
from fastapi import APIRouter

router = APIRouter(redirect_slashes=False)
BOT_STATE_FILE = "bot_state.json"

@router.get("/live")
async def get_live_signals():
    if not os.path.exists(BOT_STATE_FILE):
        return {"signals": []}
    try:
        with open(BOT_STATE_FILE, "r") as f:
            data = json.load(f)
            
            # Map history into format expected by Flutter
            signals_list = []
            for s in data.get("signals_history", []):
                # Extract HH:MM from timestamp
                ts = s.get("timestamp", "")
                time_str = ts.split("T")[-1][:5] if "T" in ts else ts
                
                conditions_obj = s.get("conditions", {})
                reasons = []
                for k, v in conditions_obj.items():
                    # Format standard keys nicely
                    text_name = str(k).replace("_", " ").capitalize()
                    if k == "rsi_oversold": text_name = f"RSI oversold ({s.get('rsi', '')})"
                    reasons.append({"text": text_name, "passed": bool(v)})
                
                signals_list.append({
                    "time": time_str,
                    "regime": s.get("regime", "UNKNOWN"),
                    "score": s.get("score", 0),
                    "action": s.get("decision", "HOLD"),
                    "reasons": reasons
                })
            
            # Sort newest first
            signals_list.reverse()
            return {"signals": signals_list[:10]} # Return last 10
            
    except Exception as e:
        return {"error": "Error reading state", "detail": str(e)}
