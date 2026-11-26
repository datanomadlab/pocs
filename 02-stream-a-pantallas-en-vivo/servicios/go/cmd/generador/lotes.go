package main

import (
	"context"
	"sync"
	"sync/atomic"
	"time"

	"stream/internal/evento"
)

type item struct {
	e      evento.Evento
	cuerpo []byte
}

// porLotes agrupa envíos para los servicios que cobran o limitan por solicitud (Kinesis y SQS).
// Cada emisor va siempre al mismo trabajador, que envía un lote tras otro: así dos eventos del
// mismo emisor nunca viajan en solicitudes simultáneas y no pueden cruzarse.
type porLotes struct {
	colas                 []chan item
	espera                sync.WaitGroup
	confirmados, fallidos atomic.Int64
}

const demoraLote = 20 * time.Millisecond

func nuevoPorLotes(trabajadores, tamano int, enviar func(context.Context, []item) (fallidos int)) *porLotes {
	p := &porLotes{colas: make([]chan item, trabajadores)}
	for i := range p.colas {
		p.colas[i] = make(chan item, 10_000)
		p.espera.Add(1)
		go p.trabajar(p.colas[i], tamano, enviar)
	}
	return p
}

func (p *porLotes) trabajar(cola chan item, tamano int, enviar func(context.Context, []item) int) {
	defer p.espera.Done()
	lote := make([]item, 0, tamano)
	despachar := func() {
		if len(lote) == 0 {
			return
		}
		fallidos := enviar(context.Background(), lote)
		p.fallidos.Add(int64(fallidos))
		p.confirmados.Add(int64(len(lote) - fallidos))
		lote = lote[:0]
	}
	reloj := time.NewTicker(demoraLote)
	defer reloj.Stop()
	for {
		select {
		case it, abierto := <-cola:
			if !abierto {
				despachar()
				return
			}
			if lote = append(lote, it); len(lote) == tamano {
				despachar()
			}
		case <-reloj.C:
			despachar()
		}
	}
}

func (p *porLotes) Enviar(_ context.Context, e evento.Evento, cuerpo []byte) {
	p.colas[e.Emisor%len(p.colas)] <- item{e, cuerpo}
}

func (p *porLotes) cerrar() (int64, int64) {
	for _, c := range p.colas {
		close(c)
	}
	p.espera.Wait()
	return p.confirmados.Load(), p.fallidos.Load()
}
