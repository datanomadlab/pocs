package main

import (
	"context"
	"log"
	"net/http"
	"sync"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"
)

// colaPantalla es cuántos eventos se guardan para una pantalla lenta antes de cortarla.
const colaPantalla = 8192

type pantalla struct {
	salida chan []byte
	cortar context.CancelFunc
}

// central recuerda qué pantallas miran cada cuenta y les reparte los eventos.
type central struct {
	mu        sync.RWMutex
	porCuenta map[int]map[*pantalla]struct{}
}

func nuevaCentral() *central { return &central{porCuenta: map[int]map[*pantalla]struct{}{}} }

// publicar nunca espera a una pantalla: si su cola está llena, la corta y sigue. Una pantalla
// lenta no puede frenar la lectura del transporte ni a las demás.
func (c *central) publicar(cuenta int, cuerpo []byte) {
	c.mu.RLock()
	defer c.mu.RUnlock()
	for p := range c.porCuenta[cuenta] {
		select {
		case p.salida <- cuerpo:
		default:
			p.cortar()
		}
	}
}

func (c *central) atender(w http.ResponseWriter, r *http.Request) {
	conn, err := websocket.Accept(w, r, &websocket.AcceptOptions{InsecureSkipVerify: true})
	if err != nil {
		return
	}
	defer conn.CloseNow()
	ctx, cortar := context.WithCancel(r.Context())
	defer cortar()

	var pedido struct {
		Suscribir []int `json:"suscribir"`
	}
	if err := wsjson.Read(ctx, conn, &pedido); err != nil {
		return
	}
	p := &pantalla{salida: make(chan []byte, colaPantalla), cortar: cortar}
	c.registrar(p, pedido.Suscribir, true)
	defer c.registrar(p, pedido.Suscribir, false)

	ctx = conn.CloseRead(ctx) // la pantalla no envía nada más: si se va, ctx termina
	for {
		select {
		case <-ctx.Done():
			return
		case cuerpo := <-p.salida:
			if err := conn.Write(ctx, websocket.MessageText, cuerpo); err != nil {
				log.Printf("pantalla desconectada: %v", err)
				return
			}
		}
	}
}

func (c *central) registrar(p *pantalla, cuentas []int, alta bool) {
	c.mu.Lock()
	defer c.mu.Unlock()
	for _, cuenta := range cuentas {
		if !alta {
			delete(c.porCuenta[cuenta], p)
			continue
		}
		if c.porCuenta[cuenta] == nil {
			c.porCuenta[cuenta] = map[*pantalla]struct{}{}
		}
		c.porCuenta[cuenta][p] = struct{}{}
	}
}
