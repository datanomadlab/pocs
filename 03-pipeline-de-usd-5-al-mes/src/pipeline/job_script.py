"""La línea base: el script que una empresa escribiría sola. Cada noche copia las tablas completas a CSV."""
import os

import psycopg2

TABLAS = ["clientes", "productos", "facturas", "lineas"]


def main() -> None:
    destino = os.path.join(os.environ["BUCKET"], "script")
    os.makedirs(destino, exist_ok=True)
    con = psycopg2.connect(os.environ["ORIGEN"])
    with con.cursor() as cur:
        for tabla in TABLAS:
            with open(os.path.join(destino, f"{tabla}.csv"), "w", encoding="utf-8") as archivo:
                cur.copy_expert(f"COPY {tabla} TO STDOUT WITH (FORMAT csv, HEADER)", archivo)
            print(f"{tabla}: copiada")
    con.close()


if __name__ == "__main__":
    main()
