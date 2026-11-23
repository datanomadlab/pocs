package main

import (
	"bufio"
	"bytes"
	"net/http"
	"sync/atomic"
	"time"

	"stream/internal/evento"
)

// silencioSSE es cuánto tiene que pasar sin eventos para dar por entregado el histórico.
const silencioSSE = time.Second

// conectarSSE abre un flujo de Server-Sent Events por cada cuenta que mira la pantalla, igual
// que lo haría el front con EventSource. Si el flujo se corta, vuelve a pedirlo con el id del
// último evento que vio (Last-Event-ID) para que el servidor siga desde ahí.
//
// Un flujo nuevo recibe primero el histórico que el servidor guarda de esa cuenta. Las pantallas
// se dan por listas cuando todos los flujos abrieron y el histórico terminó de llegar: así la
// medición parte con las pantallas al día, igual que en las otras rutas.
func conectarSSE(o opciones, r *registro, lista func()) {
	cliente := &http.Client{Transport: &http.Transport{DisableCompression: true}}
	var abiertos, flujos atomic.Int64
	var ultimoEvento atomic.Int64
	recibir := func(cuerpo []byte) {
		ultimoEvento.Store(time.Now().UnixNano())
		r.recibir(cuerpo)
	}
	for i := 0; i < o.pantallas; i++ {
		for _, cuenta := range cuentasDe(i, o) {
			flujos.Add(1)
			go func(url string) {
				ultimo, abierto := "", false
				for {
					ultimo = leerSSE(cliente, url, ultimo, recibir, func() {
						if abierto {
							r.reconexiones.Add(1)
							return
						}
						abierto = true
						abiertos.Add(1)
					})
					time.Sleep(pausaReconexion)
				}
			}(o.destino + "/" + evento.Canal(cuenta))
		}
	}
	for abiertos.Load() < flujos.Load() {
		time.Sleep(50 * time.Millisecond)
	}
	ultimoEvento.Store(time.Now().UnixNano())
	for time.Since(time.Unix(0, ultimoEvento.Load())) < silencioSSE {
		time.Sleep(50 * time.Millisecond)
	}
	for i := 0; i < o.pantallas; i++ {
		lista()
	}
}

// leerSSE lee un flujo hasta que se corta y devuelve el id del último evento recibido.
func leerSSE(cliente *http.Client, url, ultimo string, recibir func([]byte), abierto func()) string {
	pedido, err := http.NewRequest(http.MethodGet, url, nil)
	if err != nil {
		return ultimo
	}
	pedido.Header.Set("Accept", "text/event-stream")
	if ultimo != "" {
		pedido.Header.Set("Last-Event-ID", ultimo)
	}
	respuesta, err := cliente.Do(pedido)
	if err != nil {
		return ultimo
	}
	defer respuesta.Body.Close()
	if respuesta.StatusCode != http.StatusOK {
		return ultimo
	}
	abierto()
	var datos []byte
	id := ultimo
	lineas := bufio.NewReaderSize(respuesta.Body, 64<<10)
	for {
		linea, err := lineas.ReadBytes('\n')
		if err != nil {
			return ultimo
		}
		linea = bytes.TrimRight(linea, "\r\n")
		switch {
		case len(linea) == 0: // una línea vacía cierra el evento
			if datos != nil {
				recibir(datos)
				ultimo = id
			}
			datos = nil
		case bytes.HasPrefix(linea, []byte("data:")):
			datos = append(datos, bytes.TrimPrefix(linea[5:], []byte(" "))...)
		case bytes.HasPrefix(linea, []byte("id:")):
			id = string(bytes.TrimPrefix(linea[3:], []byte(" ")))
		}
	}
}
