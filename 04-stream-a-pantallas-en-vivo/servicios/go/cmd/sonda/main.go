// sonda hace de pantallas: abre conexiones (WebSocket, SSE o MQTT), se suscribe a las cuentas y mide lo que
// llega. Es la única pieza que mide, y mide donde importa: en lo que ve la persona.
//
// Imprime "LISTO" cuando todas las pantallas están suscritas y, al terminar, una línea de JSON.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"
)

type opciones struct {
	protocolo, destino, corrida string
	pantallas, cuentas          int
	duracion                    time.Duration
}

// conectar abre las pantallas y entrega cada evento recibido al registro. No retorna.
type conectar func(o opciones, r *registro, lista func())

var protocolos = map[string]conectar{"propio": conectarPropio, "centrifugo": conectarCentrifugo,
	"sse": conectarSSE, "mqtt": conectarMQTT}

func main() {
	var o opciones
	flag.StringVar(&o.protocolo, "protocolo", "propio", "propio, centrifugo, sse o mqtt")
	flag.StringVar(&o.destino, "destino", "", "URL de la pieza que entrega")
	flag.StringVar(&o.corrida, "corrida", "c0", "solo cuenta los eventos de esta corrida")
	flag.IntVar(&o.pantallas, "pantallas", 100, "conexiones abiertas")
	flag.IntVar(&o.cuentas, "cuentas", 1000, "cuentas, repartidas entre las pantallas")
	flag.DurationVar(&o.duracion, "duracion", 45*time.Second, "cuánto medir desde LISTO")
	flag.Parse()

	abrir, existe := protocolos[o.protocolo]
	if !existe {
		fmt.Fprintf(os.Stderr, "Error: protocolo desconocido %q\n", o.protocolo)
		os.Exit(1)
	}
	r := nuevoRegistro(o.corrida)
	listas := make(chan struct{}, o.pantallas)
	go abrir(o, r, func() { listas <- struct{}{} })
	for i := 0; i < o.pantallas; i++ {
		select {
		case <-listas:
		case <-time.After(60 * time.Second):
			fmt.Fprintf(os.Stderr, "Error: solo %d de %d pantallas se suscribieron\n", i, o.pantallas)
			os.Exit(1)
		}
	}
	r.empezar()
	fmt.Println("LISTO")
	time.Sleep(o.duracion)
	json.NewEncoder(os.Stdout).Encode(r.resumen())
}

// cuentasDe reparte las cuentas entre las pantallas: la pantalla i mira las cuentas i, i+P, i+2P…
func cuentasDe(pantalla int, o opciones) []int {
	var cuentas []int
	for c := pantalla; c < o.cuentas; c += o.pantallas {
		cuentas = append(cuentas, c)
	}
	return cuentas
}
