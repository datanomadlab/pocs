package main

import (
	"fmt"
	"os"
	"sync"
	"time"

	"github.com/centrifugal/centrifuge-go"

	"stream/internal/evento"
)

// conectarCentrifugo usa el cliente oficial, igual que lo haría el front con centrifuge-js. El
// cliente reconecta solo y, al volver, le pide a Centrifugo lo que se publicó mientras no estaba.
func conectarCentrifugo(o opciones, r *registro, lista func()) {
	for i := 0; i < o.pantallas; i++ {
		cliente := centrifuge.NewJsonClient(o.destino, centrifuge.Config{
			MinReconnectDelay: pausaReconexion, MaxReconnectDelay: time.Second})
		conectada := false
		cliente.OnConnected(func(centrifuge.ConnectedEvent) {
			if conectada {
				r.reconexiones.Add(1)
			}
			conectada = true
		})
		cuentas := cuentasDe(i, o)
		var suscritas sync.Map
		pendientes := len(cuentas)
		var mu sync.Mutex
		for _, cuenta := range cuentas {
			sub, err := cliente.NewSubscription(evento.Canal(cuenta), centrifuge.SubscriptionConfig{Recoverable: true})
			if err != nil {
				fmt.Fprintln(os.Stderr, "Error al crear la suscripción:", err)
				os.Exit(1)
			}
			sub.OnError(func(e centrifuge.SubscriptionErrorEvent) {
				fmt.Fprintf(os.Stderr, "Error en la suscripción a %s: %v\n", evento.Canal(cuenta), e.Error)
			})
			sub.OnPublication(func(e centrifuge.PublicationEvent) { r.recibir(e.Data) })
			sub.OnSubscribed(func(e centrifuge.SubscribedEvent) {
				// Volvió, pidió recuperar y Centrifugo no pudo: hay eventos que esta pantalla no verá.
				if e.WasRecovering && !e.Recovered {
					r.sinRecuperar.Add(1)
				}
				if _, ya := suscritas.LoadOrStore(cuenta, true); ya {
					return
				}
				mu.Lock()
				defer mu.Unlock()
				if pendientes--; pendientes == 0 {
					lista()
				}
			})
			if err := sub.Subscribe(); err != nil {
				fmt.Fprintln(os.Stderr, "Error al suscribir:", err)
				os.Exit(1)
			}
		}
		if err := cliente.Connect(); err != nil {
			fmt.Fprintln(os.Stderr, "Error al conectar:", err)
			os.Exit(1)
		}
	}
}
