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
// Lo que sobra fuera del área útil del vidrio (el arco y el papel son absolutos y no cuentan)
function sobra() {
  const cs = getComputedStyle(vidrio), b = vidrio.getBoundingClientRect();
  const arriba = b.top + parseFloat(cs.borderTopWidth) + parseFloat(cs.paddingTop) - 1, abajo = b.bottom - parseFloat(cs.paddingBottom) + 1;
  return Math.max(0, ...['.rotulo', '.revisiones'].map((s) => { const r = vidrio.querySelector(s).getBoundingClientRect(); return Math.max(arriba - r.top, r.bottom - abajo); }));
}
function ajustarRotulo() {
  let k = 1;
  vidrio.style.setProperty('--k', k);
  while (k > 0.5 && sobra() > 0) { k -= 0.04; vidrio.style.setProperty('--k', k.toFixed(2)); }
}
document.fonts.ready.then(() => { fijarSalida(); ajustarRotulo(); });
ajustarRotulo();
// Solo al cambiar la ventana: el contenido del mostrador tiene alto fijo y no debe mover el rótulo
let medida = `${innerWidth}x${innerHeight}`;
addEventListener('resize', () => { const m = `${innerWidth}x${innerHeight}`; if (m !== medida) { medida = m; requestAnimationFrame(() => { fijarSalida(); ajustarRotulo(); }); } });

// ================================================================ FIRMA-01 · la rendija
const salida = $('[data-salida]');
const papel = $('[data-papel]');
const lamparas = Object.fromEntries($$('.revisiones li').map((li) => [li.dataset.rev, li]));
const detalleInicial = Object.fromEntries(Object.entries(lamparas).map(([k, li]) => [k, $('[data-rev-detalle]', li).textContent]));
let turno = 0;

function estados(e) {
  if (e.capa === 'guardia' && e.tipo !== 'sin_grabacion') return { guardia: ['frena', e.detalle], ruta: ['omite', 'no llegó'], verificador: ['omite', 'no llegó'] };
  if (e.tipo === 'sin_grabacion') return { guardia: ['pasa', 'pasó la guardia'], ruta: ['', 'necesita el modelo'], verificador: ['', 'necesita el modelo'] };
  if (['intencion', 'herramientas', 'busqueda'].includes(e.capa)) return { guardia: ['pasa', 'pasó'], ruta: ['pasa', `${PIEZAS[e.capa]}: ${e.detalle}`], verificador: ['omite', 'sin modelo'] };
  return { guardia: ['pasa', 'pasó'], ruta: ['pasa', 'consulta a los documentos'], verificador: [e.tipo === 'bloqueo' ? 'frena' : 'pasa', e.detalle] };
}

function crearVeredicto(e, animar = !reducido) {
  const [rot, tono] = VEREDICTO[e.tipo] || ['', 'neutro'];
  const v = document.createElement('div');
  v.className = 'veredicto' + (animar ? ' nace' : '');
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
  return v;
}
const pintarVeredicto = (e) => salida.replaceChildren(crearVeredicto(e));

// El alto de la salida se fija con el veredicto más largo de los ejemplos, medido en el ancho actual:
// así ningún ejemplo se corta y el rótulo no se mueve con cada mensaje.
function fijarSalida() {
  const medidor = document.createElement('div');
  medidor.style.cssText = `position:absolute;visibility:hidden;left:-9999px;top:0;width:${salida.clientWidth}px`;
  salida.parentElement.append(medidor);
  let alto = 0;
  for (const c of CHIPS) { medidor.replaceChildren(crearVeredicto(c, false)); alto = Math.max(alto, medidor.scrollHeight); }
  medidor.remove();
  salida.style.height = `${Math.ceil(alto) + 4}px`;
}
fijarSalida(); // antes del primer fotograma: el mostrador no salta al cargar

function pasar(e) {
  const mio = ++turno;
  const est = estados(e);
  Object.entries(lamparas).forEach(([k, li]) => { li.dataset.estado = ''; $('[data-rev-detalle]', li).textContent = detalleInicial[k]; });
  const encender = (k) => { lamparas[k].dataset.estado = est[k][0]; $('[data-rev-detalle]', lamparas[k]).textContent = est[k][1]; };
  if (reducido) { Object.keys(lamparas).forEach(encender); pintarVeredicto(e); return; }
  papel.textContent = e.mensaje;
  papel.classList.remove('vuela'); void papel.offsetWidth; papel.classList.add('vuela');
  ['guardia', 'ruta', 'verificador'].forEach((k, i) => setTimeout(() => { if (mio === turno) encender(k); }, 380 + i * 80));
  setTimeout(() => { if (mio === turno) pintarVeredicto(e); }, 380 + 3 * 80);
}

