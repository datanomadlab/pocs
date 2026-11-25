// Package decorador es un prototipo mínimo para medir cuánto cuesta enriquecer un evento antes de
// entregarlo a las pantallas. Por cada evento: lo lee, traduce sus señales según el tipo de emisor y
// la plataforma de destino, evalúa las geocercas de su cuenta recordando en cuáles estaba el emisor
// (para decir a cuál entró y de cuál salió) y arma una salida por plataforma.
//
// Es un solo hilo en memoria: no lee el transporte, no escribe a ningún lado y no comparte el
// estado con otra réplica. Mide el costo de CPU por evento y nada más. Solo biblioteca estándar.
//
//	go test ./internal/decorador -run xxx -bench . -benchtime 2s -cpu 1
package decorador

import "encoding/json"

type Punto struct {
	Lat     float64            `json:"lat"`
	Lon     float64            `json:"lon"`
	Speed   float64            `json:"speed"`
	Heading float64            `json:"heading"`
	TS      int64              `json:"ts"`
	IO      map[string]float64 `json:"io"`
}

type Sobre struct {
	Schema   string `json:"schemaVersion"`
	Channel  string `json:"channel"`
	IMEI     string `json:"imei"`
	Familia  string `json:"device_family"`
	Tipo     int    `json:"device_type"`
	ClientID int    `json:"client_id"`
	GroupID  string `json:"group_id"`
	Recibido int64  `json:"received_at"`
	Raw      string `json:"raw_payload"`
	Punto    Punto  `json:"json_payload"`
}

type Senal struct {
	Nombre string
	Escala float64
}

type Geocerca struct {
	ID                             int
	MinLat, MaxLat, MinLon, MaxLon float64
	Lat, Lon                       []float64
}

type Salida struct {
	Plataforma string             `json:"platform"`
	IMEI       string             `json:"imei"`
	ClientID   int                `json:"client_id"`
	TS         int64              `json:"ts"`
	Lat        float64            `json:"lat"`
	Lon        float64            `json:"lon"`
	Speed      float64            `json:"speed"`
	Senales    map[string]float64 `json:"signals"`
	Dentro     []int              `json:"geofences"`
	Entra      []int              `json:"entered,omitempty"`
	Sale       []int              `json:"exited,omitempty"`
}

type Decorador struct {
	Plataformas []string
	// cableado[plataforma][tipo de equipo][id de IO] -> señal
	Cableado  []map[int]map[string]Senal
	Geocercas map[int][]Geocerca // por cliente
	estado    map[string][]int   // geocercas en las que está cada equipo
}

func Nuevo(plataformas []string, cableado []map[int]map[string]Senal, geo map[int][]Geocerca) *Decorador {
	return &Decorador{Plataformas: plataformas, Cableado: cableado, Geocercas: geo, estado: map[string][]int{}}
}

func dentro(g *Geocerca, lat, lon float64) bool {
	if lat < g.MinLat || lat > g.MaxLat || lon < g.MinLon || lon > g.MaxLon {
		return false
	}
	in := false
	n := len(g.Lat)
	for i, j := 0, n-1; i < n; j, i = i, i+1 {
		if (g.Lat[i] > lat) != (g.Lat[j] > lat) &&
			lon < (g.Lon[j]-g.Lon[i])*(lat-g.Lat[i])/(g.Lat[j]-g.Lat[i])+g.Lon[i] {
			in = !in
		}
	}
	return in
}

func contiene(v []int, x int) bool {
	for _, y := range v {
		if y == x {
			return true
		}
	}
	return false
}

// Decorar devuelve una salida serializada por plataforma.
func (d *Decorador) Decorar(crudo []byte) ([][]byte, error) {
	var s Sobre
	if err := json.Unmarshal(crudo, &s); err != nil {
		return nil, err
	}
	var ahora []int
	gs := d.Geocercas[s.ClientID]
	for i := range gs {
		if dentro(&gs[i], s.Punto.Lat, s.Punto.Lon) {
			ahora = append(ahora, gs[i].ID)
		}
	}
	antes := d.estado[s.IMEI]
	var entra, sale []int
	for _, g := range ahora {
		if !contiene(antes, g) {
			entra = append(entra, g)
		}
	}
	for _, g := range antes {
		if !contiene(ahora, g) {
			sale = append(sale, g)
		}
	}
	d.estado[s.IMEI] = ahora

	out := make([][]byte, 0, len(d.Plataformas))
	for p, nombre := range d.Plataformas {
		mapa := d.Cableado[p][s.Tipo]
		senales := make(map[string]float64, len(s.Punto.IO))
		for id, v := range s.Punto.IO {
			if sn, ok := mapa[id]; ok {
				senales[sn.Nombre] = v * sn.Escala
			} else {
				senales["io_"+id] = v
			}
		}
		b, err := json.Marshal(Salida{Plataforma: nombre, IMEI: s.IMEI, ClientID: s.ClientID, TS: s.Punto.TS,
			Lat: s.Punto.Lat, Lon: s.Punto.Lon, Speed: s.Punto.Speed, Senales: senales, Dentro: ahora, Entra: entra, Sale: sale})
		if err != nil {
			return nil, err
		}
		out = append(out, b)
	}
	return out, nil
}
