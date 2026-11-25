package main

import (
	"fmt"
	"os"
	"sync/atomic"

	mqtt "github.com/eclipse/paho.mqtt.golang"

	"stream/internal/evento"
)

// conectarMQTT usa MQTT sobre WebSocket, igual que lo haría el front con MQTT.js: una conexión
// por pantalla y una suscripción por cuenta, con entrega al menos una vez (QoS 1). La sesión es
// persistente: si la pantalla vuelve y el broker todavía la recuerda, le entrega lo pendiente.
func conectarMQTT(o opciones, r *registro, lista func()) {
	for i := 0; i < o.pantallas; i++ {
		temas := map[string]byte{}
		for _, cuenta := range cuentasDe(i, o) {
			temas[evento.Canal(cuenta)] = 1
		}
		var conectada, avisada atomic.Bool
		opciones := mqtt.NewClientOptions().AddBroker(o.destino).SetClientID(fmt.Sprintf("pantalla-%d", i)).
			SetCleanSession(false).SetAutoReconnect(true).SetConnectRetry(true).
			SetConnectRetryInterval(pausaReconexion).SetMaxReconnectInterval(pausaReconexion).
			SetDefaultPublishHandler(func(_ mqtt.Client, m mqtt.Message) { r.recibir(m.Payload(), i) }).
			SetOnConnectHandler(func(c mqtt.Client) {
				if conectada.Swap(true) {
					r.reconexiones.Add(1)
				}
				// Se vuelve a suscribir en cada conexión: si el broker se reinició, perdió la sesión.
				go func() {
					paso := c.SubscribeMultiple(temas, nil)
					paso.Wait()
					if paso.Error() != nil {
						fmt.Fprintln(os.Stderr, "Error al suscribir:", paso.Error())
						return
					}
					if !avisada.Swap(true) {
						lista()
					}
				}()
			})
		mqtt.NewClient(opciones).Connect()
	}
}
