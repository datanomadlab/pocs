package main

import (
	"context"
	"os"
	"strconv"
	"time"

	"github.com/twmb/franz-go/pkg/kgo"

	"stream/internal/evento"
)

// leerKafka lee con un grupo de consumidores: el broker reparte las particiones entre las
// instancias y guarda hasta dónde leyó cada una. Los valores son los de fábrica del cliente,
// salvo SESION_MS, que permite acortar cuánto tarda el broker en dar por muerta una instancia.
func leerKafka(ctx context.Context, destino string, entregar func([]byte)) error {
	opciones := []kgo.Opt{kgo.SeedBrokers(destino), kgo.ConsumerGroup("pantallas"),
		kgo.ConsumeTopics(evento.Topico), kgo.ConsumeResetOffset(kgo.NewOffset().AtEnd())}
	if ms, err := strconv.Atoi(os.Getenv("SESION_MS")); err == nil {
		opciones = append(opciones, kgo.SessionTimeout(time.Duration(ms)*time.Millisecond),
			kgo.HeartbeatInterval(time.Duration(ms/3)*time.Millisecond))
	}
	cl, err := kgo.NewClient(opciones...)
	if err != nil {
		return err
	}
	defer cl.Close()
	for {
		lote := cl.PollFetches(ctx)
		if err := lote.Err0(); err != nil {
			return err
		}
		lote.EachRecord(func(r *kgo.Record) { entregar(r.Value) })
	}
}
