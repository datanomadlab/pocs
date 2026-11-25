# Concurrencia: miles de pantallas, varias por cuenta

En `make demo` cada cuenta la mira una sola pantalla: cada evento se entrega una vez y hay 100 conexiones. Eso mide el costo por evento, no un sistema con usuarios concurrentes. Esta prueba agrega lo que faltaba: **varias pantallas mirando la misma cuenta**.

Lo que carga a la pieza de entrega deja de ser lo que entra y pasa a ser lo que sale:

```
entregas por segundo = eventos por segundo x pantallas que miran cada cuenta
```

Con 6.667 eventos por segundo y 25 pantallas por cuenta, la pieza entrega 166.675 mensajes por segundo.

## Correrlo

```bash
make setup
make concurrencia                 # 4 escenarios x 3 rutas, cerca de media hora
make concurrencia RAPIDO=1        # una combinación chica, para ver que todo levanta
make concurrencia RUTAS=nats-go   # solo algunas rutas
```

Primero mide cuánto cuesta enriquecer un evento (ver más abajo). Después, por cada escenario y ruta, corre la carga del escenario (30 s), una rampa a 2, 4 y 8 veces, y un corte: mata la pieza de entrega con todas las pantallas conectadas, que reconectan a la vez. Muestra cada fase en la terminal y guarda todo en `data/concurrencia.json`. Si ya corriste `make demo`, agrega sus tablas a [resultados.md](resultados.md); si no, te lo avisa, porque el reporte parte de esa medición. No toca `data/medicion.json`. Con `RAPIDO=1` o con `RUTAS` la corrida es parcial: se muestra y no se guarda.

Los escenarios están en [src/stream/concurrencia.py](../src/stream/concurrencia.py). Cada pantalla mira una cuenta, así que pantallas = cuentas x pantallas por cuenta. Un emisor emite cada 30 s y los eventos pesan 1.000 bytes: más que los 300 del experimento, porque un evento ya enriquecido lleva varias lecturas con sus nombres.

## Qué cambió para poder medirlo

- **La sonda acepta `-espectadores N`.** Cada cuenta la miran N pantallas. Una de ellas es la principal y sus entregas se clasifican como siempre (nuevo, repetido, desordenado); las de las demás se cuentan como copias y entran a la latencia. Con `-espectadores 1` se comporta igual que antes.
- **`ESPECTADORES` en `.env`** llega a la sonda también en `make demo`. De fábrica es 1.
- **La sonda tiene más núcleos en esta prueba** ([compose.concurrencia.yaml](../compose.concurrencia.yaml)): hace de miles de pantallas y con 2 núcleos sería ella el cuello de botella. Las piezas medidas conservan su tope de 2 núcleos y 2 GB.

## Resultados

Las cifras están en [resultados.md](resultados.md), en las tres tablas que empiezan con «Varias pantallas por cuenta». Las escribe `make concurrencia`; aquí va lo que se lee de ellas. Cada combinación se midió una vez: un escalón de 12 segundos por carga y un corte.

- **El consumidor en Go escala con la carga y se frena por CPU.** Usa 0,70 núcleos a 83.350 entregas por segundo y 1,47 a 166.675. Aguantó 333.400 con 50 pantallas por cuenta y no aguantó 333.350 con 25: su techo, con 2 núcleos, está ahí.
- **Centrifugo falla antes, y no por falta de CPU.** Con 20 pantallas por cuenta aguantó 66.680 entregas por segundo y falló a 133.360; con 50 aguantó 83.350 y falló al doble. A 83.350 usaba 0,58 de sus 2 núcleos.
- **Por qué falla quedó a medias.** En una repetición aparte de la carga de 133.360, que no queda guardada ni la repite `make concurrencia`, el log en detalle de Centrifugo mostró 1.246 conexiones cerradas por error al escribirles y ninguna por cola llena. Eso apunta a la escritura hacia la pantalla o a la lectura del cliente, no al cómputo del servidor; cuál de las dos, no quedó aislado. La sonda usa una librería cliente contra Centrifugo y otra contra el consumidor en Go, así que la comparación entre ambos lleva esa diferencia. Es un techo provisorio.
- **Centrifugo con Redis no perdió nada en sus 3 cortes bajo el techo,** igual que en el experimento con 100 pantallas, ahora con hasta 5.000 reconectando a la vez. Son tres cortes, uno por escenario. Centrifugo sin Redis dejó sin llegar el 1,0 % de las entregas y el consumidor en Go entre el 0,6 % y el 0,7 %.
- **Sobre su techo, el corte no dice nada.** Con 166.675 entregas por segundo las dos variantes de Centrifugo ya no entregaban todo antes del corte (el 71 % y el 80 %), así que lo que faltó después no se le puede cargar al corte.
- **El primer techo llega por pantallas, no por emisores.** 50.000 emisores son 1.667 eventos por segundo, poco para cualquier pieza; con 50 pantallas por cuenta son 83.350 entregas.

