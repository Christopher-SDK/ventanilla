"""Reglas de la arquitectura hexagonal, verificadas con import-linter (el equivalente de ArchUnit)."""
import subprocess
import sys
from pathlib import Path


def test_contratos_de_importacion():
    raiz = Path(__file__).resolve().parents[2]
    r = subprocess.run([sys.executable, "-m", "importlinter.cli", "--config", str(raiz / "pyproject.toml")], capture_output=True, text=True, cwd=raiz)
    if r.returncode != 0 and "No module named importlinter.cli" in r.stderr:
        r = subprocess.run(["lint-imports", "--config", str(raiz / "pyproject.toml")], capture_output=True, text=True, cwd=raiz)
    assert r.returncode == 0, r.stdout + r.stderr


def test_el_dominio_no_sale_a_la_red():
    """El dominio solo lee sus datos de referencia (corpus, tarifario, feriados). El modelo y los embeddings entran por los puertos."""
    dominio = Path(__file__).resolve().parents[2] / "src" / "ventanilla" / "dominio"
    for py in dominio.glob("*.py"):
        texto = py.read_text()
        for prohibido in ("socket", "requests", "urllib", "httpx", "subprocess"):
            assert prohibido not in texto, f"{py.name} usa {prohibido}"
