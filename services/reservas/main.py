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
    version="1.4.0",
)

INVENTORY_URL = os.getenv(
    "INVENTORY_URL",
    "http://localhost:8002",
)

PAYMENT_URL = os.getenv(
    "PAYMENT_URL",
    "http://localhost:8003",
)

NOTIFICATION_URL = os.getenv(
    "NOTIFICATION_URL",
    "http://localhost:8004",
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
    payment_status: Literal["approved", "payment_pending"]
    notification_status: Literal["sent", "notification_pending"]
    status: Literal["approved", "payment_pending"]
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


async def call_payment(
    reservation_id: str,
    quantity: int,
) -> Literal["approved", "payment_pending"]:
    """
    Consulta Pagos con un timeout corto.

    Si Pagos demora demasiado, está caído o responde con error,
    la reserva continúa con estado payment_pending.
    """

    payment_payload = {
        "reservation_id": reservation_id,
        "amount": float(quantity * 25),
        "card_token": "tok_demo_1234",
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            payment_response = await client.post(
                f"{PAYMENT_URL}/payments",
                json=payment_payload,
            )

        if payment_response.status_code != status.HTTP_201_CREATED:
            return "payment_pending"

        payment_data = payment_response.json()

        if payment_data.get("status") != "approved":
            return "payment_pending"

        return "approved"

    except (
        httpx.TimeoutException,
        httpx.RequestError,
        ValueError,
    ):
        return "payment_pending"


async def call_notification(
    reservation_id: str,
    customer_email: str,
) -> Literal["sent", "notification_pending"]:
    """
    Intenta enviar el correo de confirmación.

    Si Notificaciones está caído, demora demasiado o responde con error,
    la reserva continúa y el correo queda como notification_pending.
    """

    notification_payload = {
        "reservation_id": reservation_id,
        "customer_email": customer_email,
        "message": "Su reserva fue registrada correctamente",
    }

    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            notification_response = await client.post(
                f"{NOTIFICATION_URL}/notifications",
                json=notification_payload,
            )

        if notification_response.status_code != status.HTTP_201_CREATED:
            return "notification_pending"

        notification_data = notification_response.json()

        if notification_data.get("status") != "sent":
            return "notification_pending"

        return "sent"

    except (
        httpx.TimeoutException,
        httpx.RequestError,
        ValueError,
    ):
        return "notification_pending"


@app.post(
    "/reservations",
    response_model=ReservationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(
    request: ReservationRequest,
) -> ReservationResponse:
    """
    Crea una reserva, descuenta inventario y procesa el pago.

    Si Pagos tarda demasiado, la reserva se guarda como payment_pending.

    Después de guardar la reserva, intenta enviar la notificación.
    Si Notificaciones no está disponible, la reserva se conserva y
    el correo queda registrado como notification_pending.
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

    if inventory_response.status_code == status.HTTP_404_NOT_FOUND:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="El evento solicitado no existe",
        )

    if inventory_response.status_code == status.HTTP_409_CONFLICT:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe inventario suficiente",
        )

    if inventory_response.status_code != status.HTTP_200_OK:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Respuesta inesperada del Servicio de Inventario",
        )

    inventory_data = inventory_response.json()

    reservation_id = uuid4()
    created_at = datetime.now(timezone.utc)

    payment_status = await call_payment(
        reservation_id=str(reservation_id),
        quantity=request.quantity,
    )

    db = SessionLocal()

    try:
        reservation = Reservation(
            id=reservation_id,
            customer_name=request.customer_name,
            customer_email=request.customer_email,
            event_id=request.event_id,
            quantity=request.quantity,
            status=payment_status,
            notification_status="notification_pending",
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

    notification_status = await call_notification(
        reservation_id=str(reservation_id),
        customer_email=request.customer_email,
    )

    if notification_status == "sent":
        update_db = SessionLocal()

        try:
            saved_reservation = (
                update_db.query(Reservation)
                .filter(Reservation.id == reservation_id)
                .first()
            )

            if saved_reservation is not None:
                saved_reservation.notification_status = "sent"
                update_db.commit()

        except SQLAlchemyError:
            update_db.rollback()
            notification_status = "notification_pending"

        finally:
            update_db.close()

    return ReservationResponse(
        reservation_id=str(reservation_id),
        customer_name=request.customer_name,
        customer_email=request.customer_email,
        event_id=request.event_id,
        quantity=request.quantity,
        remaining_inventory=inventory_data["remaining"],
        payment_status=payment_status,
        notification_status=notification_status,
        status=payment_status,
        created_at=created_at,
    )