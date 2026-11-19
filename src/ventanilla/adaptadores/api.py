"""API HTTP. Errores en formato RFC 9457 (application/problem+json) con un campo «motivo» estable."""
import json
import secrets
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

import httpx
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator
from starlette.exceptions import HTTPException as StarletteHTTPException

from ..aplicacion import Asistente, Respuesta, Turno
from .grabadora import GrabacionFaltante

LARGO_MAXIMO = 1000
WEB = Path(__file__).resolve().parents[1] / "web_chat"
CABECERAS = {
    "Content-Security-Policy": "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; "
    "frame-ancestors 'none'; base-uri 'none'; form-action 'self'; object-src 'none'",
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    "Cache-Control": "no-store",
}


class TurnoEntrada(BaseModel):
    rol: str = Field(pattern="^(cliente|asistente)$")
    texto: str = Field(max_length=LARGO_MAXIMO)


class ChatEntrada(BaseModel):
    mensaje: str = Field(min_length=1, max_length=LARGO_MAXIMO)
    historial: list[TurnoEntrada] = Field(default_factory=list, max_length=8)
    sesion: str | None = Field(default=None, max_length=64)

    @field_validator("mensaje")
    @classmethod
    def no_vacio(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("el mensaje está vacío")
        return v


class SesionEntrada(BaseModel):
    token: str = Field(min_length=1, max_length=64)


class ChatSalida(BaseModel):
    texto: str
    tipo: str
    fuentes: list[str]
    aviso: str
    codigo_reclamo: str | None = None


def problema(estado: int, titulo: str, motivo: str, detalle: str = "", **extra) -> JSONResponse:
    cuerpo = {"type": "about:blank", "title": titulo, "status": estado, "motivo": motivo, **({"detail": detalle} if detalle else {}), **extra}
    return JSONResponse(cuerpo, status_code=estado, media_type="application/problem+json")


class Limitador:
    """Ventana deslizante por IP (OWASP LLM10/LLM06: consumo sin límite).

    ponytail: en memoria y por proceso; con varias réplicas va a Redis o al API gateway.
    """

    def __init__(self, por_minuto: int):
        self.por_minuto = por_minuto
        self._vistos: dict[str, deque] = defaultdict(deque)
        self._candado = threading.Lock()

    def permitir(self, clave: str, ahora: float | None = None) -> bool:
        ahora = time.monotonic() if ahora is None else ahora
        with self._candado:
            q = self._vistos[clave]
            while q and ahora - q[0] >= 60:
                q.popleft()
            if len(q) >= self.por_minuto:
                return False
            q.append(ahora)
            return True


def crear_app(asistente: Asistente, *, por_minuto: int = 30) -> FastAPI:
    app = FastAPI(title="Ventanilla", version="1.0.0", description="Asistente RAG de un banco ficticio, hecho para ser probado.")
    limitador = Limitador(por_minuto)
    sesiones: dict[str, str] = {}

    @app.middleware("http")
    async def cabeceras(request: Request, siguiente):
        if request.url.path.startswith("/api/chat") and not limitador.permitir(request.client.host if request.client else "?"):
            r = problema(429, "Demasiadas solicitudes", "LIMITE_EXCEDIDO", f"Máximo {por_minuto} mensajes por minuto.")
            r.headers["Retry-After"] = "60"
        else:
            r = await siguiente(request)
        for k, v in CABECERAS.items():
            r.headers.setdefault(k, v)
        return r

    @app.exception_handler(RequestValidationError)
    async def invalida(_, exc: RequestValidationError):
        errores = [{"campo": ".".join(str(x) for x in e["loc"][1:]), "error": e["msg"]} for e in exc.errors()]
        return problema(422, "Entrada inválida", "ENTRADA_INVALIDA", errores=errores)

    @app.exception_handler(StarletteHTTPException)
    async def http(_, exc: StarletteHTTPException):
        motivo = {404: "NO_ENCONTRADO", 405: "METODO_NO_PERMITIDO"}.get(exc.status_code, "ERROR_HTTP")
        return problema(exc.status_code, str(exc.detail), motivo)

    @app.exception_handler(GrabacionFaltante)
    async def sin_grabacion(_, exc):
        return problema(503, "Respuesta no grabada", "SIN_GRABACION", str(exc))

    @app.exception_handler(httpx.HTTPError)
    async def sin_modelo(_, exc):
        return problema(503, "El modelo no está disponible", "MODELO_NO_DISPONIBLE", "¿Está encendido Ollama?")

    def responder(e: ChatEntrada) -> Respuesta:
        historial = [Turno(t.rol, t.texto) for t in e.historial]
        return asistente.responder(e.mensaje, historial, sesiones.get(e.sesion or ""))

    @app.get("/api/salud")
    def salud():
        return {"estado": "ok", "modelo": asistente.modelo.nombre, "embeddings": asistente.embeddings.nombre}

    @app.post("/api/sesion", responses={401: {"description": "Token desconocido"}})
    def sesion(e: SesionEntrada):
        cliente = asistente.clientes.por_token(e.token)
        if not cliente:
            return problema(401, "Token desconocido", "TOKEN_INVALIDO")
        sid = secrets.token_urlsafe(24)
        sesiones[sid] = cliente.id
        return {"sesion": sid, "nombre": cliente.nombre.split()[0]}

    @app.post("/api/chat", response_model=ChatSalida, responses={422: {"description": "Entrada inválida"}, 429: {"description": "Límite"}})
    def chat(e: ChatEntrada):
        r = responder(e)
        return ChatSalida(texto=r.texto, tipo=r.tipo, fuentes=r.fuentes, aviso=r.aviso, codigo_reclamo=r.codigo_reclamo)

    @app.post("/api/chat/flujo", responses={200: {"content": {"text/event-stream": {}}}})
    def flujo(e: ChatEntrada):
        """La respuesta se verifica completa y recién entonces se envía por partes.

        Transmitir el texto del modelo antes de verificarlo mostraría al cliente lo que el verificador iba a bloquear.
        """
        r = responder(e)

        def eventos():
            meta = {"tipo": r.tipo, "fuentes": r.fuentes, "aviso": r.aviso, "codigo_reclamo": r.codigo_reclamo}
            yield f"event: meta\ndata: {json.dumps(meta, ensure_ascii=False)}\n\n"
            palabras = r.texto.split(" ")
            for i in range(0, len(palabras), 4):
                parte = " ".join(palabras[i : i + 4]) + (" " if i + 4 < len(palabras) else "")
                yield f"event: texto\ndata: {json.dumps({'t': parte}, ensure_ascii=False)}\n\n"
            yield "event: fin\ndata: {}\n\n"

        return StreamingResponse(eventos(), media_type="text/event-stream")

    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
    return app


def app_desde_entorno() -> FastAPI:
    from ..configuracion import construir

    return crear_app(construir())