// La fila de chips avisa que sigue (degradado) mientras quede algo a la derecha
const filaChips = $('.chips[data-chips]') || $('.heroe .chips');
function senalChips() {
  const resto = filaChips.scrollWidth - filaChips.clientWidth - filaChips.scrollLeft;
  if (filaChips.scrollWidth <= filaChips.clientWidth + 1) delete filaChips.dataset.desliza;
  else filaChips.dataset.desliza = resto <= 2 ? 'fin' : 'si';
}
filaChips.addEventListener('scroll', senalChips, { passive: true });
addEventListener('resize', senalChips);
senalChips();

function marcarChip(i) { $$('.chip[data-chip]').forEach((c) => c.setAttribute('aria-pressed', String(Number(c.dataset.chip) === i))); }
$$('.chip[data-chip]').forEach((c) => c.addEventListener('click', () => { parar(); marcarChip(Number(c.dataset.chip)); pasar(CHIPS[Number(c.dataset.chip)]); }));

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
  const v = guardia(texto);
  if (!v.permitido) { pasar({ mensaje: texto, tipo: 'bloqueo', texto: BLOQUEO, capa: 'guardia', detalle: `regla de ${{ inyeccion: 'inyección', juego_de_rol: 'juego de rol' }[v.categoria] || v.categoria} (la misma que en el código Python)` }); return; }
  const g = grabadas[normalizar(texto)];
  if (g) { pasar({ ...g, mensaje: texto }); return; }
  pasar({
    mensaje: texto, tipo: 'sin_grabacion', capa: 'guardia', detalle: 'lo que sigue necesita el modelo',
    texto: 'No hay una respuesta grabada para este mensaje, y aquí no se inventa una. Pruébalo en tu máquina con VENTANILLA_MODO=auto y Ollama: la guía está más abajo.',
  });
});

// Atiende sola: mensaje a mensaje, máximo 3, mientras se vea la ventanilla; cede al primer toque.
const ORDEN = [5, 0, 8];
let reloj = null;
let ciclos = 0;
function parar() { clearInterval(reloj); reloj = null; }
if (!reducido) {
  let visible = false;
  new IntersectionObserver(([e]) => { visible = e.isIntersecting; }, { threshold: 0.5 }).observe($('[data-ventanilla]'));
  reloj = setInterval(() => {
    if (ciclos >= ORDEN.length) { parar(); return; }
    if (document.hidden || !visible) return;
    const i = ORDEN[ciclos++];
    marcarChip(i);
    pasar(CHIPS[i]);
  }, 7000); // tiempo para leer el rótulo y la primera línea de cada respuesta
  ['pointerdown', 'keydown', 'focusin'].forEach((t) => $('#consola').addEventListener(t, parar, { once: true }));
}

// ================================================================ cabecera: toma el tono de la sala en la que estás
const cab = $('.cab');
$$('.trastienda, .tono-trastienda').forEach((s) => ScrollTrigger.create({ trigger: s, start: 'top 64px', end: 'bottom 64px', onToggle: (st) => cab.classList.toggle('tono-trastienda', st.isActive) }));

// ================================================================ FIRMA-02 · cruzar el vidrio y la trastienda
const tras = $('[data-trastienda]');
const pasos = $$('.paso', tras);
const indice = $$('.indice-pasos li', tras);
const cruce = $('[data-cruce]');
const escenaPosible = () => !reducido && matchMedia('(min-width: 901px) and (min-height: 601px)').matches;
let disparadores = [];
function armarEscena() {
  disparadores.forEach((d) => d.kill()); disparadores = [];
  const activa = escenaPosible();
  tras.classList.toggle('escena', activa);
  const marcar = (n) => { pasos.forEach((p, i) => p.classList.toggle('activo', !activa || i === n)); indice.forEach((l, i) => l.classList.toggle('actual', i === n)); };
  marcar(0);
  if (!reducido) {
    // La persiana baja sobre la sala mientras la trastienda sube a la pantalla...
    disparadores.push(ScrollTrigger.create({
      trigger: tras, start: 'top 40%', end: 'top top', // empieza cuando el héroe ya salió: nunca tapa lo que se está leyendo
      onUpdate: (st) => { cruce.classList.toggle('activo', st.progress > 0.01); cruce.style.clipPath = `inset(0 0 ${((1 - st.progress) * 100).toFixed(2)}% 0)`; },
      onLeaveBack: () => cruce.classList.remove('activo'),
    }));
    // ...y sube sobre la pared de terminal en el primer medio pantallazo de la trastienda.
    disparadores.push(ScrollTrigger.create({
      trigger: tras, start: 'top top', end: () => `top+=${innerHeight * 0.5} top`,
      onUpdate: (st) => { cruce.classList.toggle('activo', st.progress < 0.99); cruce.style.clipPath = `inset(0 0 ${(st.progress * 100).toFixed(2)}% 0)`; },
      onLeave: () => cruce.classList.remove('activo'),
    }));
  }
  if (activa) {
    disparadores.push(ScrollTrigger.create({
      trigger: tras, start: 'top top', end: 'bottom bottom',
      onUpdate: (st) => marcar(st.progress < 0.45 ? 0 : st.progress < 0.75 ? 1 : 2),
    }));
  }
  ScrollTrigger.refresh();
}
armarEscena();
// La pared: los últimos 5 s reales de la suite, una vez, al entrar (sin bucle: termina en «282 passed»)
const pared = $('[data-pared]', tras);
if (!reducido && 'IntersectionObserver' in window) {
  new IntersectionObserver(([e], o) => {
    if (!e.isIntersecting) return;
    o.disconnect();
    pared.preload = 'auto';
    pared.addEventListener('loadedmetadata', () => { pared.currentTime = Math.max(0, pared.duration - 5); pared.play().catch(() => {}); }, { once: true });
    pared.load();
  }, { rootMargin: '0px 0px 30% 0px' }).observe(tras);
}
let ancho = innerWidth, alto = innerHeight;
addEventListener('resize', () => { if (Math.abs(innerWidth - ancho) > 40 || Math.abs(innerHeight - alto) > 120) { ancho = innerWidth; alto = innerHeight; armarEscena(); } });

