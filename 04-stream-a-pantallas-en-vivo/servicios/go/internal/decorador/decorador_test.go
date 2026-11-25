package decorador

import (
	"encoding/base64"
	"encoding/json"
	"fmt"
	"math"
	"math/rand"
	"testing"
)

const (
	tipos    = 150
	clientes = 500
	equipos  = 50_000
	ios      = 25
)

func armar(nPlat, geoPorCliente int) (*Decorador, [][]byte) {
	r := rand.New(rand.NewSource(7))
	plats := make([]string, nPlat)
	cableado := make([]map[int]map[string]Senal, nPlat)
	for p := range plats {
		plats[p] = fmt.Sprintf("front-%d", p)
		cableado[p] = map[int]map[string]Senal{}
		for t := 0; t < tipos; t++ {
			m := map[string]Senal{}
			for i := 0; i < ios-5; i++ { // 5 IO sin cablear por tipo
				m[fmt.Sprint(i*7%240)] = Senal{Nombre: fmt.Sprintf("senal_%d_%d", p, (i+t+p)%40), Escala: 0.1 * float64(1+(t+p)%10)}
			}
			cableado[p][t] = m
		}
	}
	geo := map[int][]Geocerca{}
	for c := 0; c < clientes; c++ {
		for g := 0; g < geoPorCliente; g++ {
			cla, clo := 14.5+r.Float64()*18, -117+r.Float64()*30
			rad := 0.002 + r.Float64()*0.05
			gc := Geocerca{ID: c*10_000 + g, MinLat: 90, MaxLat: -90, MinLon: 180, MaxLon: -180}
			for v := 0; v < 20; v++ {
				a := 2 * math.Pi * float64(v) / 20
				la, lo := cla+rad*math.Sin(a), clo+rad*math.Cos(a)
				gc.Lat, gc.Lon = append(gc.Lat, la), append(gc.Lon, lo)
				gc.MinLat, gc.MaxLat = math.Min(gc.MinLat, la), math.Max(gc.MaxLat, la)
				gc.MinLon, gc.MaxLon = math.Min(gc.MinLon, lo), math.Max(gc.MaxLon, lo)
			}
			geo[c] = append(geo[c], gc)
		}
	}
	crudo := make([]byte, 180)
	eventos := make([][]byte, 20_000)
	for i := range eventos {
		e := r.Intn(equipos)
		r.Read(crudo)
		io := map[string]float64{}
		for k := 0; k < ios; k++ {
			io[fmt.Sprint(k*7%240)] = float64(r.Intn(65535))
		}
		s := Sobre{Schema: "v1", Channel: "principal", IMEI: fmt.Sprintf("86%013d", e), Familia: "familia-a",
			Tipo: e % tipos, ClientID: e % clientes, GroupID: fmt.Sprintf("grupo-%d", e%2000), Recibido: 1795219732274,
			Raw:   base64.StdEncoding.EncodeToString(crudo),
			Punto: Punto{Lat: 14.5 + r.Float64()*18, Lon: -117 + r.Float64()*30, Speed: r.Float64() * 110, Heading: r.Float64() * 360, TS: 1795219732000, IO: io}}
		eventos[i], _ = json.Marshal(s)
	}
	return Nuevo(plats, cableado, geo), eventos
}

func corre(b *testing.B, nPlat, geoPorCliente int) {
	d, ev := armar(nPlat, geoPorCliente)
	var bytesIn, bytesOut int
	b.ReportAllocs()
	b.ResetTimer()
	for i := 0; i < b.N; i++ {
		e := ev[i%len(ev)]
		out, err := d.Decorar(e)
		if err != nil {
			b.Fatal(err)
		}
		bytesIn += len(e)
		for _, o := range out {
			bytesOut += len(o)
		}
	}
	b.ReportMetric(float64(bytesIn)/float64(b.N), "B_entrada/evento")
	b.ReportMetric(float64(bytesOut)/float64(b.N)/float64(nPlat), "B_salida/plataforma")
	b.ReportMetric(float64(b.N)/b.Elapsed().Seconds(), "eventos/s")
}

func BenchmarkDecorar(b *testing.B) {
	for _, plat := range []int{1, 3, 5} {
		for _, geo := range []int{0, 150, 2000} {
			b.Run(fmt.Sprintf("plataformas=%d/geocercas_por_cliente=%d", plat, geo), func(b *testing.B) { corre(b, plat, geo) })
		}
	}
}

func TestSalida(t *testing.T) {
	d, ev := armar(3, 150)
	out, err := d.Decorar(ev[0])
	if err != nil || len(out) != 3 {
		t.Fatalf("salidas=%d err=%v", len(out), err)
	}
	var s Salida
	if err := json.Unmarshal(out[1], &s); err != nil || s.Plataforma != "front-1" || len(s.Senales) != ios {
		t.Fatalf("salida inesperada: %s", out[1])
	}
}
