"""Revisión de cada borrador del modelo antes de que llegue al cliente.

Si un control falla, el cliente recibe una respuesta segura y el hallazgo queda registrado.
"""
import re
from dataclasses import dataclass, field
from decimal import Decimal

from . import pii
from .dinero import extraer_montos, extraer_porcentajes
from .reclamos import PLAZO_DIAS_HABILES
from .texto import normalizar

# Una cita es "[fuente: x]" o "[x]" con x en forma de identificador. Puede nombrar el id o el título del documento.
_CITA_CON_PREFIJO = re.compile(r"\[\s*fuentes?\s*:\s*([^\]]{1,80})\]", re.IGNORECASE)
_CITA_SUELTA = re.compile(r"\[\s*([a-z0-9][a-z0-9-]*(?:#\d+)?)\s*\]")


def citas_en(texto: str) -> list[str]:
    crudas = _CITA_CON_PREFIJO.findall(texto) + _CITA_SUELTA.findall(texto)
    return [p.strip() for c in crudas for p in c.split(",") if p.strip()]
DOMINIOS_PERMITIDOS = ("gob.pe",)
RESPUESTA_SEGURA = (
    "No puedo confirmarte ese dato con la información oficial que tengo. "
    "Si quieres, escribe «asesor» y te paso con una persona."
)

_PIDE_SECRETO = re.compile(
    r"\b(confirma|confirmar|envia|enviar|enviame|dicta|dictar|escribe|escribir|comparte|compartir|ingresa|ingresar|responde|indicame|dame|proporciona)\b"
    r".{0,40}\b(clave|contrasena|password|token|codigo de verificacion|codigo sms|cvv|pin)\b"
)
_APRUEBA_CREDITO = re.compile(r"\b(credito|prestamo)\b.{0,30}\b(esta|fue|queda|quedo|ha sido)? ?(aprobado|pre ?aprobado)\b|\b(te|le) (aprobamos|aprobe|aprueba)\b")
_URL = re.compile(r"\b(?:https?://|www\.)([^\s/)\]]+)", re.IGNORECASE)
_PLAZO = re.compile(r"\b(\d{1,3})\s*dias\b")
_NIEGA_ASESOR = re.compile(r"\bno (puedo|podemos|es posible|se puede)\b.{0,20}\b(pasar|derivar|comunicar|transferir)\w*\b.{0,20}\b(asesor|persona|humano)")


# Solo una advertencia del tipo "nunca te pediremos tu clave" deja pasar la oración.
# "No olvides enviar tu clave" no es una advertencia: el verbo negado no es "pedir".
_ADVERTENCIA = re.compile(
    r"\b(nunca|jamas|no)\b.{0,30}\b(pedira|pediran|pediremos|pide|piden|pedimos|pedirte|solicita|solicitara|solicitaremos|solicitamos|compartas|envies|dictes|des|entregues|reveles)\b"
)


def _pide(texto: str) -> bool:
    for oracion in re.split(r"(?<=[.!?\n])\s+", normalizar(texto)):
        if _PIDE_SECRETO.search(oracion) and not _ADVERTENCIA.search(oracion):
            return True
    return False


@dataclass
class Contexto:
    montos_permitidos: set[int]
    porcentajes_permitidos: set[Decimal]
    fuentes_recuperadas: set[str]
    secretos: list[str]
    titulos: dict[str, str] = field(default_factory=dict)  # título normalizado -> id

    def resolver(self, cita: str) -> str:
        n = normalizar(cita).split("#")[0].strip()
        return self.titulos.get(n, n)


@dataclass
class Resultado:
    aprobado: bool
    texto: str
    hallazgos: list[str] = field(default_factory=list)
    citas: list[str] = field(default_factory=list)


class Verificador:
    def verificar(self, borrador: str, ctx: Contexto) -> Resultado:
        hallazgos = []
        for control in self.controles():
            hallazgos += control(borrador, ctx)
        citas = sorted({ctx.resolver(c) for c in citas_en(borrador)})
        if hallazgos:
            return Resultado(False, RESPUESTA_SEGURA, hallazgos, [])
        return Resultado(True, pii.tachar(borrador).strip(), [], citas)

    def controles(self):
        return [self.montos, self.porcentajes, self.citas, self.secretos, self.pide_secretos, self.credito, self.enlaces, self.plazo_reclamo, self.niega_asesor]

    def montos(self, t, ctx):
        return [f"monto no respaldado: {m}" for m in extraer_montos(t) if m not in ctx.montos_permitidos]

    def porcentajes(self, t, ctx):
        return [f"porcentaje no respaldado: {p} %" for p in extraer_porcentajes(t) if p not in ctx.porcentajes_permitidos]

    def citas(self, t, ctx):
        return [f"cita a una fuente no recuperada: {c}" for c in citas_en(t) if ctx.resolver(c) not in ctx.fuentes_recuperadas]

    def secretos(self, t, ctx):
        n = normalizar(t)
        return [f"filtra contenido reservado ({s[:12]}…)" for s in ctx.secretos if normalizar(s) in n]

    def pide_secretos(self, t, ctx):
        return ["pide una clave o código al cliente"] if _pide(t) else []

    def credito(self, t, ctx):
        return ["afirma la aprobación de un crédito"] if _APRUEBA_CREDITO.search(normalizar(t)) else []

    def enlaces(self, t, ctx):
        malos = [d for d in _URL.findall(t) if not d.lower().rstrip(".").endswith(DOMINIOS_PERMITIDOS)]
        return [f"enlace no permitido: {d}" for d in malos]

    def plazo_reclamo(self, t, ctx):
        n = normalizar(t)
        if "reclamo" not in n:
            return []
        return [f"plazo de reclamo incorrecto: {d} días" for d in _PLAZO.findall(n) if int(d) != PLAZO_DIAS_HABILES]

    def niega_asesor(self, t, ctx):
        """Pasar a una persona siempre es posible (DS 115-2025-PCM art. 31.4). Visto con el modelo real: «No puedo pasar con un asesor»."""
        return ["niega el paso a un asesor humano"] if _NIEGA_ASESOR.search(normalizar(t)) else []
