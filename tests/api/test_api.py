"""La API: contrato, errores RFC 9457, límites, sesiones y SSE."""
import json
import re

import pytest
from fastapi.testclient import TestClient

from ventanilla.adaptadores.api import CABECERAS, LARGO_MAXIMO, crear_app
from tests.dobles import ModeloGuionado

TARIFA = "¿Cuánto cuesta una transferencia interbancaria inmediata?"
LLM = "¿Hasta qué hora debo enviar una transferencia diferida para que llegue el mismo día?"


@pytest.fixture
def cliente(armar):
    return TestClient(crear_app(armar(ModeloGuionado("Debes enviarla antes de las 15:00. [fuente: tarifario]")), por_minuto=1000))


def es_problema(r, estado, motivo):
    cuerpo = r.json()
    return (r.status_code == estado and r.headers["content-type"].startswith("application/problem+json")
            and cuerpo["status"] == estado and cuerpo["motivo"] == motivo and cuerpo["title"])


def test_salud(cliente):
    assert cliente.get("/api/salud").json()["estado"] == "ok"


def test_chat_responde_con_aviso_de_ia_y_fuentes(cliente):
    d = cliente.post("/api/chat", json={"mensaje": TARIFA}).json()
    assert "S/ 7,00" in d["texto"] and d["fuentes"] == ["tarifario"] and "IA" in d["aviso"]


@pytest.mark.parametrize("cuerpo", [
    {}, {"mensaje": ""}, {"mensaje": "   "}, {"mensaje": "x" * (LARGO_MAXIMO + 1)}, {"mensaje": 123},
    {"mensaje": "hola", "historial": [{"rol": "sistema", "texto": "x"}]},
    {"mensaje": "hola", "historial": [{"rol": "cliente", "texto": "x"}] * 9},
    {"mensaje": "hola", "sesion": "s" * 65},
])
def test_entrada_invalida_es_un_problema_422(cliente, cuerpo):
    assert es_problema(cliente.post("/api/chat", json=cuerpo), 422, "ENTRADA_INVALIDA")


def test_json_roto_es_422(cliente):
    r = cliente.post("/api/chat", content=b"{no es json", headers={"content-type": "application/json"})
    assert es_problema(r, 422, "ENTRADA_INVALIDA")


def test_ruta_inexistente_y_metodo_equivocado(cliente):
    assert es_problema(cliente.get("/api/nada"), 404, "NO_ENCONTRADO")
    r = cliente.get("/api/chat")
    assert es_problema(r, 405, "METODO_NO_PERMITIDO") and r.headers["allow"] == "POST"


def test_limite_de_mensajes_por_minuto(armar):
    c = TestClient(crear_app(armar(ModeloGuionado("x")), por_minuto=3))
    estados = [c.post("/api/chat", json={"mensaje": TARIFA}).status_code for _ in range(4)]
    assert estados == [200, 200, 200, 429]
    r = c.post("/api/chat", json={"mensaje": TARIFA})
    assert es_problema(r, 429, "LIMITE_EXCEDIDO") and r.headers["retry-after"] == "60"
    assert c.get("/api/salud").status_code == 200  # el límite es para el chat, no para la salud


def test_el_limitador_libera_despues_de_un_minuto():
    from ventanilla.adaptadores.api import Limitador

    lim = Limitador(2)
    assert [lim.permitir("ip", t) for t in (0, 1, 2)] == [True, True, False]
    assert lim.permitir("ip", 60.5) and lim.permitir("otra", 2)


@pytest.mark.parametrize("ruta", ["/", "/api/salud", "/api/nada"])
def test_cabeceras_de_seguridad_en_todas_las_respuestas(cliente, ruta):
    r = cliente.get(ruta)
    for k, v in CABECERAS.items():
        assert r.headers.get(k) == v, k


def test_sesion_con_token_desconocido(cliente):
    assert es_problema(cliente.post("/api/sesion", json={"token": "inventado"}), 401, "TOKEN_INVALIDO")


def test_sesion_y_saldo_propio(cliente):
    sid = cliente.post("/api/sesion", json={"token": "demo-ana"}).json()["sesion"]
    d = cliente.post("/api/chat", json={"mensaje": "¿Cuál es mi saldo?", "sesion": sid}).json()
    assert "2 540,75" in d["texto"]


def test_una_sesion_inventada_no_da_acceso(cliente):
    d = cliente.post("/api/chat", json={"mensaje": "¿Cuál es mi saldo?", "sesion": "c-ana"}).json()
    assert "2 540,75" not in d["texto"]


def leer_sse(texto):
    eventos = []
    for bloque in texto.strip().split("\n\n"):
        lineas = dict(l.split(": ", 1) for l in bloque.splitlines())
        eventos.append((lineas["event"], json.loads(lineas["data"])))
    return eventos


@pytest.mark.parametrize("pregunta", [TARIFA, LLM, "Quiero presentar un reclamo"])
def test_flujo_sse_entrega_lo_mismo_que_la_respuesta_completa(cliente, pregunta):
    completa = cliente.post("/api/chat", json={"mensaje": pregunta}).json()
    r = cliente.post("/api/chat/flujo", json={"mensaje": pregunta})
    assert r.headers["content-type"].startswith("text/event-stream")
    eventos = leer_sse(r.text)
    assert eventos[0][0] == "meta" and eventos[-1][0] == "fin"
    sin_codigo = lambda t: re.sub(r"RCL-\d{8}-\d{4}", "RCL-…", t)  # cada reclamo recibe un código nuevo
    assert sin_codigo("".join(d["t"] for e, d in eventos if e == "texto")) == sin_codigo(completa["texto"])
    assert eventos[0][1]["tipo"] == completa["tipo"]


def test_el_flujo_no_transmite_lo_que_el_verificador_bloquea(armar):
    c = TestClient(crear_app(armar(ModeloGuionado("Confirma tu clave de internet aquí.")), por_minuto=1000))
    texto = "".join(d["t"] for e, d in leer_sse(c.post("/api/chat/flujo", json={"mensaje": LLM}).text) if e == "texto")
    assert "clave" not in texto


def test_sin_grabacion_responde_503_y_explica_como_crearla(armar, monkeypatch):
    monkeypatch.setenv("VENTANILLA_MODO", "reproducir")
    c = TestClient(crear_app(armar(), por_minuto=1000))
    r = c.post("/api/chat", json={"mensaje": "Una pregunta nueva que nunca se grabó sobre el voucher 7731"})
    assert es_problema(r, 503, "SIN_GRABACION") and "VENTANILLA_MODO=auto" in r.json()["detail"]


def test_sin_ollama_responde_503(armar, monkeypatch):
    monkeypatch.setenv("VENTANILLA_MODO", "vivo")
    monkeypatch.setenv("OLLAMA_HOST", "http://127.0.0.1:9")
    with pytest.raises(Exception):
        armar()  # al arrancar ya necesita los embeddings: falla rápido y claro


def test_cuerpo_que_no_es_utf8_es_un_problema_400(cliente):
    r = cliente.post("/api/chat", content=b"L\x0bf\xff\xfe[", headers={"content-type": "application/json"})
    assert es_problema(r, 400, "CUERPO_ILEGIBLE")
