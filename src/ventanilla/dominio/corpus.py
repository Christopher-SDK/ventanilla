"""Documentos del banco, fragmentos por sección y limpieza de contenido no confiable."""
import re
from dataclasses import dataclass
from pathlib import Path

from .texto import sin_invisibles

OFICIAL, EXTERNO = "oficial", "externo"


@dataclass(frozen=True)
class Documento:
    id: str
    titulo: str
    confianza: str
    texto: str


@dataclass(frozen=True)
class Fragmento:
    id: str
    doc_id: str
    seccion: str
    texto: str
    confianza: str


def leer_documento(ruta: Path) -> Documento:
    crudo = ruta.read_text(encoding="utf-8")
    m = re.match(r"---\n(.*?)\n---\n(.*)", crudo, re.DOTALL)
    if not m:
        raise ValueError(f"{ruta.name}: falta la cabecera --- id/titulo/confianza ---")
    meta = dict(linea.split(": ", 1) for linea in m.group(1).splitlines())
    if meta.get("confianza") not in (OFICIAL, EXTERNO):
        raise ValueError(f"{ruta.name}: confianza debe ser {OFICIAL} o {EXTERNO}")
    return Documento(meta["id"], meta["titulo"], meta["confianza"], m.group(2).strip())


def cargar(carpeta: Path) -> list[Documento]:
    docs = [leer_documento(p) for p in sorted(carpeta.glob("*.md"))]
    ids = [d.id for d in docs]
    if len(ids) != len(set(ids)):
        raise ValueError(f"ids de documento repetidos: {ids}")
    return docs


def fragmentar(doc: Documento) -> list[Fragmento]:
    """Un fragmento por sección '## '. El título del documento acompaña a cada uno para que se entienda solo."""
    partes = re.split(r"\n(?=## )", doc.texto)
    frags = []
    for parte in partes:
        cuerpo = parte.strip()
        if cuerpo.startswith("# "):  # cabecera del documento: se queda solo lo que no es título
            cuerpo = "\n".join(cuerpo.splitlines()[1:]).strip()
        if not cuerpo:
            continue
        seccion = cuerpo.splitlines()[0].lstrip("# ").strip() if cuerpo.startswith("## ") else doc.titulo
        frags.append(Fragmento(f"{doc.id}#{len(frags) + 1}", doc.id, seccion, f"{doc.titulo}. {cuerpo}", doc.confianza))
    return frags


_COMENTARIO = re.compile(r"<!--.*?-->", re.DOTALL)
_ETIQUETAS = re.compile(r"<\s*/?\s*(script|style|iframe|img|a)\b[^>]*>", re.IGNORECASE)


class Sanitizador:
    """Quita del texto recuperado lo que un lector humano no ve o lo que le habla al asistente.

    Defensa contra inyección indirecta (OWASP LLM01, MITRE ATLAS AML.T0051.001 / AML.T0070).
    """

    def __init__(self, guardia):
        self.guardia = guardia

    def limpiar(self, texto: str) -> tuple[str, list[str]]:
        quitado = []
        t = sin_invisibles(texto)
        for patron, motivo in ((_COMENTARIO, "comentario oculto"), (_ETIQUETAS, "etiqueta HTML")):
            if patron.search(t):
                quitado.append(motivo)
                t = patron.sub("", t)
        lineas = []
        for linea in t.splitlines():
            if not self.guardia.revisar(linea).permitido or re.match(r"\s*(asistente|assistant|system|sistema)\s*:", linea, re.I):
                quitado.append("instrucción dirigida al asistente")
                continue
            lineas.append(linea)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(lineas)).strip(), quitado
