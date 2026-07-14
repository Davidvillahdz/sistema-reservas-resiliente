from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Servicio de Reservas",
    description="Servicio principal para procesar reservas de entradas.",
    version="1.0.0",
)


class ReservationRequest(BaseModel):
    customer_name: str = Field(min_length=2, max_length=100)
    customer_email: str = Field(min_length=5, max_length=150)
    event_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=10)


class ReservationResponse(BaseModel):
    reservation_id: str
    customer_name: str
    customer_email: str
    event_id: int
    quantity: int
    status: Literal["created"]
    created_at: datetime


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "reservas",
        "message": "Servicio de Reservas funcionando correctamente",
        "status": "ok",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "service": "reservas",
        "status": "healthy",
    }


@app.post(
    "/reservations",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_reservation(request: ReservationRequest) -> ReservationResponse:
    """
    Crea una reserva básica.

    En esta primera versión todavía no consulta inventario,
    pagos, notificaciones ni PostgreSQL.
    """
    if request.customer_email.strip() == "":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El correo del cliente es obligatorio",
        )

    return ReservationResponse(
        reservation_id=str(uuid4()),
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        event_id=request.event_id,
        quantity=request.quantity,
        status="created",
        created_at=datetime.now(timezone.utc),
    )