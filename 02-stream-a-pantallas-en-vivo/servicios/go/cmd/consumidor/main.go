// consumidor es el servicio que un equipo de back escribiría a mano: lee los eventos del
// transporte y los empuja por WebSocket a las pantallas que miran cada cuenta.
package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"os"
)

// leer bloquea leyendo del transporte y llama a entregar por cada evento, en orden.
type leer func(ctx context.Context, destino string, entregar func(cuerpo []byte)) error

var lectores = map[string]leer{"redpanda": leerKafka, "nats": leerNats, "kinesis": leerKinesis, "sqs": leerSqs}

func main() {
	transporte, destino := os.Getenv("TRANSPORTE"), os.Getenv("DESTINO")
	lector, existe := lectores[transporte]
	if !existe {
		log.Fatalf("TRANSPORTE desconocido: %q", transporte)
	}
	central := nuevaCentral()
	http.HandleFunc("/ws", central.atender)
	go func() { log.Fatal(http.ListenAndServe(":8080", nil)) }()

	entregar := func(cuerpo []byte) {
		var e struct {
			Cuenta int `json:"cuenta"`
		}
		if err := json.Unmarshal(cuerpo, &e); err != nil {
			log.Printf("evento ilegible, se descarta: %v", err)
			return
		}
		central.publicar(e.Cuenta, cuerpo)
	}
	log.Printf("leyendo de %s en %s", transporte, destino)
	log.Fatal(lector(context.Background(), destino, entregar))
}
