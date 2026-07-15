\# Prueba de resiliencia: Pasarela Lenta



\## Objetivo



Comprobar que el sistema continúa procesando reservas cuando el Servicio de Pagos presenta una alta latencia, utilizando un timeout y un mecanismo de fallback.



\## Mecanismo implementado



El Servicio de Pagos fue configurado para responder lentamente mediante las variables:



\- FORCE\_SLOW\_PAYMENT=true

\- SLOW\_PAYMENT\_SECONDS=20



El Servicio de Reservas utiliza:



\- Timeout de 3 segundos para la comunicación con Pagos.

\- Fallback automático cuando el timeout es excedido.

\- Estado `payment\_pending` para permitir continuar con la reserva.



\## Inyección del fallo



Se desplegó el servicio de pagos con una demora artificial de 20 segundos.



Archivo utilizado:



```

kubernetes/base/pagos.yaml

```



Variables configuradas:



```yaml

FORCE\_SLOW\_PAYMENT=true

SLOW\_PAYMENT\_SECONDS=20

```



\## Ejecución



Se envió una solicitud de reserva al API Gateway.



Ejemplo:



```http

POST /reservations

```



Datos enviados:



```json

{

&#x20; "customer\_name": "Juan Alvarez",

&#x20; "customer\_email": "jfernandoalz18@gmail.com",

&#x20; "event\_id": 1,

&#x20; "quantity": 1

}

```



\## Resultado obtenido



La reserva fue creada correctamente.



Respuesta del sistema:



```text

reservation\_id : 263ba0a5-d9f8-468f-978b-de66bd8fc70c



customer\_name : Juan Alvarez



customer\_email : jfernandoalz18@gmail.com



event\_id : 1



quantity : 1



remaining\_inventory : 98



payment\_status : payment\_pending



status : payment\_pending

```



El tiempo de respuesta fue aproximadamente 3 segundos, demostrando que el timeout evitó esperar los 20 segundos configurados en el servicio de pagos.



\## Estado del sistema



Durante la prueba:



\- El Servicio de Pagos continuó ejecutándose.

\- El Servicio de Reservas no se bloqueó.

\- La reserva fue almacenada correctamente.

\- No se produjeron reinicios de Pods.



\## Análisis



El timeout permitió detectar rápidamente la lentitud del Servicio de Pagos.



En lugar de cancelar la operación, el Servicio de Reservas aplicó un fallback, registrando la reserva con estado `payment\_pending`.



Esto evita afectar la experiencia del usuario y mantiene disponible el sistema aun cuando un servicio secundario presenta problemas de rendimiento.



\## Conclusión



La estrategia de timeout más fallback funcionó correctamente.



El sistema mantuvo su disponibilidad, permitió registrar la reserva y dejó pendiente únicamente la confirmación del pago, evitando que una alta latencia en el Servicio de Pagos afectara el resto de la aplicación.

