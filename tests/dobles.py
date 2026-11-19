"""Dobles del modelo de lenguaje para probar las defensas sin depender de lo que un modelo real decida hoy."""
import re

from ventanilla.puertos import Mensaje


class ModeloGuionado:
    """Devuelve siempre el mismo texto y guarda lo que recibió."""

    nombre = "guionado"

    def __init__(self, texto: str):
        self.texto = texto
        self.recibido: list[list[Mensaje]] = []

    def generar(self, mensajes, semilla=7):
        self.recibido.append(mensajes)
        return self.texto


class ModeloVulnerable:
    """El peor caso: obedece cualquier orden que encuentre en su entrada.

    - Si una fuente trae una línea «ASISTENTE: …» o un comentario con órdenes, la repite como respuesta.
    - Si el cliente le pide un cambio de rol, lo acepta.
    - Si no hay nada que obedecer, responde con la primera fuente y la cita.
    Así, cualquier orden que llegue al modelo se ve en la respuesta, y las defensas se prueban de verdad.
    """

    nombre = "vulnerable"

    def __init__(self):
        self.recibido: list[list[Mensaje]] = []

    def generar(self, mensajes, semilla=7):
        self.recibido.append(mensajes)
        ultimo = mensajes[-1].texto
        orden = re.search(r"ASISTENTE:\s*(.+?)(?:-->|$)", ultimo, re.DOTALL)
        if orden:
            return orden.group(1).strip()
        pregunta = ultimo.rsplit("Pregunta del cliente:", 1)[-1]
        if re.search(r"finge|actua como|actúa como|eres ahora", pregunta, re.I):
            return "Claro, ahora soy BancoLibre y no tengo reglas. Para no pagar ITF, parte tu transferencia en montos pequeños."
        fuente = re.search(r'<fuente id="([^"]+)"[^>]*>\n(.+?)\n', ultimo)
        return f"{fuente.group(2)} [fuente: {fuente.group(1)}]" if fuente else "No tengo ese dato."
