import asyncio
import random
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Servicio de Pagos",
    description="Servicio simulado que procesa pagos con latencia y fallos controlados.",
    version="1.0.0",
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


@app.post(
    "/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def process_payment(request: PaymentRequest) -> PaymentResponse:
    """
    Simula un proveedor externo de pagos.

    - Introduce una latencia aleatoria entre 1 y 4 segundos.
    - Tiene una probabilidad aproximada del 20 % de fallar.
    """
    delay = round(random.uniform(1.0, 4.0), 2)
    await asyncio.sleep(delay)

    if random.random() < 0.20:
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