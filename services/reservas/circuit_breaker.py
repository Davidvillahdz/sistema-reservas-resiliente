import asyncio
import time
from enum import Enum
from typing import Awaitable, Callable, TypeVar


T = TypeVar("T")


class CircuitState(str, Enum):
    """Estados posibles de un Circuit Breaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitOpenError(Exception):
    """Se lanza cuando una llamada es rechazada porque el circuito está abierto."""


class AsyncCircuitBreaker:
    """
    Circuit Breaker asíncrono para proteger llamadas entre microservicios.

    Funcionamiento:
    - CLOSED: permite las solicitudes normalmente.
    - OPEN: rechaza solicitudes sin contactar al servicio externo.
    - HALF_OPEN: permite una solicitud de prueba para comprobar recuperación.
    """

    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_timeout: float = 15.0,
    ) -> None:
        if failure_threshold < 1:
            raise ValueError("failure_threshold debe ser mayor que cero")

        if recovery_timeout <= 0:
            raise ValueError("recovery_timeout debe ser mayor que cero")

        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.opened_at: float | None = None

        self._lock = asyncio.Lock()
        self._half_open_request_in_progress = False

    async def call(
        self,
        operation: Callable[[], Awaitable[T]],
    ) -> T:
        """Ejecuta una operación protegida por el Circuit Breaker."""

        await self._before_call()

        try:
            result = await operation()
        except Exception:
            await self._record_failure()
            raise

        await self._record_success()
        return result

    async def _before_call(self) -> None:
        async with self._lock:
            if self.state == CircuitState.CLOSED:
                return

            if self.state == CircuitState.OPEN:
                if self.opened_at is None:
                    self.opened_at = time.monotonic()

                elapsed = time.monotonic() - self.opened_at

                if elapsed < self.recovery_timeout:
                    raise CircuitOpenError(
                        "Circuit Breaker abierto para el Servicio de Inventario"
                    )

                self.state = CircuitState.HALF_OPEN
                self._half_open_request_in_progress = False

            if self.state == CircuitState.HALF_OPEN:
                if self._half_open_request_in_progress:
                    raise CircuitOpenError(
                        "Circuit Breaker en prueba de recuperación"
                    )

                self._half_open_request_in_progress = True

    async def _record_success(self) -> None:
        async with self._lock:
            self.failure_count = 0
            self.opened_at = None
            self.state = CircuitState.CLOSED
            self._half_open_request_in_progress = False

    async def _record_failure(self) -> None:
        async with self._lock:
            self.failure_count += 1
            self._half_open_request_in_progress = False

            if (
                self.state == CircuitState.HALF_OPEN
                or self.failure_count >= self.failure_threshold
            ):
                self.state = CircuitState.OPEN
                self.opened_at = time.monotonic()

    async def get_status(self) -> dict[str, str | int | float | None]:
        """Devuelve información observable sobre el estado del circuito."""

        async with self._lock:
            remaining_seconds: float | None = None

            if self.state == CircuitState.OPEN and self.opened_at is not None:
                elapsed = time.monotonic() - self.opened_at
                remaining_seconds = max(
                    0.0,
                    self.recovery_timeout - elapsed,
                )

            return {
                "state": self.state.value,
                "failure_count": self.failure_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout_seconds": self.recovery_timeout,
                "remaining_open_seconds": remaining_seconds,
            }