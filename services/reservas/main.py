import asyncio
import os
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError

from circuit_breaker import AsyncCircuitBreaker, CircuitOpenError
from database import SessionLocal
from models import Reservation


app = FastAPI(
    title="Servicio de Reservas",
    description="Servicio principal para procesar reservas de entradas.",
    version="1.2.0",
)

INVENTORY_URL = os.getenv(
    "INVENTORY_URL",
    "http://localhost:8002",
)

inventory_cb = AsyncCircuitBreaker(
    failure_threshold=3,
    recovery_timeout=15.0,
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
    remaining_inventory: int
    status: Literal["inventory_confirmed"]
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


@app.get("/circuit-breaker/status")
async def circuit_breaker_status() -> dict[str, str | int | float | None]:
    return await inventory_cb.get_status()


async def call_inventory(
    endpoint: str,
    quantity: int,
) -> httpx.Response:
    """
    Consulta Inventario usando timeout, reintentos con backoff
    y Circuit Breaker.
    """

    async def operation() -> httpx.Response:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.post(
                endpoint,
                json={"quantity": quantity},
            )

        if response.status_code >= 500:
            raise httpx.HTTPStatusError(
                "El Servicio de Inventario presentó un error",
                request=response.request,
                response=response,
            )

        return response

    retries = 3

    for attempt in range(retries):
        try:
            return await inventory_cb.call(operation)

        except CircuitOpenError:
            raise

        except (
            httpx.TimeoutException,
            httpx.RequestError,
            httpx.HTTPStatusError,
        ):
            if attempt == retries - 1:
                raise

            backoff_seconds = 2**attempt
            await asyncio.sleep(backoff_seconds)

    raise RuntimeError("No fue posible completar la llamada a Inventario")


@app.post(
    "/reservations",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    request: ReservationRequest,
) -> ReservationResponse:
    """
    Crea una reserva después de confirmar y descontar inventario.
    """

    inventory_endpoint = (
        f"{INVENTORY_URL}/inventory/"
        f"{request.event_id}/discount"
    )

    try:
        inventory_response = await call_inventory(
            endpoint=inventory_endpoint,
            quantity=request.quantity,
        )

    except CircuitOpenError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El Servicio de Inventario está temporalmente bloqueado "
                "por el Circuit Breaker"
            ),
        ) from exc

    except httpx.TimeoutException as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                "El Servicio de Inventario tardó demasiado en responder "
                "después de varios intentos"
            ),
        ) from exc

    except httpx.RequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=(
                "El Servicio de Inventario no está disponible "
                "después de varios intentos"
            ),
        ) from exc

    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El Servicio de Inventario presentó un error interno",
        ) from exc

    if inventory_response.status_code == 404:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El evento solicitado no existe",
        )

    if inventory_response.status_code == 409:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe inventario suficiente",
        )

    if inventory_response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta inesperada del Servicio de Inventario",
        )

    inventory_data = inventory_response.json()

    reservation_id = uuid4()
    created_at = datetime.now(timezone.utc)

    db = SessionLocal()

    try:
        reservation = Reservation(
            id=reservation_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            event_id=request.event_id,
            quantity=request.quantity,
            status="inventory_confirmed",
            created_at=created_at,
        )

        db.add(reservation)
        db.commit()

    except SQLAlchemyError as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="No fue posible guardar la reserva en PostgreSQL",
        ) from exc

    finally:
        db.close()

    return ReservationResponse(
        reservation_id=str(reservation_id),
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        event_id=request.event_id,
        quantity=request.quantity,
        remaining_inventory=inventory_data["remaining"],
        status="inventory_confirmed",
        created_at=created_at,
    )