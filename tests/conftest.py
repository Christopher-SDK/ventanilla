import os
from datetime import date

import pytest

from ventanilla.configuracion import Config, construir

HOY = date(2026, 11, 18)  # fecha fija: los plazos de reclamo no dependen del día en que se corre la suite

CAPAS = {
    "unitarias": "Unitarias", "propiedades": "Propiedades", "recuperacion": "Recuperación", "seguridad": "Seguridad",
    "privacidad": "Privacidad", "regulacion": "Regulación", "modelo": "Modelo real (grabado)", "api": "API y contrato",
    "ui": "Interfaz y accesibilidad", "arquitectura": "Arquitectura", "suministro": "Cadena de suministro", "web": "Página demo",
}


def pytest_addoption(parser):
    parser.addoption("--falla", default=None, help="Enciende una falla sembrada (igual en macOS, Linux y Windows).")


def pytest_configure(config):
    if f := config.getoption("--falla"):
        os.environ["VENTANILLA_FALLA"] = f.strip().upper()
    try:
        Config.desde_entorno()  # una falla mal escrita detiene la corrida antes de empezar, con un mensaje corto
    except ValueError as e:
        raise pytest.UsageError(str(e)) from None


def pytest_collection_modifyitems(items):
    import allure

    for item in items:
        capa = CAPAS.get(item.path.parent.name)
        if capa:
            item.add_marker(allure.parent_suite(capa))
            item.add_marker(allure.label("layer", capa))


@pytest.fixture
def armar():
    """Asistente con la falla del entorno (si la hay). Embeddings reales grabados; el modelo se puede reemplazar."""

    def _armar(modelo=None):
        return construir(modelo=modelo, hoy=lambda: HOY)

    return _armar


@pytest.fixture
def asistente(armar):
    return armar()
