import os

import httpx
from fastapi import FastAPI, HTTPException, Request, status


app = FastAPI(
    title="API Gateway - Sistema de Reservas",
    description="Punto de entrada del sistema distribuido.",
    version="1.1.0",
)

RESERVATION_URL = os.getenv(
    "RESERVATION_URL",
    "http://localhost:8001",
)


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


@app.post("/reservations", status_code=status.HTTP_201_CREATED)
async def create_reservation(request: Request) -> dict:
    """Reenvía la solicitud al Servicio de Reservas."""

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
            detail="El Servicio de Reservas tardó demasiado en responder",
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
                "detail": "Error recibido desde el Servicio de Reservas"
            }

        detail = error_body.get("detail", error_body)

        raise HTTPException(
            status_code=response.status_code,
            detail=detail,
        )

    return response.json()