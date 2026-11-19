// Inicio: la rendija (FIRMA-01), la trastienda (FIRMA-02), rompe una pieza (FIRMA-03), videos y la guía.
import { ScrollTrigger, reducido } from './comun.js';
import escenarios from '../datos/escenarios.json';
import grabadas from '../datos/grabadas.json';
import guardiaDatos from '../datos/guardia.json';
import { crearGuardia, normalizar } from './guardia.js';

const $ = (s, c = document) => c.querySelector(s);
const $$ = (s, c = document) => [...c.querySelectorAll(s)];
const guardia = crearGuardia(guardiaDatos.reglas);
const CHIPS = escenarios.chips;
const BLOQUEO = CHIPS.find((c) => c.capa === 'guardia').texto; // el texto real que devuelve el sistema al bloquear
const PIEZAS = { guardia: 'Guardia', intencion: 'Intención', herramientas: 'Herramientas', busqueda: 'Búsqueda', sanitizador: 'Sanitizador', prompt: 'Prompt', verificador: 'Verificador' };
const VEREDICTO = {
  bloqueo: ['Bloqueado', 'mal'], respuesta: ['Pasó la revisión', 'bien'], tarifa: ['Pasó · tarifario', 'bien'], calculo: ['Pasó · cálculo', 'bien'],
  reclamo: ['Reclamo registrado', 'bien'], abstencion: ['No sabe: se abstiene', 'neutro'], saldo: ['Solo el titular', 'bien'], asesor: ['Pasa a una persona', 'bien'],
  sin_grabacion: ['Pasó la guardia', 'neutro'],
};

// ================================================================ el rótulo llena el vidrio sin desbordarlo (--k medido, no a ojo)
const vidrio = $('.ventanilla__vidrio');
const rotulo = $('.rotulo', vidrio);
function ajustarRotulo() {
  let k = 1;
  vidrio.style.setProperty('--k', k);
  while (k > 0.5 && vidrio.scrollHeight > vidrio.clientHeight + 1) { k -= 0.04; vidrio.style.setProperty('--k', k.toFixed(2)); }
}
document.fonts.ready.then(ajustarRotulo);
ajustarRotulo();
new ResizeObserver(() => requestAnimationFrame(ajustarRotulo)).observe(vidrio);

// ================================================================ FIRMA-01 · la rendija
const salida = $('[data-salida]');
const papel = $('[data-papel]');
const lamparas = Object.fromEntries($$('.revisiones li').map((li) => [li.dataset.rev, li]));
let turno = 0;

function estados(e) {
  if (e.capa === 'guardia') return { guardia: 'frena', ruta: 'omite', verificador: 'omite' };
  if (e.tipo === 'sin_grabacion') return { guardia: 'pasa', ruta: '', verificador: '' };
  if (['intencion', 'herramientas', 'busqueda'].includes(e.capa)) return { guardia: 'pasa', ruta: 'pasa', verificador: 'omite' };
  return { guardia: 'pasa', ruta: 'pasa', verificador: e.tipo === 'bloqueo' ? 'frena' : 'pasa' };
}

function pintarVeredicto(e) {
  const [rot, tono] = VEREDICTO[e.tipo] || ['', 'neutro'];
  const v = document.createElement('div');
  v.className = 'veredicto' + (reducido ? '' : ' nace');
  v.dataset.tono = tono;
  const p = (cls, txt) => { const el = document.createElement('p'); el.className = cls; el.textContent = txt; return el; };
  const r = p('veredicto__rotulo', rot);
  if (e.codigo) { const c = document.createElement('code'); c.textContent = e.codigo; r.append(' ', c); }
  const m = p('veredicto__mensaje', `«${e.mensaje}»`);
  const sr = document.createElement('span'); sr.className = 'sr'; sr.textContent = 'Tu mensaje: '; m.prepend(sr);
  const capa = p('veredicto__capa', 'Decidió: ');
  const fuerte = document.createElement('strong'); fuerte.textContent = PIEZAS[e.capa] || e.capa;
  capa.append(fuerte, ` · ${e.detalle}`);
  v.append(r, m, p('veredicto__texto', e.texto), capa);
  salida.replaceChildren(v);
}

