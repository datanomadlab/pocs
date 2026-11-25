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
	espectadores                int
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
	flag.IntVar(&o.espectadores, "espectadores", 1, "pantallas que miran cada cuenta")
	flag.DurationVar(&o.duracion, "duracion", 45*time.Second, "cuánto medir desde LISTO")
	flag.Parse()

	abrir, existe := protocolos[o.protocolo]
	if !existe {
		fmt.Fprintf(os.Stderr, "Error: protocolo desconocido %q\n", o.protocolo)
		os.Exit(1)
	}
	if err := validar(o); err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
	r := nuevoRegistro(o.corrida)
	r.o = o
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

// validar rechaza las combinaciones en que el reparto de cuentasDe no se cumple: más espectadores
// por cuenta que pantallas, o tan pocas cuentas que alguna pantalla quedaría sin ninguna.
func validar(o opciones) error {
	switch {
	case o.pantallas < 1 || o.cuentas < 1 || o.espectadores < 1:
		return fmt.Errorf("pantallas, cuentas y espectadores tienen que ser al menos 1")
	case o.espectadores > o.pantallas:
		return fmt.Errorf("%d espectadores por cuenta no caben en %d pantallas", o.espectadores, o.pantallas)
	case o.espectadores > 1 && o.cuentas*o.espectadores < o.pantallas:
		return fmt.Errorf("con %d cuentas y %d espectadores por cuenta, alguna de las %d pantallas quedaría sin cuentas",
			o.cuentas, o.espectadores, o.pantallas)
	case o.espectadores == 1 && o.cuentas < o.pantallas:
		return fmt.Errorf("con %d cuentas, alguna de las %d pantallas quedaría sin cuentas", o.cuentas, o.pantallas)
	}
	return nil
}

// cuentasDe reparte las cuentas entre las pantallas: la pantalla i mira las cuentas i, i+P, i+2P…
// Con -espectadores V, cada cuenta la miran V pantallas: el espectador j de la cuenta c es la
// pantalla (c·V + j) mod P. Hace falta cuentas·V >= pantallas para que ninguna quede sin cuentas.
func cuentasDe(pantalla int, o opciones) []int {
	var cuentas []int
	if o.espectadores <= 1 {
		for c := pantalla; c < o.cuentas; c += o.pantallas {
			cuentas = append(cuentas, c)
		}
		return cuentas
	}
	for c := 0; c < o.cuentas; c++ {
		for j := 0; j < o.espectadores; j++ {
			if (c*o.espectadores+j)%o.pantallas == pantalla {
				cuentas = append(cuentas, c)
				break
			}
		}
	}
	return cuentas
}

// principal dice si esta pantalla es el espectador 0 de la cuenta: solo sus entregas se clasifican
// (nuevo, repetido, desordenado). Las de los demás espectadores se cuentan como copias.
func principal(cuenta, pantalla int, o opciones) bool {
	return o.espectadores <= 1 || (cuenta*o.espectadores)%o.pantallas == pantalla
}
