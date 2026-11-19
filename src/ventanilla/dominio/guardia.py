"""Revisión de la entrada del usuario antes de que llegue al modelo (OWASP LLM01, MITRE ATLAS AML.T0051 / AML.T0054)."""
import base64
import binascii
import re
from dataclasses import dataclass

from .texto import normalizar


@dataclass(frozen=True)
class Veredicto:
    permitido: bool
    categoria: str = ""
    regla: str = ""


INYECCION = [
    r"\b(ignor|olvid|omit|desobedec|saltat|salte)\w*\b.{0,30}\b(instrucciones|reglas|indicaciones|restricciones|politicas)\b",
    r"\bignore\b.{0,30}\b(instructions|rules)\b",
    r"\bdisregard\b.{0,30}\b(instructions|rules)\b",
    r"\b(muestra|muestrame|revela|dime|repite|imprime|copia|ensename|escribe)\b.{0,40}\b(prompt|instrucciones|mensaje|reglas) (de|del) sistema\b",
    r"\b(system|developer) (prompt|message)\b",
    r"\bprompt (de|del) sistema\b",
    r"\binstrucciones (ocultas|iniciales|originales|internas)\b",
    r"\bnuevas instrucciones\b",
]
ROL = [
    r"\bmodo (desarrollador|developer|dios|sin restricciones|sin filtros|dan)\b",
    r"\b(eres|seras|actua como|actuas como) (un |una )?(dan|ia sin|asistente sin|modelo sin)\b",
    r"\b(finge|fingir|imagina|haz de cuenta|pretende|juguemos|simula)\b.{0,40}\b(que eres|que seas|que fueras|ser un|ser una|a que eres|como si fueras)\b",
    r"\b(sin|no tienes|no hay) (reglas|restricciones|filtros|limites|censura)\b",
    r"\bjailbreak\b",
    r"\bdo anything now\b",
    r"\b(pretend|act as|roleplay|role-play)\b",
]


class Guardia:
    reglas = {"inyeccion": INYECCION, "juego_de_rol": ROL}

    def __init__(self):
        self._compiladas = [(cat, re.compile(p)) for cat, ps in self.reglas.items() for p in ps]

    def revisar(self, texto: str) -> Veredicto:
        candidatos = [normalizar(texto), normalizar(texto, leet=True), *self._decodificados(texto)]
        for c in candidatos:
            for cat, regex in self._compiladas:
                if regex.search(c):
                    return Veredicto(False, cat, regex.pattern)
        return Veredicto(True)

    @staticmethod
    def _decodificados(texto: str) -> list[str]:
        """Instrucciones escondidas en base64 se revisan igual que el texto plano."""
        salida = []
        for bloque in re.findall(r"[A-Za-z0-9+/]{16,}={0,2}", texto):
            try:
                salida.append(normalizar(base64.b64decode(bloque + "=" * (-len(bloque) % 4), validate=True).decode("utf-8")))
            except (binascii.Error, UnicodeDecodeError, ValueError):
                pass
        return salida
