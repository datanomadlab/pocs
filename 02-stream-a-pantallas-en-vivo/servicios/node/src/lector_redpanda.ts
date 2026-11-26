import confluent from "@confluentinc/kafka-javascript";
import type { Leer } from "./consumidor.ts";

/**
 * Lee con un grupo de consumidores: el broker reparte las particiones entre las instancias y
 * guarda hasta dónde leyó cada una. Los valores son los de fábrica del cliente, salvo SESION_MS,
 * que permite acortar cuánto tarda el broker en dar por muerta una instancia.
 */
export const leerKafka: Leer = async (destino, entregar) => {
  const sesion = Number(process.env.SESION_MS);
  const kafka = new confluent.KafkaJS.Kafka({ kafkaJS: { brokers: [destino] } });
  const consumidor = kafka.consumer({
    kafkaJS: {
      groupId: "pantallas",
      fromBeginning: false,
      ...(sesion > 0 ? { sessionTimeout: sesion, heartbeatInterval: Math.floor(sesion / 3) } : {}),
    },
  });
  await consumidor.connect();
  await consumidor.subscribe({ topic: "eventos" });
  await consumidor.run({
    eachMessage: async ({ message }) => {
      if (message.value) entregar(message.value.toString());
    },
  });
  await new Promise<never>(() => {}); // run() sigue leyendo en segundo plano
};