function pasar(e) {
  const mio = ++turno;
  Object.values(lamparas).forEach((li) => { li.dataset.estado = ''; });
  if (reducido) { Object.entries(estados(e)).forEach(([k, v]) => { lamparas[k].dataset.estado = v; }); pintarVeredicto(e); mostrarSalida(); return; }
  papel.classList.remove('vuela'); void papel.offsetWidth; papel.classList.add('vuela');
  const est = estados(e);
  ['guardia', 'ruta', 'verificador'].forEach((k, i) => setTimeout(() => { if (mio === turno) lamparas[k].dataset.estado = est[k]; }, 450 + i * 80));
  setTimeout(() => { if (mio === turno) { pintarVeredicto(e); mostrarSalida(); } }, 450 + 3 * 80);
}
// El veredicto nace bajo la ventanilla: si no se ve, la página baja lo justo (solo cuando lo pidió el visitante).
let pedido = false;
function mostrarSalida() {
  if (!pedido) return;
  pedido = false;
  const r = salida.getBoundingClientRect();
  if (r.top < 0 || r.bottom > innerHeight) salida.scrollIntoView({ behavior: reducido ? 'auto' : 'smooth', block: 'nearest' });
}

function marcarChip(i) { $$('.chip[data-chip]').forEach((c) => c.setAttribute('aria-pressed', String(Number(c.dataset.chip) === i))); }
$$('.chip[data-chip]').forEach((c) => c.addEventListener('click', () => { parar(); pedido = true; marcarChip(Number(c.dataset.chip)); pasar(CHIPS[Number(c.dataset.chip)]); }));

// Campo libre: la guardia corre aquí con las reglas exportadas del código; lo que no está grabado no se inventa.
const libre = $('[data-libre]');
const error = $('#libre-error');
const entrada = $('#mensaje-libre');
libre.addEventListener('submit', (ev) => {
  ev.preventDefault();
  parar();
  const texto = entrada.value.trim();
  error.textContent = '';
  if (!texto) { error.textContent = 'Escribe un mensaje antes de pasarlo.'; entrada.focus(); return; }
  if (texto.length > 1000) { error.textContent = 'Máximo 1000 caracteres: la API rechaza lo demás.'; entrada.focus(); return; }
  marcarChip(-1);
  pedido = true;
  const v = guardia(texto);
  if (!v.permitido) { pasar({ mensaje: texto, tipo: 'bloqueo', texto: BLOQUEO, capa: 'guardia', detalle: `regla de ${v.categoria.replace(/_/g, ' ')} (la misma que en el código Python)` }); return; }
  const g = grabadas[normalizar(texto)];
  if (g) { pasar({ ...g, mensaje: texto }); return; }
  pasar({
    mensaje: texto, tipo: 'sin_grabacion', capa: 'guardia', detalle: 'lo que sigue necesita el modelo',
    texto: 'No hay una respuesta grabada para este mensaje, y aquí no se inventa una. Pruébalo en tu máquina con VENTANILLA_MODO=auto y Ollama: la guía está más abajo.',
  });
});

// Atiende sola: mensaje a mensaje, máximo 3, y cede al primer toque.
const ORDEN = [5, 0, 8];
let reloj = null;
let ciclos = 0;
function parar() { clearInterval(reloj); reloj = null; }
if (!reducido) {
  let salidaVisible = false;
  new IntersectionObserver(([e]) => { salidaVisible = e.isIntersecting; }, { threshold: 0.6 }).observe(salida);
  reloj = setInterval(() => {
    if (ciclos >= ORDEN.length) { parar(); return; }
    if (document.hidden || !salidaVisible) return; // atiende solo si alguien mira el veredicto
    const i = ORDEN[ciclos++];
    marcarChip(i);
    pasar(CHIPS[i]);
  }, 3400);
  ['pointerdown', 'keydown', 'focusin'].forEach((t) => $('#consola').addEventListener(t, parar, { once: true }));
}

