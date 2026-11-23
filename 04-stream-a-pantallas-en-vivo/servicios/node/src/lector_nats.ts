import { connect } from "@nats-io/transport-node";
import { AckPolicy, DeliverPolicy, jetstream, jetstreamManager } from "@nats-io/jetstream";
import type { Leer } from "./consumidor.ts";

/**
 * Usa un consumidor durable de JetStream: el servidor recuerda qué mensajes ya fueron confirmados,
 * así que al reiniciar se sigue desde ahí. Con una sola instancia el orden se conserva.
 */
export const leerNats: Leer = async (destino, entregar) => {
  const conexion = await connect({ servers: destino, maxReconnectAttempts: -1 });
  const administrador = await jetstreamManager(conexion);
  await administrador.consumers.add("EVENTOS", {
    durable_name: "pantallas",
    ack_policy: AckPolicy.Explicit,
    deliver_policy: DeliverPolicy.New,
  });
  const consumidor = await jetstream(conexion).consumers.get("EVENTOS", "pantallas");
  const texto = new TextDecoder();
  for await (const mensaje of await consumidor.consume()) {
    entregar(texto.decode(mensaje.data));
    mensaje.ack();
  }
};
