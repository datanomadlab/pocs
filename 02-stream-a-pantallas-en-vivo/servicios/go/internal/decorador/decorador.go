// Package decorador es un prototipo mínimo para medir cuánto cuesta enriquecer un evento antes de
// entregarlo a las pantallas. Por cada evento: lo lee, traduce sus lecturas al nombre y la escala
// que espera cada destino según el tipo de emisor, evalúa las reglas de la cuenta recordando cuáles
// estaban activas para ese emisor (para decir cuál se activó y cuál se desactivó) y arma una salida
// por destino.
//
// Es un solo hilo en memoria: no lee el transporte, no escribe a ningún lado y no comparte el
// estado con otra réplica. Mide el costo de CPU por evento y nada más. Solo biblioteca estándar.
package decorador

import (
	"encoding/json"
	"fmt"
	"slices"
)

// Lectura es el evento que llega: un emisor informa varios valores, cada uno en un canal.
// Datos es relleno, como en los eventos del experimento: lleva el evento al tamaño que se mide.
type Lectura struct {
	Emisor  string             `json:"emisor"`
	Tipo    int                `json:"tipo"`
	Cuenta  int                `json:"cuenta"`
	TsUs    int64              `json:"ts_us"`
	Valores map[string]float64 `json:"valores"`
	Datos   string             `json:"datos"`
}

// Senal dice cómo llama un destino a un canal y por cuánto multiplica su valor.
type Senal struct {
	Nombre string
	Escala float64
}

// Regla está activa mientras el valor de su canal esté entre Min y Max.
type Regla struct {
	ID       int
	Min, Max float64
}

// Salida es lo que recibe un destino por cada evento.
type Salida struct {
	Destino      string             `json:"destino"`
	Emisor       string             `json:"emisor"`
	Cuenta       int                `json:"cuenta"`
	TsUs         int64              `json:"ts_us"`
	Senales      map[string]float64 `json:"senales"`
	Activas      []int              `json:"reglas_activas"`
	Activadas    []int              `json:"activadas,omitempty"`
	Desactivadas []int              `json:"desactivadas,omitempty"`
}

// Decorador guarda la configuración y, por emisor, qué reglas estaban activas en su última lectura.
type Decorador struct {
	destinos   []string
	traduccion []map[int]map[string]Senal // por destino y tipo de emisor: canal -> señal
	reglas     map[int]map[string][]Regla // por cuenta: canal -> reglas sobre ese canal
	activas    map[string][]int           // por emisor
}

// Nuevo arma un decorador. traduccion va en el mismo orden que destinos.
func Nuevo(destinos []string, traduccion []map[int]map[string]Senal, reglas map[int]map[string][]Regla) (*Decorador, error) {
	if len(destinos) == 0 || len(destinos) != len(traduccion) {
		return nil, fmt.Errorf("hay %d destinos y %d traducciones: tiene que haber una por destino", len(destinos), len(traduccion))
	}
	return &Decorador{destinos: destinos, traduccion: traduccion, reglas: reglas, activas: map[string][]int{}}, nil
}

// Decorar devuelve una salida serializada por destino.
func (d *Decorador) Decorar(crudo []byte) ([][]byte, error) {
	var l Lectura
	if err := json.Unmarshal(crudo, &l); err != nil {
		return nil, fmt.Errorf("el evento no es una lectura: %w", err)
	}
	ahora := d.evaluar(l)
	antes := d.activas[l.Emisor]
	activadas, desactivadas := faltan(ahora, antes), faltan(antes, ahora)
	d.activas[l.Emisor] = ahora

	salidas := make([][]byte, 0, len(d.destinos))
	for i, destino := range d.destinos {
		cuerpo, err := json.Marshal(Salida{Destino: destino, Emisor: l.Emisor, Cuenta: l.Cuenta, TsUs: l.TsUs,
			Senales: traducir(l.Valores, d.traduccion[i][l.Tipo]), Activas: ahora,
			Activadas: activadas, Desactivadas: desactivadas})
		if err != nil {
			return nil, fmt.Errorf("no se pudo armar la salida para %s: %w", destino, err)
		}
		salidas = append(salidas, cuerpo)
	}
	return salidas, nil
}

// evaluar devuelve, ordenadas, las reglas de la cuenta que esta lectura deja activas.
func (d *Decorador) evaluar(l Lectura) []int {
	activas := []int{}
	for canal, reglas := range d.reglas[l.Cuenta] {
		valor, informado := l.Valores[canal]
		if !informado {
			continue
		}
		for _, r := range reglas {
			if valor >= r.Min && valor <= r.Max {
				activas = append(activas, r.ID)
			}
		}
	}
	slices.Sort(activas)
	return activas
}

// faltan devuelve los elementos de a que no están en b.
func faltan(a, b []int) []int {
	var solo []int
	for _, x := range a {
		if !slices.Contains(b, x) {
			solo = append(solo, x)
		}
	}
	return solo
}

// traducir aplica el nombre y la escala de cada canal. Un canal sin señal pasa con su número.
func traducir(valores map[string]float64, senales map[string]Senal) map[string]float64 {
	salida := make(map[string]float64, len(valores))
	for canal, valor := range valores {
		if s, ok := senales[canal]; ok {
			salida[s.Nombre] = valor * s.Escala
		} else {
			salida["canal_"+canal] = valor
		}
	}
	return salida
}
