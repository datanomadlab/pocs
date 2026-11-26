import { WebSocketServer, type WebSocket } from "ws";

/** Cuánto se acumula para una pantalla lenta antes de cortarla. */
const COLA_MAX_BYTES = 4 * 1024 * 1024;

/** Qué pantallas miran cada cuenta. */
const porCuenta = new Map<number, Set<WebSocket>>();

/**
 * Nunca espera a una pantalla: si acumuló demasiado, la corta y sigue. Una pantalla lenta no
 * puede frenar la lectura del transporte ni a las demás.
 */
export function publicar(cuenta: number, cuerpo: string): void {
  const pantallas = porCuenta.get(cuenta);
  if (!pantallas) return;
  for (const pantalla of pantallas) {
    if (pantalla.bufferedAmount > COLA_MAX_BYTES) {
      pantalla.terminate();
      continue;
    }
    pantalla.send(cuerpo);
  }
}

export function atender(puerto: number): void {
  const servidor = new WebSocketServer({ port: puerto, path: "/ws" });
  servidor.on("connection", (pantalla) => {
    let cuentas: number[] = [];
    pantalla.once("message", (pedido) => {
      try {
        const suscribir: unknown = JSON.parse(pedido.toString()).suscribir;
        if (!Array.isArray(suscribir)) throw new Error("falta la lista 'suscribir'");
        cuentas = suscribir.filter((c): c is number => Number.isInteger(c));
      } catch (error) {
        console.error("pedido de suscripción inválido:", error);
        pantalla.close(1008, "pedido inválido");
        return;
      }
      for (const cuenta of cuentas) {
        if (!porCuenta.has(cuenta)) porCuenta.set(cuenta, new Set());
        porCuenta.get(cuenta)!.add(pantalla);
      }
    });
    pantalla.on("close", () => {
      for (const cuenta of cuentas) porCuenta.get(cuenta)?.delete(pantalla);
    });
    pantalla.on("error", (error) => console.error("pantalla con error:", error.message));
  });
}
