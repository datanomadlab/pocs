package main

import (
	"context"
	"fmt"
	"strconv"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
	"github.com/aws/aws-sdk-go-v2/service/sqs/types"

	"stream/internal/evento"
)

// sqsP escribe en una cola FIFO, 10 mensajes por solicitud (el máximo). El grupo del mensaje es
// el emisor: SQS FIFO entrega en orden dentro de cada grupo.
type sqsP struct {
	*porLotes
	cl  *sqs.Client
	url string
}

const colaFifo = evento.Topico + ".fifo"

func nuevoSqs(o opciones) (*sqsP, error) {
	cfg, err := evento.ConfigAWS(context.Background())
	if err != nil {
		return nil, err
	}
	s := &sqsP{cl: sqs.NewFromConfig(cfg, func(s *sqs.Options) { s.BaseEndpoint = aws.String(o.destino) }),
		url: o.destino + "/000000000000/" + colaFifo}
	s.porLotes = nuevoPorLotes(16, 10, s.enviar)
	return s, nil
}

func (s *sqsP) Preparar(ctx context.Context) error {
	_, err := s.cl.CreateQueue(ctx, &sqs.CreateQueueInput{QueueName: aws.String(colaFifo),
		Attributes: map[string]string{"FifoQueue": "true", "VisibilityTimeout": "30"}})
	return err
}

func (s *sqsP) enviar(ctx context.Context, lote []item) int {
	entradas := make([]types.SendMessageBatchRequestEntry, len(lote))
	for i, it := range lote {
		id := fmt.Sprintf("%s-%d-%d", it.e.Corrida, it.e.Emisor, it.e.Seq)
		entradas[i] = types.SendMessageBatchRequestEntry{Id: aws.String(strconv.Itoa(i)),
			MessageBody: aws.String(string(it.cuerpo)), MessageGroupId: aws.String(strconv.Itoa(it.e.Emisor)),
			MessageDeduplicationId: aws.String(id),
			MessageAttributes: map[string]types.MessageAttributeValue{evento.CabeceraCanales: {
				DataType: aws.String("String"), StringValue: aws.String(evento.Canal(it.e.Cuenta))}}}
	}
	r, err := s.cl.SendMessageBatch(ctx, &sqs.SendMessageBatchInput{QueueUrl: &s.url, Entries: entradas})
	if err != nil {
		return len(lote)
	}
	return len(r.Failed)
}

func (s *sqsP) Cerrar(context.Context) (int64, int64) { return s.cerrar() }
