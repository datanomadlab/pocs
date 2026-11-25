# Concurrencia: miles de pantallas, varias por cuenta

En `make demo` cada cuenta la mira una sola pantalla: cada evento se entrega una vez y hay 100
conexiones. Eso mide el costo por evento, no un sistema con usuarios concurrentes. Esta prueba
agrega lo que faltaba: **varias pantallas mirando la misma cuenta**.

Lo que carga a la pieza de entrega deja de ser lo que entra y pasa a ser lo que sale:

```
entregas por segundo = eventos por segundo x pantallas que miran cada cuenta
```

Con 6.667 eventos por segundo y 25 pantallas por cuenta, la pieza entrega 166.675 mensajes por segundo.

## Correrlo

```bash
make setup
make concurrencia                 # 4 escenarios x 3 rutas, cerca de una hora
make concurrencia RAPIDO=1        # una combinación chica, para ver que todo levanta
make concurrencia RUTAS=nats-go   # solo algunas rutas
```

Por cada escenario y ruta corre carga nominal (30 s), rampa a 2, 4 y 8 veces, y un corte: mata la
pieza de entrega con todas las pantallas conectadas, que reconectan a la vez. Muestra cada fase en
la terminal y guarda todo en `data/concurrencia.json`. No toca `data/medicion.json` ni `docs/resultados.md`.

Los escenarios están en [src/stream/concurrencia.py](../src/stream/concurrencia.py). Cada pantalla
mira una cuenta, así que pantallas = cuentas x espectadores. Un emisor emite cada 30 s.

## Qué cambió para poder medirlo

- **La sonda acepta `-espectadores N`.** Cada cuenta la miran N pantallas. Una de ellas es la
  principal y sus entregas se clasifican como siempre (nuevo, repetido, desordenado); las de las
  demás se cuentan como copias y entran a la latencia. Con `-espectadores 1` se comporta igual que antes.
- **`ESPECTADORES` en `.env`** llega a la sonda también en `make demo`. Por defecto es 1.
- **La sonda tiene más núcleos en esta prueba** (`compose.concurrencia.yaml`): hace de miles de
  pantallas y con 2 núcleos sería ella el cuello de botella. Las piezas medidas conservan su tope de
  2 núcleos y 2 GB.

## Resultados

Medido el 2026-11-24 en un Apple M5 Pro (Docker con 15 núcleos y 8 GB), eventos de 1.143 bytes,
transporte NATS JetStream, una sola instancia de cada pieza de entrega.

### Hasta dónde aguanta una instancia de 2 núcleos

| Escenario | Entregas por segundo | Centrifugo | Centrifugo con Redis | Consumidor propio en Go |
|---|---|---|---|---|
| 10.000 emisores, 1.000 pantallas, 10 por cuenta | 3.330 | Aguanta 8 veces más | Aguanta 8 veces más | Aguanta 8 veces más |
| 50.000 emisores, 2.000 pantallas, 20 por cuenta | 33.340 | Aguanta 66.680, falla a 133.360 | Aguanta 66.680, falla a 133.360 | Aguanta 266.720 |
| 50.000 emisores, 5.000 pantallas, 50 por cuenta | 83.350 | Aguanta, falla al doble | Aguanta, falla al doble | Aguanta 333.400, falla a 666.800 |
| 200.000 emisores, 5.000 pantallas, 25 por cuenta | 166.675 | No aguanta: entrega el 90 % | No aguanta: entrega el 93 % | Aguanta, falla al doble |

"Aguanta" es lo mismo que en el experimento (el generador emite todo, no se pierde nada y el p99
queda bajo 1 s) más una condición: todos los espectadores reciben al menos el 99,9 % de lo esperado.
Mientras aguantan, el p99 queda bajo 20 ms en Centrifugo y bajo 54 ms en Go.

Núcleos usados por la pieza de entrega con carga nominal:

| Entregas por segundo | Pantallas | Centrifugo | Centrifugo con Redis | Go |
|---|---|---|---|---|
| 3.330 | 1.000 | 0,11 | 0,15 | 0,11 |
| 33.340 | 2.000 | 0,21 | 0,36 | 0,41 |
| 83.350 | 5.000 | 0,49 | 0,59 | 0,65 |
| 166.675 | 5.000 | no aguanta | no aguanta | 1,22 |

### Corte con todas las pantallas reconectando a la vez

Porcentaje de entregas que no llegaron.

