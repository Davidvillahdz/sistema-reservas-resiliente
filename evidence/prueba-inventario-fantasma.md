\# Prueba de resiliencia: Inventario Fantasma



\## Objetivo



Comprobar que el Servicio de Reservas maneja de forma controlada la caída total del Servicio de Inventario mediante timeout, reintentos con backoff y Circuit Breaker.



\## Mecanismo implementado



El Servicio de Reservas utiliza:



\- Timeout de 3 segundos.

\- Tres intentos de comunicación.

\- Backoff exponencial entre intentos.

\- Circuit Breaker con umbral de 3 fallos.

\- Tiempo de recuperación de 15 segundos.



\## Estado inicial



El Circuit Breaker se encontraba cerrado:





state: closed

failure\_count: 0

failure\_threshold: 3

Fallo inyectado



El Servicio de Inventario fue escalado a cero réplicas:

kubectl scale deployment inventario --replicas=0 -n reservas-app

Resultado durante el fallo



Después de tres fallos consecutivos, el Circuit Breaker cambió a estado abierto:
state: open

failure\_count: 3

failure\_threshold: 3

Las solicitudes siguientes fueron rechazadas rápidamente sin volver a contactar Inventario. El tiempo observado fue aproximadamente:

1.02 segundos

Recuperación



Inventario fue restaurado con dos réplicas:

kubectl scale deployment inventario --replicas=2 -n reservas-app

Después del tiempo de recuperación, una nueva solicitud fue procesada correctamente:



status: inventory\_confirmed

remaining\_inventory: 99
Conclusión



El sistema evitó mantener solicitudes bloqueadas contra un servicio caído, rechazó llamadas posteriores de forma rápida y recuperó automáticamente la comunicación cuando Inventario volvió a estar disponible.

