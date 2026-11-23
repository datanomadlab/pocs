package main

import (
	"context"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"
)

// leerNats usa un consumidor durable de JetStream: el servidor recuerda qué mensajes ya fueron
// confirmados, así que al reiniciar se sigue desde ahí. Con una sola instancia el orden se conserva.
func leerNats(ctx context.Context, destino string, entregar func([]byte)) error {
	nc, err := nats.Connect(destino, nats.MaxReconnects(-1))
	if err != nil {
		return err
	}
	defer nc.Close()
	js, err := jetstream.New(nc)
	if err != nil {
		return err
	}
	consumidor, err := js.CreateOrUpdateConsumer(ctx, "EVENTOS", jetstream.ConsumerConfig{
		Durable: "pantallas", AckPolicy: jetstream.AckExplicitPolicy, DeliverPolicy: jetstream.DeliverNewPolicy})
	if err != nil {
		return err
	}
	lectura, err := consumidor.Consume(func(m jetstream.Msg) {
		entregar(m.Data())
		m.Ack()
	})
	if err != nil {
		return err
	}
	defer lectura.Stop()
	<-ctx.Done()
	return ctx.Err()
}