// ================================================================ FIRMA-03 · rompe una pieza
// La falla se propaga: el papel recorre el diagrama, la pieza rota se tacha al tocarla,
// un hilo rojo baja de ella hasta la respuesta «con la falla», que entra desde ese hilo; al final, la prueba roja.
const interruptores = $$('.interruptor');
const banco = $('[data-banco]');
const diagrama = $('.diagrama');
const piezas = $$('.pieza', diagrama);
const papelDiagrama = $('[data-papel-diagrama]');
const hilo = $('.hilo path', banco);
const marcarPieza = (p) => piezas.forEach((x) => x.classList.toggle('rota', x.dataset.pieza === p));
let animaciones = [], relojes = [];
const pararBanco = () => { animaciones.forEach((a) => a.cancel()); relojes.forEach(clearTimeout); animaciones = []; relojes = []; hilo.style.opacity = ''; };
const anima = (el, k, o) => { const a = el.animate(k, { fill: 'both', ...o }); animaciones.push(a); return a; };
const luego = (ms, f) => relojes.push(setTimeout(f, ms));

function propagar(panel, pieza) {
  pararBanco();
  marcarPieza(null);
  papelDiagrama.classList.remove('danado');
  if (reducido) { marcarPieza(pieza); papelDiagrama.classList.add('danado'); return; }
  const rota = piezas.find((x) => x.dataset.pieza === pieza);
  const sin = $('.lado:not(.lado--rota)', panel), con = $('.lado--rota', panel), prueba = $('.prueba-roja', panel);
  const b = banco.getBoundingClientRect(), d = diagrama.getBoundingClientRect(), r = rota.getBoundingClientRect(), c = con.getBoundingClientRect();
  // El papel corre como en una cinta (lineal): el toque cae justo al pasar por la pieza
  const largo = d.width - 12 * 2 - 46 - 20, viaje = 700;
  const golpe = Math.round(Math.min(1, Math.max(0, (r.left + r.width / 2 - d.left - 12 - 23) / largo)) * viaje);
  anima(papelDiagrama, [{ transform: 'translateX(0)' }, { transform: `translateX(${largo}px)` }], { duration: viaje, easing: 'linear' });
  anima(sin, [{ clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0 0 0)' }], { duration: 380, easing: 'cubic-bezier(.16,1,.3,1)' });
  let llega = golpe + 120;
  // En columnas el hilo baja por el borde derecho, sin cruzar texto, hasta el borde de la respuesta dañada
  if (innerWidth > 760 && c.top > d.bottom) {
    const x0 = r.left + r.width / 2 - b.left, y0 = r.bottom - b.top, xr = d.right - b.left - 1, y1 = c.top - b.top + 1.5;
    hilo.setAttribute('d', `M${x0},${y0} V${d.bottom - b.top + 8} H${xr} V${y1} H${c.right - b.left}`);
    const L = hilo.getTotalLength();
    hilo.style.strokeDasharray = L;
    // Se traza (480 ms), se queda mientras entra la respuesta y se recoge hacia la respuesta (320 ms)
    anima(hilo, [
      { strokeDashoffset: L, opacity: 1, easing: 'cubic-bezier(.65,0,.35,1)' },
      { strokeDashoffset: 0, opacity: 1, offset: 480 / 1700 },
      { strokeDashoffset: 0, opacity: 1, offset: 1380 / 1700, easing: 'cubic-bezier(.7,0,.84,0)' },
      { strokeDashoffset: -L, opacity: 1 },
    ], { duration: 1700, delay: golpe, fill: 'backwards' });
    llega = golpe + 480;
  }
  luego(golpe, () => { rota.classList.add('rota'); papelDiagrama.classList.add('danado'); });
  anima(con, [{ clipPath: 'inset(0 0 0 100%)' }, { clipPath: 'inset(0 0 0 0)' }], { duration: 460, delay: llega, easing: 'cubic-bezier(.16,1,.3,1)' });
  anima(prueba, [{ clipPath: 'inset(0 100% 0 0)' }, { clipPath: 'inset(0 0 0 0)' }], { duration: 360, delay: llega + 380, easing: 'cubic-bezier(.16,1,.3,1)' });
}
marcarPieza(interruptores[0].dataset.pieza);
interruptores.forEach((b) => b.addEventListener('click', () => {
  if (b.getAttribute('aria-checked') === 'true') return;
  interruptores.forEach((x) => x.setAttribute('aria-checked', String(x === b)));
  const panel = $(`[data-panel="${b.dataset.falla}"]`);
  $$('[data-panel]').forEach((p) => { p.hidden = p !== panel; });
  // En móvil, que se vea lo que rompió: el diagrama sube a la vista si quedó abajo
  if (innerWidth <= 760 && diagrama.getBoundingClientRect().top > innerHeight - 120) diagrama.scrollIntoView({ behavior: reducido ? 'auto' : 'smooth', block: 'start' });
  propagar(panel, b.dataset.pieza);
}));
new IntersectionObserver(([e], o) => {
  if (!e.isIntersecting) return;
  const b = interruptores.find((x) => x.getAttribute('aria-checked') === 'true');
  propagar($(`[data-panel="${b.dataset.falla}"]`), b.dataset.pieza);
  o.disconnect();
}, { threshold: 0.6 }).observe(diagrama);
// Flechas entre interruptores (el foco se mueve; Espacio o Enter encienden)
$('.interruptores').addEventListener('keydown', (e) => {
  const i = interruptores.indexOf(document.activeElement);
  if (i < 0 || !['ArrowDown', 'ArrowUp', 'ArrowRight', 'ArrowLeft'].includes(e.key)) return;
  e.preventDefault();
  interruptores[(i + (['ArrowDown', 'ArrowRight'].includes(e.key) ? 1 : interruptores.length - 1)) % interruptores.length].focus();
});

// ================================================================ hallazgos: el antes se tacha y entra el después al verse
if ('IntersectionObserver' in window && !reducido) {
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('visto'); io.unobserve(e.target); } }), { threshold: 0.5 });
  $$('.tarjeta').forEach((t) => io.observe(t));
} else $$('.tarjeta').forEach((t) => t.classList.add('visto'));

