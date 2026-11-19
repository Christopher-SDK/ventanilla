"""La página del chat en un navegador real: salida segura, accesibilidad (WCAG 2.2) y uso con teclado."""
import socket
import threading
import time

import pytest
import uvicorn
from axe_playwright_python.sync_playwright import Axe
from playwright.sync_api import expect, sync_playwright

from ventanilla.adaptadores.api import crear_app

XSS = '<img src=x onerror="window.__xss=1"><script>window.__xss=2</script> Debes enviarla antes de las 15:00. [fuente: tarifario]'


class ModeloXss:
    """Un modelo que devuelve HTML activo: la página tiene que mostrarlo como texto."""

    nombre = "xss"

    def generar(self, mensajes, semilla=7):
        time.sleep(0.6)  # como un modelo real: da tiempo a que el usuario intente mandar otro mensaje
        return XSS


@pytest.fixture(scope="module")
def url():
    from datetime import date

    from ventanilla.configuracion import construir

    app = crear_app(construir(modelo=ModeloXss(), hoy=lambda: date(2026, 11, 18)), por_minuto=1000)
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        puerto = s.getsockname()[1]
    servidor = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=puerto, log_level="error"))
    hilo = threading.Thread(target=servidor.run, daemon=True)
    hilo.start()
    while not servidor.started:
        time.sleep(0.05)
    yield f"http://127.0.0.1:{puerto}"
    servidor.should_exit = True


@pytest.fixture(scope="module")
def navegador():
    with sync_playwright() as p:
        b = p.chromium.launch()
        yield b
        b.close()


@pytest.fixture
def pagina(navegador, url):
    ctx = navegador.new_context()
    pg = ctx.new_page()
    errores = []
    pg.on("pageerror", lambda e: errores.append(str(e)))
    pg.on("console", lambda m: m.type == "error" and errores.append(m.text))
    pg.goto(url)
    yield pg
    assert not errores, errores
    ctx.close()


def enviar(pg, texto):
    pg.fill("#mensaje", texto)
    pg.keyboard.press("Enter")
    expect(pg.locator(".msg.asistente").last).not_to_have_text("Escribiendo…")


def test_el_html_del_modelo_se_muestra_como_texto(pagina):
    """OWASP LLM05:2025 / LLM10:2026 (manejo inseguro de la salida), ATLAS AML.T0077."""
    enviar(pagina, "¿Hasta qué hora debo enviar una transferencia diferida para que llegue el mismo día?")
    ultimo = pagina.locator(".msg.asistente").last
    expect(ultimo).to_contain_text("<img src=x")
    assert pagina.evaluate("window.__xss") is None
    assert pagina.locator(".log img, .log script").count() == 0


def test_la_csp_bloquea_scripts_en_linea(pagina):
    assert "script-src 'self'" in pagina.request.get(pagina.url).headers["content-security-policy"]


def test_el_aviso_de_ia_se_ve_siempre(pagina):
    expect(pagina.locator("#aviso")).to_contain_text("con IA")


def test_flujo_completo_con_teclado(pagina):
    pagina.keyboard.press("Tab")  # botón «Hablar con un asesor»
    pagina.keyboard.press("Tab")  # «Iniciar sesión de prueba»
    pagina.keyboard.press("Tab")  # caja de texto
    assert pagina.evaluate("document.activeElement.id") == "mensaje"
    pagina.keyboard.type("Quiero presentar un reclamo")
    pagina.keyboard.press("Enter")
    expect(pagina.locator(".msg.asistente.reclamo")).to_contain_text("RCL-20261118-")
    assert pagina.evaluate("document.activeElement.id") == "mensaje"  # el foco vuelve a la caja


def test_las_respuestas_se_anuncian_en_una_region_viva(pagina):
    log = pagina.locator("#log")
    assert log.get_attribute("role") == "log" and log.get_attribute("aria-live") == "polite"


def test_mensaje_vacio_muestra_un_error_anunciado(pagina):
    pagina.fill("#mensaje", "   ")
    pagina.click("#enviar")
    expect(pagina.locator("#error")).to_have_text("Escribe un mensaje antes de enviar.")
    assert pagina.locator("#error").get_attribute("role") == "alert"


