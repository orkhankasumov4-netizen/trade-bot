# 🚀 BTC-Bot: High-Frequency Trading & Live Dashboard

Professional Bitcoin trading platform consisting of a robust **FastAPI Backend** and a premium **Flutter Mobile Dashboard**. Designed for high-performance monitoring and remote control of automated trading strategies.

![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Python: 3.10+](https://img.shields.io/badge/Python-3.10+-blue.svg)
![Flutter: 3.x](https://img.shields.io/badge/Flutter-3.x-02569B.svg)
![FastAPI: Latest](https://img.shields.io/badge/FastAPI-Latest-009688.svg)

---

## 📸 Dashboard Preview
> **Theme:** Binance-style Dark Aesthetic
> **Core Colors:** `#0B0E11` (BG), `#F0B90B` (Accent), `#0ECB81` (Profit)

*   **Real-time Monitoring:** Live price feeds and trade metrics via WebSockets.
*   **Tactical Controls:** Start, Stop, and Restart the bot remotely.
*   **Analytical Depth:** Market regime indicators, RSI Gauges, and multi-factor Signal Scores.

---

## 🏗 Project Architecture

The system uses a **Bridge Architecture** to ensure the trading bot remains isolated and stable while providing real-time data to the mobile interface.

```mermaid
graph LR
    subgraph VPS (Ubuntu 22.04)
        B[Python Trading Bot] <--> F[(File System)]
        F <--> A[FastAPI Backend]
    end
    subgraph Mobile
        A <--> M[Flutter Dashboard]
    end
    F ---|bot_state.json| A
    F ---|trades.csv| A
    F ---|bot_commands.json| B
```

---

## 🛠 Tech Stack

### Backend
- **FastAPI**: Asynchronous API framework.
- **JWT (OAuth2)**: Secure authentication.
- **WebSocket**: Full-duplex communication for live updates.
- **SlowAPI**: Rate limiting for security.
- **Nginx**: Reverse proxy & SSL termination.

### Mobile
- **Flutter**: Cross-platform high-performance UI.
- **WebSocket Channel**: Real-time stream handling.
- **Secure Storage**: Encrypted JWT token persistence.
- **Null-Safety**: Robust JSON parsing and fallback mechanisms.

---

## 🚀 Installation & Setup

### 1. Backend Configuration
```bash
cd trading_bot/api
pip install -r requirements_api.txt
cp .env.example .env  # Update with your credentials
screen -dmS api uvicorn main:app --host 0.0.0.0 --port 8000
```

### 2. Mobile App Setup
```bash
cd Best-Flutter-UI-Templates/best_flutter_ui_templates
flutter pub get
# Ensure api_config.dart points to your VPS IP
flutter run --release
```

---

## ⚙️ Environment Variables
Create a `.env` file in the root directory:
```env
SECRET_KEY=d8f7a9c2e4b6d8a8f9c2e4b6d7f1a3c5e8b0d2f4a6c9e1b3
JWT_EXPIRE_HOURS=24
API_USERNAME=admin
API_PASSWORD=your_password
MODE=testnet
BINANCE_API_KEY=your_key
BINANCE_API_SECRET=your_secret
```

---

## 🛡 Security & Stability Features
- **Deterministic Null Safety**: All API responses are normalized with guaranteed defaults to prevent UI crashes.
- **Automatic Trailing-Slash Handling**: Backend and app are synchronized to avoid 307 Redirects on POST payloads.
- **Global Error Handling**: Robust `try-catch` blocks for `SocketException` and `TimeoutException`.
- **Background Persistence**: Token-based auth with automatic session expiry handling.

---

## 👨‍💻 Author
**Antigravity AI** (Developed for Kasumov756)

---
*Disclaimer: Trading cryptocurrencies involves significant risk. This software is for informational purposes only.*
