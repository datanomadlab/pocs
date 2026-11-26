// El servicio que un equipo de back escribiría a mano: lee los eventos del transporte y los
// empuja por WebSocket a las pantallas que miran cada cuenta.
import { atender, publicar } from "./central.ts";
import { leerKafka } from "./lector_redpanda.ts";
import { leerNats } from "./lector_nats.ts";

/** Lee del transporte sin terminar y llama a entregar por cada evento, en orden. */
export type Leer = (destino: string, entregar: (cuerpo: string) => void) => Promise<void>;

const lectores: Record<string, Leer> = { redpanda: leerKafka, nats: leerNats };

const transporte = process.env.TRANSPORTE ?? "";
const destino = process.env.DESTINO ?? "";
const leer = lectores[transporte];
if (!leer) {
  console.error(`TRANSPORTE desconocido: "${transporte}"`);
  process.exit(1);
}

function entregar(cuerpo: string): void {
  let cuenta: unknown;
  try {
    cuenta = JSON.parse(cuerpo).cuenta;
  } catch (error) {
    console.error("evento ilegible, se descarta:", error);
    return;
  }
  if (typeof cuenta === "number") publicar(cuenta, cuerpo);
}

atender(8080);
console.log(`leyendo de ${transporte} en ${destino}`);
leer(destino, entregar).catch((error) => {
  console.error("la lectura falló:", error);
  process.exit(1);
});
