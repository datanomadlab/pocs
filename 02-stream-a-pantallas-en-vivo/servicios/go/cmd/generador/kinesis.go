package main

import (
	"context"
	"errors"
	"strconv"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/kinesis"
	"github.com/aws/aws-sdk-go-v2/service/kinesis/types"

	"stream/internal/evento"
)

// kinesisP escribe con PutRecords, hasta 500 registros por solicitud. La llave de partición es el
// emisor, así que cada emisor cae siempre en el mismo shard.
type kinesisP struct {
	*porLotes
	cl     *kinesis.Client
	shards int32
}

func nuevoKinesis(o opciones) (*kinesisP, error) {
	cfg, err := evento.ConfigAWS(context.Background())
	if err != nil {
		return nil, err
	}
	k := &kinesisP{shards: int32(o.particiones),
		cl: kinesis.NewFromConfig(cfg, func(k *kinesis.Options) { k.BaseEndpoint = aws.String(o.destino) })}
	k.porLotes = nuevoPorLotes(8, 500, k.enviar)
	return k, nil
}

func (k *kinesisP) Preparar(ctx context.Context) error {
	_, err := k.cl.CreateStream(ctx, &kinesis.CreateStreamInput{StreamName: aws.String(evento.Topico), ShardCount: &k.shards})
	var yaExiste *types.ResourceInUseException
	if err != nil && !errors.As(err, &yaExiste) {
		return err
	}
	return kinesis.NewStreamExistsWaiter(k.cl).Wait(ctx,
		&kinesis.DescribeStreamInput{StreamName: aws.String(evento.Topico)}, time.Minute)
}

// enviar reintenta solo los registros que Kinesis rechazó (por ejemplo, por pasar el límite del
// shard) y devuelve cuántos no entraron después de cinco intentos.
func (k *kinesisP) enviar(ctx context.Context, lote []item) int {
	registros := make([]types.PutRecordsRequestEntry, len(lote))
	for i, it := range lote {
		registros[i] = types.PutRecordsRequestEntry{Data: it.cuerpo, PartitionKey: aws.String(strconv.Itoa(it.e.Emisor))}
	}
	for intento := 0; intento < 5 && len(registros) > 0; intento++ {
		r, err := k.cl.PutRecords(ctx, &kinesis.PutRecordsInput{StreamName: aws.String(evento.Topico), Records: registros})
		if err != nil {
			time.Sleep(100 * time.Millisecond)
			continue
		}
		var pendientes []types.PutRecordsRequestEntry
		for i, res := range r.Records {
			if res.ErrorCode != nil {
				pendientes = append(pendientes, registros[i])
			}
		}
		if registros = pendientes; len(registros) > 0 {
			time.Sleep(100 * time.Millisecond)
		}
	}
	return len(registros)
}

func (k *kinesisP) Cerrar(context.Context) (int64, int64) { return k.cerrar() }
