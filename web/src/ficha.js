// Fichas, hallazgos y 404: piezas compartidas y el rótulo de la falla a todo el ancho.
import './comun.js';

// El rótulo de la ficha va de borde a borde: se mide el texto real (no una estimación) y se escala.
const h1 = document.querySelector('h1.rotulo--ficha[data-nombre-falla]');
function ajustar() {
  h1.style.fontSize = '';
  const r = document.createRange();
  r.selectNodeContents(h1);
  const ancho = r.getBoundingClientRect().width;
  const base = parseFloat(getComputedStyle(h1).fontSize);
  const tope = Math.min(innerHeight * 0.26, 280);
  if (ancho > 0) h1.style.fontSize = `${Math.min(base * (h1.clientWidth / ancho) * 0.985, tope)}px`;
}
if (h1) { ajustar(); document.fonts.ready.then(ajustar); addEventListener('resize', ajustar); }
