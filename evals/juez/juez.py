"""Juez LLM (DeepEval G-Eval) con granite4.1:3b, detrás de la grabadora: la calibración se reproduce igual en la CI.

El juez es de otra familia que el modelo que redacta (qwen): reduce la preferencia por su propio estilo.
"""
import json
import os
import re
from pathlib import Path

import httpx
from deepeval.metrics import FaithfulnessMetric, GEval
from pydantic import BaseModel
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, SingleTurnParams

from ventanilla.adaptadores.grabadora import Grabadora

RAIZ = Path(__file__).resolve().parents[2]
MODELO_JUEZ = "granite4.1:3b"
OPCIONES = {"temperature": 0, "top_k": 1, "num_ctx": 4096, "seed": 7}


class JuezGrabado(DeepEvalBaseLLM):
    def __init__(self, grabadora: Grabadora, host: str):
        self.grabadora, self.host = grabadora, host.rstrip("/")

    def load_model(self):
        return self

    def get_model_name(self):
        return MODELO_JUEZ

    def supports_log_probs(self):
        return False

    def _enviar(self, peticion):
        r = httpx.post(f"{self.host}/api/chat", json=peticion, timeout=300)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def generate(self, prompt: str, schema=None):
        peticion = {"model": MODELO_JUEZ, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False, "options": OPCIONES}
        if schema is not None:
            peticion["format"] = schema.model_json_schema()
        texto = self.grabadora.llamar(peticion, self._enviar)
        return schema.model_validate_json(texto) if schema is not None else texto

    async def a_generate(self, prompt: str, schema=None):
        return self.generate(prompt, schema)


def metrica(juez: JuezGrabado) -> GEval:
    return GEval(
        name="Correctitud frente a la fuente",
        evaluation_steps=[
            "Lee el contexto: es la información oficial del banco.",
            "Compara cada afirmación de la respuesta con el contexto.",
            "Si alguna afirmación contradice el contexto o agrega un dato que el contexto no dice (montos, plazos, horarios, condiciones), la respuesta es incorrecta.",
            "Si todo lo que afirma está respaldado por el contexto, la respuesta es correcta, aunque sea breve.",
        ],
        evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.CONTEXT],
        model=juez,
        threshold=0.5,
        async_mode=False,
    )


class Veredicto(BaseModel):
    contradiccion: str
    correcta: bool


RUBRICA = """Eres auditor de un banco. Decide si la RESPUESTA es correcta según el CONTEXTO oficial.

CONTEXTO:
{contexto}

PREGUNTA: {pregunta}
RESPUESTA: {respuesta}

Primero escribe en «contradiccion» la afirmación de la respuesta que contradice el contexto o que el contexto no dice (montos, plazos,
horarios, quién paga, condiciones). Si no hay ninguna, escribe «ninguna». Luego «correcta»: true solo si no hay ninguna."""


class RubricaBinaria:
    """Pasa o no pasa, con la contradicción escrita antes del veredicto: un juez pequeño puntúa mal en escalas de 1 a 10."""

    def __init__(self, juez: JuezGrabado):
        self.juez, self.threshold = juez, 0.5

    def measure(self, caso: LLMTestCase):
        v = self.juez.generate(RUBRICA.format(contexto="\n\n".join(caso.context), pregunta=caso.input, respuesta=caso.actual_output), Veredicto)
        self.score = 1.0 if v.correcta else 0.0
        return self.score


class AmbosJueces:
    """Pasa solo si aprueban la fidelidad Y la rúbrica: con 47 casos, cada uno por separado aprobó alguna respuesta mala."""

    def __init__(self, juez: JuezGrabado):
        self.fidelidad = FaithfulnessMetric(model=juez, threshold=0.99, async_mode=False, include_reason=False)
        self.rubrica, self.threshold = RubricaBinaria(juez), 0.5

    def measure(self, caso: LLMTestCase):
        f = self.fidelidad.measure(caso) >= self.fidelidad.threshold
        r = self.rubrica.measure(caso) >= self.rubrica.threshold
        self.score = 1.0 if f and r else 0.0
        return self.score


_CITA = re.compile(r"\s*\[[^\]]{1,80}\]")


def sin_citas(texto: str) -> str:
    """Las citas las revisa el verificador; al juez solo lo confunden («esta información sale de la fuente itf» no es un dato)."""
    return _CITA.sub("", texto).strip()


class Razonado(BaseModel):
    el_contexto_dice: str
    la_respuesta_dice: str
    contradiccion: str
    correcta: bool


