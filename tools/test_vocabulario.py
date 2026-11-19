"""Pruebas de tools/vocabulario.py. Correr desde la raíz: uv run --with pytest pytest tools"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import vocabulario as v  # noqa: E402

FICHA = ("---\ntermino: Docker\ntitulo: \"Docker: sin instalar\"\nsubtitulo: s\ndescripcion: d\nresumen: Empaqueta programas.\n"
         "categoria: infraestructura\nestado: {estado}\n---\n\n# Docker\n")


@pytest.fixture
def repo(tmp_path):
    fichas = tmp_path / "vocabulario"
    fichas.mkdir()
    (fichas / "docker.md").write_text(FICHA.format(estado="borrador"))
    (fichas / "_plantilla.md").write_text("---\nestado: nada\n---\n")
    (fichas / "README.md").write_text(f"# Vocabulario\n\n{v.INICIO}\nviejo\n{v.FIN}\n\npie\n")
    experimento = tmp_path / "01-uno"
    experimento.mkdir()
    (experimento / "vocabulario.txt").write_text("docker\niceberg\n\n")
    return tmp_path


def test_estado_marca_las_fichas_que_faltan(repo):
    texto, faltantes = v.estado(repo, repo / "vocabulario")
    assert faltantes == ["iceberg"]
    assert "docker" in texto and "borrador" in texto and "FALTA" in texto


def test_la_plantilla_y_el_readme_no_cuentan_como_fichas(repo):
    assert list(v.fichas(repo / "vocabulario")) == ["docker"]


def test_estado_desconocido_se_rechaza(repo):
    (repo / "vocabulario" / "docker.md").write_text(FICHA.format(estado="listo"))
    with pytest.raises(ValueError, match="estado debe ser"):
        v.fichas(repo / "vocabulario")


def test_ficha_sin_encabezado_se_rechaza():
    with pytest.raises(ValueError, match="no empieza"):
        v.leer_encabezado("# Docker\n")
    with pytest.raises(ValueError, match="no se cierra"):
        v.leer_encabezado("---\ntermino: Docker\n")


def test_termino_con_mayusculas_o_espacios_se_rechaza(repo):
    (repo / "01-uno" / "vocabulario.txt").write_text("Apache Iceberg\n")
    with pytest.raises(ValueError, match="términos inválidos"):
        v.terminos_por_experimento(repo)


def test_indice_reemplaza_solo_lo_que_esta_entre_las_marcas(repo):
    v.actualizar_indice(repo / "vocabulario")
    texto = (repo / "vocabulario" / "README.md").read_text()
    assert "viejo" not in texto and texto.startswith("# Vocabulario") and texto.endswith("pie\n")
    assert "| [Docker](docker.md) | Empaqueta programas. | infraestructura | borrador |" in texto


def test_ficha_publicada_enlaza_a_substack(repo):
    ficha = repo / "vocabulario" / "docker.md"
    ficha.write_text(ficha.read_text().replace("estado: borrador", "estado: publicado\nsubstack: https://x.test/docker"))
    assert "[Docker](https://x.test/docker)" in v.tabla_indice(v.fichas(repo / "vocabulario"))


def test_post_sin_campos_obligatorios_se_rechaza(repo):
    (repo / "vocabulario" / "docker.md").write_text("---\ntermino: Docker\nestado: borrador\n---\n")
    with pytest.raises(ValueError, match="faltan campos"):
        v.fichas(repo / "vocabulario")


def test_publicado_sin_url_se_rechaza(repo):
    (repo / "vocabulario" / "docker.md").write_text(FICHA.format(estado="publicado"))
    with pytest.raises(ValueError, match="necesita su URL"):
        v.fichas(repo / "vocabulario")


def test_substack_quita_el_encabezado_y_lleva_los_enlaces_al_newsletter(repo):
    fichas = repo / "vocabulario"
    (fichas / "docker.md").write_text(
        FICHA.format(estado="publicado\nsubstack: https://x.test/docker"))
    (fichas / "duckdb.md").write_text(
        FICHA.format(estado="borrador")
        + "Ver [Docker](docker.md), [Parquet](parquet.md), otra vez [Parquet](parquet.md), [el experimento](../01-uno/) "
          "y [la doc](https://duckdb.org/docs/).\n")
    texto, avisos = v.para_substack("duckdb", fichas)
    assert texto.startswith("# Docker") and "termino:" not in texto
    assert "[Docker](https://x.test/docker)" in texto
    assert "[Parquet](parquet.md)" in texto          # no existe ese post: se deja y se avisa
    assert f"[el experimento]({v.REPO}/tree/main/01-uno)" in texto
    assert "[la doc](https://duckdb.org/docs/)" in texto
    assert len(avisos) == 1 and "parquet" in avisos[0]


def test_enlace_a_un_post_sin_publicar_usa_la_direccion_prevista_del_newsletter(repo):
    fichas = repo / "vocabulario"
    (fichas / "duckdb.md").write_text(FICHA.format(estado="borrador") + "Ver [Docker](docker.md).\n")
    texto, avisos = v.para_substack("duckdb", fichas)
    assert f"[Docker]({v.NEWSLETTER}/p/que-es-docker)" in texto
    assert "que-es-docker" in avisos[0]


def test_la_pagina_html_no_lleva_titulo_ni_enlaces_relativos(repo):
    pytest.importorskip("markdown")
    fichas = repo / "vocabulario"
    (fichas / "duckdb.md").write_text(
        FICHA.format(estado="borrador")
        + "*Subtítulo.*\n\n![DuckDB en una imagen](imagenes/duckdb.png)\n\nVer [Docker](docker.md) y [el experimento](../01-uno/).\n\n```bash\nls\n```\n")
    pagina, _ = v.pagina_html("duckdb", fichas)
    articulo = pagina.split('<article id="cuerpo">')[1]
    assert "<h1>" not in articulo and "Subtítulo." not in articulo
    assert "<img" not in articulo and 'src="../imagenes/duckdb.png"' in pagina
    assert f'href="{v.NEWSLETTER}/p/que-es-docker"' in articulo
    assert f'href="{v.REPO}/tree/main/01-uno"' in articulo
    assert "<pre><code" in articulo and 'href="docker.md"' not in pagina
    assert "que-es-duckdb" in pagina and "Docker: sin instalar" in pagina


def test_substack_de_un_termino_inexistente_falla(repo):
    with pytest.raises(ValueError, match="no existe"):
        v.para_substack("kafka", repo / "vocabulario")


def test_las_comillas_del_encabezado_no_forman_parte_del_valor(repo):
    assert v.fichas(repo / "vocabulario")["docker"]["titulo"] == "Docker: sin instalar"


def test_valor_con_dos_puntos_sin_comillas_se_rechaza(repo):
    (repo / "vocabulario" / "docker.md").write_text(
        FICHA.format(estado="borrador").replace('"Docker: sin instalar"', "Docker: sin instalar"))
    with pytest.raises(ValueError, match="docker.md.*comillas"):
        v.fichas(repo / "vocabulario")
