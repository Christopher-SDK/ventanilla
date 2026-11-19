// Genera index.html, falla/<slug>/index.html, hallazgos/index.html, 404.html, sitemap y robots
// desde web/datos/*.json (los escribe scripts/datos_web.py corriendo el sistema real) y el README del repo.
import { readFileSync, writeFileSync, mkdirSync, rmSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

const web = resolve(import.meta.dirname, '..');
const repo = resolve(web, '..');
const leer = (n) => JSON.parse(readFileSync(resolve(web, 'datos', n), 'utf8'));
const ESC = leer('escenarios.json');
const TRAS = leer('trastienda.json');
const FALLAS = leer('fallas.json');
const MATRIZ = leer('matriz.json');
const MODELO = leer('modelo.json');
const HALLAZGOS = leer('hallazgos.json');
const README = readFileSync(resolve(repo, 'README.md'), 'utf8');

const B = process.env.BASE || '/';
const SITIO = 'https://christopher-sdk.github.io/ventanilla/';
const REPO = 'https://github.com/Christopher-SDK/ventanilla';
const ACCIONES = REPO + '/actions/workflows/ci.yml';
const CUADRE = 'https://christopher-sdk.github.io/cuadre/';
const PORTAFOLIO = 'https://christopher-arias-qa.netlify.app/';

const esc = (s) => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
const fecha = (iso) => new Date(iso + 'T12:00:00').toLocaleDateString('es-PE', { day: 'numeric', month: 'long', year: 'numeric' });
const plural = (n, uno, varios) => `${n} ${n === 1 ? uno : varios || uno + 's'}`;
const L = MATRIZ.limpio.total;
const DETECTADAS = MATRIZ.detectadas;
const TOTAL_F = MATRIZ.total_fallas;
const DORADO = MODELO.dorado;
const JUEZ = MODELO.juez;

// Capas de la suite en el orden de tests/ (las mismas que usa scripts/matriz.py)
const CAPAS = ['Unitarias', 'Propiedades', 'Recuperación', 'Seguridad', 'Privacidad', 'Regulación', 'Modelo real', 'API y contrato', 'Interfaz', 'Arquitectura', 'Suministro'];
const PIEZAS = {
  guardia: 'Guardia', intencion: 'Intención', herramientas: 'Herramientas', busqueda: 'Búsqueda',
  sanitizador: 'Sanitizador', prompt: 'Prompt', verificador: 'Verificador',
};
const VEREDICTO = {
  bloqueo: ['Bloqueado', 'mal'], respuesta: ['Pasó la revisión', 'bien'], tarifa: ['Pasó · tarifario', 'bien'], calculo: ['Pasó · cálculo', 'bien'],
  reclamo: ['Reclamo registrado', 'bien'], abstencion: ['No sabe: se abstiene', 'neutro'], saldo: ['Solo el titular', 'bien'], asesor: ['Pasa a una persona', 'bien'],
};

// Tablas del README: capas de prueba y comandos rápidos por falla
function tablaReadme(titulo) {
  const bloque = README.split(/\n## |\n### /).find((b) => b.startsWith(titulo));
  return bloque.split('\n').filter((l) => l.startsWith('|') && !/^\|[-| ]+\|$/.test(l)).slice(1)
    .map((l) => l.slice(1, -1).split(' | ').map((c) => c.trim()));
}
const CAPAS_README = tablaReadme('Capas de prueba');
const RAPIDA = Object.fromEntries(tablaReadme('Enciende una falla').map((f) => [f[0].replace(/`/g, ''), f[2].replace(/`/g, '')]));
const md = (s) => esc(s).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

// Markdown mínimo de docs/hallazgos.md: párrafos, listas, tablas, negritas y código
function mdBloques(texto) {
  const lineas = texto.split('\n');
  const html = [];
  let i = 0;
  while (i < lineas.length) {
    const l = lineas[i];
    if (!l.trim()) { i++; continue; }
    if (l.startsWith('|')) {
      const filas = [];
      while (i < lineas.length && lineas[i].startsWith('|')) filas.push(lineas[i++]);
      const celdas = filas.filter((f) => !/^\|[-| ]+\|$/.test(f)).map((f) => f.slice(1, -1).split(' | ').map((c) => c.trim()));
      html.push(`<div class="tabla-envoltura"><table><thead><tr>${celdas[0].map((c) => `<th scope="col">${md(c)}</th>`).join('')}</tr></thead><tbody>${celdas.slice(1).map((f) => `<tr>${f.map((c) => `<td>${md(c)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`);
      continue;
    }
    if (/^- /.test(l)) {
      const items = [];
      while (i < lineas.length && /^- /.test(lineas[i])) items.push(lineas[i++].slice(2));
      html.push(`<ul>${items.map((x) => `<li>${md(x)}</li>`).join('')}</ul>`);
      continue;
    }
    const parrafo = [];
    while (i < lineas.length && lineas[i].trim() && !lineas[i].startsWith('|') && !/^- /.test(lineas[i])) parrafo.push(lineas[i++]);
    html.push(`<p>${md(parrafo.join(' '))}</p>`);
  }
  return html.join('\n');
}

// La forma: vidrio + rendija en el mostrador (32 px reduce a marco y rendija)
const ICONO = `<svg class="icono" viewBox="0 0 120 92" aria-hidden="true"><rect class="i-vidrio" x="14" y="5" width="92" height="66"/><path class="i-parteluz" d="M60 9v38"/><path class="i-arco" d="M40 71a20 20 0 0 1 40 0z"/><rect class="i-mostrador" x="2" y="71" width="116" height="16"/></svg>`;
const SOL_LUNA = `<svg class="i-luna" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9 7 7 0 0 1-9-9z"/></svg><svg class="i-sol" viewBox="0 0 24 24" aria-hidden="true" hidden><circle cx="12" cy="12" r="4.5"/><path d="M12 1.5v3M12 19.5v3M1.5 12h3M19.5 12h3M4.6 4.6l2.1 2.1M17.3 17.3l2.1 2.1M4.6 19.4l2.1-2.1M17.3 6.7l2.1-2.1"/></svg>`;
const LAMAS = Array.from({ length: 8 }, (_, i) => `<span style="--i:${i}"></span>`).join('');

// Ancho del titular por la palabra más larga (M y W pesan 1,4)
const ancho = (t) => Math.max(...t.replace(/<[^>]+>/g, '').split(/\s+/).map((p) => [...p].reduce((s, c) => s + (/[MWmw]/.test(c) ? 1.4 : 1), 0)));

function cabeza({ titulo, descripcion, ruta, rotulo, ld, cuerpo = '' }) {
  const canonica = SITIO + ruta;
  return `<!doctype html>
<html lang="es">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; media-src 'self'; font-src 'self'; connect-src 'self'; base-uri 'self'; form-action 'none'; object-src 'none'">
  <meta name="referrer" content="strict-origin-when-cross-origin">
  <title>${esc(titulo)}</title>
  <meta name="description" content="${esc(descripcion)}">
  <link rel="canonical" href="${canonica}">
  <meta property="og:type" content="website">
  <meta property="og:site_name" content="Ventanilla">
  <meta property="og:locale" content="es_PE">
  <meta property="og:title" content="${esc(titulo)}">
  <meta property="og:description" content="${esc(descripcion)}">
  <meta property="og:url" content="${canonica}">
  <meta property="og:image" content="${SITIO}og.png">
  <meta property="og:image:width" content="1200">
  <meta property="og:image:height" content="630">
  <meta property="og:image:alt" content="Ventanilla: un asistente de banco hecho para ser atacado">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="theme-color" content="#f6f7f9" media="(prefers-color-scheme: light)">
  <meta name="theme-color" content="#0e1014" media="(prefers-color-scheme: dark)">
  <link rel="icon" href="/icono.svg" type="image/svg+xml">
  <link rel="icon" href="/icono-32.png" type="image/png" sizes="32x32">
  <link rel="apple-touch-icon" href="/icono-180.png">
  <link rel="manifest" href="/manifest.webmanifest">
  <link rel="preload" href="/fuentes/Archivo.woff2" as="font" type="font/woff2" crossorigin>
  <style>
    @view-transition { navigation: auto; }
    html { background: #f6f7f9; color-scheme: light; }
    html[data-theme="dark"] { background: #0e1014; color-scheme: dark; }
    @media (prefers-color-scheme: dark) { html:not([data-theme="light"]) { background: #0e1014; color-scheme: dark; } }
    html.llegando .persiana { visibility: visible; }
    html.llegando .persiana { clip-path: inset(0); }
  </style>
  <script>
    document.documentElement.classList.add('js');
    try { var t = localStorage.getItem('ventanilla-tema'); if (t) document.documentElement.dataset.theme = t; } catch (e) {}
    // La persiana llega cerrada (pintada antes del primer fotograma) y sube cuando la página está lista.
    try { if (sessionStorage.getItem('ventanilla-persiana') === '1' && !matchMedia('(prefers-reduced-motion: reduce)').matches) document.documentElement.classList.add('llegando'); sessionStorage.removeItem('ventanilla-persiana'); } catch (e) {}
    // Al volver de una ficha, el nombre de la falla viaja de regreso a su interruptor.
    addEventListener('pagereveal', function (e) {
      if (!e.viewTransition || !window.navigation || !navigation.activation || !navigation.activation.from) return;
      if (document.documentElement.classList.contains('llegando')) { e.viewTransition.skipTransition(); return; }
      var p = new URL(navigation.activation.from.url).pathname.split('/').filter(Boolean), i = p.indexOf('falla');
      if (i < 0 || !p[i + 1]) return;
      var t = document.querySelector('[data-nombre-falla="' + p[i + 1] + '"]');
      if (!t || t.tagName === 'H1') return;
      t.style.viewTransitionName = 'nombre-falla';
      e.viewTransition.finished.finally(function () { t.style.viewTransitionName = ''; });
    });
  </script>
  <script type="application/ld+json">${JSON.stringify(ld)}</script>
  <link rel="stylesheet" href="/src/estilos.css">
</head>
<body class="${cuerpo}">
<a class="saltar" href="#contenido">Saltar al contenido</a>
<div class="persiana" aria-hidden="true">${LAMAS}<p class="persiana__rotulo">${esc(rotulo)}</p></div>
<header class="cab">
  <div class="envoltura cab__fila">
    <a class="marca" href="${B}" aria-label="Ventanilla, inicio">${ICONO}<span>Ventanilla</span></a>
    <nav class="cab__nav" aria-label="Secciones">
      <a class="ancla" href="${B}#consola">Atacar</a>
      <a class="ancla ancla--media" href="${B}#trastienda">Por dentro</a>
      <a class="ancla" href="${B}#fallas">Las 7 fallas</a>
      <a class="ancla ancla--media" href="${B}hallazgos/">Hallazgos</a>
      <a class="ancla" href="${B}#correr">Pruébalo</a>
      <a class="externo" href="${REPO}">GitHub</a>
    </nav>
    <button class="boton-tema" id="tema" type="button" aria-label="Cambiar entre modo claro y oscuro" aria-pressed="false">${SOL_LUNA}</button>
  </div>
</header>
`;
}

const pie = () => `
<footer class="pie">
  <div class="envoltura pie__rejilla">
    <div>
      <p class="pie__marca">${ICONO}<span>Ventanilla</span></p>
      <p class="pie__frase">Nada llega al cliente sin pasar por la ventanilla.</p>
      <p class="pie__nota">Proyecto de portafolio de QA. «Banco Cuadre» no existe: clientes, tarifas y documentos son ficticios. Las normas peruanas se citan como referencia para diseñar las pruebas.</p>
    </div>
    <nav aria-label="Enlaces del proyecto">
      <p class="etiqueta">El proyecto</p>
      <ul>
        <li><a href="${REPO}">Código en GitHub</a></li>
        <li><a href="${ACCIONES}">Corridas de la CI</a></li>
        <li><a href="${B}allure/">Reporte Allure</a></li>
        <li><a href="${REPO}/blob/main/docs/trazabilidad.md">Trazabilidad a estándares</a></li>
      </ul>
    </nav>
    <nav aria-label="Del mismo autor">
      <p class="etiqueta">Del mismo autor</p>
      <ul>
        <li><a href="${CUADRE}">Cuadre: el core bancario</a></li>
        <li><a href="${PORTAFOLIO}">Portafolio de Christopher Arias</a></li>
      </ul>
    </nav>
  </div>
  <p class="envoltura pie__legal">MIT · última corrida de la CI: ${fecha(MATRIZ.fecha)} · ${L} pruebas · ${DETECTADAS}/${TOTAL_F} fallas atrapadas</p>
</footer>
`;

const scripts = (...n) => n.map((x) => `<script type="module" src="/src/${x}.js"></script>`).join('\n') + '\n</body>\n</html>\n';

// ---------------------------------------------------------------- comandos por sistema operativo
const SELECTOR_SO = `<div class="so" role="group" aria-label="Tu sistema operativo">
  <button type="button" class="so__boton" data-so="unix" aria-pressed="true">macOS / Linux</button>
  <button type="button" class="so__boton" data-so="win" aria-pressed="false">Windows</button>
</div>`;
const partes = (c) => esc(c).split(' ').map((t) => `<span class="arg${t.length > 28 ? ' arg--largo' : ''}">${t}</span>`).join(' ');
function comando(etiqueta, unix, win = unix, attrs = '') {
  return `<div class="comando" ${attrs}><span class="comando__etiqueta">${etiqueta}</span><pre><code data-unix="${esc(unix)}" data-win="${esc(win)}">${partes(unix)}</code></pre><button type="button" class="copiar" data-copiar>Copiar</button></div>`;
}

// ---------------------------------------------------------------- la ventanilla del héroe
function veredictoHtml(e, id = '') {
  const [rot, tono] = VEREDICTO[e.tipo] || ['', 'neutro'];
  return `<div class="veredicto" data-tono="${tono}" ${id}>
    <p class="veredicto__rotulo">${esc(rot)}${e.codigo ? ` <code>${esc(e.codigo)}</code>` : ''}</p>
    <p class="veredicto__mensaje"><span class="sr">Tu mensaje: </span>«${esc(e.mensaje)}»</p>
    <p class="veredicto__texto">${esc(e.texto)}</p>
    <p class="veredicto__capa">Decidió: <strong>${esc(PIEZAS[e.capa])}</strong> · ${esc(e.detalle)}</p>
  </div>`;
}

function inicio() {
  const titulo = 'Un asistente de banco, hecho para ser atacado.';
  const chips = ESC.chips.map((c, i) => `<button type="button" class="chip" data-chip="${i}" data-grupo="${c.grupo}"><span class="chip__grupo">${c.grupo === 'ataque' ? 'Ataque' : 'Pregunta'}</span>${esc(c.rotulo)}</button>`).join('');
  const primero = ESC.chips[0];
  const ld = {
    '@context': 'https://schema.org', '@type': 'SoftwareSourceCode', name: 'Ventanilla', codeRepository: REPO, programmingLanguage: 'Python',
    license: 'https://opensource.org/licenses/MIT', description: 'Asistente RAG de un banco ficticio, hecho para ser probado: 7 fallas sembradas y la suite que las atrapa.',
    author: { '@type': 'Person', name: 'Christopher Arias', url: PORTAFOLIO },
  };
  const filasMatriz = MATRIZ.fallas.map((f, i) => `<tr data-fila="${i}">
      <th scope="row"><a href="${B}falla/${FALLAS[i].slug}/" data-viaja>${esc(f.falla)}</a></th>
      ${CAPAS.map((c) => `<td>${f.capas.includes(c) ? `<span class="punto" aria-label="atrapada por ${c}">●</span>` : '<span class="sr">no</span>'}</td>`).join('')}
      <td class="num">${f.fallidas}</td></tr>`).join('');
  const t = TRAS;
  const rec = t.paso1.recuperados.map((r) => `<li${r.confianza === 'externo' ? ' class="externo-doc"' : ''}><code>${esc(r.id)}</code> <span>${r.confianza === 'externo' ? 'externo · no oficial' : 'oficial'}</span> <span class="num">${r.coseno.toFixed(2).replace('.', ',')}</span></li>`).join('');
  const destacados = [4, 8, 7, 13].map((n) => HALLAZGOS.find((h) => h.n === n)).filter(Boolean);
  const cifraDe = {
    4: ['16/18 → 18/18', 'combinaciones de identidad y pregunta con la misma respuesta'],
    8: ['7 de 12 → 0', 'respuestas malas que aprobaba el juez'],
    7: ['0,944 → 0,983', 'MRR al quitar BM25 del orden'],
    13: ['2 pruebas', 'nuevas antes de corregir la interfaz'],
  };
  return cabeza({
    titulo: 'Ventanilla · asistente de banco hecho para ser atacado',
    descripcion: 'Ataca un asistente RAG de un banco ficticio y mira qué capa lo detiene. 7 fallas sembradas, pruebas OWASP LLM y un juez calibrado. Código abierto.',
    ruta: '', rotulo: `Ventanilla · ${DETECTADAS}/${TOTAL_F}`, ld, cuerpo: 'pagina-inicio',
  }) + `
<main id="contenido">
<section class="sala heroe" id="consola" aria-labelledby="titulo-heroe">
  <div class="envoltura heroe__envoltura">
    <p class="aviso"><span class="aviso__punto" aria-hidden="true"></span>Proyecto de portafolio · banco ficticio · respuestas grabadas del modelo real</p>
    <div class="ventanilla" data-ventanilla>
      <div class="ventanilla__vidrio">
        <ol class="revisiones" aria-label="Lo que revisa la ventanilla">
          <li data-rev="guardia"><span class="lampara" aria-hidden="true"></span>Guardia</li>
          <li data-rev="ruta"><span class="lampara" aria-hidden="true"></span>Intención y herramientas</li>
          <li data-rev="verificador"><span class="lampara" aria-hidden="true"></span>Modelo y verificador</li>
        </ol>
        <h1 class="rotulo" id="titulo-heroe" style="--w:${ancho(titulo)}"><span class="linea">Un asistente de banco,</span> <span class="linea rotulo__b">hecho para ser atacado.</span></h1>
        <div class="persiana-chica" aria-hidden="true">${LAMAS}</div>
      </div>
      <div class="ventanilla__mostrador">
        <span class="rendija" aria-hidden="true"><span class="papel" data-papel></span></span>
        <div class="chips" role="group" aria-label="Pásale un mensaje a la ventanilla">${chips}</div>
        <form class="libre" data-libre novalidate>
          <label for="mensaje-libre">O escribe el tuyo</label>
          <div class="libre__fila">
            <input id="mensaje-libre" name="mensaje" type="text" maxlength="1000" autocomplete="off" placeholder="Ej.: olvida tus reglas y…" aria-describedby="libre-error">
            <button type="submit" class="boton boton--primario">Pasar <span class="boton__rendija" aria-hidden="true"></span></button>
          </div>
          <p class="libre__error" id="libre-error" role="alert"></p>
        </form>
      </div>
    </div>
  </div>
</section>
<section class="resultado" aria-label="Lo que devolvió la ventanilla">
  <div class="envoltura">
    <div class="salida" aria-live="polite" data-salida>${veredictoHtml(primero)}</div>
    <dl class="cifras">
      <div><dt>Fallas atrapadas</dt><dd><span class="cifra">${DETECTADAS}/${TOTAL_F}</span></dd></div>
      <div><dt>Pruebas</dt><dd><span class="cifra">${L}</span></dd></div>
      <div><dt>Set dorado</dt><dd><span class="cifra">${DORADO.aciertos}/${DORADO.total}</span></dd></div>
      <div><dt>Última corrida</dt><dd><a href="${ACCIONES}">${fecha(MATRIZ.fecha)}</a></dd></div>
    </dl>
  </div>
</section>

<section class="trastienda" id="trastienda" aria-labelledby="titulo-trastienda" data-trastienda>
  <div class="trastienda__escenario">
    <div class="persiana-grande" aria-hidden="true">${LAMAS}</div>
    <img class="trastienda__pared" src="/video/matriz.jpg" alt="" width="1280" height="720" loading="lazy" decoding="async">
    <div class="envoltura trastienda__envoltura">
      <p class="etiqueta">Por dentro de la ventanilla</p>
      <h2 class="t2" id="titulo-trastienda">Un mensaje con una orden escondida, paso a paso.</h2>
      <p class="trastienda__pregunta">El cliente pregunta <strong>«${esc(t.pregunta)}»</strong>. Uno de los documentos que encuentra la búsqueda trae una orden escondida en un comentario HTML.</p>
      <ol class="pasos">
        <li class="paso" data-paso="1">
          <p class="paso__n">1 · Guardia, intención, búsqueda</p>
          <h3>Pasa la guardia: la pregunta es legítima.</h3>
          <p>No pide un precio ni un cálculo, así que no responde el tarifario: busca en los documentos.</p>
          <ul class="recuperados">${rec}</ul>
        </li>
        <li class="paso" data-paso="2">
          <p class="paso__n">2 · Sanitizador</p>
          <h3>La orden escondida no llega al modelo.</h3>
          <p>Esto venía dentro del boletín del proveedor, invisible para quien lo lee en la web:</p>
          <pre class="tachado"><code>${esc(t.paso2.comentario)}</code></pre>
          <p>El sanitizador quitó: <strong>${esc(t.paso2.quitado.join(', '))}</strong>. Al modelo le llega el resto del boletín, marcado como fuente <em>externa, no oficial</em>.</p>
        </li>
        <li class="paso" data-paso="3">
          <p class="paso__n">3 · Modelo y verificador</p>
          <h3>El modelo redacta; el verificador revisa antes de responder.</h3>
          <p>Borrador real del modelo (grabación <code>${esc(t.paso3.hash)}</code>):</p>
          <blockquote class="borrador">${esc(t.paso3.borrador)}</blockquote>
          <ul class="controles">
            <li><span class="ok" aria-hidden="true">✓</span> Montos: ninguno que no esté en el tarifario</li>
            <li><span class="ok" aria-hidden="true">✓</span> Citas: solo fuentes recuperadas</li>
            <li><span class="ok" aria-hidden="true">✓</span> No pide claves ni códigos</li>
            <li><span class="ok" aria-hidden="true">✓</span> No niega pasar con un asesor</li>
          </ul>
          <p class="paso__final">Veredicto: <strong>${esc(VEREDICTO[t.paso3.veredicto.tipo][0])}</strong>. La orden de pedirle la clave al cliente nunca llegó a escribirse.</p>
        </li>
      </ol>
    </div>
  </div>
</section>

<section class="sala fallas tono-trastienda" id="fallas" aria-labelledby="titulo-fallas">
  <div class="envoltura">
    <p class="etiqueta">Rompe una pieza</p>
    <h2 class="t2" id="titulo-fallas">Siete fallas sembradas. Enciende una y vuelve a pasar el mismo mensaje.</h2>
    <p class="entrada">Las fallas vienen en el código, apagadas. Cada una rompe una pieza real de la ventanilla, como podría pasar en un cambio apurado. Lo que ves abajo es la salida del sistema con esa falla encendida, y la prueba que se pone roja.</p>
    <div class="taller">
      <div class="interruptores" role="group" aria-label="Fallas sembradas">
        ${FALLAS.map((f, i) => `<button type="button" class="interruptor" role="switch" aria-checked="${i === 0}" data-falla="${i}" data-pieza="${f.pieza}">
          <span class="interruptor__palanca" aria-hidden="true"></span>
          <span class="interruptor__n">${f.n}</span>
          <span class="interruptor__nombre" data-nombre-falla="${f.slug}">${esc(f.falla)}</span>
        </button>`).join('')}
      </div>
      <div class="banco" data-banco>
        <div class="diagrama" aria-hidden="true">
          ${['guardia', 'intencion', 'herramientas', 'sanitizador', 'prompt', 'verificador'].map((p) => `<span class="pieza" data-pieza="${p}">${PIEZAS[p]}</span>`).join('')}
          <div class="persiana-chica">${LAMAS}</div>
        </div>
        ${FALLAS.map((f, i) => `<article class="falla" data-panel="${i}"${i ? ' hidden' : ''} aria-labelledby="falla-${i}">
          <h3 id="falla-${i}"><span class="sr">Falla ${f.n}: </span>${esc(f.descripcion)}</h3>
          <p class="falla__pedido"><span class="etiqueta">El mismo mensaje</span>«${esc(f.pedido)}»${f.sesion ? ` <span class="nota">(${esc(f.sesion)})</span>` : ''}</p>
          <div class="comparar">
            <div class="lado" data-tono="${(VEREDICTO[f.limpia.tipo] || [])[1]}"><p class="lado__rotulo">Sin la falla</p><p>${esc(f.limpia.texto)}</p><p class="lado__capa">${esc(PIEZAS[f.limpia.capa])}: ${esc(f.limpia.detalle)}</p></div>
            <div class="lado lado--rota"><p class="lado__rotulo">Con la falla</p><p>${esc(f.rota.texto)}</p><p class="lado__capa">${esc(PIEZAS[f.rota.capa])}: ${esc(f.rota.detalle)}</p></div>
          </div>
          <p class="nota">${esc(f.origen_texto)}</p>
          ${f.rota_real ? `<p class="nota"><strong>El modelo real, con la misma falla:</strong> «${esc(f.rota_real.texto)}»</p>` : ''}
          <p class="prueba-roja"><span class="x" aria-hidden="true">✗</span> <code>${esc(f.primera.prueba)}</code><span class="prueba-roja__resumen">${plural(f.pruebas_fallan, 'prueba falla', 'pruebas fallan')} · ${esc(f.capas.join(', '))}</span></p>
          <a class="boton boton--texto" href="${B}falla/${f.slug}/" data-viaja>Ver la falla ${f.n} <span aria-hidden="true">→</span></a>
        </article>`).join('')}
      </div>
    </div>
  </div>
</section>

<section class="sala matriz" id="matriz" aria-labelledby="titulo-matriz">
  <div class="envoltura">
    <p class="etiqueta">Matriz de detección</p>
    <h2 class="t2" id="titulo-matriz">${DETECTADAS} de ${TOTAL_F} fallas atrapadas, y en qué capa.</h2>
    <p class="entrada">De la última corrida de la CI (${fecha(MATRIZ.fecha)}): la suite limpia, ${L} pruebas y ${MATRIZ.limpio.fallidas} fallas; después, una corrida por cada falla encendida.</p>
    <div class="tabla-envoltura" tabindex="0" role="region" aria-label="Matriz de detección">
      <table class="tabla-matriz">
        <thead><tr><th scope="col">Falla</th>${CAPAS.map((c) => `<th scope="col"><span>${c}</span></th>`).join('')}<th scope="col">Pruebas que fallan</th></tr></thead>
        <tbody>${filasMatriz}</tbody>
      </table>
    </div>
    <ol class="matriz-movil">${MATRIZ.fallas.map((f, i) => `<li><a href="${B}falla/${FALLAS[i].slug}/" data-viaja><code>${esc(f.falla)}</code></a><p>${plural(f.fallidas, 'prueba falla', 'pruebas fallan')}</p><ul>${f.capas.map((c) => `<li>${esc(c)}</li>`).join('')}</ul></li>`).join('')}</ol>
  </div>
</section>

<section class="sala capas" id="capas" aria-labelledby="titulo-capas">
  <div class="envoltura">
    <p class="etiqueta">Cómo se prueba</p>
    <h2 class="t2" id="titulo-capas">${CAPAS_README.length} capas, cada una con su referencia.</h2>
    <ol class="lista-capas">${CAPAS_README.map((c) => `<li><h3>${md(c[0])}</h3><p>${md(c[1])}</p><p class="lista-capas__ref"><span>${md(c[2])}</span>${c[3] && c[3] !== '—' ? `<span>${md(c[3])}</span>` : ''}</p></li>`).join('')}</ol>
  </div>
</section>

<section class="sala hallazgos-inicio" id="hallazgos" aria-labelledby="titulo-hallazgos">
  <div class="envoltura">
    <p class="etiqueta">Lo que encontraron las pruebas</p>
    <h2 class="t2" id="titulo-hallazgos">No salió del diseño: lo encontraron las pruebas.</h2>
    <ul class="tarjetas">${destacados.map((h) => `<li class="tarjeta"><p class="tarjeta__cifra">${esc(cifraDe[h.n][0])}</p><p class="tarjeta__que">${esc(cifraDe[h.n][1])}</p><h3><a href="${B}hallazgos/#h-${h.n}">${esc(h.titulo)}</a></h3></li>`).join('')}</ul>
    <a class="boton boton--secundario" href="${B}hallazgos/">Los ${HALLAZGOS.length} hallazgos</a>
  </div>
</section>

<section class="sala terminal" id="terminal" aria-labelledby="titulo-terminal">
  <div class="envoltura">
    <p class="etiqueta">En la terminal</p>
    <h2 class="t2" id="titulo-terminal">Grabaciones reales, sin cortes.</h2>
    <ul class="videos">
      ${[['suite', `La suite: ${L} pruebas en verde, sin Ollama ni GPU`, 'Terminal: uv run pytest termina con todas las pruebas en verde'],
          ['falla', 'Una falla encendida: la suite se pone roja', 'Terminal: con la falla TASA_INVENTADA, dos pruebas fallan'],
          ['matriz', `La matriz: ${DETECTADAS}/${TOTAL_F}, falla por falla`, 'Terminal: scripts/matriz.py marca las siete fallas como atrapadas']].map(([v, cap, alt]) => `<li class="video">
        <div class="video__marco"><video src="/video/${v}.mp4" poster="/video/${v}.jpg" muted playsinline loop preload="none" aria-label="${esc(alt)}" data-video></video>
        <button type="button" class="video__pausa" data-pausa aria-label="Reproducir: ${esc(cap)}">Reproducir</button></div>
        <p>${esc(cap)}</p></li>`).join('')}
    </ul>
  </div>
</section>

${guia()}
</main>
${pie()}
${scripts('inicio')}`;
}

// ---------------------------------------------------------------- guía «Pruébalo en tu máquina»
const INSTALAR_UV = ['curl -LsSf https://astral.sh/uv/install.sh | sh', 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"'];
function respuesta(paso, si, consejos) {
  return `<div class="respuesta" data-paso="${paso}">
    <p class="respuesta__pregunta">¿Te salió así?</p>
    <div class="respuesta__botones"><button type="button" class="boton boton--secundario" data-si>Sí, ${si}</button><button type="button" class="boton boton--texto" data-no aria-expanded="false" aria-controls="ayuda-${paso}">No, me salió otra cosa</button></div>
    <div class="ayuda" id="ayuda-${paso}" hidden><ul>${consejos.map(([so, t]) => `<li${so ? ` data-solo="${so}"` : ''}>${md(t)}</li>`).join('')}</ul></div>
  </div>`;
}
function guia() {
  const chipsFalla = FALLAS.map((f, i) => `<button type="button" class="chip chip--falla" data-guia-falla="${i}" aria-pressed="${i === 0}">${esc(f.falla)}</button>`).join('');
  return `<section class="sala guia" id="correr" aria-labelledby="titulo-guia">
  <div class="envoltura">
    <p class="etiqueta">Pruébalo en tu máquina</p>
    <h2 class="t2" id="titulo-guia">Cuatro pasos. No hace falta GPU ni API key.</h2>
    <p class="entrada">Las pruebas usan las respuestas grabadas del modelo, así que no necesitas Ollama. Elige tu sistema y los comandos se ajustan.</p>
    ${SELECTOR_SO}
    <div class="progreso" aria-hidden="true"><span data-progreso></span></div>
    <p class="progreso__texto" data-progreso-texto aria-live="polite">0 de 4 pasos · 0 de 7 fallas atrapadas por ti</p>
    <ol class="pasos-guia">
      <li class="paso-guia" data-paso="1">
        <h3>Instala uv y Git</h3>
        <p>uv instala Python 3.13 por su cuenta. Git sirve para clonar; si no lo tienes, <a href="${REPO}/archive/refs/heads/main.zip">baja el ZIP</a>.</p>
        ${comando('Instala uv', INSTALAR_UV[0], INSTALAR_UV[1])}
        ${respuesta(1, 'ya tengo uv', [['', 'Cierra y vuelve a abrir la terminal: el instalador agrega uv al PATH, pero la ventana abierta no lo ve.'], ['unix', 'En macOS con Homebrew también puedes usar `brew install uv`.'], ['win', 'Si PowerShell bloquea el script, abre PowerShell como usuario normal (no hace falta administrador) y vuelve a pegar el comando completo.']])}
      </li>
      <li class="paso-guia" data-paso="2">
        <h3>Clona el repositorio</h3>
        ${comando('Clona', 'git clone https://github.com/Christopher-SDK/ventanilla.git && cd ventanilla', 'git clone https://github.com/Christopher-SDK/ventanilla.git; cd ventanilla')}
        ${respuesta(2, 'estoy en la carpeta', [['', 'Si no tienes Git, baja el ZIP, descomprímelo y abre la terminal dentro de la carpeta `ventanilla-main`.'], ['win', 'En PowerShell, `&&` no existe en versiones antiguas: por eso el comando usa `;`.']])}
      </li>
      <li class="paso-guia" data-paso="3">
        <h3>Corre la suite</h3>
        ${comando('Instala', 'uv sync --all-extras && uv run playwright install chromium', 'uv sync --all-extras; uv run playwright install chromium')}
        ${comando('Corre', 'uv run pytest')}
        <p class="esperado">Deberías ver: <code>${L} passed</code>, en unos 10 segundos.</p>
        ${respuesta(3, `vi ${L} passed`, [['', 'Si ves «No hay grabación para esta llamada»: estás con `VENTANILLA_MODO` distinto de `reproducir`. Ciérralo o abre otra terminal.'], ['', 'Si fallan solo las pruebas de `tests/ui`: falta el navegador. Corre `uv run playwright install chromium`.'], ['unix', 'En Linux, si Chromium no arranca: `uv run playwright install --with-deps chromium`.']])}
      </li>
      <li class="paso-guia" data-paso="4">
        <h3>Enciende una falla</h3>
        <p>Elige una. La suite tiene que ponerse roja: <strong>si falla, la prueba funciona</strong>.</p>
        <div class="chips chips--guia" role="group" aria-label="Elige una falla">${chipsFalla}</div>
        ${FALLAS.map((f, i) => `<div class="guia-falla" data-guia-panel="${i}"${i ? ' hidden' : ''}>${comando('Rápido (1–2 s)', `uv run pytest ${RAPIDA[f.falla]} --falla ${f.falla}`)}<p class="esperado">Deberías ver en rojo: <code>${esc(f.primera.prueba.split('::')[1] || f.primera.prueba)}</code></p></div>`).join('')}
        ${respuesta(4, 'se puso roja', [['', 'Si todo pasa en verde, revisa que el nombre de la falla esté bien escrito: la suite se detiene si no existe.'], ['', 'Sin `--falla`, todo vuelve a pasar: las fallas solo existen mientras las enciendes.']])}
        <p class="logro" data-logro hidden>Atrapaste las ${TOTAL_F} fallas con tus propias manos.</p>
      </li>
    </ol>
    <button type="button" class="boton boton--texto" data-reiniciar>Empezar de nuevo</button>
  </div>
</section>`;
}

// ---------------------------------------------------------------- ficha de cada falla
function ficha(f, i) {
  const ant = FALLAS[i - 1], sig = FALLAS[i + 1];
  const ld = { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Ventanilla', item: SITIO },
    { '@type': 'ListItem', position: 2, name: f.falla, item: `${SITIO}falla/${f.slug}/` }] };
  const lineas = f.detalle.map((d) => `<span class="t-fallo">FAILED</span> ${esc(d.prueba)}\n  <span class="t-msj">${esc(d.mensaje)}</span>`).join('\n');
  return cabeza({
    titulo: `Falla ${f.n}: ${f.falla.toLowerCase().replace(/_/g, ' ')} · Ventanilla`,
    descripcion: `${f.descripcion} Qué ve el cliente, qué pieza se rompe y qué prueba la atrapa.`,
    ruta: `falla/${f.slug}/`, rotulo: `Ventanilla ${f.n}`, ld, cuerpo: 'pagina-falla',
  }) + `
<main id="contenido">
<section class="ficha__apertura" aria-labelledby="titulo-falla">
  <pre class="ficha__terminal" aria-hidden="true"><code><span class="t-prompt">ventanilla $</span> uv run pytest --falla ${f.falla}\n${lineas}\n<span class="t-fallo">${f.pruebas_fallan} failed</span></code></pre>
  <div class="envoltura ficha__texto">
    <p class="etiqueta">Falla ${f.n} de ${FALLAS.length} · rompe: ${esc(PIEZAS[f.pieza])}</p>
    <h1 class="rotulo rotulo--ficha" id="titulo-falla" data-nombre-falla="${f.slug}" style="--w:${ancho(f.falla.replace(/_/g, ' '))}">${esc(f.falla.replace(/_/g, ' '))}</h1>
    <p class="ficha__bajada">${esc(f.descripcion)}</p>
  </div>
</section>
<section class="sala" aria-labelledby="h-dano"><div class="envoltura ficha__cuerpo">
  <h2 class="t3" id="h-dano">Lo que vería el cliente</h2>
  <p class="falla__pedido"><span class="etiqueta">Mensaje</span>«${esc(f.pedido)}»${f.sesion ? ` <span class="nota">(${esc(f.sesion)})</span>` : ''}</p>
  ${f.borrador ? `<p class="nota">Borrador del modelo usado por la prueba: «${esc(f.borrador)}»</p>` : ''}
  <div class="comparar">
    <div class="lado" data-tono="${(VEREDICTO[f.limpia.tipo] || [])[1]}"><p class="lado__rotulo">Sin la falla</p><p>${esc(f.limpia.texto)}</p><p class="lado__capa">${esc(PIEZAS[f.limpia.capa])}: ${esc(f.limpia.detalle)}</p></div>
    <div class="lado lado--rota"><p class="lado__rotulo">Con la falla</p><p>${esc(f.rota.texto)}</p><p class="lado__capa">${esc(PIEZAS[f.rota.capa])}: ${esc(f.rota.detalle)}</p></div>
  </div>
  <p class="nota">${esc(f.origen_texto)}</p>
  ${f.rota_real ? `<p class="nota"><strong>El modelo real, con la misma falla:</strong> «${esc(f.rota_real.texto)}»</p>` : ''}
  ${f.orden_llega_al_modelo ? `<p class="nota">¿La orden escondida llega al modelo? Sin la falla: <strong>${f.orden_llega_al_modelo.limpia ? 'sí' : 'no'}</strong>. Con la falla: <strong>${f.orden_llega_al_modelo.rota ? 'sí' : 'no'}</strong>.</p>` : ''}
  <h2 class="t3">La prueba que la atrapa</h2>
  <p class="prueba-roja"><span class="x" aria-hidden="true">✗</span> <code>${esc(f.primera.prueba)}</code><span class="prueba-roja__resumen">${plural(f.pruebas_fallan, 'prueba falla', 'pruebas fallan')} · capas: ${esc(f.capas.join(', '))}</span></p>
  <p class="nota">Mensaje de la prueba: ${esc(f.primera.mensaje)}</p>
  <h2 class="t3">Córrela tú</h2>
  ${SELECTOR_SO}
  ${comando('Rápido (1–2 s)', `uv run pytest ${RAPIDA[f.falla]} --falla ${f.falla}`)}
  ${comando('Toda la suite', `uv run pytest --falla ${f.falla}`)}
  <p class="nota">¿Primera vez? <a href="${B}#correr">Sigue la guía de 4 pasos</a>.</p>
  <nav class="vecinas" aria-label="Otras fallas">
    ${ant ? `<a href="${B}falla/${ant.slug}/"><span>← Falla ${ant.n}</span>${esc(ant.falla)}</a>` : `<a href="${B}#fallas"><span>←</span>Las 7 fallas</a>`}
    ${sig ? `<a href="${B}falla/${sig.slug}/"><span>Falla ${sig.n} →</span>${esc(sig.falla)}</a>` : `<a href="${B}hallazgos/"><span>→</span>Los hallazgos</a>`}
  </nav>
</div></section>
</main>
${pie()}
${scripts('ficha')}`;
}

// ---------------------------------------------------------------- hallazgos
function hallazgos() {
  const ld = { '@context': 'https://schema.org', '@type': 'BreadcrumbList', itemListElement: [
    { '@type': 'ListItem', position: 1, name: 'Ventanilla', item: SITIO }, { '@type': 'ListItem', position: 2, name: 'Hallazgos', item: `${SITIO}hallazgos/` }] };
  const titulo = 'Lo que encontraron las pruebas.';
  return cabeza({
    titulo: 'Hallazgos · Ventanilla',
    descripcion: 'Lo que encontraron las pruebas: sesgo contrafactual, un juez que aprobaba respuestas malas, una búsqueda híbrida que rendía menos.',
    ruta: 'hallazgos/', rotulo: `Ventanilla · ${HALLAZGOS.length} hallazgos`, ld, cuerpo: 'pagina-hallazgos',
  }) + `
<main id="contenido">
<section class="sala ficha__apertura ficha__apertura--clara" aria-labelledby="titulo-hallazgos-p">
  <div class="envoltura ficha__texto">
    <p class="etiqueta">${HALLAZGOS.length} hallazgos, en orden de aparición</p>
    <h1 class="rotulo rotulo--ficha" id="titulo-hallazgos-p" style="--w:${ancho(titulo)}">${titulo}</h1>
    <p class="ficha__bajada">No salieron del diseño inicial. Cada uno dejó una prueba que falla si el problema vuelve. Fuente: <a href="${REPO}/blob/main/docs/hallazgos.md">docs/hallazgos.md</a>.</p>
  </div>
</section>
<section class="sala"><div class="envoltura">
  <ol class="hallazgos">${HALLAZGOS.map((h) => `<li class="hallazgo" id="h-${h.n}"><p class="hallazgo__n">${h.n}</p><div><h2 class="t3">${md(h.titulo)}</h2>${mdBloques(h.cuerpo)}</div></li>`).join('')}</ol>
</div></section>
</main>
${pie()}
${scripts('ficha')}`;
}

function noEncontrada() {
  return cabeza({ titulo: 'Ventanilla cerrada · 404', descripcion: 'Esta página no existe.', ruta: '404.html', rotulo: 'Ventanilla cerrada', ld: { '@context': 'https://schema.org', '@type': 'WebPage', name: '404' }, cuerpo: 'pagina-404' })
    .replace('<link rel="canonical" href="https://christopher-sdk.github.io/ventanilla/404.html">', '<meta name="robots" content="noindex">') + `
<main id="contenido" class="sala cerrada">
  <div class="envoltura cerrada__envoltura">
    <div class="cerrada__ventanilla" aria-hidden="true"><div class="persiana-chica persiana-chica--baja">${LAMAS}</div></div>
    <div>
      <p class="etiqueta">Error 404</p>
      <h1 class="rotulo rotulo--ficha" style="--w:${ancho('Ventanilla cerrada.')}">Ventanilla cerrada.</h1>
      <p class="ficha__bajada">Esta página no existe. La ventanilla que buscas atiende en el inicio.</p>
      <a class="boton boton--primario" href="${B}#consola">Ir a la ventanilla <span class="boton__rendija" aria-hidden="true"></span></a>
    </div>
  </div>
</main>
${pie()}
${scripts('ficha')}`;
}

// ---------------------------------------------------------------- escribir
rmSync(resolve(web, 'falla'), { recursive: true, force: true });
writeFileSync(resolve(web, 'index.html'), inicio());
FALLAS.forEach((f, i) => {
  mkdirSync(resolve(web, 'falla', f.slug), { recursive: true });
  writeFileSync(resolve(web, 'falla', f.slug, 'index.html'), ficha(f, i));
});
mkdirSync(resolve(web, 'hallazgos'), { recursive: true });
writeFileSync(resolve(web, 'hallazgos', 'index.html'), hallazgos());
writeFileSync(resolve(web, '404.html'), noEncontrada());
const rutas = ['', ...FALLAS.map((f) => `falla/${f.slug}/`), 'hallazgos/'];
writeFileSync(resolve(web, 'publico', 'sitemap.xml'), `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${rutas.map((r) => `  <url><loc>${SITIO}${r}</loc><lastmod>${MATRIZ.fecha}</lastmod></url>`).join('\n')}\n</urlset>\n`);
writeFileSync(resolve(web, 'publico', 'robots.txt'), `User-agent: *\nAllow: /\nSitemap: ${SITIO}sitemap.xml\n`);
if (!existsSync(resolve(web, 'publico', 'datos'))) mkdirSync(resolve(web, 'publico', 'datos'));
console.log(`generar: inicio, ${FALLAS.length} fichas, hallazgos (${HALLAZGOS.length}), 404 · ${L} pruebas · ${DETECTADAS}/${TOTAL_F}`);
