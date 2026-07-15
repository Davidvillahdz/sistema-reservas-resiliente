import asyncio
import os

import httpx
from fastapi import FastAPI, HTTPException, Request, status


app = FastAPI(
    title="API Gateway - Sistema de Reservas",
    description=(
        "Punto de entrada del sistema distribuido "
        "protegido mediante el patrón Bulkhead."
    ),
    version="1.2.0",
)

RESERVATION_URL = os.getenv(
    "RESERVATION_URL",
    "http://localhost:8001",
)

MAX_CONCURRENT_REQUESTS = int(
    os.getenv("MAX_CONCURRENT_REQUESTS", "5")
)

active_requests = 0
rejected_requests = 0
bulkhead_lock = asyncio.Lock()


async def enter_bulkhead() -> bool:
    """
    Intenta reservar un espacio dentro del Bulkhead.

    Retorna False cuando ya se alcanzó el máximo de solicitudes
    concurrentes permitidas.
    """

    global active_requests
    global rejected_requests

    async with bulkhead_lock:
        if active_requests >= MAX_CONCURRENT_REQUESTS:
            rejected_requests += 1
            return False

        active_requests += 1
        return True


async def leave_bulkhead() -> None:
    """Libera un espacio del Bulkhead al terminar la solicitud."""

    global active_requests

    async with bulkhead_lock:
        active_requests = max(0, active_requests - 1)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "api-gateway",
        "message": "API Gateway funcionando correctamente",
        "status": "ok",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "service": "api-gateway",
        "status": "healthy",
    }


@app.get("/bulkhead/status")
async def bulkhead_status() -> dict[str, int]:
    """Permite observar el estado actual del Bulkhead."""

    async with bulkhead_lock:
        return {
            "maximum_concurrent_requests": MAX_CONCURRENT_REQUESTS,
            "active_requests": active_requests,
            "available_slots": max(
                0,
                MAX_CONCURRENT_REQUESTS - active_requests,
            ),
            "rejected_requests": rejected_requests,
        }


@app.post(
    "/reservations",
    status_code=status.HTTP_201_CREATED,
)
async def create_reservation(request: Request) -> dict:
    """
    Reenvía la solicitud al Servicio de Reservas.

    El patrón Bulkhead limita el número de solicitudes simultáneas.
    Cuando no hay espacios disponibles, responde 429 rápidamente.
    """

    admitted = await enter_bulkhead()

    if not admitted:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                "El sistema alcanzó el límite de solicitudes "
                "concurrentes. Intente nuevamente."
            ),
            headers={"Retry-After": "1"},
        )

    try:
        payload = await request.json()

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                response = await client.post(
                    f"{RESERVATION_URL}/reservations",
                    json=payload,
                )

        except httpx.TimeoutException as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=(
                    "El Servicio de Reservas tardó demasiado "
                    "en responder"
                ),
            ) from exc

        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="El Servicio de Reservas no está disponible",
            ) from exc

        if response.status_code >= 400:
            try:
                error_body = response.json()
            except ValueError:
                error_body = {
                    "detail": (
                        "Error recibido desde el Servicio de Reservas"
                    )
                }

            detail = error_body.get("detail", error_body)

            raise HTTPException(
                status_code=response.status_code,
                detail=detail,
            )

        return response.json()

    finally:
        await leave_bulkhead()