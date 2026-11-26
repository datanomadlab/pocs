package main

import (
	"context"
	"encoding/json"
	"log"
	"os"
	"sync"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/kinesis"
	"github.com/aws/aws-sdk-go-v2/service/kinesis/types"

	"stream/internal/evento"
)

// Kinesis no reparte shards ni recuerda hasta dónde leyó cada consumidor: eso lo hace quien lee.
// Este lector hace lo mínimo para una sola instancia: un hilo por shard y un archivo con el último
// número de secuencia entregado. Lo que le falta para producción es justo lo que traen KCL o
// Flink: repartir shards entre varias instancias, seguir un resharding y guardar el avance en un
// lugar compartido (KCL usa tablas de DynamoDB).
const (
	archivoAvance = "/estado/avance.json"
	pausaLectura  = 200 * time.Millisecond // 5 lecturas por segundo y por shard: el límite de Kinesis
)

type avance struct {
	mu       sync.Mutex
	Porshard map[string]string `json:"por_shard"`
}

func leerKinesis(ctx context.Context, destino string, entregar func([]byte)) error {
	cfg, err := evento.ConfigAWS(ctx)
	if err != nil {
		return err
	}
	cl := kinesis.NewFromConfig(cfg, func(k *kinesis.Options) { k.BaseEndpoint = aws.String(destino) })
	shards, err := cl.ListShards(ctx, &kinesis.ListShardsInput{StreamName: aws.String(evento.Topico)})
	if err != nil {
		return err
	}
	a := &avance{Porshard: map[string]string{}}
	if guardado, err := os.ReadFile(archivoAvance); err == nil {
		json.Unmarshal(guardado, a)
	}
	go a.guardarCada(ctx, time.Second)

	fallo := make(chan error, len(shards.Shards))
	for _, s := range shards.Shards {
		go func(shard string) { fallo <- leerShard(ctx, cl, shard, a, entregar) }(*s.ShardId)
	}
	return <-fallo
}

func leerShard(ctx context.Context, cl *kinesis.Client, shard string, a *avance, entregar func([]byte)) error {
	desde := &kinesis.GetShardIteratorInput{StreamName: aws.String(evento.Topico), ShardId: &shard,
		ShardIteratorType: types.ShardIteratorTypeLatest}
	if seq := a.leer(shard); seq != "" {
		desde.ShardIteratorType, desde.StartingSequenceNumber = types.ShardIteratorTypeAfterSequenceNumber, &seq
	}
	it, err := cl.GetShardIterator(ctx, desde)
	if err != nil {
		return err
	}
	for cursor := it.ShardIterator; cursor != nil; {
		r, err := cl.GetRecords(ctx, &kinesis.GetRecordsInput{ShardIterator: cursor, Limit: aws.Int32(10_000)})
		if err != nil {
			return err // incluye el iterador vencido y el límite de lecturas: el proceso se reinicia
		}
		for _, registro := range r.Records {
			entregar(registro.Data)
			a.anotar(shard, *registro.SequenceNumber)
		}
		cursor = r.NextShardIterator
		time.Sleep(pausaLectura)
	}
	log.Printf("shard %s cerrado: hubo resharding y este lector no lo sigue", shard)
	<-ctx.Done()
	return ctx.Err()
}

func (a *avance) leer(shard string) string {
	a.mu.Lock()
	defer a.mu.Unlock()
	return a.Porshard[shard]
}

func (a *avance) anotar(shard, seq string) {
	a.mu.Lock()
	a.Porshard[shard] = seq
	a.mu.Unlock()
}

// guardarCada escribe el avance cada cierto tiempo. Si el proceso muere entre dos escrituras, al
// volver repite lo leído desde la última escritura. Eso no garantiza que la pantalla lo vea todo:
// lo que se lee antes de que las pantallas se reconecten no le llega a nadie.
func (a *avance) guardarCada(ctx context.Context, cada time.Duration) {
	for {
		select {
		case <-ctx.Done():
			return
		case <-time.After(cada):
		}
		a.mu.Lock()
		contenido, _ := json.Marshal(a)
		a.mu.Unlock()
		if err := os.WriteFile(archivoAvance+".tmp", contenido, 0o644); err != nil {
			log.Printf("no pude guardar el avance: %v", err)
			continue
		}
		os.Rename(archivoAvance+".tmp", archivoAvance)
	}
}
