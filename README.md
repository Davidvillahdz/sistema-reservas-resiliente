\# Sistema de Reservas Resiliente



Sistema distribuido desarrollado para demostrar mecanismos de tolerancia a fallos utilizando microservicios desplegados sobre Kubernetes.



\---



\# Integrantes



\- David Villa Hernández

\- Juan Fernando Álvarez Picón



\---



\# Objetivo



Diseñar, implementar y desplegar un sistema de reservas de entradas basado en microservicios que sea capaz de mantener su disponibilidad ante diferentes escenarios de fallo.



El proyecto implementa mecanismos de resiliencia ampliamente utilizados en arquitecturas distribuidas modernas y demuestra su funcionamiento mediante pruebas controladas sobre un clúster Kubernetes multinodo.



\---



\# Arquitectura del sistema



El sistema está compuesto por los siguientes microservicios:



\- API Gateway

\- Servicio de Reservas

\- Servicio de Inventario

\- Servicio de Pagos

\- Servicio de Notificaciones

\- PostgreSQL



Flujo general:



```

Cliente

&#x20;  │

&#x20;  ▼

API Gateway

&#x20;  │

&#x20;  ▼

Servicio de Reservas

&#x20;  ├────────► Inventario

&#x20;  ├────────► Pagos

&#x20;  ├────────► Notificaciones

&#x20;  │

&#x20;  ▼

PostgreSQL

```



\---



\# Tecnologías utilizadas



\- Python 3.12

\- FastAPI

\- PostgreSQL

\- SQLAlchemy

\- Docker

\- Docker Compose

\- Kubernetes

\- kind

\- k6

\- PowerShell



\---



\# Estructura del proyecto



```

.

├── services/

│   ├── api-gateway/

│   ├── reservas/

│   ├── inventario/

│   ├── pagos/

│   └── notificaciones/

│

├── kubernetes/

│   ├── base/

│   ├── chaos/

│   └── cluster/

│

├── scripts/

│   ├── load/

│   ├── demo/

│   └── concurrency/

│

├── evidence/

│

└── docker-compose.yml

```



\---



\# Requisitos



Antes de ejecutar el proyecto es necesario instalar:



\- Docker Desktop

\- Kubernetes (kubectl)

\- kind

\- Python 3.12

\- Git

\- k6



\---



\# Construcción de imágenes



Cada microservicio debe construirse mediante Docker.



Ejemplo:



```bash

docker build -t sistema-reservas-resiliente-api-gateway ./services/api-gateway

docker build -t sistema-reservas-resiliente-reservas ./services/reservas

docker build -t sistema-reservas-resiliente-inventario ./services/inventario

docker build -t sistema-reservas-resiliente-pagos ./services/pagos

docker build -t sistema-reservas-resiliente-notificaciones ./services/notificaciones

```



Posteriormente las imágenes se cargan al clúster kind.



Ejemplo:



```bash

kind load docker-image sistema-reservas-resiliente-api-gateway:latest --name reservas-cluster

```



\---



\# Despliegue en Kubernetes



Crear el clúster:



```bash

kind create cluster --config kubernetes/cluster/kind-config.yaml

```



Aplicar los recursos:



```bash

kubectl apply -k kubernetes/base

```



Comprobar el estado:



```bash

kubectl get nodes



kubectl get deployments -n reservas-app



kubectl get pods -n reservas-app



kubectl get services -n reservas-app

```



\---



\# Prueba funcional



Crear una reserva mediante el API Gateway.



Ejemplo:



```http

POST /reservations

```



```json

{

&#x20;   "customer\_name": "David Villa",

&#x20;   "customer\_email": "d01072004@gmail.com",

&#x20;   "event\_id": 1,

&#x20;   "quantity": 1

}

```



\---



\# Escenarios de tolerancia a fallos implementados



\## 1. Caída de un Pod



Se elimina manualmente un Pod del Servicio de Reservas para verificar que Kubernetes cree automáticamente una nueva réplica sin afectar la disponibilidad del sistema.



\*\*Mecanismo utilizado\*\*



\- ReplicaSet

\- Deployment



\---



\## 2. Inventario Fantasma



Se simula la caída del Servicio de Inventario.



El Servicio de Reservas utiliza un Circuit Breaker para evitar llamadas repetidas a un servicio que se encuentra fallando.



\*\*Mecanismo utilizado\*\*



\- Circuit Breaker

\- Reintentos

\- Backoff exponencial



\---



\## 3. Pasarela Lenta



Se introduce una demora artificial en el Servicio de Pagos.



Cuando el tiempo de espera es superado, el Servicio de Reservas registra la reserva con estado:



```

payment\_pending

```



permitiendo que la operación continúe.



\*\*Mecanismos utilizados\*\*



\- Timeout

\- Fallback



\---



\## 4. Diluvio de Peticiones



Se genera una carga masiva utilizando k6.



El API Gateway limita el número de solicitudes concurrentes mediante un Bulkhead.



Cuando el límite es alcanzado responde con:



```

HTTP 429

```



sin comprometer la estabilidad del sistema.



\*\*Mecanismo utilizado\*\*



\- Bulkhead



\---



\# Evidencias



Las pruebas realizadas se encuentran documentadas en la carpeta:



```

evidence/

```



Incluye:



\- prueba-caida-pod-reservas.md

\- prueba-inventario-fantasma.md

\- prueba-pasarela-lenta.md

\- prueba-diluvio-peticiones.md



\---



\# Resultados obtenidos



Durante las pruebas se comprobó que:



\- Kubernetes recupera automáticamente Pods eliminados.

\- El Circuit Breaker evita llamadas repetidas hacia servicios caídos.

\- El timeout y el fallback permiten continuar el flujo de negocio ante servicios lentos.

\- El Bulkhead protege al API Gateway frente a grandes volúmenes de solicitudes.

\- PostgreSQL mantiene la persistencia de las reservas.

\- El sistema conserva su disponibilidad durante los escenarios de fallo.



\---



\# Conclusiones



La implementación permitió comprobar la importancia de aplicar mecanismos de resiliencia en sistemas distribuidos.



Cada estrategia implementada protege un tipo diferente de fallo:



\- Kubernetes garantiza la alta disponibilidad mediante la recreación automática de Pods.

\- Circuit Breaker evita fallos en cascada.

\- Timeout y Fallback reducen el impacto de servicios con alta latencia.

\- Bulkhead limita el consumo de recursos y evita la saturación del sistema.



La combinación de estos mecanismos incrementa significativamente la disponibilidad y confiabilidad de la aplicación.



\---



\# Autores



\*\*David Villa Hernández\*\*



\*\*Juan Fernando Álvarez Picón\*\*



Universidad Politécnica Salesiana



Computación



2026

