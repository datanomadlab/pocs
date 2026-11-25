package main

import "testing"

// Con un espectador, el reparto es el original: la pantalla i mira las cuentas i, i+P, i+2P…
func TestCuentasDeUnEspectador(t *testing.T) {
	o := opciones{pantallas: 3, cuentas: 10, espectadores: 1}
	vistas := map[int]int{}
	for p := 0; p < o.pantallas; p++ {
		for _, c := range cuentasDe(p, o) {
			if c%o.pantallas != p {
				t.Fatalf("la pantalla %d no debería mirar la cuenta %d", p, c)
			}
			if !principal(c, p, o) {
				t.Fatalf("con un espectador, toda entrega es la principal")
			}
			vistas[c]++
		}
	}
	for c := 0; c < o.cuentas; c++ {
		if vistas[c] != 1 {
			t.Fatalf("la cuenta %d la miran %d pantallas, esperaba 1", c, vistas[c])
		}
	}
}

func TestValidarRechazaRepartosQueNoSeCumplen(t *testing.T) {
	malas := []opciones{
		{pantallas: 10, cuentas: 100, espectadores: 0},
		{pantallas: 10, cuentas: 100, espectadores: 11}, // más espectadores que pantallas
		{pantallas: 100, cuentas: 9, espectadores: 10},  // alguna pantalla sin cuentas
		{pantallas: 100, cuentas: 50, espectadores: 1},
	}
	for _, o := range malas {
		if validar(o) == nil {
			t.Fatalf("esperaba un error para %+v", o)
		}
	}
	for _, o := range []opciones{{pantallas: 100, cuentas: 1000, espectadores: 1}, {pantallas: 5000, cuentas: 200, espectadores: 25}} {
		if err := validar(o); err != nil {
			t.Fatalf("no esperaba un error para %+v: %v", o, err)
		}
	}
}

// Con V espectadores, cada cuenta la miran exactamente V pantallas y una sola es la principal.
func TestCuentasDeVariosEspectadores(t *testing.T) {
	for _, o := range []opciones{
		{pantallas: 1000, cuentas: 100, espectadores: 10},
		{pantallas: 5000, cuentas: 200, espectadores: 25},
		{pantallas: 100, cuentas: 20, espectadores: 5},
	} {
		miran, principales := map[int]int{}, map[int]int{}
		for p := 0; p < o.pantallas; p++ {
			cuentas := cuentasDe(p, o)
			if len(cuentas) == 0 {
				t.Fatalf("la pantalla %d quedó sin cuentas (%+v)", p, o)
			}
			for _, c := range cuentas {
				miran[c]++
				if principal(c, p, o) {
					principales[c]++
				}
			}
		}
		for c := 0; c < o.cuentas; c++ {
			if miran[c] != o.espectadores || principales[c] != 1 {
				t.Fatalf("cuenta %d: %d espectadores y %d principales, esperaba %d y 1 (%+v)",
					c, miran[c], principales[c], o.espectadores, o)
			}
		}
	}
}
