# Resultados

> Archivo generado por `make demo`. No lo edites a mano: vuelve a correr la demo.

- **Máquina:** Darwin 25.6.0, Apple M4 Pro, 14 núcleos. Docker 29.9.3 con 12 núcleos y 7,7 GB.
- **Fecha de la medición:** 2026-11-21. NATS + Centrifugo/Redis se volvió a medir el 25 de noviembre de 2026.
- **Carga:** 10.000/s (menos en las rutas simuladas: ver su tabla), 100.000 emisores en 1.000 cuentas, 100 pantallas, eventos de 300 bytes.
- **Versiones:** Redpanda 26.3.1, NATS 2.15.3, kinesis-mock 0.6.2, ElasticMQ 1.7.1, Centrifugo 6.10.3, Redis 8-alpine, Zilla 2.7.1, EMQX 6.3.3.
- **Etiquetas:** medido (corrió en esta máquina), simulado (contra un emulador: comprueba que funciona, no cuánto tarda ni cuánto cobra) y modelo (proyección con los supuestos de `escenario.toml`).

- **Concurrencia:** las tablas con varias pantallas por cuenta y la de enriquecer un evento salen de `make concurrencia`, que se midió aparte el 25 de noviembre de 2026.

## Lo que ve la pantalla a 10.000/s

| Ruta | p99 en pantalla (medido) | Aguanta hasta (medido) | Núcleos (medido) | Código propio (medido) |
|---|---|---|---|---|
| Redpanda + Go | 16 ms | >= 80.000/s | 0,10 + 0,20 | 135 líneas |
| Redpanda + Go, 6 s | 16 ms | >= 80.000/s | 0,12 + 0,25 | 135 líneas |
| Redpanda + Node | 20 ms | >= 80.000/s | 0,09 + 0,26 | 88 líneas |
| Redpanda + Centrifugo | 17 ms | >= 80.000/s | 0,10 + 0,19 | 28 de config. |
| Redpanda + Zilla | 22 ms | 20.000/s | 0,08 + 0,64 | 57 de config. |
| Redpanda + EMQX | 18 ms | 40.000/s | 0,12 + 0,57 | 27 de config. |
| NATS + Go | 3,7 ms | >= 80.000/s | 0,31 + 0,26 | 138 líneas |
| NATS + Node | 3,3 ms | 40.000/s | 0,31 + 0,25 | 85 líneas |
| NATS + Centrifugo | 3,9 ms | >= 80.000/s | 0,25 + 0,22 | 29 de config. |
| NATS + Centrifugo/Redis | 9,4 ms | 10.000/s | 0,45 + 0,75 | 44 de config. |

Medido el 21 de noviembre de 2026 en Apple M4 Pro, con Docker, cada pieza limitada a 2 núcleos y 2 GB. NATS + Centrifugo/Redis se volvió a medir el 25 de noviembre de 2026. 100.000 emisores, 100 pantallas, eventos de 300 bytes. Aguanta: la mayor tasa con p99 bajo 1,0 s y sin pérdida; la rampa llega hasta 80.000/s. Núcleos: los que usó el transporte más los que usó la entrega; en la ruta con Redis no cuentan los de Redis, que corre aparte con 1 núcleo. Código propio: líneas que el equipo escribe y mantiene; en Centrifugo, Zilla y EMQX son líneas de configuración. «6 s» es el tiempo de sesión del grupo de Kafka; de fábrica son 45 s en Go y 30 s en Node. En Redpanda + Zilla el productor escribe a Kafka sin comprimir.

## Al matar la pieza que entrega a las pantallas

| Ruta | Congelada (medido) | Atraso máx. (medido) | No llegaron (medido) | Repetidos (medido) | Sin orden (medido) |
|---|---|---|---|---|---|
| Redpanda + Go | 45 s | 45 s | 0 | 23.600 | 0 |
| Redpanda + Go, 6 s | 5,7 s | 5,9 s | 0 | 24.100 | 0 |
| Redpanda + Node | 30 s | 33 s | 0 | 22.700 | 0 |
| Redpanda + Centrifugo | 45 s | 45 s | 0 | 24.100 | 0 |
| Redpanda + Zilla | 19 s | 56 s | 28.669 | 0 | 0 |
| Redpanda + EMQX | 29 s | 30 s | 0 | 34.900 | 0 |
| NATS + Go | < 0,4 s | 30 s | 2.121 | 0 | 100 |
| NATS + Node | 0,3 s | 30 s | 3.159 | 1 | 98 |
| NATS + Centrifugo | < 0,4 s | 30 s | 4.016 | 1 | 96 |
| NATS + Centrifugo/Redis | < 0,4 s | 30 s | 0 | 1 | 73 |

