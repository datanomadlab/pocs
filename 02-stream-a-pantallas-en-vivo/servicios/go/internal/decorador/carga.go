package decorador

import (
	"encoding/json"
	"fmt"
	"math/rand"
	"strings"
)

// La carga sintética de la medición: siempre la misma, para que las corridas se puedan comparar.
const (
	tiposDeEmisor     = 100
	cuentas           = 500
	emisores          = 5_000 // cada uno aparece varias veces con valores distintos: su estado cambia
	lecturasPorEvento = 20
	sinTraducir       = 4     // lecturas de cada evento que ningún destino sabe nombrar
	valorMaximo       = 1_000 // los valores van de 0 a este número
	bytesPorEvento    = 1_000 // el mismo tamaño que usa la prueba de concurrencia
	eventosDistintos  = 20_000
	semilla           = 7
)

// Cargar arma un decorador con `destinos` destinos y `reglasPorCuenta` reglas por cuenta, y los
// eventos con que medirlo. Cada regla cubre entre el 0,05 % y el 0,5 % del rango de un canal, así
// que una lectura deja activas unas pocas.
func Cargar(destinos, reglasPorCuenta int) (*Decorador, [][]byte, error) {
	azar := rand.New(rand.NewSource(semilla))
	canal := func(i int) string { return fmt.Sprintf("c%02d", i) }

	nombres := make([]string, destinos)
	traduccion := make([]map[int]map[string]Senal, destinos)
	for d := range nombres {
		nombres[d] = fmt.Sprintf("destino-%d", d)
		traduccion[d] = map[int]map[string]Senal{}
		for tipo := 0; tipo < tiposDeEmisor; tipo++ {
			senales := map[string]Senal{}
			for i := 0; i < lecturasPorEvento-sinTraducir; i++ {
				senales[canal(i)] = Senal{Nombre: fmt.Sprintf("senal_%d_%d", d, (i+tipo+d)%40), Escala: 0.1 * float64(1+(tipo+d)%10)}
			}
			traduccion[d][tipo] = senales
		}
	}

	reglas := map[int]map[string][]Regla{}
	for c := 0; c < cuentas; c++ {
		reglas[c] = map[string][]Regla{}
		for r := 0; r < reglasPorCuenta; r++ {
			ancho := valorMaximo * (0.0005 + azar.Float64()*0.0045)
			desde := azar.Float64() * (valorMaximo - ancho)
			sobre := canal(azar.Intn(lecturasPorEvento))
			reglas[c][sobre] = append(reglas[c][sobre], Regla{ID: c*10_000 + r, Min: desde, Max: desde + ancho})
		}
	}

	eventos := make([][]byte, eventosDistintos)
	for i := range eventos {
		emisor := azar.Intn(emisores)
		valores := map[string]float64{}
		for k := 0; k < lecturasPorEvento; k++ {
			valores[canal(k)] = float64(azar.Intn(valorMaximo*100)) / 100
		}
		lectura := Lectura{Emisor: fmt.Sprintf("emisor-%06d", emisor), Tipo: emisor % tiposDeEmisor,
			Cuenta: emisor % cuentas, TsUs: 1_795_219_732_000_000, Valores: valores}
		cuerpo, err := rellenar(lectura)
		if err != nil {
			return nil, nil, fmt.Errorf("no se pudo armar el evento %d: %w", i, err)
		}
		eventos[i] = cuerpo
	}
	d, err := Nuevo(nombres, traduccion, reglas)
	return d, eventos, err
}

// rellenar serializa la lectura y la completa con relleno hasta bytesPorEvento.
func rellenar(l Lectura) ([]byte, error) {
	cuerpo, err := json.Marshal(l)
	if err != nil {
		return nil, err
	}
	if falta := bytesPorEvento - len(cuerpo); falta > 0 {
		l.Datos = strings.Repeat("x", falta)
		return json.Marshal(l)
	}
	return cuerpo, nil
}
