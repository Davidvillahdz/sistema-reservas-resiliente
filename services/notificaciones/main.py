import asyncio
import random
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Servicio de Notificaciones",
    description="Servicio simulado para el envío de correos de confirmación.",
    version="1.0.0",
)


class NotificationRequest(BaseModel):
    reservation_id: str = Field(min_length=5)
    customer_email: str = Field(min_length=5)
    message: str = Field(min_length=3, max_length=500)


class NotificationResponse(BaseModel):
    notification_id: str
    reservation_id: str
    customer_email: str
    status: Literal["sent"]
    simulated_delay_seconds: float


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "notificaciones",
        "message": "Servicio de Notificaciones funcionando correctamente",
        "status": "ok",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "service": "notificaciones",
        "status": "healthy",
    }


@app.post(
    "/notifications",
    response_model=NotificationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def send_notification(
    request: NotificationRequest,
) -> NotificationResponse:
    """
    Simula el envío de una notificación.

    - Introduce latencia aleatoria.
    - Tiene una probabilidad aproximada del 15 % de fallar.
    """
    delay = round(random.uniform(0.5, 2.5), 2)
    await asyncio.sleep(delay)

    if random.random() < 0.15:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible enviar la notificación",
        )

    return NotificationResponse(
        notification_id=str(uuid4()),
        reservation_id=request.reservation_id,
        customer_email=request.customer_email,
        status="sent",
        simulated_delay_seconds=delay,
    )