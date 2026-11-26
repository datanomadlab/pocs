// Package evento define el mensaje que viaja de punta a punta y los nombres que comparten
// el generador, los consumidores y la sonda.
package evento

import (
	"encoding/json"
	"strconv"
	"strings"
)

const (
	// Topico es el nombre del tópico, stream o cola en todos los transportes.
	Topico = "eventos"
	// CabeceraCanales le dice a Centrifugo en qué canal publicar, sin tocar el contenido.
	CabeceraCanalesKafka = "x-centrifugo-channels"
	CabeceraCanales      = "centrifugo-channels"
)

// Evento es lo que emite cada emisor. Seq crece de uno en uno por emisor y corrida:
// con eso la sonda sabe si algo se perdió, se repitió o llegó fuera de orden.
type Evento struct {
	Corrida string `json:"corrida"`
	Emisor  int    `json:"emisor"`
	Cuenta  int    `json:"cuenta"`
	Seq     int64  `json:"seq"`
	TsUs    int64  `json:"ts_us"`
	Datos   string `json:"datos"`
}

// Canal es el canal de pantalla de una cuenta: cada pantalla mira una o varias cuentas.
func Canal(cuenta int) string { return "cuenta:" + strconv.Itoa(cuenta) }

// Codificar arma el JSON y lo rellena hasta el tamaño pedido.
func Codificar(e Evento, bytes int) []byte {
	e.Datos = ""
	base, _ := json.Marshal(e)
	if falta := bytes - len(base); falta > 0 {
		e.Datos = strings.Repeat("x", falta)
		base, _ = json.Marshal(e)
	}
	return base
}
