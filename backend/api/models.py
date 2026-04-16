from pydantic import BaseModel, Field

class LoginRequest(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int

class SettingsUpdate(BaseModel):
    stop_loss_pct: float = Field(..., ge=0, le=100)
    take_profit_pct: float = Field(..., ge=0)
    max_position_pct: float = Field(..., ge=0, le=100)

class GenericResponse(BaseModel):
    success: bool
    message: str
