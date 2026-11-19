"""Guardia de entrada: atrapa los ataques escritos a mano y deja pasar las preguntas legítimas."""
import json
from pathlib import Path

import pytest

from ventanilla.configuracion import construir

ATAQUES = json.loads((Path(__file__).resolve().parents[2] / "evals" / "ataques.json").read_text())


@pytest.fixture(scope="module")
def guardia():
    return construir().guardia


@pytest.mark.parametrize("ataque", ATAQUES["inyeccion_directa"]["casos"], ids=lambda s: s[:60])
def test_bloquea_inyeccion_directa(guardia, ataque):
    assert not guardia.revisar(ataque).permitido


@pytest.mark.parametrize("ataque", ATAQUES["juego_de_rol"]["casos"], ids=lambda s: s[:60])
def test_bloquea_cambio_de_rol(guardia, ataque):
    assert not guardia.revisar(ataque).permitido


@pytest.mark.parametrize("pregunta", ATAQUES["legitimas"]["casos"], ids=lambda s: s[:60])
def test_no_bloquea_preguntas_legitimas(guardia, pregunta):
    v = guardia.revisar(pregunta)
    assert v.permitido, f"rechazo indebido por la regla {v.regla}"
