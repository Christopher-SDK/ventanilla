"""Calibración del juez LLM contra etiquetas de referencia. Se eligió la métrica con datos (ver docs/juez.md)."""
import pytest

pytest.importorskip("deepeval", reason="instala el extra: uv sync --extra evals")


def test_el_juez_coincide_con_las_etiquetas_y_nunca_aprueba_una_respuesta_mala(metricas):
    from evals.juez.juez import calibrar

    r = calibrar(nombre="fidelidad")
    metricas["juez"] = {k: r[k] for k in ("juez", "metrica", "n", "acuerdo", "kappa")}
    malas_aprobadas = [d["id"] for d in r["detalle"] if not d["etiqueta"] and d["juez"]]
    assert r["kappa"] >= 0.6, f"κ {r['kappa']}"
    assert not malas_aprobadas, f"el juez aprobó respuestas incorrectas: {malas_aprobadas}"
