package decorador

import (
	"encoding/json"
	"fmt"
	"slices"
	"testing"
)

func leer(t *testing.T, cuerpo []byte) Salida {
	t.Helper()
	var s Salida
	if err := json.Unmarshal(cuerpo, &s); err != nil {
		t.Fatalf("la salida no se puede leer: %v", err)
	}
	return s
}

func TestDecorarTraduceLasLecturasParaCadaDestino(t *testing.T) {
	d, err := Nuevo([]string{"a", "b"},
		[]map[int]map[string]Senal{
			{1: {"7": {Nombre: "temperatura", Escala: 0.5}}},
			{1: {"7": {Nombre: "temp_c", Escala: 2}}},
		}, nil)
	if err != nil {
		t.Fatal(err)
	}

	salidas, err := d.Decorar([]byte(`{"emisor":"e1","tipo":1,"cuenta":3,"valores":{"7":10,"9":4}}`))

	if err != nil || len(salidas) != 2 {
		t.Fatalf("esperaba 2 salidas sin error: %d, %v", len(salidas), err)
	}
	a, b := leer(t, salidas[0]), leer(t, salidas[1])
	if a.Destino != "a" || a.Senales["temperatura"] != 5 || a.Senales["canal_9"] != 4 {
		t.Fatalf("salida inesperada para a: %+v", a)
	}
	if b.Destino != "b" || b.Senales["temp_c"] != 20 || b.Emisor != "e1" || b.Cuenta != 3 {
		t.Fatalf("salida inesperada para b: %+v", b)
	}
}

func TestDecorarRecuerdaLasReglasActivasDeCadaEmisor(t *testing.T) {
	reglas := map[int]map[string][]Regla{3: {"7": {{ID: 1, Min: 0, Max: 10}, {ID: 2, Min: 8, Max: 20}}}}
	d, err := Nuevo([]string{"a"}, []map[int]map[string]Senal{{}}, reglas)
	if err != nil {
		t.Fatal(err)
	}
	evento := func(emisor string, valor int) []byte {
		return []byte(fmt.Sprintf(`{"emisor":%q,"cuenta":3,"valores":{"7":%d}}`, emisor, valor))
	}
	pasos := []struct {
		emisor                           string
		valor                            int
		activas, activadas, desactivadas []int
	}{
		{"e1", 5, []int{1}, []int{1}, nil},
		{"e1", 9, []int{1, 2}, []int{2}, nil},
		{"e2", 15, []int{2}, []int{2}, nil}, // otro emisor: su estado es aparte
		{"e1", 15, []int{2}, nil, []int{1}},
		{"e1", 30, []int{}, nil, []int{2}},
	}
	for i, p := range pasos {
		salidas, err := d.Decorar(evento(p.emisor, p.valor))
		if err != nil {
			t.Fatalf("paso %d: %v", i, err)
		}
		s := leer(t, salidas[0])
		if !slices.Equal(s.Activas, p.activas) || !slices.Equal(s.Activadas, p.activadas) || !slices.Equal(s.Desactivadas, p.desactivadas) {
			t.Fatalf("paso %d: activas %v, activadas %v, desactivadas %v", i, s.Activas, s.Activadas, s.Desactivadas)
		}
	}
}

func TestDecorarRechazaLoQueNoEsUnaLectura(t *testing.T) {
	d, _ := Nuevo([]string{"a"}, []map[int]map[string]Senal{{}}, nil)
	if _, err := d.Decorar([]byte("no es json")); err == nil {
		t.Fatal("esperaba un error")
	}
}

func TestNuevoPideUnaTraduccionPorDestino(t *testing.T) {
	if _, err := Nuevo([]string{"a", "b"}, []map[int]map[string]Senal{{}}, nil); err == nil {
		t.Fatal("esperaba un error")
	}
}

func TestCargarArmaUnaSalidaPorDestino(t *testing.T) {
	d, eventos, err := Cargar(3, 100)
	if err != nil {
		t.Fatal(err)
	}
	salidas, err := d.Decorar(eventos[0])
	if err != nil || len(salidas) != 3 {
		t.Fatalf("esperaba 3 salidas sin error: %d, %v", len(salidas), err)
	}
	if s := leer(t, salidas[1]); s.Destino != "destino-1" || len(s.Senales) != lecturasPorEvento {
		t.Fatalf("salida inesperada: %+v", s)
	}
	for _, e := range eventos[:100] {
		if len(e) != bytesPorEvento {
			t.Fatalf("un evento pesa %d bytes, esperaba %d", len(e), bytesPorEvento)
		}
	}
}
