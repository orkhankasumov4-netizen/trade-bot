import os
import json
import pytest
from fastapi.testclient import TestClient
from backend.api.main import app

client = TestClient(app)

# Test Data setup
def setup_module(module):
    # Ensure no dirty files
    teardown_module(module)
    
    with open("bot_state.json", "w") as f:
        json.dump({
            "status": "running", "uptime_seconds": 9240, 
            "portfolio_value": 512.30, "overall_regime": "TRENDING_UP"
        }, f)
        
    with open("trades.csv", "w") as f:
        f.write("timestamp,side,entry_price,exit_price,size_btc,size_usdt,pnl_usdt,pnl_pct,hold_hours,exit_reason,signal_score\n")
        f.write("2024-01-15T10:00:00,BUY,43100,44420,0.0116,500,15.20,3.06,18,TAKE_PROFIT,8\n")

def teardown_module(module):
    for fp in ["bot_state.json", "trades.csv", "bot_commands.json", "bot_settings.json"]:
        if os.path.exists(fp):
            os.remove(fp)

# Tests
def test_health():
    # Use fake IP to prevent rate limiting blocks in dense tests
    response = client.get("/api/health", headers={"X-Forwarded-For": "1.2.3.4"})
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_login_success():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "Admin20160906!"})
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

def test_login_fail():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "wrongpassword"})
    assert response.status_code == 401

def get_auth_headers():
    response = client.post("/api/auth/login", json={"username": "admin", "password": "Admin20160906!"})
    return {"Authorization": f"Bearer {response.json()['access_token']}"}

def test_get_status():
    response = client.get("/api/status", headers=get_auth_headers())
    assert response.status_code == 200
    assert response.json()["bot_status"] == "running"

def test_get_trades():
    response = client.get("/api/trades", headers=get_auth_headers())
    assert response.status_code == 200
    data = response.json()
    assert data["total_trades"] == 1
    assert len(data["trades"]) == 1
    assert data["trades"][0]["pnlPct"] == 3.06

def test_unauthorized_access():
    response = client.get("/api/status")
    assert response.status_code == 401
    assert response.json()["error"] == "Unauthorized"

def test_commands():
    headers = get_auth_headers()
    r = client.post("/api/control/start", headers=headers)
    assert r.status_code == 200
    assert os.path.exists("bot_commands.json")
    with open("bot_commands.json", "r") as f:
        cmd = json.load(f)
        assert cmd["command"] == "start"

def test_settings_put():
    headers = get_auth_headers()
    r = client.put("/api/settings", headers=headers, json={
        "stop_loss_pct": 5.0,
        "take_profit_pct": 12.0,
        "max_position_pct": 25.0
    })
    assert r.status_code == 200
    with open("bot_settings.json", "r") as f:
        settings = json.load(f)
        assert settings["stop_loss_pct"] == 5.0
