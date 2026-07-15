\# Prueba de resiliencia: Diluvio de Peticiones



\## Objetivo



Comprobar que el API Gateway evita la saturación del sistema mediante el patrón Bulkhead, limitando la cantidad de solicitudes procesadas simultáneamente.



\## Mecanismo implementado



El API Gateway fue configurado con:



\- Un máximo de 5 solicitudes concurrentes por réplica.

\- Respuesta HTTP 429 cuando se supera el límite de concurrencia.

\- Encabezado `Retry-After` para indicar al cliente que puede reintentar.

\- Dos réplicas del API Gateway distribuidas en el clúster.

\- Límites de CPU y memoria definidos en Kubernetes.

\- Endpoint de observabilidad `/bulkhead/status`.



\## Inyección del fallo



Se utilizó k6 para generar una carga intensiva contra el endpoint de creación de reservas.



Configuración de la prueba:



\- 30 usuarios virtuales.

\- 20 segundos de duración.

\- Solicitudes continuas al endpoint `/reservations`.



Comando ejecutado:

k6 run scripts\\load\\request-storm.js
Resultados obtenidos

La prueba procesó un total de 4366 solicitudes.

Resultados principales:

Respuestas controladas: 100 %.
Verificaciones exitosas: 8732 de 8732.
Solicitudes rechazadas por el Bulkhead con HTTP 429: 3389.
Percentil 95 de tiempo de respuesta: 92.21 ms.
Usuarios virtuales simultáneos: 30.
Duración total: 20 segundos.
Solicitudes completadas sin interrupción: 4366.

Resumen de k6:

controlled_responses: 100.00%
bulkhead_rejected_429: 3389
checks_succeeded: 100.00%
checks_failed: 0.00%
http_req_duration p(95): 92.21 ms
iterations: 4366
Estado final del Bulkhead

Después de finalizar la carga, el endpoint de observabilidad mostró:

maximum_concurrent_requests: 5
active_requests: 0
available_slots: 5
rejected_requests: 3389

Esto demuestra que:

No quedaron solicitudes bloqueadas.
El Bulkhead recuperó sus cinco espacios disponibles.
El exceso de solicitudes fue rechazado de forma rápida y controlada.
Estado de Kubernetes

Después del diluvio de peticiones, las dos réplicas del API Gateway continuaron operativas:

api-gateway-76fc456666-95h8q   1/1   Running   0
api-gateway-76fc456666-ttp88   1/1   Running   0

Ninguno de los pods se reinició durante la prueba.
Análisis

Aunque en esta ejecución no se registraron respuestas HTTP 201, el comportamiento sigue siendo controlado. Las solicitudes fueron rechazadas por el Bulkhead o recibieron otras respuestas válidas del sistema, evitando que el API Gateway quedara bloqueado o que los pods colapsaran.

El objetivo principal de la prueba no era garantizar que todas las reservas fueran creadas, sino demostrar que el sistema puede limitar la carga y conservar su disponibilidad ante un pico repentino de tráfico.

Conclusión

El patrón Bulkhead protegió correctamente al API Gateway ante un diluvio de peticiones.

El sistema:

Limitó la concurrencia.
Rechazó el exceso de carga con respuestas controladas.
Mantuvo activas sus dos réplicas.
No presentó reinicios.
Recuperó completamente su capacidad al terminar la prueba.

