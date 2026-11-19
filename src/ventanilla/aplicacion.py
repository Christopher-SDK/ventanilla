"""Caso de uso «responder»: une guardia, intención, búsqueda, modelo y verificador."""
import hashlib
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path

from .dominio import itf, pii
from .dominio.corpus import EXTERNO, OFICIAL, Fragmento, Sanitizador
from .dominio.dinero import extraer_montos, extraer_porcentajes, formatear
from .dominio.guardia import Guardia
from .dominio.intencion import Intencion, detectar
from .dominio.reclamos import PLAZO_DIAS_HABILES, Reclamos
from .dominio.tarifario import Tarifario
from .dominio.recuperacion import Bm25, coseno, ordenar
from .dominio.texto import normalizar
from .dominio.verificador import Contexto, Verificador
from .puertos import Clientes, Embeddings, Mensaje, ModeloDeLenguaje

AVISO_IA = "Asistente virtual con IA · datos 100 % ficticios · puede equivocarse"
BLOQUEO = (
    "No puedo ayudarte con ese pedido. Puedo responder sobre comisiones, el ITF, reclamos, privacidad y atención. "
    "Si prefieres, escribe «asesor» y te paso con una persona."
)
ABSTENCION = (
    "No tengo ese dato en la información oficial del banco y prefiero no adivinar. "
    "Escribe «asesor» y te paso con una persona."
)
ASESOR = (
    "Te paso con un asesor. Atienden de lunes a viernes de 9:00 a 18:00 y sábados de 9:00 a 13:00; "
    "fuera de ese horario dejamos tu caso registrado y te contactamos el siguiente día hábil. [fuente: atencion]"
)
SALDO_SIN_SESION = "Para ver el saldo de una cuenta necesito verificar que eres el titular. Inicia sesión y vuelve a preguntarme."


@dataclass(frozen=True)
class Turno:
    rol: str  # cliente | asistente
    texto: str


@dataclass
class Respuesta:
    texto: str
    tipo: str  # respuesta | bloqueo | abstencion | reclamo | asesor | saldo
    fuentes: list[str] = field(default_factory=list)
    hallazgos: list[str] = field(default_factory=list)
    aviso: str = AVISO_IA
    codigo_reclamo: str | None = None