La pieza se mata sin aviso a los 10 s de carga y se levanta de inmediato. Se repite 2 veces por ruta y cada columna muestra su peor valor. Congelada: tiempo sin que llegue nada a la pantalla. Atraso máx.: lo que tardó en llegar el evento más demorado. Sin orden: eventos que llegaron después de uno posterior del mismo emisor; como cada emisor emite cada 10 s, solo se ve un desorden mayor que eso. Las pantallas se reconectan a los 100 ms. No llegaron: eventos que ninguna pantalla recibió hasta 20 s después de terminar la carga.

## Las rutas sobre servicios de AWS, contra emuladores

| Ruta | Tasa (simulado) | Congelada (simulado) | Atraso máx. (simulado) | No llegaron (simulado) | Código propio (medido) |
|---|---|---|---|---|---|
| Kinesis + Go | 200/s | 0,3 s | 2,3 s | 66 | 201 líneas |
| SQS FIFO + Go | 1.000/s | < 0,4 s | 30 s | 190 | 149 líneas |
| SQS FIFO + Centrifugo | 1.000/s | 13 s | 51 s | 60.589 | 29 de config. |

Con carga estable, todas entregaron todo. El orden no se pudo comprobar: a estas tasas cada emisor emite a lo más una vez por corrida. Kinesis y SQS son emuladores locales: comprueban que la ruta funciona y qué hace el código frente a un corte (el peor valor de 2). No dicen cuánto tarda ni cuánto aguanta el servicio real.

## Costo mensual de cada camino

| Camino | 1.000 eventos/s (modelo) | 10.000 eventos/s (modelo) | 100.000 eventos/s (modelo) |
|---|---|---|---|
| Kinesis + Flink | USD 703 | USD 2.428 | USD 22.319 |
| Kinesis + propio | USD 303 | USD 2.219 | USD 22.174 |
| SQS FIFO + Centrifugo | USD 1.013 | USD 9.705 | USD 97.569 |
| SQS FIFO empaquetado | USD 161 | USD 1.190 | USD 12.422 |
| MSK + Centrifugo | USD 997 | USD 1.505 | USD 8.426 |
| Redpanda + Centrifugo | USD 303 | USD 1.001 | USD 8.923 |
| NATS + Centrifugo | USD 303 | USD 1.001 | USD 9.459 |

Modelo, no una factura: precios por demanda de us-east-1 y supuestos en escenario.toml. Flink: administrado, una aplicación por consumidor. Propio: un consumidor escrito a mano. SQS FIFO: con SNS FIFO repartiendo a 3 colas; empaquetado lleva 10 eventos por mensaje y pide consumidor propio. MSK: Kafka administrado. Redpanda y NATS: 3 nodos propios. Incluye transporte, transferencia entre zonas y el cómputo de la entrega para 3 consumidores. La línea base lleva además la pieza que habla WebSocket. No incluye el disco de los brokers propios, Redis para Centrifugo, la salida a internet hacia las pantallas, el balanceador ni horas de personas. Flink no se midió: su costo supone 1 MB por segundo por KPU. A 100.000 eventos por segundo, las aplicaciones de Flink cuestan USD 7.918; USD 15.595 si una KPU rinde la mitad y USD 4.079 si rinde el doble.

## Cuántas horas caídas al mes vale la diferencia

| Camino | Diferencia (modelo) | Hora a USD 100 (modelo) | Hora a USD 1.000 (modelo) | Hora a USD 10.000 (modelo) |
|---|---|---|---|---|
| Kinesis + propio | −USD 208 | −2,1 h | −0,2 h | igual |
| SQS FIFO + Centrifugo | +USD 7.277 | +72,8 h | +7,3 h | +0,7 h |
| SQS FIFO empaquetado | −USD 1.237 | −12,4 h | −1,2 h | −0,1 h |
| MSK + Centrifugo | −USD 922 | −9,2 h | −0,9 h | −0,1 h |
| Redpanda + Centrifugo | −USD 1.426 | −14,3 h | −1,4 h | −0,1 h |
| NATS + Centrifugo | −USD 1.426 | −14,3 h | −1,4 h | −0,1 h |

A 10.000 eventos por segundo, contra la línea base, Kinesis + Flink (USD 2.428 al mes). Cada columna supone un costo distinto de la hora caída. Con signo +, el camino es más caro: conviene solo si evita al menos esas horas de caída al mes. Con signo −, es más barato: sigue conviniendo aunque sume hasta esas horas.

