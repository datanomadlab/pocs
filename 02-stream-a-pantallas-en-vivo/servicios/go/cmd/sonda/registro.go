package main

import (
	"encoding/json"
	"sync"
	"sync/atomic"
	"time"

	"github.com/HdrHistogram/hdrhistogram-go"

	"stream/internal/evento"
)

const (
	tramoSerie = 200 * time.Millisecond
	// La latencia se guarda en microsegundos, de 1 µs a 10 minutos, con 3 cifras significativas.
	latenciaMaxUs = 600_000_000
)

// emisor guarda qué números de secuencia ya llegaron (un bit por evento) y el mayor visto.
type emisor struct {
	vistos []uint64
	ultimo int64
}

// registro lleva la cuenta de todo lo que las pantallas recibieron.
type registro struct {
	corrida      string
	o            opciones
	mu           sync.Mutex
	emisores     map[int]*emisor
	total, tramo *hdrhistogram.Histogram
	inicio       time.Time
	serie        [][4]int64 // [ms desde el inicio, eventos, p99 en ms, máximo en ms]

	unicos, duplicados, desordenados, ajenos atomic.Int64
	reconexiones, sinRecuperar               atomic.Int64
	copias                                   atomic.Int64
}

func nuevoRegistro(corrida string) *registro {
	return &registro{corrida: corrida, emisores: map[int]*emisor{},
		total: hdrhistogram.New(1, latenciaMaxUs, 3), tramo: hdrhistogram.New(1, latenciaMaxUs, 3)}
}

// recibir clasifica un evento: nuevo, duplicado (ya había llegado) o desordenado (nuevo, pero
// llegó después de uno posterior del mismo emisor).
//
// Cuando una cuenta la miran varias pantallas, solo se clasifica lo que recibe la principal; lo que
// reciben las demás se cuenta como copia y entra a la latencia.
func (r *registro) recibir(cuerpo []byte, pantalla int) {
	var e evento.Evento
	if err := json.Unmarshal(cuerpo, &e); err != nil || e.Corrida != r.corrida {
		r.ajenos.Add(1)
		return
	}
	latencia := min(max(time.Now().UnixMicro()-e.TsUs, 1), latenciaMaxUs)

	r.mu.Lock()
	defer r.mu.Unlock()
	if !principal(e.Cuenta, pantalla, r.o) {
		r.copias.Add(1)
		r.total.RecordValue(latencia)
		r.tramo.RecordValue(latencia)
		return
	}
	em := r.emisores[e.Emisor]
	if em == nil {
		em = &emisor{ultimo: -1}
		r.emisores[e.Emisor] = em
	}
	palabra, bit := int(e.Seq/64), uint64(1)<<(e.Seq%64)
	for len(em.vistos) <= palabra {
		em.vistos = append(em.vistos, 0)
	}
	if em.vistos[palabra]&bit != 0 {
		r.duplicados.Add(1)
		return
	}
	em.vistos[palabra] |= bit
	r.unicos.Add(1)
	if e.Seq < em.ultimo {
		r.desordenados.Add(1)
	} else {
		em.ultimo = e.Seq
	}
	r.total.RecordValue(latencia)
	r.tramo.RecordValue(latencia)
}

// empezar arranca el reloj y la serie por tramos, que sirve para ver cuánto dura un corte.
func (r *registro) empezar() {
	r.inicio = time.Now()
	go func() {
		for range time.Tick(tramoSerie) {
			r.mu.Lock()
			r.serie = append(r.serie, [4]int64{time.Since(r.inicio).Milliseconds(), r.tramo.TotalCount(),
				r.tramo.ValueAtQuantile(99) / 1000, r.tramo.Max() / 1000})
			r.tramo.Reset()
			r.mu.Unlock()
		}
	}()
}

func (r *registro) resumen() map[string]any {
	r.mu.Lock()
	defer r.mu.Unlock()
	ms := func(q float64) float64 { return float64(r.total.ValueAtQuantile(q)) / 1000 }
	return map[string]any{
		"unicos": r.unicos.Load(), "duplicados": r.duplicados.Load(), "desordenados": r.desordenados.Load(),
		"ajenos": r.ajenos.Load(), "copias": r.copias.Load(), "reconexiones": r.reconexiones.Load(), "sin_recuperar": r.sinRecuperar.Load(),
		"latencia_ms": map[string]float64{"p50": ms(50), "p95": ms(95), "p99": ms(99), "max": float64(r.total.Max()) / 1000},
		"tramo_ms":    tramoSerie.Milliseconds(), "serie": r.serie,
	}
}
