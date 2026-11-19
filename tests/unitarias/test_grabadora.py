"""La grabadora: lo grabado tiene que poder reproducirse tal cual."""
from itertools import count

from ventanilla.adaptadores.grabadora import Grabadora


def test_al_grabar_la_primera_respuesta_se_queda_aunque_el_modelo_cambie(tmp_path):
    """En Linux sin GPU, la misma petición respondió distinto dentro de una corrida y la cadena dejó de reproducirse."""
    respuestas = count()
    grabar = Grabadora(tmp_path, "grabar")
    primera = grabar.llamar({"p": 1}, lambda _: next(respuestas))
    assert grabar.llamar({"p": 1}, lambda _: next(respuestas)) == primera
    assert Grabadora(tmp_path, "reproducir").llamar({"p": 1}, None) == primera
