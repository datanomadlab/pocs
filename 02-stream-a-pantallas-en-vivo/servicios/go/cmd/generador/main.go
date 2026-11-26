// generador emite eventos a una tasa fija, como lo haría la pieza que ya los entrega armados.
//
// Cada emisor numera sus eventos de uno en uno. Al terminar imprime en una línea de JSON cuántos
// confirmó el transporte: la sonda compara contra ese número para saber si algo se perdió.
package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"

	"stream/internal/evento"
)

// Productor es lo mínimo que el generador necesita de un transporte.
type Productor interface {
	// Preparar crea el tópico, stream o cola si no existe.
	Preparar(ctx context.Context) error
	// Enviar encola un evento. No bloquea salvo que el transporte esté saturado.
	Enviar(ctx context.Context, e evento.Evento, cuerpo []byte)
	// Cerrar espera las confirmaciones pendientes y devuelve confirmados y fallidos.
	Cerrar(ctx context.Context) (confirmados, fallidos int64)
}

type opciones struct {
	transporte, destino, corrida string
	tasa, emisores, cuentas      int
	bytes, particiones           int
	duracion                     time.Duration
	preparar                     bool
	sinComprimir                 bool
}

func nuevoProductor(o opciones) (Productor, error) {
	switch o.transporte {
	case "redpanda":
		return nuevoKafka(o)
	case "nats":
		return nuevoNats(o)
	case "kinesis":
		return nuevoKinesis(o)
	case "sqs":
		return nuevoSqs(o)
	}
	return nil, fmt.Errorf("transporte desconocido: %q", o.transporte)
}

func main() {
	var o opciones
	flag.StringVar(&o.transporte, "transporte", "", "redpanda, nats, kinesis o sqs")
	flag.StringVar(&o.destino, "destino", "", "dirección del transporte")
	flag.StringVar(&o.corrida, "corrida", "c0", "identificador de la corrida")
	flag.IntVar(&o.tasa, "tasa", 10000, "eventos por segundo")
	flag.IntVar(&o.emisores, "emisores", 100000, "emisores distintos")
	flag.IntVar(&o.cuentas, "cuentas", 1000, "cuentas entre las que se reparten los emisores")
	flag.IntVar(&o.bytes, "bytes", 300, "tamaño de cada evento")
	flag.IntVar(&o.particiones, "particiones", 12, "particiones o shards al crear el tópico")
	flag.DurationVar(&o.duracion, "duracion", 30*time.Second, "cuánto tiempo emitir")
	flag.BoolVar(&o.preparar, "preparar", false, "solo crea el tópico, stream o cola y termina")
	flag.BoolVar(&o.sinComprimir, "sin-comprimir", false, "Kafka: escribe los lotes sin comprimir")
	flag.Parse()

	ctx := context.Background()
	p, err := nuevoProductor(o)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Error:", err)
		os.Exit(1)
	}
	if o.preparar {
		if err := p.Preparar(ctx); err != nil {
			fmt.Fprintln(os.Stderr, "Error al preparar:", err)
			os.Exit(1)
		}
		p.Cerrar(ctx)
		return
	}
	emitidos, atraso := emitir(ctx, p, o)
	inicioCierre := time.Now()
	confirmados, fallidos := p.Cerrar(ctx)
	json.NewEncoder(os.Stdout).Encode(map[string]any{
		"emitidos": emitidos, "confirmados": confirmados, "fallidos": fallidos,
		"atraso_max_ms": atraso.Milliseconds(), "cierre_ms": time.Since(inicioCierre).Milliseconds(),
	})
}

// emitir reparte la tasa en pasos de 10 ms. Si el transporte frena al generador, el atraso
// máximo lo delata: una ruta que no absorbe la tasa no pasa por "lenta en la pantalla".
func emitir(ctx context.Context, p Productor, o opciones) (int64, time.Duration) {
	const paso = 10 * time.Millisecond
	seq := make([]int64, o.emisores)
	inicio := time.Now()
	var emitidos int64
	var atrasoMax time.Duration
	for n := int64(1); ; n++ {
		transcurrido := time.Duration(n) * paso
		if transcurrido > o.duracion {
			return emitidos, atrasoMax
		}
		meta := int64(float64(o.tasa) * transcurrido.Seconds())
		for ; emitidos < meta; emitidos++ {
			emisor := int(emitidos % int64(o.emisores))
			e := evento.Evento{Corrida: o.corrida, Emisor: emisor, Cuenta: emisor % o.cuentas,
				Seq: seq[emisor], TsUs: time.Now().UnixMicro()}
			seq[emisor]++
			p.Enviar(ctx, e, evento.Codificar(e, o.bytes))
		}
		if espera := time.Until(inicio.Add(transcurrido)); espera > 0 {
			time.Sleep(espera)
		} else if -espera > atrasoMax {
			atrasoMax = -espera
		}
	}
}
