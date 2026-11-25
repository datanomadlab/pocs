package main

import (
	"context"
	"time"

	"github.com/coder/websocket"
	"github.com/coder/websocket/wsjson"
)

const pausaReconexion = 100 * time.Millisecond

// conectarPropio habla el protocolo del consumidor escrito a mano: un mensaje para suscribirse y
// después un evento por mensaje. Si la conexión se cae, vuelve a conectar y a suscribirse; lo que
// se haya publicado mientras tanto no se recupera, porque ese servidor no guarda historial.
func conectarPropio(o opciones, r *registro, lista func()) {
	for i := 0; i < o.pantallas; i++ {
		go func(pantalla int, cuentas []int) {
			for primera := true; ; primera = false {
				if !primera {
					r.reconexiones.Add(1)
					time.Sleep(pausaReconexion)
				}
				escuchar(o.destino, pantalla, cuentas, r, func() {
					if primera {
						lista()
					}
				})
			}
		}(i, cuentasDe(i, o))
	}
}

func escuchar(destino string, pantalla int, cuentas []int, r *registro, suscrita func()) {
	ctx := context.Background()
	conn, _, err := websocket.Dial(ctx, destino, nil)
	if err != nil {
		return
	}
	defer conn.CloseNow()
	conn.SetReadLimit(1 << 20)
	if err := wsjson.Write(ctx, conn, map[string][]int{"suscribir": cuentas}); err != nil {
		return
	}
	suscrita()
	for {
		_, cuerpo, err := conn.Read(ctx)
		if err != nil {
			return
		}
		r.recibir(cuerpo, pantalla)
	}
}
