# Vocabulario del Lab

Posts sobre las herramientas y conceptos que los experimentos dan por sabidos: qué es cada uno, qué problema resuelve, un ejemplo para correr en cinco minutos, los errores típicos y con qué se suele confundir. Están pensados para alguien que recién parte o que nunca usó esa herramienta en particular.

Se publican en el newsletter, en la sección Vocabulario. El post de cada experimento enlaza hacia ellos, así quien no conoce un término lo entiende sin salir del newsletter y vuelve al experimento.

Los redacta una IA siguiendo una plantilla fija, y cada post lo dice al final. Los comandos se ejecutan de verdad antes de escribirlo; cuando un ejemplo no se pudo correr, el post lo avisa.

<!-- indice:inicio -->
| Término | Qué es | Categoría | Estado |
|---|---|---|---|
| [BigQuery](https://datanomadlab.substack.com/p/que-es-bigquery) | Warehouse de Google Cloud sin servidores que administrar, donde consultas con SQL y pagas por los datos que lee cada consulta. | base de datos | publicado |
| [Bucket](https://datanomadlab.substack.com/p/que-es-bucket) | Carpeta en la nube donde se guardan archivos de cualquier tamaño y se pagan por lo que pesan, sin servidor que mantener. | infraestructura | publicado |
| [Centrifugo](centrifugo.md) | Servidor que mantiene las conexiones con las pantallas y les reparte al instante los mensajes de cada canal. | mensajería | borrador |
| [Docker](https://datanomadlab.substack.com/p/docker-como-probar-una-base-de-datos) | Empaqueta un programa con todo lo que necesita para correr igual en cualquier máquina. | infraestructura | publicado |
| [DuckDB](https://datanomadlab.substack.com/p/que-es-duckdb) | Motor SQL para análisis que corre dentro de tu programa y lee archivos directamente, sin servidor. | motor de consulta | publicado |
| [EMQX](emqx.md) | Servidor que recibe mensajes MQTT y los reparte a quien se suscribió, con reglas para filtrarlos y reenviarlos. | mensajería | borrador |
| [Apache Flink](flink.md) | Calcula sobre eventos que no dejan de llegar y recuerda sus cuentas aunque se caiga una máquina. | procesamiento | borrador |
| [Apache Iceberg](https://datanomadlab.substack.com/p/que-es-iceberg) | Formato de tabla abierto que convierte un montón de archivos Parquet en una tabla con versiones, particiones y cambios seguros. | formato | publicado |
| [Apache Kafka](kafka.md) | Guarda eventos en orden y deja que varios programas los lean, cada uno a su ritmo y sin perder su lugar. | mensajería | borrador |
| [Amazon Kinesis Data Streams](kinesis.md) | Servicio de AWS que guarda eventos en orden y deja que varios programas los lean, cada uno a su ritmo. | mensajería | borrador |
| [MQTT](mqtt.md) | Protocolo en que unos programas publican mensajes en un tema y otros los reciben al suscribirse, mediante un broker. | protocolo | borrador |
| [NATS](nats.md) | Lleva mensajes entre programas y, si se lo pides, los guarda hasta que alguien confirma que los recibió. | mensajería | borrador |
| [Parquet](https://datanomadlab.substack.com/p/que-es-parquet) | Formato de archivo que guarda las tablas por columnas, comprimidas, para que las consultas lean solo lo que necesitan. | formato | publicado |
| [PostgreSQL](postgres.md) | Base de datos con servidor donde una aplicación guarda sus registros y muchos escriben a la vez sin perder datos. | base de datos | borrador |
| [Redis](redis.md) | Servidor que guarda datos en memoria, por clave, con estructuras como listas y streams, y los borra cuando vencen. | base de datos | borrador |
| [Redpanda](redpanda.md) | Servidor de eventos que entiende a los clientes de Kafka y corre como un solo programa, sin Java. | mensajería | borrador |
| [Amazon SQS](sqs.md) | Cola de mensajes que opera AWS: un programa deja mensajes y otro los retira, los procesa y los borra. | mensajería | borrador |
| [SSE](sse.md) | Una respuesta HTTP que no se cierra: el servidor escribe eventos y la pantalla los lee a medida que llegan. | protocolo | borrador |
| [WebSocket](websocket.md) | Protocolo que deja abierta una conexión entre una página y un servidor para que cualquiera de los dos envíe mensajes. | protocolo | borrador |
| [Zilla](zilla.md) | Proxy que reparte un tópico de Kafka a las pantallas por protocolos de la web, solo con un archivo de configuración. | mensajería | borrador |
<!-- indice:fin -->

## Un término, un post

El vocabulario no se duplica a medida que salen experimentos. Cada término tiene un solo post y los experimentos nuevos enlazan al que ya existe. Un post se actualiza, en el mismo archivo y con la misma URL, solo cuando la herramienta trae una característica nueva que cambia lo que dice, o cuando un experimento la usa de una forma o en una combinación que el post no cubría.

## Cómo se hace un post

```mermaid
flowchart LR
  A[experimento<br/>vocabulario.txt] --> B[vocabulario.py estado<br/>qué posts faltan]
  B --> C[la IA redacta<br/>y corre el ejemplo]
  C --> D[lectura en frío<br/>como alguien que recién parte]
  D --> E[borrador]
  E --> F[revisado por Felipe]
  F --> G[vocabulario.py html<br/>página con botones de copiar]
  G --> H[publicado]
  H --> I[el post del experimento<br/>enlaza al término]
```

1. **Declarar.** Cada experimento lista sus términos en `vocabulario.txt`, uno por línea, en minúsculas y con guiones (`docker`, `apache-polaris`). También se puede escribir un post de un concepto que no pertenece a ningún experimento.
2. **Ver qué falta.** `python3 tools/vocabulario.py estado`.
3. **Generar.** La IA redacta el post con la estructura de [_plantilla.md](_plantilla.md), corre el ejemplo, comprueba los enlaces, pide una lectura en frío como la haría alguien que recién parte y deja el post como `borrador`.
4. **Revisar.** Con la lista de abajo. Al terminar, cambia `estado: revisado` en el encabezado.
5. **Exportar.** `uv run --no-project --with markdown tools/vocabulario.py html docker` crea `vocabulario/_substack/docker.html` y lo abre en el navegador. No copies desde la vista previa del editor de código: sus enlaces apuntan a tu disco.
6. **Publicar.** En esa página, cada botón copia un campo: título, subtítulo, descripción para redes, dirección del post y cuerpo. Pégalos en Substack (sección Vocabulario) y pon la dirección indicada (`que-es-docker`) en los ajustes del post antes de publicar. Luego copia la URL en `substack:`, cambia `estado: publicado` y corre `python3 tools/vocabulario.py indice`.
7. **Enlazar desde el experimento.** En el post principal, la primera mención del término lleva el enlace al post de vocabulario en Substack.

### Orden de publicación

La dirección de cada post está decidida de antemano (`https://datanomadlab.substack.com/p/que-es-<termino>`), así que los enlaces entre posts ya apuntan al newsletter aunque el otro post no exista todavía. Mientras no se publique, ese enlace da error: conviene publicar la tanda completa el mismo día, o partir por los que otros enlazan (Parquet y bucket, después DuckDB, después Apache Iceberg y BigQuery).

### Lista de revisión

- [ ] Corrí el ejemplo yo mismo y la salida coincide.
- [ ] La frase inicial la entendería alguien que nunca usó la herramienta.
- [ ] Los errores típicos son cosas que he visto pasar, no relleno.
- [ ] "Cuándo no usarlo" nombra una alternativa concreta.
- [ ] Los enlaces abren y los externos son documentación oficial.
- [ ] No hay datos, nombres ni casos de mi trabajo.
- [ ] La versión de `probado_con` sigue vigente.

### Estados

| Estado | Significa |
|---|---|
| `borrador` | Generado, con el ejemplo ejecutado (o marcado como no ejecutado) y con su lectura en frío. Nadie más lo ha revisado |
| `revisado` | Felipe lo leyó, corrió el ejemplo y lo corrigió |
| `publicado` | Está en Substack y su URL quedó en `substack:` |

### Imágenes

Cada post lleva una imagen de 1600×900 con el estilo de la marca, definida en `imagenes/<termino>.toml` y dibujada con `tools/diagrama.py` (ver el README de la raíz). Sirve dentro del post y como imagen para redes. Al exportar, la imagen no va en el cuerpo que se copia: la página de exportación la muestra aparte para arrastrarla al editor de Substack.

### Formato

Los posts no usan tablas, porque el editor de Substack no las tiene. Sí usan títulos, listas, negritas, enlaces y bloques de código.
