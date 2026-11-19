#!/usr/bin/env python3
"""Vocabulario del Lab. Sin dependencias: python3 tools/vocabulario.py <orden>

estado              por experimento, qué términos de su vocabulario.txt tienen post y cuáles faltan.
indice              reescribe la tabla de vocabulario/README.md a partir del encabezado de cada post.
substack <termino>  imprime el post en Markdown, sin encabezado y con todos los enlaces absolutos:
                    los que van a otros posts de vocabulario apuntan al newsletter.
html <termino>      escribe vocabulario/_substack/<termino>.html y lo abre en el navegador. Esa página
                    tiene botones para copiar el título, el subtítulo, la dirección y el cuerpo con
                    formato, listos para pegar en el editor de Substack. Necesita la librería markdown:
                    uv run --no-project --with markdown tools/vocabulario.py html docker

Nunca copies desde la vista previa del editor de código: sus enlaces relativos apuntan a tu disco.
"""
from __future__ import annotations

import html as html_lib
import re
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FICHAS = RAIZ / "vocabulario"
INICIO, FIN = "<!-- indice:inicio -->", "<!-- indice:fin -->"
ESTADOS = ("borrador", "revisado", "publicado")
SLUG = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
REPO = "https://github.com/datanomadlab/pocs"
NEWSLETTER = "https://datanomadlab.substack.com"
PREFIJO_URL = "que-es-"
SALIDA_HTML = "_substack"
IMAGEN = re.compile(r"^!\[([^\]]*)\]\((imagenes/[^)\s]+)\)\s*$", re.MULTILINE)
ENLACE_LOCAL = re.compile(r"\]\((?!https?://|mailto:|#)([^)\s]+)\)")
OBLIGATORIOS = ("termino", "titulo", "subtitulo", "descripcion", "resumen", "categoria", "estado")


def leer_encabezado(texto: str) -> dict[str, str]:
    """Lee el bloque `clave: valor` entre las dos primeras líneas `---`."""
    lineas = texto.splitlines()
    if not lineas or lineas[0].strip() != "---":
        raise ValueError("la ficha no empieza con un encabezado ---")
    campos = {}
    for linea in lineas[1:]:
        if linea.strip() == "---":
            return campos
        clave, sep, valor = linea.partition(":")
        if not sep:
            continue
        valor = valor.strip()
        if len(valor) >= 2 and valor[0] == valor[-1] == '"':
            valor = valor[1:-1]
        elif ": " in valor or valor.endswith(":") or (valor and valor[0] in "#[{>|*&!%@`'"):
            # GitHub y la vista previa del editor leen el encabezado como YAML: sin comillas, esto falla.
            raise ValueError(f"el campo '{clave.strip()}' necesita ir entre comillas dobles")
        campos[clave.strip()] = valor
    raise ValueError("el encabezado no se cierra con ---")


def fichas(carpeta: Path = FICHAS) -> dict[str, dict[str, str]]:
    resultado = {}
    for ruta in sorted(carpeta.glob("*.md")):
        if ruta.name.startswith("_") or ruta.name == "README.md":
            continue
        try:
            campos = leer_encabezado(ruta.read_text(encoding="utf-8"))
        except ValueError as e:
            raise ValueError(f"{ruta.name}: {e}") from e
        faltan = [c for c in OBLIGATORIOS if not campos.get(c)]
        if faltan:
            raise ValueError(f"{ruta.name}: faltan campos en el encabezado: {', '.join(faltan)}")
        if campos["estado"] not in ESTADOS:
            raise ValueError(f"{ruta.name}: estado debe ser uno de {ESTADOS}")
        if campos["estado"] == "publicado" and not campos.get("substack"):
            raise ValueError(f"{ruta.name}: un post publicado necesita su URL en substack:")
        resultado[ruta.stem] = campos
    return resultado


def terminos_por_experimento(raiz: Path = RAIZ) -> dict[str, list[str]]:
    resultado = {}
    for lista in sorted(raiz.glob("[0-9][0-9]-*/vocabulario.txt")):
        terminos = [t.strip() for t in lista.read_text(encoding="utf-8").splitlines() if t.strip()]
        malos = [t for t in terminos if not SLUG.match(t)]
        if malos:
            raise ValueError(f"{lista}: términos inválidos {malos} (minúsculas, números y guiones)")
        resultado[lista.parent.name] = terminos
    return resultado


def estado(raiz: Path = RAIZ, carpeta: Path = FICHAS) -> tuple[str, list[str]]:
    hechas = fichas(carpeta)
    lineas, faltantes = [], []
    for experimento, terminos in terminos_por_experimento(raiz).items():
        lineas.append(experimento)
        for termino in terminos:
            if termino in hechas:
                lineas.append(f"  {termino:<16} {hechas[termino]['estado']}")
            else:
                lineas.append(f"  {termino:<16} FALTA")
                if termino not in faltantes:
                    faltantes.append(termino)
    return "\n".join(lineas), faltantes


