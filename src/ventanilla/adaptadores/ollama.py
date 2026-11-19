"""Ollama por HTTP. Opciones fijas para que la salida sea lo más estable posible (temperatura 0, semilla, contexto)."""
import httpx

from ..puertos import Mensaje

OPCIONES = {"temperature": 0, "num_ctx": 4096, "num_predict": 400, "top_k": 1}


class OllamaChat:
    def __init__(self, nombre: str, host: str, timeout: float = 180):
        self.nombre, self.host, self.timeout = nombre, host.rstrip("/"), timeout

    def peticion(self, mensajes: list[Mensaje], semilla: int) -> dict:
        return {
            "model": self.nombre,
            "messages": [{"role": m.rol, "content": m.texto} for m in mensajes],
            "stream": False,
            "think": False,
            "options": {**OPCIONES, "seed": semilla},
        }

    def enviar(self, peticion: dict) -> str:
        r = httpx.post(f"{self.host}/api/chat", json=peticion, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["message"]["content"]

    def generar(self, mensajes, semilla=7):
        return self.enviar(self.peticion(mensajes, semilla))


class OllamaEmbeddings:
    def __init__(self, nombre: str, host: str, timeout: float = 120):
        self.nombre, self.host, self.timeout = nombre, host.rstrip("/"), timeout

    def peticion(self, textos: list[str]) -> dict:
        return {"model": self.nombre, "input": textos}

    def enviar(self, peticion: dict) -> list[list[float]]:
        r = httpx.post(f"{self.host}/api/embed", json=peticion, timeout=self.timeout)
        r.raise_for_status()
        return r.json()["embeddings"]

    def vectores(self, textos):
        return self.enviar(self.peticion(textos))
