// Todo el texto del modelo se pinta con textContent: nunca como HTML (OWASP LLM05 / LLM10:2026).
const $ = (s) => document.querySelector(s);
const log = $('#log'), form = $('#form'), caja = $('#mensaje'), boton = $('#enviar'), error = $('#error');
const historial = [];
let sesion = null;
let esperando = false; // Enter no puede saltarse el botón deshabilitado

function agregar(rol, texto, extra = {}) {
  const li = document.createElement('div');
  li.className = `msg ${rol}${extra.tipo ? ' ' + extra.tipo : ''}`;
  const quien = document.createElement('span');
  quien.className = 'quien';
  quien.textContent = rol === 'cliente' ? 'Tú' : 'Ventanilla';
  const p = document.createElement('p');
  p.textContent = texto;
  li.append(quien, p);
  if (extra.fuentes && extra.fuentes.length) {
    const f = document.createElement('p');
    f.className = 'fuentes';
    f.textContent = 'Fuentes: ' + extra.fuentes.join(', ');
    li.append(f);
  }
  log.append(li);
  li.scrollIntoView({ block: 'end' }); // scroll-margin-bottom deja el mensaje sobre la caja fija
  return li;
}

async function enviar(texto) {
  esperando = true;
  error.textContent = '';
  agregar('cliente', texto);
  boton.disabled = true;
  const espera = agregar('asistente', 'Escribiendo…', { tipo: 'espera' });
  try {
    const r = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mensaje: texto, historial: historial.slice(-8), sesion }),
    });
    const d = await r.json();
    espera.remove();
    if (!r.ok) {
      error.textContent = d.detail || d.title || 'No se pudo enviar el mensaje.';
      return;
    }
    agregar('asistente', d.texto, { tipo: d.tipo, fuentes: d.fuentes });
    historial.push({ rol: 'cliente', texto }, { rol: 'asistente', texto: d.texto });
  } catch {
    espera.remove();
    error.textContent = 'No hay conexión con el asistente. Intenta de nuevo.';
  } finally {
    esperando = false;
    boton.disabled = false;
    caja.focus();
  }
}

form.addEventListener('submit', (e) => {
  e.preventDefault();
  if (esperando) return; // lo escrito se queda en la caja hasta que llegue la respuesta
  const texto = caja.value.trim();
  if (!texto) { error.textContent = 'Escribe un mensaje antes de enviar.'; caja.focus(); return; }
  caja.value = '';
  $('#contador').textContent = '0 / 1000';
  enviar(texto);
});
caja.addEventListener('input', () => { $('#contador').textContent = `${caja.value.length} / 1000`; });
caja.addEventListener('keydown', (e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); } });
$('#asesor').addEventListener('click', () => { if (!esperando) enviar('Quiero hablar con un asesor'); });
$('#form-sesion').addEventListener('submit', async (e) => {
  e.preventDefault();
  const r = await fetch('/api/sesion', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ token: $('#token').value }) });
  const d = await r.json();
  if (r.ok) { sesion = d.sesion; $('#estado-sesion').textContent = `Sesión iniciada como ${d.nombre}.`; }
  else $('#estado-sesion').textContent = 'No se pudo iniciar sesión.';
});

// La caja de escritura es fija: su alto real reserva espacio para que el último mensaje no quede debajo (WCAG 2.4.11).
new ResizeObserver(([e]) => document.documentElement.style.setProperty('--alto-caja', `${Math.ceil(e.target.getBoundingClientRect().height) + 12}px`)).observe(form);
