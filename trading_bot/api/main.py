from datetime import datetime
from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi.responses import JSONResponse

from .auth import router as auth_router, get_current_user
from .websocket import router as ws_router
from .routes import status, portfolio, trades, signals, control, settings

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Trading Bot API", version="1.0.0", strict_slashes=False)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom exception handler for 401
@app.exception_handler(401)
async def custom_401_handler(request: Request, exc):
    return JSONResponse(
        status_code=401,
        content={"error": "Unauthorized", "detail": "Invalid token", "code": 401}
    )

# Public routes
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])
app.include_router(ws_router, prefix="/ws", tags=["WebSocket"])

@app.get("/api/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

# Protected routes wrapper mapped sequentially as defined above
protected_dependency = [Depends(get_current_user)]

app.include_router(status.router, prefix="/api/status", tags=["Status"], dependencies=protected_dependency)
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"], dependencies=protected_dependency)
app.include_router(trades.router, prefix="/api/trades", tags=["Trades"], dependencies=protected_dependency)
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"], dependencies=protected_dependency)
app.include_router(control.router, prefix="/api/control", tags=["Control"], dependencies=protected_dependency)
app.include_router(settings.router, prefix="/api/settings", tags=["Settings"], dependencies=protected_dependency)
