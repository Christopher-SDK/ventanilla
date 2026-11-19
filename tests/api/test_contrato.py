"""Fuzzing del contrato OpenAPI con Schemathesis: entradas generadas a partir del esquema, ninguna puede dar 500 ni salirse del contrato."""
import schemathesis
from hypothesis import HealthCheck, settings

from ventanilla.adaptadores.api import crear_app
from ventanilla.configuracion import construir
from tests.dobles import ModeloGuionado


class EmbeddingsDeterministas:
    """Vectores por hash de palabras: el fuzzing genera textos que nunca se grabaron."""

    nombre = "hash"

    def vectores(self, textos):
        import hashlib

        salida = []
        for t in textos:
            v = [0.0] * 64
            for palabra in t.lower().split():
                v[int(hashlib.md5(palabra.encode()).hexdigest(), 16) % 64] += 1.0
            salida.append(v)
        return salida


APP = crear_app(construir(modelo=ModeloGuionado("Debes enviarla antes de las 15:00. [fuente: tarifario]"), embeddings=EmbeddingsDeterministas()),
                por_minuto=10**9)
schema = schemathesis.openapi.from_asgi("/openapi.json", APP)


@schema.parametrize()
@settings(max_examples=60, deadline=None, suppress_health_check=list(HealthCheck))
def test_la_api_cumple_su_contrato(case):
    case.call_and_validate()
