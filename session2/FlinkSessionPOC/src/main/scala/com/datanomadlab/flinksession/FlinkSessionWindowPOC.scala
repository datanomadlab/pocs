package com.datanomadlab.flinksession

import com.datanomadlab.flinksession.models.{SessionEvent, SessionAggregate}
import com.datanomadlab.flinksession.sink.InfluxDBSessionSink
import org.apache.flink.streaming.api.scala._
import org.apache.flink.streaming.api.TimeCharacteristic
import org.apache.flink.streaming.api.windowing.time.Time
import org.apache.flink.streaming.api.windowing.assigners.EventTimeSessionWindows
import org.apache.flink.streaming.api.windowing.windows.TimeWindow
import org.apache.flink.streaming.api.functions.timestamps.BoundedOutOfOrdernessTimestampExtractor
import org.apache.flink.streaming.api.scala.function.ProcessWindowFunction
import org.apache.flink.util.Collector
import org.apache.flink.streaming.connectors.kafka.FlinkKafkaConsumer
import org.apache.flink.api.common.serialization.SimpleStringSchema
import org.apache.flink.api.common.eventtime.WatermarkStrategy
import org.apache.flink.connector.kafka.source.KafkaSource
import org.apache.flink.connector.kafka.source.enumerator.initializer.OffsetsInitializer
import java.time.Duration
import org.apache.flink.api.common.eventtime.SerializableTimestampAssigner

object FlinkSessionWindowPOC {
  // Definimos una clase serializable para el timestamp assigner
  class SessionTimestampAssigner extends SerializableTimestampAssigner[SessionEvent] {
    override def extractTimestamp(element: SessionEvent, recordTimestamp: Long): Long = {
      element.timestamp
    }
  }

  def main(args: Array[String]): Unit = {
    // 1. Crear el entorno de ejecución de Flink
    val env = StreamExecutionEnvironment.getExecutionEnvironment
    env.setStreamTimeCharacteristic(TimeCharacteristic.EventTime)
    env.getConfig.setAutoWatermarkInterval(1000)
    
    // 2. Configurar propiedades para Kafka con más opciones
    val properties = new java.util.Properties()
    properties.setProperty("bootstrap.servers", "localhost:9092")
    properties.setProperty("group.id", "flink-session-group")
    properties.setProperty("auto.offset.reset", "earliest")
    properties.setProperty("enable.auto.commit", "false")
    properties.setProperty("isolation.level", "read_committed")

    // 3. Crear el consumidor de Kafka con más configuración
    val kafkaConsumer = new FlinkKafkaConsumer[String](
      "session-topic",
      new SimpleStringSchema(),
      properties
    )
    kafkaConsumer.setStartFromEarliest()
    kafkaConsumer.setCommitOffsetsOnCheckpoints(true)

    // 4. Fuente de datos con manejo de errores
    val messageStream: DataStream[String] = env
      .addSource(kafkaConsumer)
      .name("Kafka Source")
      .uid("kafka-source")
      .setParallelism(1)  // Reducimos el paralelismo para debugging

    // 5. Parsear los mensajes con mejor manejo de errores
    val sessionEvents: DataStream[SessionEvent] = messageStream
      .flatMap { msg =>
        try {
          val parts = msg.split(",")
          if (parts.length != 4) {
            println(s"Skipping invalid message format: $msg")
            None
          } else {
            try {
              val sessionId = parts(0).trim
              val userId = parts(1).trim
              val timestamp = parts(2).trim.toLong
              val action = parts(3).trim
              Some(SessionEvent(userId, timestamp, action))
            } catch {
              case e: NumberFormatException =>
                println(s"Invalid timestamp in message: $msg")
                None
              case e: Exception =>
                println(s"Error processing message: $msg - ${e.getMessage}")
                None
            }
          }
        } catch {
          case e: Exception =>
            println(s"Unexpected error processing message: $msg - ${e.getMessage}")
            None
        }
      }
      .name("Message Parser")
      .uid("message-parser")

    // Asignar timestamps y watermarks con más tolerancia usando la clase serializable
    val withTimestamps = sessionEvents.assignTimestampsAndWatermarks(
      WatermarkStrategy
        .forBoundedOutOfOrderness[SessionEvent](Duration.ofSeconds(20))
        .withTimestampAssigner(new SessionTimestampAssigner())
    )

    // 6. Procesar las ventanas de sesión  
    // Se agrupan los eventos por userId y se crea una ventana que se cierra 30 segundos después de inactividad.
    val sessionAggregates: DataStream[SessionAggregate] = withTimestamps
      .keyBy(_.userId)
      .window(EventTimeSessionWindows.withGap(Time.seconds(30)))
      .process(new ProcessWindowFunction[SessionEvent, SessionAggregate, String, TimeWindow] {
        override def process(key: String, context: Context, elements: Iterable[SessionEvent], out: Collector[SessionAggregate]): Unit = {
          val sortedEvents = elements.toList.sortBy(_.timestamp)
          val sessionStart = sortedEvents.head.timestamp
          val sessionEnd = sortedEvents.last.timestamp
          out.collect(SessionAggregate(key, sessionStart, sessionEnd, sortedEvents))
        }
      })

    // 7. Configuración de InfluxDB  
    // Asegúrate de haber levantado InfluxDB 2.7 en Docker (ver instrucciones más abajo)
    val influxUrl = "http://localhost:8086"
    val influxToken = "myinfluxtoken"  // Reemplaza con tu token de InfluxDB
    val influxOrg = "myorg"
    val influxBucket = "mybucket"

    // 8. Agregar el sink de InfluxDB para insertar los datos de sesión
    sessionAggregates.addSink(new InfluxDBSessionSink(influxUrl, influxToken, influxOrg, influxBucket))

    // 9. Ejecutar el job de Flink
    env.execute("Flink Session Window PoC - Kafka a InfluxDB")
  }
}
