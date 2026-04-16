import asyncio
import json
import os
from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(redirect_slashes=False)
BOT_STATE_FILE = "bot_state.json"

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

def read_bot_state():
    if not os.path.exists(BOT_STATE_FILE):
        return {"bot_status": "offline", "message": "bot_state.json not found"}
    try:
        with open(BOT_STATE_FILE, "r") as f:
            data = json.load(f)
            # Send exactly what the Flutter Dashboard expects
            return {
                "btc_price": data.get("btc_price", 0.0),
                "btc_change": data.get("btc_change_24h", 0.0), # mapped from btc_change_24h to match Flutter var btcChange
                "portfolioUsdt": data.get("portfolio_value", 0.0), # Flutter reads portfolioUsdt
                "openPnl": data.get("open_pnl", 0.0), # Flutter reads openPnl
                "totalPnl": data.get("total_pnl", 0.0),
                "totalPnlPct": data.get("total_pnl_pct", 0.0),
                "regime": data.get("overall_regime", "SIDEWAYS"),
                "status": data.get("status", "offline").upper(), # mapped to 'status' as expected by Flutter
                "lastUpdate": data.get("last_update", "").split("T")[-1][:5] if "last_update" in data else "",
                "signalScore": data.get("signal_score", 0),
                "rsi1h": data.get("rsi_1h", 50.0),
                "rsi4h": data.get("rsi_4h", 50.0),
                "rsi1d": data.get("rsi_1d", 50.0),
            }
    except Exception as e:
        return {"bot_status": "error", "message": str(e)}

async def websocket_broadcaster():
    while True:
        if manager.active_connections:
            state = read_bot_state()
            await manager.broadcast(json.dumps(state))
        await asyncio.sleep(15)

@router.websocket("/live")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # Push immediate state upon connection
        await websocket.send_text(json.dumps(read_bot_state()))
        while True:
            # Keep connection alive, listen for any client messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