## Varias pantallas por cuenta: hasta dónde aguanta

| Escenario | Entregas/s | Centrifugo (medido) | Centrifugo/Redis (medido) | Go (medido) |
|---|---|---|---|---|
| 1.000 pantallas, 10 por cuenta | 3.330 | >= 26.640/s | >= 26.640/s | >= 26.640/s |
| 2.000 pantallas, 20 por cuenta | 33.340 | 66.680/s | 66.680/s | >= 266.720/s |
| 5.000 pantallas, 50 por cuenta | 83.350 | 83.350/s | 83.350/s | 333.400/s |
| 5.000 pantallas, 25 por cuenta | 166.675 | entrega el 71 % | entrega el 80 % | 166.675/s |

Medido el 25 de noviembre de 2026 en Apple M4 Pro, con Docker (12 núcleos y 7,7 GB). Transporte NATS JetStream; una sola instancia de cada pieza de entrega, limitada a 2 núcleos y 2 GB. Eventos de 1.000 bytes; cada emisor emite cada 30 s. Emisores de cada escenario, en orden: 10.000, 50.000, 50.000, 200.000. Entregas/s: eventos por segundo por las pantallas que miran cada cuenta. Cada celda es la mayor cantidad de entregas por segundo que aguantó: el generador emite todo, no se pierde nada, el p99 queda bajo 1,0 s y las pantallas reciben al menos el 99,9 % de lo esperado. La rampa llega a 8 veces la carga del escenario. «Entrega el N %»: no aguantó ni la carga del escenario, y eso fue lo que alcanzó a entregar.

## Varias pantallas por cuenta: núcleos usados

| Escenario | Entregas/s | Centrifugo (medido) | Centrifugo/Redis (medido) | Go (medido) |
|---|---|---|---|---|
| 1.000 pantallas, 10 por cuenta | 3.330 | 0,18 | 0,20 | 0,17 |
| 2.000 pantallas, 20 por cuenta | 33.340 | 0,24 | 0,33 | 0,42 |
| 5.000 pantallas, 50 por cuenta | 83.350 | 0,58 | 0,66 | 0,70 |
| 5.000 pantallas, 25 por cuenta | 166.675 | no aguanta | no aguanta | 1,47 |

Núcleos que usó la pieza de entrega con la carga del escenario, de los 2 que tiene. En la ruta con Redis no cuentan los de Redis, que corre aparte.

## Varias pantallas por cuenta: el corte

| Escenario | Entregas/s | Centrifugo (medido) | Centrifugo/Redis (medido) | Go (medido) |
|---|---|---|---|---|
| 1.000 pantallas, 10 por cuenta | 3.330 | 1,0 % | 0 | 0,6 % |
| 2.000 pantallas, 20 por cuenta | 33.340 | 1,0 % | 0 | 0,6 % |
| 5.000 pantallas, 50 por cuenta | 83.350 | 1,0 % | 0 | 0,7 % |
| 5.000 pantallas, 25 por cuenta | 166.675 | ya no aguantaba | ya no aguantaba | 0,7 % |

Entregas que no llegaron a su pantalla. La pieza de entrega se mata sin aviso a los 10 s de carga y se levanta de inmediato; todas las pantallas reconectan a la vez, a los 100 ms. Un corte por combinación. El porcentaje es sobre todas las entregas esperadas en los 40 s de carga, sumando todas las pantallas. «Ya no aguantaba»: la pieza no entregaba todo antes del corte, así que lo que faltó después no es del corte. Bajo su techo, la que más tardó en volver a entregar se congeló menos de 0,4 s.

## Eventos por segundo que enriquece un núcleo

| Destinos | Sin reglas (medido) | 100 reglas por cuenta (medido) | 1.000 reglas por cuenta (medido) |
|---|---|---|---|
| 1 | 140.500 | 120.900 | 91.300 |
| 3 | 70.300 | 65.300 | 53.600 |
| 5 | 45.800 | 44.700 | 38.500 |

Medido el 25 de noviembre de 2026 en Apple M4 Pro, con Docker (12 núcleos y 7,7 GB). Un solo hilo en un contenedor limitado a 1 núcleo, con eventos de 1.000 bytes. Por cada evento: lo lee, traduce sus lecturas al nombre y la escala que espera cada destino, evalúa las reglas de la cuenta recordando cuáles estaban activas para ese emisor y arma una salida por destino. No lee el transporte, no escribe a ningún lado y no comparte el estado con otra réplica.