// ================================================================ pósteres: se piden al acercarse (no compiten con el JS en redes lentas)
const ioPoster = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.poster = e.target.dataset.poster; ioPoster.unobserve(e.target); } }), { rootMargin: '800px 0px' });
$$('video[data-poster]').forEach((v) => ioPoster.observe(v));

// ================================================================ videos: todos a la vez, cada uno con su pausa
const videos = $$('[data-video]');
function rotular(v) {
  const b = v.parentElement.querySelector('[data-pausa]');
  const cap = b.getAttribute('aria-label').replace(/^(Pausar|Reproducir): /, '');
  b.textContent = v.paused ? 'Reproducir' : 'Pausar';
  b.setAttribute('aria-label', `${v.paused ? 'Reproducir' : 'Pausar'}: ${cap}`);
}
videos.forEach((v) => {
  // Los últimos 6 s en bucle, donde ya hay salida en pantalla (el póster es el final): nunca un recuadro vacío
  const tramo = () => { v.currentTime = Math.max(0, v.duration - 6); };
  v.addEventListener('loadedmetadata', tramo, { once: true });
  v.addEventListener('ended', () => { tramo(); v.play().catch(() => {}); });
  v.addEventListener('play', () => rotular(v));
  v.addEventListener('pause', () => rotular(v));
  v.parentElement.querySelector('[data-pausa]').addEventListener('click', () => { v.dataset.manual = '1'; v.paused ? v.play().catch(() => {}) : v.pause(); });
});
if ('IntersectionObserver' in window) {
  new IntersectionObserver(([e]) => {
    videos.forEach((v) => {
      if (e.isIntersecting && !reducido && !v.dataset.manual) {
        v.play().catch(() => {});
      }
      if (!e.isIntersecting && !v.paused) v.pause();
    });
  }, { threshold: 0.5 }).observe($('.videos'));
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

// Lo que se tocó antes de que cargara el JS se atiende ahora (solo lo último)
window.__listo = true;
const pendiente = window.__cola?.pop();
if (pendiente) { if (pendiente.tagName === 'FORM') pendiente.requestSubmit(); else pendiente.click(); }
