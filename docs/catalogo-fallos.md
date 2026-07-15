\# Catálogo de fallos y mecanismos de inyección



| Escenario de fallo | Mecanismo para provocar el fallo | Defensa propuesta | Tipo de trabajo |

|---|---|---|---|

| Inventario Fantasma | Escalar el Deployment de Inventario a 0 réplicas | Circuit Breaker, timeout y retries con backoff | Implementación - David |

| Pasarela Lenta | Configurar Pagos con una demora de 20 segundos | Timeout, Circuit Breaker y fallback de pago pendiente | Implementación - Juan |

| Diluvio de Peticiones | Ejecutar carga concurrente contra el API Gateway | Bulkhead, límite de concurrencia y límites de recursos | Implementación - David |

| Base de Datos Intermitente | Interrumpir temporalmente la comunicación con PostgreSQL | Reintentos controlados, idempotencia y manejo del pool | Análisis teórico |

| Correo Perdido | Escalar Notificaciones a 0 réplicas | Fallback y registro de notificación pendiente | Implementación - Juan |

| Condición de Carrera | Enviar dos compras simultáneas sobre el último asiento | Transacción, bloqueo pesimista o control optimista | Análisis teórico |

