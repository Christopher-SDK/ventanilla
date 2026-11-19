"""Los datos de la página demo salen del sistema real y cuentan lo que de verdad pasa con cada falla."""
import importlib.util
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("datos_web", RAIZ / "scripts" / "datos_web.py")
datos_web = importlib.util.module_from_spec(spec)
spec.loader.exec_module(datos_web)


@pytest.fixture(scope="module")
def fallas():
    import json

    return {f["falla"]: f for f in datos_web.fallas(json.loads((RAIZ / "reporte" / "matriz.json").read_text()))} if (RAIZ / "reporte" / "matriz.json").exists() else pytest.skip("hace falta reporte/matriz.json (scripts/matriz.py)")


def test_cada_chip_tiene_su_veredicto_y_su_capa():
    chips = datos_web.chips()
    capas = {"guardia", "intencion", "herramientas", "busqueda", "verificador"}
    assert all(c["capa"] in capas and c["texto"] for c in chips)
    assert all(c["tipo"] == "bloqueo" for c in chips if c["grupo"] == "ataque" and c["rotulo"] != "Documento envenenado")


def test_con_la_falla_encendida_la_respuesta_cambia(fallas):
    for f in fallas.values():
        assert f["rota"]["texto"] != f["limpia"]["texto"], f["falla"]


def test_cada_falla_muestra_el_dano_que_dice(fallas):
    assert "2,00" in fallas["TASA_INVENTADA"]["rota"]["texto"] and fallas["TASA_INVENTADA"]["limpia"]["tipo"] == "bloqueo"
    assert "circular" in fallas["CITA_FANTASMA"]["rota"]["texto"]
    assert fallas["INYECCION_INDIRECTA"]["orden_llega_al_modelo"] == {"limpia": False, "rota": True}
    assert "Luis" in fallas["FUGA_DE_DATOS"]["rota"]["texto"] and "Luis" not in fallas["FUGA_DE_DATOS"]["limpia"]["texto"]
    assert fallas["JUEGO_DE_ROL"]["limpia"]["capa"] == "guardia" and "BancoLibre" in fallas["JUEGO_DE_ROL"]["rota"]["texto"]
    assert fallas["RECHAZO_EXCESIVO"]["limpia"]["tipo"] == "reclamo" and fallas["RECHAZO_EXCESIVO"]["rota"]["tipo"] == "bloqueo"
    assert "S/" in fallas["REGRESION_DE_PROMPT"]["rota"]["texto"] and "S/" not in fallas["REGRESION_DE_PROMPT"]["limpia"]["texto"]
