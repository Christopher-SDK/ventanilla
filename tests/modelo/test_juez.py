"""Calibración del juez LLM contra etiquetas de referencia. Se eligió la métrica con datos (ver docs/hallazgos.md, 8 y 16)."""
import pytest

pytest.importorskip("deepeval", reason="instala el extra: uv sync --extra evals")


def test_el_juez_nunca_aprueba_una_respuesta_mala_y_coincide_con_las_etiquetas(metricas):
    from evals.juez.juez import calibrar

    r = calibrar(nombre="tres")  # rúbrica, rúbrica razonada y fidelidad (docs/hallazgos.md, 16 y 19)
    malas_aprobadas = [d["id"] for d in r["detalle"] if not d["etiqueta"] and d["juez"]]
    buenas_rechazadas = [d["id"] for d in r["detalle"] if d["etiqueta"] and not d["juez"]]
    metricas["juez"] = {**{k: r[k] for k in ("juez", "metrica", "n", "acuerdo", "kappa")},
                        "malas_aprobadas": malas_aprobadas, "buenas_rechazadas": buenas_rechazadas}
    # Lo crítico primero: en banca, un juez que deja pasar una respuesta incorrecta no sirve.
    assert not malas_aprobadas, f"el juez aprobó respuestas incorrectas: {malas_aprobadas}"
    assert r["kappa"] >= 0.6, f"κ {r['kappa']} (rechazó {len(buenas_rechazadas)} buenas: {buenas_rechazadas})"
