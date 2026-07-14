from fastapi import FastAPI

app = FastAPI(
    title="API Gateway - Sistema de Reservas",
    description="Punto de entrada del sistema distribuido de venta de entradas.",
    version="1.0.0",
)


@app.get("/")
def root() -> dict[str, str]:
    """Devuelve información básica del API Gateway."""
    return {
        "service": "api-gateway",
        "message": "API Gateway funcionando correctamente",
        "status": "ok",
    }


@app.get("/health")
def health_check() -> dict[str, str]:
    """Permite comprobar si el servicio se encuentra disponible."""
    return {
        "service": "api-gateway",
        "status": "healthy",
    }