class Asistente:
    K = 4
    # Fragmentos muy por debajo del mejor solo meten ruido: con «¿Puedo reclamar por teléfono?» el 4.º era el bloqueo de tarjetas
    # y el modelo mezcló su «línea de emergencias»; con 0,25, «¿cómo pido que borren mis datos?» tomaba reclamos#3 y mandaba
    # a la SBS. Con 0,15 no se pierde ninguna consulta de evals/recuperacion.json y el set dorado sigue completo.
    MARGEN_COSENO = 0.15
    UMBRAL_COSENO = 0.0  # se calibra con el set dorado (ver evals/calibracion)
    UMBRAL_BM25 = 0.0

    def __init__(self, *, modelo: ModeloDeLenguaje, embeddings: Embeddings, fragmentos: list[Fragmento], clientes: Clientes,
                 reclamos: Reclamos, prompt_sistema: str, guardia: Guardia | None = None, verificador: Verificador | None = None,
                 sanitizador: Sanitizador | None = None, hoy=date.today, umbrales: tuple[float, float] | None = None,
                 tarifario: Tarifario | None = None):
        self.modelo, self.embeddings, self.clientes, self.reclamos = modelo, embeddings, clientes, reclamos
        self.guardia = guardia or Guardia()
        self.verificador = verificador or Verificador()
        self.sanitizador = sanitizador or Sanitizador(self.guardia)
        self.hoy = hoy
        self.tarifario = tarifario or Tarifario([])
        if umbrales:
            self.UMBRAL_BM25, self.UMBRAL_COSENO = umbrales
        self.fragmentos = fragmentos
        self.titulos = {normalizar(f.texto.split(". ", 1)[0]): f.doc_id for f in fragmentos}
        self.bm25 = Bm25([f.texto for f in fragmentos])
        self.vectores = embeddings.vectores([f.texto for f in fragmentos])
        oficiales = "\n".join(f.texto for f in fragmentos if f.confianza == OFICIAL)
        self.montos_oficiales = set(extraer_montos(oficiales))
        self.porcentajes_oficiales = set(extraer_porcentajes(oficiales))
        self.canario = "VNT-" + hashlib.sha256(prompt_sistema.encode()).hexdigest()[:10].upper()
        self.prompt_sistema = prompt_sistema.replace("{canario}", self.canario)

    # --- caso de uso -------------------------------------------------------------
    def responder(self, mensaje: str, historial: list[Turno] = (), cliente_id: str | None = None, semilla: int = 7) -> Respuesta:
        veredicto = self.guardia.revisar(mensaje)
        if not veredicto.permitido:
            return Respuesta(BLOQUEO, "bloqueo", hallazgos=[f"entrada bloqueada: {veredicto.categoria}"])

        intencion = detectar(mensaje)
        if intencion is Intencion.RECLAMO:
            return self._reclamo(mensaje)
        if intencion is Intencion.SALDO:
            return self._saldo(mensaje, cliente_id)
        if intencion is Intencion.ASESOR:
            return Respuesta(ASESOR, "asesor", fuentes=["atencion"])
        if r := self._calculo_o_tarifa(mensaje):
            return r
        return self._consulta(mensaje, historial, semilla)

    def buscar(self, consulta: str) -> list[tuple[Fragmento, float, float]]:
        q = self.embeddings.vectores([consulta])[0]
        cosenos = [coseno(q, v) for v in self.vectores]
        hallados = ordenar(self.bm25.puntajes(consulta), cosenos)[: self.K]
        tope = max(h.coseno for h in hallados)
        return [(self.fragmentos[h.indice], h.bm25, h.coseno) for h in hallados if h.coseno >= tope - self.MARGEN_COSENO]

    # --- ramas -------------------------------------------------------------------
    def _reclamo(self, mensaje: str) -> Respuesta:
        r = self.reclamos.registrar(pii.tachar(mensaje), self.hoy())
        texto = (
            f"Registré tu reclamo con el código {r.codigo}. El banco te responderá en un plazo máximo de "
            f"{PLAZO_DIAS_HABILES} días hábiles, es decir, a más tardar el {r.fecha_limite:%d/%m/%Y}. "
            "Si no estás de acuerdo con la respuesta, puedes acudir a la SBS o a Indecopi. [fuente: reclamos]"
        )
        return Respuesta(texto, "reclamo", fuentes=["reclamos"], codigo_reclamo=r.codigo)

    def _calculo_o_tarifa(self, mensaje: str) -> Respuesta | None:
        """Números con consecuencias: los da el sistema, nunca el modelo."""
        n = normalizar(mensaje)
        montos = extraer_montos(mensaje)
        if "itf" in n and montos:
            lineas = [f"El ITF de una operación de {formatear(m)} es {formatear(itf.calcular(m))}." for m in montos]
            texto = " ".join(lineas) + (
                " Se calcula con la tasa de 0,005 % y se trunca al múltiplo de cinco céntimos inferior; lo paga quien envía el dinero. [fuente: itf]"
            )
            return Respuesta(texto, "calculo", fuentes=["itf"])
        partidas = self.tarifario.buscar(mensaje)
        if partidas:
            return Respuesta("\n".join(p.texto() for p in partidas) + " [fuente: tarifario]", "tarifa", fuentes=["tarifario"])
        return None

    def cliente_para_saldo(self, mensaje: str, cliente_id: str | None):
        """Solo el titular con sesión ve sus cuentas (secreto bancario, Ley 26702; Ley 29733)."""
        return self.clientes.por_id(cliente_id) if cliente_id else None

    def _saldo(self, mensaje: str, cliente_id: str | None) -> Respuesta:
        cliente = self.cliente_para_saldo(mensaje, cliente_id)
        if not cliente:
            return Respuesta(SALDO_SIN_SESION, "saldo")
        lineas = [f"{c.tipo} {c.numero}: {formatear(c.saldo_centimos)}" for c in cliente.cuentas]
        return Respuesta(pii.tachar(f"Hola, {cliente.nombre.split()[0]}. Tus cuentas:\n" + "\n".join(lineas)), "saldo")

    def _consulta(self, mensaje: str, historial, semilla: int = 7) -> Respuesta:
        hallados = self.buscar(mensaje)
        if not hallados or (max(b for _, b, _ in hallados) < self.UMBRAL_BM25 and max(c for _, _, c in hallados) < self.UMBRAL_COSENO):
            return Respuesta(ABSTENCION, "abstencion")

        montos = set(self.montos_oficiales) | set(extraer_montos(mensaje))
        porcentajes = set(self.porcentajes_oficiales)
        calculado = ""
        if "itf" in normalizar(mensaje):
            for monto in extraer_montos(mensaje):
                impuesto = itf.calcular(monto)
                montos.add(impuesto)
                calculado += f"Dato calculado por el sistema: el ITF de una operación de {formatear(monto)} es {formatear(impuesto)}.\n"

        fuentes_txt, quitado = [], []
        for frag, _, _ in hallados:
            limpio, q = self.sanitizador.limpiar(frag.texto)
            quitado += [f"{frag.id}: {x}" for x in q]
            etiqueta = "externa (no es del banco)" if frag.confianza == EXTERNO else "oficial"
            fuentes_txt.append(f'<fuente id="{frag.doc_id}" tipo="{etiqueta}">\n{limpio}\n</fuente>')

        ids = ", ".join(f"[fuente: {d}]" for d in dict.fromkeys(f.doc_id for f, _, _ in hallados))
        # Formato elegido midiendo 3 variantes (evals/sesgo.json + evals/dorado.json): con el mensaje entre etiquetas
        # el modelo deja de copiar la presentación del cliente («Soy Wilber, de Puno…») y responde igual a todos.
        usuario = (
            "\n\n".join(fuentes_txt) + ("\n\n" + calculado if calculado else "")
            + f"\n\nCitas válidas: {ids}.\n\n<mensaje_del_cliente>\n{mensaje}\n</mensaje_del_cliente>\n\nEscribe solo tu respuesta al cliente."
        )
        mensajes = [Mensaje("system", self.prompt_sistema)]
        # El historial llega del cliente (API sin estado): se revisa igual que el mensaje y se descarta lo que no pase.
        for t in [t for t in historial if self.guardia.revisar(t.texto).permitido][-4:]:
            mensajes.append(Mensaje("user" if t.rol == "cliente" else "assistant", t.texto[:1000]))
        mensajes.append(Mensaje("user", usuario))

        borrador = self.modelo.generar(mensajes, semilla)
        recuperadas = {f.doc_id for f, _, _ in hallados}
        ctx = Contexto(montos, porcentajes, recuperadas, [self.canario, *self._frases_del_prompt()], self.titulos,
                       fuentes_texto="\n".join(fuentes_txt) + "\n" + calculado, pregunta=mensaje)
        r = self.verificador.verificar(borrador, ctx)
        return Respuesta(r.texto, "respuesta" if r.aprobado else "bloqueo", fuentes=r.citas, hallazgos=r.hallazgos + quitado)

    def _frases_del_prompt(self) -> list[str]:
        """Frases largas del prompt de sistema: si aparecen textuales en la salida, se filtró (OWASP LLM07/LLM08)."""
        return [l.strip() for l in self.prompt_sistema.splitlines() if len(l.strip()) > 60][:6]


def cargar_prompt(version: str = "v1") -> str:
    return (Path(__file__).parent / "prompts" / f"sistema-{version}.md").read_text(encoding="utf-8")