Pasado el techo de una instancia quedan dos palancas: entregar menos (el último valor por emisor cada pocos segundos, canales por grupo en vez de por cuenta) o repartir entre varias réplicas, que en Centrifugo exige Redis.

## Cuánto cuesta enriquecer un evento antes de entregarlo

Si entre el transporte y las pantallas va una pieza que agrega información a cada evento, hay que saber cuánto pesa. [servicios/go/internal/decorador](../servicios/go/internal/decorador) es un prototipo mínimo: lee el evento, traduce sus lecturas al nombre y la escala que espera cada destino según el tipo de emisor, evalúa las reglas de la cuenta recordando cuáles estaban activas para ese emisor, y arma una salida por destino. Una regla está activa mientras una lectura cae dentro de un rango; el prototipo avisa cuál se activó y cuál se desactivó.

`make concurrencia` lo mide en un contenedor con 1 núcleo, con 100 tipos de emisor, 500 cuentas, 20 lecturas por evento y eventos de 1.000 bytes. La tabla «Eventos por segundo que enriquece un núcleo» de [resultados.md](resultados.md) tiene las cifras.

Un núcleo enriquece 140.500 eventos por segundo hacia un destino sin reglas, y 38.500 hacia 5 destinos con 1.000 reglas por cuenta. Lo que más pesa es armar una salida por destino: pasar de 1 a 5 destinos deja el rendimiento entre un tercio y algo menos de la mitad. Pasar de ninguna regla a 1.000 por cuenta le quita entre el 16 % y el 35 %. Cada combinación se midió una vez, durante 3 segundos.

Para los 6.667 eventos por segundo del escenario más grande, eso es menos de un quinto de núcleo. Entregar esos mismos eventos a 25 pantallas por cuenta le pidió 1,47 núcleos al consumidor en Go: enriquecer cuesta poco frente a entregar.

## El límite

- **Un solo lector del transporte.** No hay dos réplicas repartiéndose particiones o shards, ni se mide cuánto se congela la pantalla cuando cae una, ni qué pasa con el estado por emisor (qué reglas tenía activas) cuando su partición cambia de dueño.
- **Una sola instancia de la pieza de entrega.** Varias réplicas de Centrifugo necesitan Redis para repartirse las publicaciones; eso no se midió.
- **Un corte por combinación.** Lo que pasa al matar una pieza depende de en qué estaba en ese instante.
- **Los repetidos solo se detectan en la pantalla principal de cada cuenta.** Para las demás se supone que recibieron las mismas repeticiones, y se descuentan.
- **La sonda también tiene un techo.** Recibe todas las entregas en un solo proceso, y lo que se demore ella en anotar una entrega cuenta como latencia de la ruta.
- **Todas las cuentas son iguales.** En la práctica unas pocas concentran emisores y pantallas.
- **No hay último estado al conectar.** Una pantalla que abre ve solo lo que llega después. Para mostrar el estado de todos los emisores de una cuenta hace falta un almacén con el último valor de cada uno.
- **La sonda corre en la misma máquina,** sin TLS, sin permisos por cuenta y sin navegadores reales.
- **Solo NATS como transporte.** El número de pantallas por cuenta es un supuesto.
- **El prototipo de enriquecimiento es un solo hilo en memoria.** No lee el transporte, no escribe y no comparte estado con otra réplica: dice cuánta CPU pide enriquecer, no cómo se reparte ese trabajo.

## Para retomar

1. Aislar el techo de Centrifugo: protocolo binario en vez de JSON, la sonda repartida en varios procesos y los tiempos de escritura del servidor.
2. Medir la lectura repartida entre réplicas contra un transporte con varias particiones: corte de una réplica, repetidos al retomar y estado por emisor al cambiar de dueño.
3. Dos o más réplicas de la pieza de entrega detrás de un balanceador.
4. Cuentas de tamaño desigual y último estado al conectar.
5. Detectar repetidos en todas las pantallas de una cuenta, no solo en la principal.
