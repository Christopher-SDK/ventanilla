"""Normalización para comparar texto sin que tildes, mayúsculas o trucos de escritura cambien el resultado."""
import re
import unicodedata

_INVISIBLES = re.compile("[​-‏‪-‮⁠-⁤﻿­]")
_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})


def sin_invisibles(texto: str) -> str:
    return _INVISIBLES.sub("", texto)


def normalizar(texto: str, leet: bool = False) -> str:
    t = unicodedata.normalize("NFKD", sin_invisibles(texto))
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    if leet:
        t = t.translate(_LEET)
    return re.sub(r"\s+", " ", t).strip()
