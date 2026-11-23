package main

import (
	"context"
	"strconv"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/aws/aws-sdk-go-v2/service/sqs/types"

	"stream/internal/evento"
)

// lectoresSqs es cuántas solicitudes de lectura corren a la vez. Cada una trae 10 mensajes como
// máximo, así que el ritmo de lectura lo fija este número y no el volumen de datos.
const lectoresSqs = 16

// leerSqs lee de una cola FIFO. SQS no entrega el siguiente mensaje de un grupo (un emisor)
// hasta que el anterior se borra, y eso mantiene el orden aunque haya varios lectores.
func leerSqs(ctx context.Context, destino string, entregar func([]byte)) error {
	cfg, err := evento.ConfigAWS(ctx)
	if err != nil {
		return err
	}
	cl := sqs.NewFromConfig(cfg, func(s *sqs.Options) { s.BaseEndpoint = aws.String(destino) })
	cola := aws.String(destino + "/000000000000/" + evento.Topico + ".fifo")
	fallo := make(chan error, lectoresSqs)
	for i := 0; i < lectoresSqs; i++ {
		go func() { fallo <- leerCola(ctx, cl, cola, entregar) }()
	}
	return <-fallo
}

func leerCola(ctx context.Context, cl *sqs.Client, cola *string, entregar func([]byte)) error {
	for {
		r, err := cl.ReceiveMessage(ctx, &sqs.ReceiveMessageInput{QueueUrl: cola,
			MaxNumberOfMessages: 10, WaitTimeSeconds: 1})
		if err != nil {
			return err
		}
		if len(r.Messages) == 0 {
			continue
		}
		borrar := make([]types.DeleteMessageBatchRequestEntry, len(r.Messages))
		for i, m := range r.Messages {
			entregar([]byte(*m.Body))
			borrar[i] = types.DeleteMessageBatchRequestEntry{Id: aws.String(strconv.Itoa(i)), ReceiptHandle: m.ReceiptHandle}
		}
		if _, err := cl.DeleteMessageBatch(ctx, &sqs.DeleteMessageBatchInput{QueueUrl: cola, Entries: borrar}); err != nil {
			return err
		}
	}
}
