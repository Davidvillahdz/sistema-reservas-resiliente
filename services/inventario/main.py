from typing import Literal

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field


app = FastAPI(
    title="Servicio de Inventario",
    description="Servicio encargado de consultar y descontar entradas.",
    version="1.0.0",
)


class InventoryItem(BaseModel):
    event_id: int
    event_name: str
    available: int


class DiscountRequest(BaseModel):
    quantity: int = Field(ge=1, le=10)


class DiscountResponse(BaseModel):
    event_id: int
    discounted: int
    remaining: int
    status: Literal["confirmed"]


inventory: dict[int, InventoryItem] = {
    1: InventoryItem(
        event_id=1,
        event_name="Concierto de prueba",
        available=100,
    ),
    2: InventoryItem(
        event_id=2,
        event_name="Festival tecnológico",
        available=50,
    ),
}


@app.get("/")
def root() -> dict[str, str]:
    return {
        "service": "inventario",
        "message": "Servicio de Inventario funcionando correctamente",
        "status": "ok",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    return {
        "service": "inventario",
        "status": "healthy",
    }


@app.get("/inventory/{event_id}", response_model=InventoryItem)
def get_inventory(event_id: int) -> InventoryItem:
    item = inventory.get(event_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    return item


@app.post(
    "/inventory/{event_id}/discount",
    response_model=DiscountResponse,
)
def discount_inventory(
    event_id: int,
    request: DiscountRequest,
) -> DiscountResponse:
    item = inventory.get(event_id)

    if item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evento no encontrado",
        )

    if item.available < request.quantity:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="No existe inventario suficiente",
        )

    item.available -= request.quantity

    return DiscountResponse(
        event_id=event_id,
        discounted=request.quantity,
        remaining=item.available,
        status="confirmed",
    )