| Pantallas | Centrifugo | Centrifugo con Redis | Consumidor propio en Go |
|---|---|---|---|
| 1.000 | 1,0 % | 0 | 0,6 % |
| 2.000 | 1,1 % | 0 | 0,7 % |
| 5.000 (50.000 emisores) | 1,5 % | 0 | 1,8 % |
| 5.000 (200.000 emisores) | colapsa, ya estaba sobre su techo | colapsa | 3,2 % |

Bajo su techo, todas vuelven en menos de 0,3 s.

## Qué se lee de esto

- **El consumidor en Go escala lineal y se frena por CPU.** Llega a unas 300.000 entregas por
  segundo con los 2 núcleos llenos.
- **Centrifugo falla entre 83.000 y 133.000 entregas por segundo, y no por CPU.** Repetida esa
  carga midiendo todo, el servidor usaba 0,55 de sus 2 núcleos y la sonda 4,8 de 8. Algo encola
  mensajes y termina cortando conexiones. No quedó aislado si el límite es de Centrifugo o de la
  librería cliente que usa la sonda: es un techo provisorio.
- **Centrifugo con Redis es la única que no pierde nada en el corte**, igual que en el experimento
  con 100 pantallas, ahora con hasta 5.000 reconectando a la vez.
- **El primer techo llega por usuarios, no por emisores.** 50.000 emisores son 1.667 eventos por
  segundo, poco para cualquier pieza; con 50 pantallas por cuenta son 83.350 entregas.

Pasado el techo de una instancia quedan dos palancas: entregar menos (el último valor por emisor
cada pocos segundos, canales por grupo o por zona en vez de por cuenta) o repartir entre varias
réplicas, que en Centrifugo exige Redis.

## Cuánto cuesta enriquecer un evento antes de entregarlo

Si entre el transporte y las pantallas va una pieza que agrega información a cada evento, hay que
saber cuánto pesa. [servicios/go/internal/decorador](../servicios/go/internal/decorador) es un
prototipo mínimo: lee el evento, traduce sus señales según el tipo de emisor y la plataforma de
destino, evalúa las geocercas de la cuenta recordando en cuáles estaba el emisor, y arma una salida
por plataforma.

```bash
cd servicios/go && go test ./internal/decorador -run xxx -bench . -benchtime 2s -cpu 1
```

Eventos por segundo en un núcleo (M5 Pro), con 150 tipos de emisor y 500 cuentas:

| Plataformas de destino | Sin geocercas | 150 geocercas por cuenta | 2.000 geocercas por cuenta |
|---|---|---|---|
| 1 | 86.000 | 87.200 | 54.100 |
| 3 | 48.300 | 48.700 | 36.100 |
| 5 | 33.200 | 33.700 | 27.600 |

Es un solo hilo en memoria: no lee el transporte, no escribe y no comparte estado con otra réplica.
Dice que el costo de CPU de enriquecer es chico frente al de entregar; no dice nada de cómo se
reparte ese trabajo entre réplicas.

## El límite

- **Un solo lector del transporte.** No hay dos réplicas repartiéndose particiones o shards, ni se
  mide cuánto se congela la pantalla cuando cae una, ni qué pasa con el estado por emisor (en qué
  geocercas estaba) cuando su partición cambia de dueño.
- **Una sola instancia de la pieza de entrega.** Varias réplicas de Centrifugo necesitan Redis para
  repartirse las publicaciones; eso no se midió.
- **Todas las cuentas son iguales.** En la práctica unas pocas concentran emisores y espectadores.
- **No hay último estado al conectar.** Una pantalla que abre ve solo lo que llega después. Para
  mostrar una flota completa hace falta un almacén de último valor por emisor.
- **La sonda corre en la misma máquina,** sin TLS, sin permisos por cuenta y sin navegadores reales.
- **Solo NATS como transporte.** El número de usuarios y de espectadores por cuenta es un supuesto.

## Para retomar

1. Aislar el techo de Centrifugo: logs en debug, protocolo binario en vez de JSON y la sonda
   repartida en varios procesos.
2. Medir la lectura repartida entre réplicas contra un transporte real con varias particiones:
   corte de una réplica, repetidos al retomar y estado por emisor al cambiar de dueño.
3. Dos o más réplicas de la pieza de entrega detrás de un balanceador.
4. Cuentas de tamaño desigual y último estado al conectar.
5. Llevar estos resultados a `docs/resultados.md` y al README, con sus tablas generadas como las demás.
