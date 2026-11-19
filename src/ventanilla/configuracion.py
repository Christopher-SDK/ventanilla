"""Ensamble: arma el asistente según el entorno. Es el único lugar que conoce las fallas sembradas."""
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from .adaptadores.clientes_json import ClientesJson
from .adaptadores.grabadora import ChatGrabado, EmbeddingsGrabados, Grabadora
from .adaptadores.ollama import OllamaChat, OllamaEmbeddings
from .aplicacion import Asistente, cargar_prompt
from .dominio import corpus
from .dominio.corpus import Sanitizador
from .dominio.guardia import Guardia
from .dominio.reclamos import Calendario, Reclamos
from .dominio.tarifario import Tarifario
from .dominio.verificador import Verificador
from .fallas import (FALLAS, AsistenteConFuga, GuardiaEstricta, GuardiaSinRol, SanitizadorPermisivo, VerificadorSinCitas,
                     VerificadorSinMontos)

RAIZ = Path(os.environ.get("VENTANILLA_RAIZ", Path(__file__).resolve().parents[2]))
# Umbrales de abstención calibrados con evals/recuperacion.json y evals/fuera_de_alcance.json (ver tests/recuperacion)
UMBRALES = (float(os.environ.get("VENTANILLA_UMBRAL_BM25", "2.0")), float(os.environ.get("VENTANILLA_UMBRAL_COSENO", "0.35")))


@dataclass(frozen=True)
class Config:
    falla: str | None
    modo: str
    host: str
    modelo: str
    modelo_embeddings: str

    @classmethod
    def desde_entorno(cls) -> "Config":
        falla = os.environ.get("VENTANILLA_FALLA") or None
        if falla and falla not in FALLAS:
            raise ValueError(f"VENTANILLA_FALLA={falla!r} no existe. Opciones: {', '.join(FALLAS)}")
        return cls(
            falla=falla,
            modo=os.environ.get("VENTANILLA_MODO", "reproducir"),
            host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
            modelo=os.environ.get("VENTANILLA_MODELO", "qwen3.5:2b-q4_K_M"),
            modelo_embeddings=os.environ.get("VENTANILLA_EMBEDDINGS", "embeddinggemma:300m"),
        )


def construir(cfg: Config | None = None, *, modelo=None, embeddings=None, hoy=date.today) -> Asistente:
    """Sin argumentos: modelo real (Ollama) detrás de la grabadora. Las pruebas pueden pasar dobles."""
    cfg = cfg or Config.desde_entorno()
    grabadora = Grabadora(RAIZ / "grabaciones", cfg.modo)
    modelo = modelo or ChatGrabado(OllamaChat(cfg.modelo, cfg.host), grabadora)
    embeddings = embeddings or EmbeddingsGrabados(OllamaEmbeddings(cfg.modelo_embeddings, cfg.host), grabadora)

    f = cfg.falla
    guardia = GuardiaSinRol() if f == "JUEGO_DE_ROL" else GuardiaEstricta() if f == "RECHAZO_EXCESIVO" else None
    guardia = guardia or Guardia()
    verificador = VerificadorSinMontos() if f == "TASA_INVENTADA" else VerificadorSinCitas() if f == "CITA_FANTASMA" else Verificador()
    sanitizador = SanitizadorPermisivo(guardia) if f == "INYECCION_INDIRECTA" else Sanitizador(guardia)
    clase = AsistenteConFuga if f == "FUGA_DE_DATOS" else Asistente

    fragmentos = [fr for d in corpus.cargar(RAIZ / "corpus") for fr in corpus.fragmentar(d)]
    return clase(
        modelo=modelo,
        embeddings=embeddings,
        fragmentos=fragmentos,
        clientes=ClientesJson(RAIZ / "datos" / "clientes.json"),
        reclamos=Reclamos(Calendario.desde_archivo(RAIZ / "datos" / "feriados.json")),
        prompt_sistema=cargar_prompt("v2" if f == "REGRESION_DE_PROMPT" else "v1"),
        guardia=guardia,
        verificador=verificador,
        sanitizador=sanitizador,
        hoy=hoy,
        umbrales=UMBRALES,
        tarifario=Tarifario.desde_archivo(RAIZ / "datos" / "tarifario.json"),
    )
