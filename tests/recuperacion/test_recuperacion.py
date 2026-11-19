"""Búsqueda sin el modelo de lenguaje: métricas sobre consultas etiquetadas a mano."""
import json
from pathlib import Path

import pytest

from ventanilla.configuracion import UMBRALES
from ventanilla.dominio.dinero import extraer_montos, formatear
from ventanilla.dominio.recuperacion import coseno

EVALS = Path(__file__).resolve().parents[2] / "evals"
CONSULTAS = json.loads((EVALS / "recuperacion.json").read_text())["consultas"]
FUERA = json.loads((EVALS / "fuera_de_alcance.json").read_text())["consultas"]


def mrr(posiciones):
    return sum(1 / p for p in posiciones if p) / len(posiciones)


def posicion(ids, esperado):
    return ids.index(esperado) + 1 if esperado in ids else None


@pytest.fixture(scope="module")
def a():
    from ventanilla.configuracion import construir

    return construir()


def test_recall_en_4_es_total(a):
    perdidas = [c["q"] for c in CONSULTAS if c["fragmento"] not in [f.id for f, _, _ in a.buscar(c["q"])]]
    assert not perdidas, f"consultas cuyo fragmento no llega al modelo: {perdidas}"


def test_mrr_minimo(a):
    m = mrr([posicion([f.id for f, _, _ in a.buscar(c["q"])], c["fragmento"]) for c in CONSULTAS])
    assert m >= 0.9, f"MRR {m:.3f}"


def test_el_peso_elegido_para_bm25_es_el_mejor_medido(a):
    """Ablación: si otro peso de BM25 rindiera más, la configuración está mal elegida."""
    from ventanilla.dominio.recuperacion import PESO_BM25, ordenar

    def mrr_con(peso):
        pos = []
        for c in CONSULTAS:
            q = a.embeddings.vectores([c["q"]])[0]
            orden = ordenar(a.bm25.puntajes(c["q"]), [coseno(q, v) for v in a.vectores], peso)
            pos.append(posicion([a.fragmentos[h.indice].id for h in orden], c["fragmento"]))
        return mrr(pos)

    elegido = mrr_con(PESO_BM25)
    for peso in (0.0, 0.25, 0.5, 1.0):
        assert elegido >= mrr_con(peso) - 0.005, f"BM25 con peso {peso} rinde más que {PESO_BM25}"


def _abstiene(a, q):
    h = a.buscar(q)
    return max(b for _, b, _ in h) < UMBRALES[0] and max(c for _, _, c in h) < UMBRALES[1]


def test_el_umbral_nunca_descarta_una_pregunta_cubierta(a):
    assert not [c["q"] for c in CONSULTAS if _abstiene(a, c["q"])]


def test_el_umbral_filtra_parte_de_lo_que_no_esta_cubierto(a):
    """La búsqueda es la primera barrera, no la única: el prompt y el verificador cubren el resto (ver tests/modelo)."""
    filtradas = sum(_abstiene(a, q) for q in FUERA)
    assert filtradas >= 5, f"solo {filtradas} de {len(FUERA)}"


def test_el_tarifario_publicado_y_el_estructurado_dicen_lo_mismo():
    """El verificador usa los montos del texto; el sistema del banco, el JSON. Si divergen, uno miente."""
    datos = json.loads((EVALS.parent / "datos" / "tarifario.json").read_text())
    md = (EVALS.parent / "corpus" / "tarifario.md").read_text()
    for p in datos["partidas"]:
        linea = next((l for l in md.splitlines() if p["concepto"] in l), None)
        assert linea, f"{p['concepto']} no aparece en tarifario.md"
        if p["monto_centimos"]:
            assert formatear(p["monto_centimos"]) in linea, linea
        else:
            assert "sin costo" in linea.lower(), linea
    montos_md = set(extraer_montos(md))
    esperados = {p["monto_centimos"] for p in datos["partidas"] if p["monto_centimos"]} | {100000}
    assert montos_md == esperados, montos_md ^ esperados
