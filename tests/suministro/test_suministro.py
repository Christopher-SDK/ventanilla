"""Cadena de suministro del modelo (OWASP LLM04): qué modelos, con qué digest y con qué licencia."""
import json
from pathlib import Path

from ventanilla.configuracion import Config

RAIZ = Path(__file__).resolve().parents[2]
LOCK = json.loads((RAIZ / "modelos.lock.json").read_text())
NOMBRES = {m["nombre"] for m in LOCK["modelos"]}


def test_la_configuracion_usa_los_modelos_fijados(monkeypatch):
    for v in ("VENTANILLA_MODELO", "VENTANILLA_EMBEDDINGS"):
        monkeypatch.delenv(v, raising=False)
    cfg = Config.desde_entorno()
    assert {cfg.modelo, cfg.modelo_embeddings} <= NOMBRES


def test_cada_modelo_tiene_digest_y_licencia_permitida():
    for m in LOCK["modelos"]:
        assert len(m["digest"]) == 64 and int(m["digest"], 16) >= 0
        assert m["licencia"] in LOCK["licencias_permitidas"], m


def test_las_grabaciones_solo_vienen_de_modelos_fijados():
    """Una grabación de otro modelo haría pasar la CI con respuestas que el modelo fijado nunca dio."""
    for p in (RAIZ / "grabaciones").glob("*/*.json"):
        modelo = json.loads(p.read_text())["peticion"]["model"]
        assert modelo in NOMBRES, f"{p.name}: {modelo}"


def test_las_grabaciones_usan_las_opciones_fijas():
    from ventanilla.adaptadores.ollama import OPCIONES

    redactor = next(m["nombre"] for m in LOCK["modelos"] if m["rol"] == "redacta")
    for p in (RAIZ / "grabaciones").glob("*/*.json"):
        pet = json.loads(p.read_text())["peticion"]
        if pet["model"] == redactor:
            assert {k: v for k, v in pet["options"].items() if k != "seed"} == OPCIONES, p.name