def tabla_indice(hechas: dict[str, dict[str, str]]) -> str:
    filas = ["| Término | Qué es | Categoría | Estado |", "|---|---|---|---|"]
    for slug, c in hechas.items():
        enlace = c["substack"] if c.get("substack") else f"{slug}.md"
        filas.append(f"| [{c['termino']}]({enlace}) | {c['resumen']} | {c['categoria']} | {c['estado']} |")
    return "\n".join(filas)


def actualizar_indice(carpeta: Path = FICHAS) -> None:
    readme = carpeta / "README.md"
    texto = readme.read_text(encoding="utf-8")
    if INICIO not in texto or FIN not in texto:
        raise ValueError(f"{readme} no tiene las marcas {INICIO} y {FIN}")
    antes, resto = texto.split(INICIO, 1)
    despues = resto.split(FIN, 1)[1]
    readme.write_text(f"{antes}{INICIO}\n{tabla_indice(fichas(carpeta))}\n{FIN}{despues}", encoding="utf-8")


def cuerpo(texto: str) -> str:
    """El post sin el encabezado."""
    partes = texto.split("\n---\n", 1)
    if not texto.startswith("---\n") or len(partes) != 2:
        raise ValueError("el post no tiene encabezado")
    return partes[1].lstrip("\n")


def direccion(slug: str) -> str:
    """La última parte de la URL del post en Substack. Se fija a mano al publicar (Settings > URL)."""
    return f"{PREFIJO_URL}{slug}"


def url_substack(slug: str, campos: dict[str, str] | None = None) -> str:
    """La URL publicada si ya existe; si no, la que tendrá cuando se publique con su dirección."""
    return (campos or {}).get("substack") or f"{NEWSLETTER}/p/{direccion(slug)}"


def para_substack(termino: str, carpeta: Path = FICHAS) -> tuple[str, list[str]]:
    """Devuelve el post en Markdown con todos los enlaces absolutos, y la lista de avisos.

    - Enlaces a otros posts de vocabulario -> su URL en el newsletter. Como la dirección de cada
      post se decide de antemano (que-es-<termino>), el enlace sirve aunque el otro post todavía
      no esté publicado; solo avisa de que hay que publicarlo con esa dirección.
    - Enlaces a carpetas del repo (../01-.../) -> URL de GitHub.
    """
    ruta = carpeta / f"{termino}.md"
    if not ruta.exists():
        raise ValueError(f"no existe vocabulario/{termino}.md")
    hechas = fichas(carpeta)
    avisos = []

    def cambiar(m: re.Match) -> str:
        destino = m.group(1)
        nombre = destino.removeprefix("./")
        if nombre.endswith(".md") and "/" not in nombre:
            slug = nombre.removesuffix(".md")
            if slug not in hechas:
                avisos.append(f"enlaza a '{slug}', que no tiene post de vocabulario")
                return m.group(0)
            if hechas[slug]["estado"] != "publicado":
                avisos.append(f"'{slug}' aún no está publicado: el enlace funcionará cuando lo "
                              f"publiques con la dirección {direccion(slug)}")
            return f"]({url_substack(slug, hechas[slug])})"
        if destino.startswith("../"):
            return f"]({REPO}/tree/main/{destino.removeprefix('../').rstrip('/')})"
        avisos.append(f"enlace local sin convertir: {destino}")
        return m.group(0)

    # Las imágenes se suben a mano en Substack: aquí se quitan del cuerpo (html las muestra aparte).
    sin_imagenes = re.sub(r"\n{3,}", "\n\n", IMAGEN.sub("", cuerpo(ruta.read_text(encoding="utf-8"))))
    texto = ENLACE_LOCAL.sub(cambiar, sin_imagenes)
    return texto, list(dict.fromkeys(avisos))


