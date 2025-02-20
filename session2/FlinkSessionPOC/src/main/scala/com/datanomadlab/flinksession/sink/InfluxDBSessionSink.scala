package com.datanomadlab.flinksession.sink

import com.datanomadlab.flinksession.models.SessionAggregate
import org.apache.flink.configuration.Configuration
import org.apache.flink.streaming.api.functions.sink.RichSinkFunction
import java.sql.{Connection, DriverManager, PreparedStatement}

import com.influxdb.client.InfluxDBClient
import com.influxdb.client.InfluxDBClientFactory
import com.influxdb.client.WriteApi
import com.influxdb.client.domain.WritePrecision
import com.influxdb.client.write.Point

import java.time.Instant

class InfluxDBSessionSink(url: String, token: String, org: String, bucket: String)
  extends RichSinkFunction[SessionAggregate] {

  var influxDBClient: InfluxDBClient = _
  var writeApi: WriteApi = _

  override def open(parameters: Configuration): Unit = {
    // Inicializa el cliente de InfluxDB
    influxDBClient = InfluxDBClientFactory.create(url, token.toCharArray, org, bucket)
    writeApi = influxDBClient.getWriteApi
  }

  override def invoke(value: SessionAggregate): Unit = {
    try {
      // Crea un punto para InfluxDB. Se usa el measurement "session" y se agregan tags y campos.
      val point = Point.measurement("session")
        .addTag("user_id", value.userId)
        .addField("session_start", value.sessionStart)
        .addField("session_end", value.sessionEnd)
        .addField("event_count", value.events.size)
        // Utiliza el timestamp del final de la sesión (puedes cambiarlo si lo requieres)
        .time(Instant.ofEpochMilli(value.sessionEnd), WritePrecision.MS)

      // Escribe el punto en InfluxDB
      writeApi.writePoint(point)
    } catch {
      case e: Exception => e.printStackTrace()
    }
  }

  override def close(): Unit = {
    if (writeApi != null) writeApi.close()
    if (influxDBClient != null) influxDBClient.close()
  }
}
