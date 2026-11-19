import json
import unicodedata
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
REPORTE = RAIZ / "reporte" / "modelo.json"


def norm(t: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", t.lower()) if not unicodedata.combining(c))


def datos_de_texto(texto: str) -> set:
    """Plazos y horas que una respuesta afirma: «15 días», «18:00»."""
    import re

    t = norm(texto)
    return {f"{d} dias" for d in re.findall(r"\b(\d{1,3}) dias", t)} | set(re.findall(r"\b\d{1,2}:\d{2}\b", t))


def cumple(texto: str, caso: dict) -> bool:
    t = norm(texto)
    return all(any(norm(x) in t for x in g) for g in caso["debe"]) and not any(norm(x) in t for x in caso["no_debe"])


@pytest.fixture(scope="session")
def metricas():
    datos: dict = {}
    yield datos
    REPORTE.parent.mkdir(exist_ok=True)
    REPORTE.write_text(json.dumps(datos, ensure_ascii=False, indent=1))


@pytest.fixture(scope="module")
def real():
    """El modelo real, desde las grabaciones (o en vivo con VENTANILLA_MODO=vivo/auto)."""
    from datetime import date

    from ventanilla.configuracion import construir

    return construir(hoy=lambda: date(2026, 11, 18))


def cargar(nombre):
    return json.loads((RAIZ / "evals" / nombre).read_text())
