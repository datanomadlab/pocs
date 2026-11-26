package main

import (
	"context"
	"strconv"
	"sync/atomic"
	"time"

	"github.com/nats-io/nats.go"
	"github.com/nats-io/nats.go/jetstream"

	"stream/internal/evento"
)

// natsJS publica en un stream de JetStream guardado en disco. Un stream es un solo registro
// ordenado, así que el orden por emisor sale gratis mientras haya un solo lector.
type natsJS struct {
	nc       *nats.Conn
	js       jetstream.JetStream
	enviados int64
	fallidos atomic.Int64
}

func nuevoNats(o opciones) (*natsJS, error) {
	nc, err := nats.Connect(o.destino, nats.MaxReconnects(-1))
	if err != nil {
		return nil, err
	}
	n := &natsJS{nc: nc}
	n.js, err = jetstream.New(nc, jetstream.WithPublishAsyncMaxPending(8000),
		jetstream.WithPublishAsyncErrHandler(func(jetstream.JetStream, *nats.Msg, error) { n.fallidos.Add(1) }))
	return n, err
}

func (n *natsJS) Preparar(ctx context.Context) error {
	_, err := n.js.CreateOrUpdateStream(ctx, jetstream.StreamConfig{Name: "EVENTOS",
		Subjects: []string{evento.Topico + ".>"}, Storage: jetstream.FileStorage,
		MaxAge: time.Hour, Duplicates: time.Minute})
	return err
}

func (n *natsJS) Enviar(_ context.Context, e evento.Evento, cuerpo []byte) {
	msg := &nats.Msg{Subject: evento.Topico + "." + strconv.Itoa(e.Cuenta), Data: cuerpo,
		Header: nats.Header{evento.CabeceraCanales: []string{evento.Canal(e.Cuenta)}}}
	if _, err := n.js.PublishMsgAsync(msg); err != nil {
		n.fallidos.Add(1)
	}
	n.enviados++
}

func (n *natsJS) Cerrar(context.Context) (int64, int64) {
	select {
	case <-n.js.PublishAsyncComplete():
	case <-time.After(30 * time.Second):
		n.fallidos.Add(int64(n.js.PublishAsyncPending()))
	}
	n.nc.Close()
	return n.enviados - n.fallidos.Load(), n.fallidos.Load()
}
