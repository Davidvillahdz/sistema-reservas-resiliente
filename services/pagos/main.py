import asyncio
import os
import random
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Servicio de Pagos",
    description="Servicio simulado con latencia y fallos controlados.",
    version="1.1.0",
)

FORCE_SLOW_PAYMENT = os.getenv(
    "FORCE_SLOW_PAYMENT",
    "false",
).lower() == "true"

SLOW_PAYMENT_SECONDS = float(
    os.getenv("SLOW_PAYMENT_SECONDS", "20")
)


class PaymentRequest(BaseModel):
    reservation_id: str = Field(min_length=5)
    amount: float = Field(gt=0)
    card_token: str = Field(min_length=4)


class PaymentResponse(BaseModel):
    payment_id: str
    reservation_id: str
    amount: float
    status: Literal["approved"]
    simulated_delay_seconds: float


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "pagos",
        "message": "Servicio de Pagos funcionando correctamente",
        "status": "ok",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "service": "pagos",
        "status": "healthy",
    }


@app.get("/simulation")
def simulation_status() -> dict[str, bool | float]:
    return {
        "force_slow_payment": FORCE_SLOW_PAYMENT,
        "slow_payment_seconds": SLOW_PAYMENT_SECONDS,
    }


@app.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_payment(request: PaymentRequest) -> PaymentResponse:
    if FORCE_SLOW_PAYMENT:
        delay = SLOW_PAYMENT_SECONDS
    else:
        delay = round(random.uniform(1.0, 4.0), 2)

    await asyncio.sleep(delay)

    if not FORCE_SLOW_PAYMENT and random.random() < 0.20:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="La pasarela de pagos no se encuentra disponible",
        )

    return PaymentResponse(
        payment_id=str(uuid4()),
        reservation_id=request.reservation_id,
        amount=request.amount,
        status="approved",
        simulated_delay_seconds=delay,
    )