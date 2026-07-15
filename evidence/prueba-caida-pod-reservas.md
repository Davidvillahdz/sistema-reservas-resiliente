\## Objetivo



Comprobar que el sistema mantiene la disponibilidad cuando una de las dos réplicas del Servicio de Reservas deja de funcionar.



\## Estado inicial



Antes de inyectar el fallo se verificó que:



\- El Deployment de Reservas tenía 2 réplicas disponibles.

\- Una réplica estaba desplegada en reservas-cluster-worker.

\- La segunda réplica estaba desplegada en reservas-cluster-worker2.

\- El API Gateway procesaba reservas correctamente.

\- La solicitud inicial devolvió el estado inventory\_confirmed.



\## Fallo inyectado



Se seleccionó uno de los pods de Reservas y se eliminó manualmente con:



kubectl delete pod $podEliminar -n reservas-app



El pod eliminado fue:



reservas-cb7f7cc66-b9lfh

Comportamiento observado



Después de eliminar el pod:



La segunda réplica permaneció en estado Running.

El Deployment creó automáticamente un nuevo pod.

Durante la recuperación se realizó otra solicitud de reserva.

La solicitud fue procesada correctamente con estado inventory\_confirmed.

El nuevo pod alcanzó el estado Ready.

El Deployment volvió a tener 2 réplicas disponibles.

Evidencias técnicas



Estado final del Deployment:

READY   UP-TO-DATE   AVAILABLE

2/2     2            2

El nuevo pod fue programado nuevamente en el clúster y quedó en estado Running.



Durante el proceso apareció temporalmente un evento FailedScheduling, provocado por la regla de anti-afinidad entre réplicas. Kubernetes volvió a evaluar la programación y ubicó correctamente el pod en un nodo disponible.



Resultado



La aplicación continuó procesando reservas aunque una instancia del Servicio de Reservas fue eliminada.



Conclusión



La combinación de dos réplicas, un Service de Kubernetes y el controlador Deployment permitió mantener la disponibilidad del Servicio de Reservas. Kubernetes detectó la pérdida del pod, creó una nueva réplica y restauró automáticamente el estado deseado del sistema.

