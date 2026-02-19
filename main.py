import os
import math
import logging
from datetime import datetime, timedelta
from typing import Optional

import jwt
import httpx
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field

# ==========================================================
# CONFIG
# ==========================================================

SECRET_KEY = os.getenv("JWT_SECRET", "CHANGE_THIS_SECRET")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SMARTCARGO")

app = FastAPI(title="SMARTCARGO-AIPA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# ==========================================================
# MODELS
# ==========================================================

class LoginRequest(BaseModel):
    username: str
    password: str


class CargoInput(BaseModel):
    origin: str
    destination: str
    weight_kg: float = Field(..., gt=0)
    length_cm: float = Field(..., gt=0)
    width_cm: float = Field(..., gt=0)
    height_cm: float = Field(..., gt=0)
    pieces: int = Field(..., gt=0)
    temperature_required: Optional[bool] = False
    dangerous_goods: Optional[bool] = False
    packaging_ok: bool
    documents_complete: bool
    dry_ice_kg: Optional[float] = 0


class CargoResponse(BaseModel):
    volumetric_weight: float
    chargeable_weight: float
    psi: float
    status: str
    critical_alert: Optional[str]
    ai_observation: Optional[str]


# ==========================================================
# AUTH
# ==========================================================

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ==========================================================
# AI FALLBACK
# ==========================================================

async def ai_observation(prompt: str) -> str:
    # Try OpenAI first
    if OPENAI_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=20
                )
                return r.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.warning("OpenAI failed, trying Gemini")

    if GEMINI_API_KEY:
        try:
            async with httpx.AsyncClient() as client:
                r = await client.post(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={GEMINI_API_KEY}",
                    json={"contents":[{"parts":[{"text":prompt}]}]},
                    timeout=20
                )
                return r.json()["candidates"][0]["content"]["parts"][0]["text"]
        except:
            return "AI service unavailable."

    return "AI not configured."


# ==========================================================
# ROUTES
# ==========================================================

@app.post("/login")
def login(data: LoginRequest):
    if data.username == "admin" and data.password == "admin123":
        token = create_access_token({"sub": data.username})
        return {"access_token": token}
    raise HTTPException(status_code=401, detail="Invalid credentials")


@app.post("/analyze", response_model=CargoResponse)
async def analyze_cargo(data: CargoInput, user=Depends(verify_token)):

    # -----------------------------
    # Volumetric weight (IATA 6000)
    # -----------------------------
    volume = (data.length_cm * data.width_cm * data.height_cm) / 6000
    volumetric_weight = round(volume * data.pieces, 2)

    chargeable_weight = max(volumetric_weight, data.weight_kg)

    # -----------------------------
    # PSI calculation
    # -----------------------------
    base_area = (data.length_cm * data.width_cm) / 10000
    psi = round((chargeable_weight / base_area) if base_area > 0 else 0, 2)

    status = "CLEARED"
    critical_alert = None

    # -----------------------------
    # Hard Rules
    # -----------------------------
    if not data.documents_complete:
        status = "CRITICAL"
        critical_alert = "Documents incomplete. Must be corrected before departure."

    if not data.packaging_ok:
        status = "CRITICAL"
        critical_alert = "Packaging not compliant."

    if psi > 300:
        status = "CRITICAL"
        critical_alert = "PSI exceeds aircraft limit."

    if data.dangerous_goods and data.dry_ice_kg > 2.5:
        status = "CRITICAL"
        critical_alert = "Dry ice exceeds allowed DG limit."

    # -----------------------------
    # AI Observation (non-decision)
    # -----------------------------
    prompt = f"""
    Analyze cargo:
    From {data.origin} to {data.destination}.
    Chargeable weight: {chargeable_weight}.
    PSI: {psi}.
    Provide operational observation only.
    """

    observation = await ai_observation(prompt)

    logger.info(f"Cargo analyzed by {user['sub']} - Status: {status}")

    return CargoResponse(
        volumetric_weight=volumetric_weight,
        chargeable_weight=chargeable_weight,
        psi=psi,
        status=status,
        critical_alert=critical_alert,
        ai_observation=observation
    )
