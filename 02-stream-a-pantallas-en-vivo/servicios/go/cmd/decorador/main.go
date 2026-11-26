// decorador mide, en un solo hilo, cuántos eventos por segundo se pueden enriquecer antes de
// entregarlos. Corre una combinación de destinos y reglas por cuenta y escribe el resultado en JSON.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"

	"stream/internal/decorador"
)

func main() {
	destinos := flag.Int("destinos", 1, "destinos que reciben una salida por evento")
	reglas := flag.Int("reglas", 0, "reglas por cuenta")
	duracion := flag.Duration("duracion", 3*time.Second, "cuánto medir")
	flag.Parse()

	d, eventos, err := decorador.Cargar(*destinos, *reglas)
	if err != nil {
		fmt.Fprintln(os.Stderr, "Error al armar la carga:", err)
		os.Exit(1)
	}
	var n, entrada, salida int
	inicio := time.Now()
	for time.Since(inicio) < *duracion {
		evento := eventos[n%len(eventos)]
		salidas, err := d.Decorar(evento)
		if err != nil {
			fmt.Fprintln(os.Stderr, "Error al enriquecer:", err)
			os.Exit(1)
		}
		n++
		entrada += len(evento)
		for _, s := range salidas {
			salida += len(s)
		}
	}
	json.NewEncoder(os.Stdout).Encode(map[string]any{
		"destinos": *destinos, "reglas": *reglas, "eventos": n,
		"eventos_s":     float64(n) / time.Since(inicio).Seconds(),
		"bytes_entrada": entrada / n, "bytes_salida": salida / n / *destinos,
	})
}