// ================================================================ cabecera: toma el tono de la sala en la que estás
const cab = $('.cab');
$$('.trastienda, .fallas').forEach((s) => ScrollTrigger.create({ trigger: s, start: 'top 64px', end: 'bottom 64px', onToggle: (st) => cab.classList.toggle('tono-trastienda', st.isActive) }));

// ================================================================ FIRMA-02 · la trastienda
const tras = $('[data-trastienda]');
const pasos = $$('.paso', tras);
const escenaPosible = () => !reducido && matchMedia('(min-width: 901px) and (min-height: 601px)').matches;
let escena = null;
function armarEscena() {
  escena?.kill(); escena = null;
  const activa = escenaPosible();
  tras.classList.toggle('escena', activa);
  if (!activa) { pasos.forEach((p) => p.classList.add('activo')); ScrollTrigger.refresh(); return; }
  const marcar = (n) => pasos.forEach((p, i) => p.classList.toggle('activo', i === n));
  marcar(0);
  escena = ScrollTrigger.create({
    trigger: tras, start: 'top top', end: 'bottom bottom',
    onUpdate: (st) => {
      const p = st.progress;
      tras.style.setProperty('--abierta', Math.min(1, p / 0.14).toFixed(3)); // la persiana sube: se cruza el vidrio
      marcar(p < 0.42 ? 0 : p < 0.72 ? 1 : 2);
    },
  });
  ScrollTrigger.refresh();
}
armarEscena();
let ancho = innerWidth, alto = innerHeight;
addEventListener('resize', () => { if (Math.abs(innerWidth - ancho) > 40 || Math.abs(innerHeight - alto) > 120) { ancho = innerWidth; alto = innerHeight; armarEscena(); } });

// ================================================================ FIRMA-03 · rompe una pieza
const interruptores = $$('.interruptor');
const persianaBanco = $('.diagrama .persiana-chica');
const piezas = $$('.diagrama .pieza');
const marcarPieza = (p) => piezas.forEach((x) => x.classList.toggle('rota', x.dataset.pieza === p));
marcarPieza(interruptores[0].dataset.pieza);
let cambio = 0;
interruptores.forEach((b) => b.addEventListener('click', () => {
  if (b.getAttribute('aria-checked') === 'true') return;
  const mio = ++cambio;
  interruptores.forEach((x) => x.setAttribute('aria-checked', String(x === b)));
  const mostrar = () => {
    if (mio !== cambio) return;
    $$('[data-panel]').forEach((p) => { p.hidden = p.dataset.panel !== b.dataset.falla; });
    marcarPieza(b.dataset.pieza);
  };
  if (reducido) { mostrar(); return; }
  persianaBanco.classList.remove('sube'); persianaBanco.classList.add('baja');
  setTimeout(() => { mostrar(); persianaBanco.classList.remove('baja'); persianaBanco.classList.add('sube'); }, 470);
}));
// Flechas entre interruptores (el foco se mueve; Espacio o Enter encienden)
$('.interruptores').addEventListener('keydown', (e) => {
  const i = interruptores.indexOf(document.activeElement);
  if (i < 0 || !['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft'].includes(e.key)) return;
  e.preventDefault();
  interruptores[(i + (['ArrowDown', 'ArrowRight'].includes(e.key) ? 1 : interruptores.length - 1)) % interruptores.length].focus();
});

