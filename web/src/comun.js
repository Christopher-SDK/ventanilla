// Piezas compartidas: tema, scroll suave, persiana entre páginas, comandos por sistema, copiar y entradas.
import Lenis from 'lenis';
import { gsap } from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);
export { gsap, ScrollTrigger };
const raiz = document.documentElement;
export const reducido = matchMedia('(prefers-reduced-motion: reduce)').matches;
const guardar = (k, v) => { try { localStorage.setItem(k, v); } catch { /* sin almacenamiento: no se recuerda */ } };
const leerLS = (k) => { try { return localStorage.getItem(k); } catch { return null; } };

// ---------------------------------------------------------------- tema
const botonTema = document.getElementById('tema');
const oscuro = () => (raiz.dataset.theme ? raiz.dataset.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches);
function pintarTema() {
  if (!botonTema) return;
  const o = oscuro();
  botonTema.setAttribute('aria-pressed', String(o));
  botonTema.setAttribute('aria-label', o ? 'Modo oscuro activado: cambiar a modo claro' : 'Modo claro activado: cambiar a modo oscuro');
  botonTema.querySelector('.i-sol').hidden = !o;
  botonTema.querySelector('.i-luna').hidden = o;
}
botonTema?.addEventListener('click', () => { raiz.dataset.theme = oscuro() ? 'light' : 'dark'; guardar('ventanilla-tema', raiz.dataset.theme); pintarTema(); });
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', pintarTema);
pintarTema();

// ---------------------------------------------------------------- scroll suave (solo rueda; el táctil queda nativo)
export let lenis = null;
if (!reducido && matchMedia('(pointer: fine)').matches) {
  lenis = new Lenis({ lerp: 0.12 });
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}

// ---------------------------------------------------------------- persiana entre páginas (una sola familia de transición)
const persiana = document.querySelector('.persiana');
const ROTULOS = JSON.parse(document.getElementById('rotulos')?.textContent || '{}');
function subir() {
  if (!raiz.classList.contains('llegando')) return;
  raiz.classList.remove('llegando');
  persiana.classList.add('descubre');
  setTimeout(() => persiana.classList.remove('descubre'), 620);
}
if (document.readyState === 'complete') requestAnimationFrame(subir); else addEventListener('load', () => requestAnimationFrame(subir));
setTimeout(subir, 1200); // nunca queda tapada
addEventListener('pageshow', (e) => {
  if (!e.persisted) return;
  persiana.classList.remove('cubre', 'descubre'); raiz.classList.remove('llegando');
  // Al volver desde la caché, el scroll suave retoma donde está la página (si no, el primer giro de rueda salta)
  lenis?.scrollTo(scrollY, { immediate: true, force: true });
  ScrollTrigger.refresh();
});
document.addEventListener('click', (e) => {
  const a = e.target.closest('a[href]');
  if (!a || reducido || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || a.target) return;
  const url = new URL(a.href, location.href);
  if (url.origin !== location.origin || (url.pathname === location.pathname && url.hash)) return;
  if (a.hasAttribute('data-viaja') && 'startViewTransition' in document) { // el nombre de la falla viaja a su ficha
    const nombre = a.closest('[data-panel], tr')?.querySelector('[data-nombre-falla]') || document.querySelector(`.interruptor[aria-checked="true"] [data-nombre-falla]`);
    if (nombre) nombre.style.viewTransitionName = 'nombre-falla';
    return;
  }
  e.preventDefault();
  try { sessionStorage.setItem('ventanilla-persiana', '1'); } catch { /* sin almacenamiento: llega sin persiana */ }
  // El rótulo de la persiana ya dice adónde vas (no cambia en seco bajo la persiana cerrada)
  const base = new URL(document.querySelector('.marca').href).pathname;
  const destino = url.pathname.startsWith(base) ? url.pathname.slice(base.length) : '';
  persiana.querySelector('.persiana__rotulo').textContent = ROTULOS[destino] ?? 'Ventanilla';
  persiana.classList.add('cubre');
  setTimeout(() => { location.href = url.href; }, 470);
});

// ---------------------------------------------------------------- menú en móvil: se cierra al elegir o con Escape
const menu = document.querySelector('.menu-movil');
menu?.addEventListener('click', (e) => { if (e.target.closest('a')) menu.open = false; });
document.addEventListener('pointerdown', (e) => { if (menu?.open && !menu.contains(e.target)) menu.open = false; });
addEventListener('keydown', (e) => { if (e.key === 'Escape' && menu?.open) { menu.open = false; menu.querySelector('summary').focus(); } });

// ---------------------------------------------------------------- entradas al ver
export function observar(selector, alVer, margen = '0px 0px -8% 0px') {
  const piezas = document.querySelectorAll(selector);
  if (!('IntersectionObserver' in window) || reducido) { piezas.forEach((p) => { p.classList.add('visto'); alVer?.(p); }); return; }
  const io = new IntersectionObserver((es) => {
    for (const e of es) { if (!e.isIntersecting) continue; e.target.classList.add('visto'); alVer?.(e.target); io.unobserve(e.target); }
  }, { rootMargin: margen });
  piezas.forEach((p) => io.observe(p));
}
document.querySelectorAll('main .t2, main .t3, .entrada, .tarjeta, .registro li, .video, .paso-guia, .hallazgo, .ficha__bajada, .comparar, .prueba-roja').forEach((el, i, todos) => {
  if (el.closest('.heroe') || el.closest('.paso') || el.closest('[hidden]')) return;
  el.classList.add('entra');
  const hermanos = [...el.parentElement.children].filter((x) => x.classList.contains('entra'));
  el.style.setProperty('--d', Math.min(hermanos.indexOf(el), 5));
});
observar('.entra');

// ---------------------------------------------------------------- comandos según el sistema operativo
let so = leerLS('ventanilla-so') || (/Windows/i.test(navigator.userAgent) ? 'win' : 'unix');
const partes = (c) => c.split(' ').map((t) => { const s = document.createElement('span'); s.className = t.length > 28 ? 'arg arg--largo' : 'arg'; s.textContent = t; return s; });
export function aplicarSO(nuevo) {
  if (nuevo) { so = nuevo; guardar('ventanilla-so', so); }
  raiz.dataset.so = so;
  document.querySelectorAll('[data-so]').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.so === so)));
  document.querySelectorAll('code[data-unix]').forEach((c) => {
    const texto = so === 'win' ? c.dataset.win : c.dataset.unix;
    c.replaceChildren(...partes(texto).flatMap((s, i) => (i ? [document.createTextNode(' '), s] : [s])));
  });
}
document.querySelectorAll('.so__boton').forEach((b) => b.addEventListener('click', () => aplicarSO(b.dataset.so)));
aplicarSO();

// ---------------------------------------------------------------- copiar lo que se ve
document.addEventListener('click', async (e) => {
  const b = e.target.closest('[data-copiar]');
  if (!b) return;
  const texto = b.parentElement.querySelector('code').textContent.replace(/\s+/g, ' ').trim();
  try { await navigator.clipboard.writeText(texto); b.textContent = 'Copiado'; } catch { b.textContent = 'Selecciónalo'; }
  b.classList.add('hecho');
  setTimeout(() => { b.textContent = 'Copiar'; b.classList.remove('hecho'); }, 1600);
});
