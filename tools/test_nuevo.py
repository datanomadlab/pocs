"""Pruebas de tools/nuevo.py. Desde la raíz: uv run --no-project --with pytest --with markdown pytest -q tools"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import nuevo  # noqa: E402

PLANTILLA = Path(__file__).resolve().parents[1] / "_plantilla"
README = """# Experimentos

## Experimentos

| # | Experimento | Pregunta | Estado | Veredicto |
|---|---|---|---|---|
| 01 | [Uno](01-uno/) | ¿Uno? | En construcción | Pendiente |

Los veredictos posibles son tres.
"""
LAB = {"experimentos": [
    {"numero": "01", "titulo": "Uno", "pregunta": "¿Uno?", "stack": ["a"], "estado": "en-construccion",
     "en": {"titulo": "One", "pregunta": "One?"}},
    {"numero": "02", "titulo": "Agente de datos con MCP", "pregunta": "¿Puede un agente no inventar cifras?",
     "stack": ["mcp"], "estado": "proxima", "en": {"titulo": "Agent", "pregunta": "Can it?"}}]}


@pytest.fixture
def raiz(tmp_path):
    shutil.copytree(PLANTILLA, tmp_path / "_plantilla", ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "README.md").write_text(README, encoding="utf-8")
    (tmp_path / "lab.json").write_text(json.dumps(LAB, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return tmp_path


def test_carpeta_y_paquete_salen_del_titulo():
    assert nuevo.carpeta("02", "Agente de datos con MCP") == "02-agente-de-datos-con-mcp"
    assert nuevo.carpeta("03", "Pipeline de USD 5 al mes") == "03-pipeline-de-usd-5-al-mes"
    assert nuevo.paquete("02-agente-de-datos-con-mcp") == "agente"
    assert nuevo.paquete("11-un-catalogo-para-todos") == "catalogo"


def test_toma_titulo_y_pregunta_de_lab_json(raiz):
    destino = nuevo.crear(raiz, "02")
    assert destino.name == "02-agente-de-datos-con-mcp"
    readme = (destino / "README.md").read_text(encoding="utf-8")
    assert "# Experimento 02 · Agente de datos con MCP" in readme
    assert "¿Puede un agente no inventar cifras?" in readme


def test_no_quedan_marcas_sin_reemplazar_y_el_paquete_se_renombra(raiz):
    destino = nuevo.crear(raiz, "02")
    assert (destino / "src" / "agente" / "__main__.py").exists()
    assert not (destino / "src" / "__paquete__").exists()
    for archivo in destino.rglob("*"):
        if archivo.is_file():
            assert "{{" not in archivo.read_text(encoding="utf-8"), archivo


def test_agrega_la_fila_al_readme_y_pasa_lab_json_a_en_construccion(raiz):
    nuevo.crear(raiz, "02")
    readme = (raiz / "README.md").read_text(encoding="utf-8")
    assert ("| 02 | [Agente de datos con MCP](02-agente-de-datos-con-mcp/) | ¿Puede un agente no inventar cifras? "
            "| En construcción | Pendiente |") in readme
    assert readme.index("| 01 |") < readme.index("| 02 |") < readme.index("Los veredictos")
    lab = json.loads((raiz / "lab.json").read_text(encoding="utf-8"))
    assert [e["estado"] for e in lab["experimentos"]] == ["en-construccion", "en-construccion"]


def test_solo_cambia_la_linea_del_estado_en_lab_json(raiz):
    compacto = (raiz / "lab.json").read_text(encoding="utf-8").replace('[\n      "mcp"\n    ]', '["mcp"]')
    (raiz / "lab.json").write_text(compacto, encoding="utf-8")
    nuevo.crear(raiz, "02")
    despues = (raiz / "lab.json").read_text(encoding="utf-8")
    assert despues == compacto.replace('"estado": "proxima"', '"estado": "en-construccion"')


def test_no_pisa_un_experimento_que_ya_existe(raiz):
    nuevo.crear(raiz, "02")
    with pytest.raises(ValueError, match="ya existe"):
        nuevo.crear(raiz, "02")


def test_sin_entrada_en_lab_json_exige_titulo_y_pregunta(raiz):
    with pytest.raises(ValueError, match="título y pregunta"):
        nuevo.crear(raiz, "07")
    destino = nuevo.crear(raiz, "07", titulo="Siete", pregunta="¿Siete?")
    assert destino.name == "07-siete"
    assert len(json.loads((raiz / "lab.json").read_text(encoding="utf-8"))["experimentos"]) == 2


def test_el_experimento_nuevo_pasa_sus_pruebas_recien_creado(raiz):
    destino = nuevo.crear(raiz, "02")
    r = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=",
                        str(destino / "tests")], cwd=destino, capture_output=True, text=True,
                       env={"PYTHONPATH": str(destino / "src"), "PATH": "/usr/bin:/bin"})
    assert r.returncode == 0, r.stdout + r.stderr