// ================================================================ videos: todos a la vez, cada uno con su pausa
const videos = $$('[data-video]');
function rotular(v) {
  const b = v.parentElement.querySelector('[data-pausa]');
  const cap = b.getAttribute('aria-label').replace(/^(Pausar|Reproducir): /, '');
  b.textContent = v.paused ? 'Reproducir' : 'Pausar';
  b.setAttribute('aria-label', `${v.paused ? 'Reproducir' : 'Pausar'}: ${cap}`);
}
videos.forEach((v) => {
  v.addEventListener('play', () => rotular(v));
  v.addEventListener('pause', () => rotular(v));
  v.parentElement.querySelector('[data-pausa]').addEventListener('click', () => { v.dataset.manual = '1'; v.paused ? v.play().catch(() => {}) : v.pause(); });
});
if ('IntersectionObserver' in window) {
  new IntersectionObserver(([e]) => {
    videos.forEach((v) => {
      if (e.isIntersecting && !reducido && !v.dataset.manual) v.play().catch(() => {});
      if (!e.isIntersecting && !v.paused) v.pause();
    });
  }, { threshold: 0.25 }).observe($('.videos'));
}

// ================================================================ guía «Pruébalo en tu máquina»
const CLAVE = 'ventanilla-guia';
let estado = { hechos: [], atrapadas: [] };
try { estado = { ...estado, ...JSON.parse(localStorage.getItem(CLAVE) || '{}') }; } catch { /* sin almacenamiento */ }
const guardarGuia = () => { try { localStorage.setItem(CLAVE, JSON.stringify(estado)); } catch { /* idem */ } };
const totalFallas = $$('[data-guia-falla]').length;
let fallaGuia = 0;
function pintarGuia() {
  $$('.paso-guia').forEach((p) => p.classList.toggle('hecho', estado.hechos.includes(Number(p.dataset.paso))));
  $('[data-progreso]').style.width = `${(estado.hechos.length / 4) * 100}%`;
  $('[data-progreso-texto]').textContent = `${estado.hechos.length} de 4 pasos · ${estado.atrapadas.length} de ${totalFallas} fallas atrapadas por ti`;
  $('[data-logro]').hidden = estado.atrapadas.length < totalFallas;
  $$('[data-guia-falla]').forEach((b) => b.classList.toggle('atrapada', estado.atrapadas.includes(Number(b.dataset.guiaFalla))));
}
$$('[data-guia-falla]').forEach((b) => b.addEventListener('click', () => {
  fallaGuia = Number(b.dataset.guiaFalla);
  $$('[data-guia-falla]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
  $$('[data-guia-panel]').forEach((p) => { p.hidden = Number(p.dataset.guiaPanel) !== fallaGuia; });
}));
$$('.respuesta').forEach((r) => {
  const paso = Number(r.dataset.paso);
  const ayuda = $('.ayuda', r);
  const no = $('[data-no]', r);
  $('[data-si]', r).addEventListener('click', () => {
    if (!estado.hechos.includes(paso)) estado.hechos.push(paso);
    if (paso === 4 && !estado.atrapadas.includes(fallaGuia)) estado.atrapadas.push(fallaGuia);
    ayuda.hidden = true; no.setAttribute('aria-expanded', 'false');
    guardarGuia(); pintarGuia();
    const sig = $(`.paso-guia[data-paso="${paso + 1}"]`);
    if (sig) sig.scrollIntoView({ behavior: reducido ? 'auto' : 'smooth', block: 'start' });
  });
  no.addEventListener('click', () => {
    // Acordeón exclusivo: abrir una ayuda cierra las demás
    $$('.respuesta').forEach((x) => { if (x !== r) { $('.ayuda', x).hidden = true; $('[data-no]', x).setAttribute('aria-expanded', 'false'); } });
    ayuda.hidden = !ayuda.hidden;
    no.setAttribute('aria-expanded', String(!ayuda.hidden));
  });
});
$('[data-reiniciar]').addEventListener('click', () => { estado = { hechos: [], atrapadas: [] }; guardarGuia(); pintarGuia(); });
pintarGuia();
