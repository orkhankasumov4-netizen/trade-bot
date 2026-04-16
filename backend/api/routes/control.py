import os
import json
from datetime import datetime
from fastapi import APIRouter

router = APIRouter(redirect_slashes=False)
BOT_COMMANDS_FILE = "bot_commands.json"

def write_command(action: str):
    commands = {}
    if os.path.exists(BOT_COMMANDS_FILE):
        try:
            with open(BOT_COMMANDS_FILE, "r") as f:
                commands = json.load(f)
        except Exception:
            commands = {}
            
    commands["command"] = action
    commands["timestamp"] = datetime.utcnow().isoformat()
    
    with open(BOT_COMMANDS_FILE, "w") as f:
        json.dump(commands, f, indent=4)

@router.post("/start")
async def start_bot():
    try:
        write_command("start")
        return {"success": True, "message": "Start command sent to bot", "status": "RUNNING"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

@router.post("/stop")
async def stop_bot():
    try:
        write_command("stop")
        return {"success": True, "message": "Stop command sent to bot", "status": "STOPPED"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}

@router.post("/pause")
async def pause_bot():
    try:
        write_command("pause")
        return {"success": True, "message": "Pause command sent to bot", "status": "PAUSED"}
    except Exception as e:
        return {"success": False, "message": f"Error: {e}"}