RAZONADA = """Eres auditor de un banco. Decide si la RESPUESTA es correcta según el CONTEXTO oficial.

CONTEXTO:
{contexto}

PREGUNTA: {pregunta}
RESPUESTA: {respuesta}

Escribe, en este orden:
- «el_contexto_dice»: qué responde el CONTEXTO a la PREGUNTA, en una oración.
- «la_respuesta_dice»: qué responde la RESPUESTA, en una oración.
- «contradiccion»: lo que la RESPUESTA afirma y el CONTEXTO contradice o no dice (montos, plazos, horarios, a dónde acudir,
  si atiende una persona o un asistente, condiciones), o «ninguna». Negarse a dar un dato u ofrecer un asesor no es contradicción.
- «correcta»: true solo si escribiste «ninguna»."""


class RubricaRazonada:
    """La rúbrica, pero escribiendo antes qué dice el contexto y qué dice la respuesta (docs/hallazgos.md, 19)."""

    def __init__(self, juez: JuezGrabado):
        self.juez, self.threshold = juez, 0.5

    def measure(self, caso: LLMTestCase):
        v = self.juez.generate(RAZONADA.format(contexto="\n\n".join(caso.context), pregunta=caso.input, respuesta=sin_citas(caso.actual_output)), Razonado)
        self.score = 1.0 if v.correcta else 0.0
        return self.score


class TresJueces:
    """Pasa solo si aprueban los tres: la rúbrica, la rúbrica razonada y la fidelidad de DeepEval (≥ 0,5).
    Cada uno por separado aprobó alguna respuesta mala en la Mac o en Linux; juntos, ninguna en las dos máquinas."""

    def __init__(self, juez: JuezGrabado):
        self.jueces = [RubricaBinaria(juez), RubricaRazonada(juez),
                       FaithfulnessMetric(model=juez, threshold=0.5, async_mode=False, include_reason=False)]
        self.threshold = 0.5

    def measure(self, caso: LLMTestCase):
        self.score = 1.0 if all(j.measure(caso) >= j.threshold for j in self.jueces) else 0.0
        return self.score


def metricas(juez: JuezGrabado) -> dict:
    return {
        "geval": lambda: metrica(juez),
        "fidelidad": lambda: FaithfulnessMetric(model=juez, threshold=0.99, async_mode=False, include_reason=False),
        "rubrica": lambda: RubricaBinaria(juez),
        "ambos": lambda: AmbosJueces(juez),
        "razonada": lambda: RubricaRazonada(juez),
        "tres": lambda: TresJueces(juez),
    }


def kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    pa, pb = sum(a) / n, sum(b) / n
    pe = pa * pb + (1 - pa) * (1 - pb)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


def calibrar(modo: str | None = None, nombre: str = "rubrica") -> dict:
    os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")
    grabadora = Grabadora(RAIZ / "grabaciones", modo or os.environ.get("VENTANILLA_MODO", "reproducir"))
    juez = JuezGrabado(grabadora, os.environ.get("OLLAMA_HOST", "http://localhost:11434"))
    items = json.loads((RAIZ / "evals" / "juez" / "etiquetas.json").read_text())["items"]
    veredictos, detalle = [], []
    for it in items:
        m = metricas(juez)[nombre]()
        m.measure(LLMTestCase(input=it["pregunta"], actual_output=it["respuesta"], context=it["contexto"], retrieval_context=it["contexto"]))
        veredictos.append(m.score >= m.threshold)
        detalle.append({"id": it["id"], "etiqueta": it["etiqueta"], "juez": veredictos[-1], "puntaje": round(m.score, 3)})
    etiquetas = [it["etiqueta"] for it in items]
    acuerdo = sum(x == y for x, y in zip(etiquetas, veredictos)) / len(items)
    return {"juez": MODELO_JUEZ, "metrica": nombre, "n": len(items), "acuerdo": round(acuerdo, 3), "kappa": round(kappa(etiquetas, veredictos), 3), "detalle": detalle}


if __name__ == "__main__":
    import sys

    nombres = sys.argv[1:] or ["rubrica"]
    todos = {n: calibrar(nombre=n) for n in nombres}
    (RAIZ / "reporte").mkdir(exist_ok=True)
    (RAIZ / "reporte" / "juez.json").write_text(json.dumps(todos, ensure_ascii=False, indent=1))
    for n, r in todos.items():
        print(f"{n}: acuerdo {r['acuerdo']:.0%}, κ {r['kappa']}")
        for d in r["detalle"]:
            if d["etiqueta"] != d["juez"]:
                print("   desacuerdo:", d)