PAGINA = """<!doctype html>
<html lang="es"><head><meta charset="utf-8"><title>{titulo}</title>
<style>
  body {{ font: 17px/1.6 Georgia, serif; max-width: 720px; margin: 2rem auto; padding: 0 1rem; color: #0F1D1B; }}
  .panel {{ font: 14px/1.5 system-ui, sans-serif; background: #E9EFEC; border-radius: 10px; padding: 1rem 1.25rem; }}
  .panel p {{ margin: .4rem 0; }} .panel code {{ background: #fff; padding: .1rem .35rem; border-radius: 4px; }}
  button {{ font: inherit; cursor: pointer; border: 1px solid #0C4A40; background: #fff; color: #0C4A40;
            border-radius: 6px; padding: .15rem .6rem; margin-left: .4rem; }}
  button.principal {{ background: #0C4A40; color: #fff; padding: .45rem 1rem; margin: .6rem 0 0; }}
  pre {{ background: #f3f3f0; padding: .8rem; overflow-x: auto; font-size: 14px; }}
  .aviso {{ color: #B5452F; }}
  .panel img {{ max-width: 100%; border: 1px solid #D5DED9; border-radius: 8px; margin-top: .4rem; }}
</style></head><body>
<div class="panel">
  <p><strong>Para pegar en Substack.</strong> Copia cada campo con su botón. Los enlaces ya son absolutos.</p>
  <p>Título: <span id="titulo">{titulo}</span><button data-copia="titulo">Copiar</button></p>
  <p>Subtítulo: <span id="subtitulo">{subtitulo}</span><button data-copia="subtitulo">Copiar</button></p>
  <p>Descripción para redes (Settings &gt; SEO): <span id="descripcion">{descripcion}</span><button data-copia="descripcion">Copiar</button></p>
  <p>Dirección del post (Settings &gt; URL): <code id="direccion">{direccion}</code><button data-copia="direccion">Copiar</button></p>
  <p>Quedará en: <code>{url}</code>. Los otros posts enlazan a esa dirección, así que no la cambies.</p>
  {imagen}
  {avisos}
  <button class="principal" data-copia="cuerpo">Copiar el cuerpo del post</button> <span id="estado"></span>
</div>
<article id="cuerpo">
{cuerpo}
</article>
<script>
  document.querySelectorAll("button[data-copia]").forEach(function (boton) {{
    boton.addEventListener("click", function () {{
      var rango = document.createRange();
      rango.selectNodeContents(document.getElementById(boton.dataset.copia));
      var seleccion = window.getSelection();
      seleccion.removeAllRanges();
      seleccion.addRange(rango);
      var ok = document.execCommand("copy");
      seleccion.removeAllRanges();
      document.getElementById("estado").textContent = ok ? "Copiado: " + boton.dataset.copia : "No se pudo copiar";
    }});
  }});
</script>
</body></html>
"""


def sin_titulo(texto: str) -> str:
    """Quita el título y el subtítulo del cuerpo: en Substack van en sus propios campos."""
    lineas = texto.splitlines()
    if lineas and lineas[0].startswith("# "):
        lineas = lineas[1:]
        while lineas and not lineas[0].strip():
            lineas = lineas[1:]
        if lineas and lineas[0].startswith("*") and lineas[0].rstrip().endswith("*"):
            lineas = lineas[1:]
    return "\n".join(lineas).strip() + "\n"


def pagina_html(termino: str, carpeta: Path = FICHAS) -> tuple[str, list[str]]:
    try:
        import markdown
    except ImportError as e:
        raise ValueError("falta la librería markdown. Corre: "
                         f"uv run --no-project --with markdown tools/vocabulario.py html {termino}") from e
    texto, avisos = para_substack(termino, carpeta)
    campos = fichas(carpeta)[termino]
    cuerpo_html = markdown.markdown(sin_titulo(texto), extensions=["fenced_code"])
    restantes = ENLACE_LOCAL.findall(sin_titulo(texto))
    if restantes:
        raise ValueError(f"quedaron enlaces relativos sin convertir: {restantes}")
    esc = html_lib.escape
    imagenes = IMAGEN.findall((carpeta / f"{termino}.md").read_text(encoding="utf-8"))
    bloque = "".join(
        f'<p>Imagen (<code>vocabulario/{esc(ruta)}</code>): arrástrala al editor después del primer '
        f'párrafo y úsala también como imagen para redes. Texto alternativo: {esc(alt)}</p>'
        f'<img src="../{esc(ruta)}" alt="{esc(alt)}">' for alt, ruta in imagenes)
    lista = "".join(f'<p class="aviso">Aviso: {esc(a)}</p>' for a in avisos)
    return PAGINA.format(titulo=esc(campos["titulo"]), subtitulo=esc(campos["subtitulo"]),
                         descripcion=esc(campos["descripcion"]), direccion=esc(direccion(termino)),
                         url=esc(url_substack(termino, campos)), imagen=bloque, avisos=lista,
                         cuerpo=cuerpo_html), avisos


def main() -> int:
    orden = sys.argv[1] if len(sys.argv) > 1 else "estado"
    try:
        if orden == "estado":
            texto, faltantes = estado()
            print(texto)
            if faltantes:
                print(f"\nFaltan {len(faltantes)} fichas: {', '.join(faltantes)}")
        elif orden == "indice":
            actualizar_indice()
            print("vocabulario/README.md actualizado")
        elif orden == "html" and len(sys.argv) == 3:
            pagina, avisos = pagina_html(sys.argv[2])
            salida = FICHAS / SALIDA_HTML / f"{sys.argv[2]}.html"
            salida.parent.mkdir(exist_ok=True)
            salida.write_text(pagina, encoding="utf-8")
            print(f"Listo: {salida.relative_to(RAIZ)}")
            for aviso in avisos:
                print(f"Aviso: {aviso}", file=sys.stderr)
            if sys.platform == "darwin":
                subprocess.run(["open", str(salida)], check=False)
        elif orden == "substack" and len(sys.argv) == 3:
            texto, avisos = para_substack(sys.argv[2])
            print(texto)
            for aviso in avisos:
                print(f"Aviso: {aviso}", file=sys.stderr)
        else:
            print(__doc__)
            return 2
    except (ValueError, KeyError, OSError) as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
