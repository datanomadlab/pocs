package main

import (
	"context"
	"errors"
	"strconv"
	"sync/atomic"

	"github.com/twmb/franz-go/pkg/kadm"
	"github.com/twmb/franz-go/pkg/kerr"
	"github.com/twmb/franz-go/pkg/kgo"

	"stream/internal/evento"
)

// kafka produce a Redpanda por la API de Kafka. La llave es el emisor: todos sus eventos caen en
// la misma partición y por eso conservan el orden.
type kafka struct {
	cl                    *kgo.Client
	particiones           int32
	confirmados, fallidos atomic.Int64
}

func nuevoKafka(o opciones) (*kafka, error) {
	opciones := []kgo.Opt{kgo.SeedBrokers(o.destino), kgo.DefaultProduceTopic(evento.Topico),
		kgo.MaxBufferedRecords(200_000)}
	if o.sinComprimir {
		// De fábrica el cliente comprime cada lote con snappy. Hay lectores que no lo descomprimen.
		opciones = append(opciones, kgo.ProducerBatchCompression(kgo.NoCompression()))
	}
	cl, err := kgo.NewClient(opciones...)
	return &kafka{cl: cl, particiones: int32(o.particiones)}, err
}

func (k *kafka) Preparar(ctx context.Context) error {
	r, err := kadm.NewClient(k.cl).CreateTopic(ctx, k.particiones, 1, nil, evento.Topico)
	if err == nil {
		err = r.Err
	}
	if errors.Is(err, kerr.TopicAlreadyExists) {
		return nil
	}
	return err
}

func (k *kafka) Enviar(ctx context.Context, e evento.Evento, cuerpo []byte) {
	registro := &kgo.Record{Key: []byte(strconv.Itoa(e.Emisor)), Value: cuerpo, Headers: []kgo.RecordHeader{
		{Key: evento.CabeceraCanalesKafka, Value: []byte(evento.Canal(e.Cuenta))}}}
	k.cl.Produce(ctx, registro, func(_ *kgo.Record, err error) {
		if err != nil {
			k.fallidos.Add(1)
			return
		}
		k.confirmados.Add(1)
	})
}

func (k *kafka) Cerrar(ctx context.Context) (int64, int64) {
	k.cl.Flush(ctx)
	k.cl.Close()
	return k.confirmados.Load(), k.fallidos.Load()
}