def test_boton_de_asesor(pagina):
    pagina.click("#asesor")
    expect(pagina.locator(".msg.asistente.asesor")).to_contain_text("9:00 a 18:00")


def test_sesion_de_prueba_y_saldo(pagina):
    pagina.click("summary")
    pagina.select_option("#token", "demo-rosa")
    pagina.click("#form-sesion button")
    expect(pagina.locator("#estado-sesion")).to_have_text("Sesión iniciada como Rosa.")
    enviar(pagina, "¿Cuál es mi saldo?")
    expect(pagina.locator(".msg.asistente").last).to_contain_text("480,90")


@pytest.mark.parametrize("ancho", [320, 390, 1280])
def test_sin_desborde_horizontal(navegador, url, ancho):
    """WCAG 1.4.10 Reflow: a 320 px no hay scroll horizontal."""
    pg = navegador.new_page(viewport={"width": ancho, "height": 800})
    pg.goto(url)
    pg.fill("#mensaje", "x" * 400)
    pg.keyboard.press("Enter")
    expect(pg.locator(".msg.asistente").last).not_to_have_text("Escribiendo…")
    assert pg.evaluate("document.documentElement.scrollWidth <= innerWidth")
    pg.close()


def test_objetivos_tactiles_de_al_menos_24_px(pagina):
    """WCAG 2.5.8 Target Size (Minimum)."""
    for b in pagina.locator("button:visible, summary:visible, select:visible").all():
        caja = b.bounding_box()
        assert caja["width"] >= 24 and caja["height"] >= 24, b.inner_text()


@pytest.mark.parametrize("esquema", ["light", "dark"])
def test_axe_sin_violaciones(navegador, url, esquema):
    pg = navegador.new_page(color_scheme=esquema)
    pg.goto(url)
    pg.fill("#mensaje", "Quiero presentar un reclamo")
    pg.keyboard.press("Enter")
    expect(pg.locator(".msg.asistente.reclamo")).to_be_visible()
    resultado = Axe().run(pg, options={"runOnly": ["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]})
    assert resultado.violations_count == 0, resultado.generate_report()
    pg.close()


def test_enter_no_envia_otro_mensaje_mientras_espera_la_respuesta(pagina):
    """Hallado al grabar la demo: Enter saltaba el botón deshabilitado y dos respuestas se cruzaban."""
    pagina.fill("#mensaje", "¿Hasta qué hora debo enviar una transferencia diferida para que llegue el mismo día?")
    pagina.keyboard.press("Enter")
    pagina.fill("#mensaje", "¿Cuánto cuesta una transferencia interbancaria inmediata?")
    pagina.keyboard.press("Enter")
    expect(pagina.locator(".msg.asistente").last).not_to_have_text("Escribiendo…")
    pagina.wait_for_timeout(1500)
    assert pagina.locator(".msg.cliente").count() == 1
    assert pagina.locator(".msg.asistente", has_text="Escribiendo…").count() == 0
    assert pagina.input_value("#mensaje").startswith("¿Cuánto cuesta")  # lo que escribió no se pierde


def test_la_ultima_respuesta_no_queda_tapada_por_la_caja(navegador, url):
    """WCAG 2.4.11: la caja fija no puede tapar el mensaje que acaba de llegar."""
    pg = navegador.new_page(viewport={"width": 1280, "height": 700})
    pg.goto(url)
    for m in ("Quiero presentar un reclamo", "asesor", "Quiero presentar un reclamo", "asesor"):
        pg.fill("#mensaje", m)
        pg.keyboard.press("Enter")
        expect(pg.locator(".msg.asistente").last).not_to_have_text("Escribiendo…")
    pg.wait_for_timeout(400)
    ultimo = pg.locator(".msg.asistente").last.bounding_box()
    caja = pg.locator("#form").bounding_box()
    assert ultimo["y"] + ultimo["height"] <= caja["y"] + 1, (ultimo, caja)
    pg.close()
