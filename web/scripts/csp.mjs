// Después de vite build: CSP y Referrer-Policy por <meta> (GitHub Pages no permite cabeceras propias).
// Cada <script> en línea que se ejecuta entra por su hash; los de datos (JSON) no se ejecutan y no lo necesitan.
import { createHash } from 'node:crypto';
import { readdirSync, readFileSync, writeFileSync, statSync } from 'node:fs';
import { join, resolve } from 'node:path';

const dist = resolve(import.meta.dirname, '..', 'dist');
const html = (d) => readdirSync(d).flatMap((n) => {
  const p = join(d, n);
  if (n === 'allure') return [];
  return statSync(p).isDirectory() ? html(p) : n.endsWith('.html') ? [p] : [];
});
let total = 0;
for (const archivo of html(dist)) {
  let s = readFileSync(archivo, 'utf8');
  const hashes = [...s.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((m) => `'sha256-${createHash('sha256').update(m[1]).digest('base64')}'`);
  const csp = [
    "default-src 'self'", `script-src 'self' ${hashes.join(' ')}`.trim(), "style-src 'self' 'unsafe-inline'", "img-src 'self' data:",
    "media-src 'self'", "font-src 'self'", "connect-src 'self'", "object-src 'none'", "base-uri 'self'", "form-action 'self'",
  ].join('; ');
  s = s.replace(/<meta http-equiv="Content-Security-Policy"[^>]*>\n?|<meta name="referrer"[^>]*>\n?/g, '');
  s = s.replace('<head>', `<head>\n  <meta http-equiv="Content-Security-Policy" content="${csp}">\n  <meta name="referrer" content="strict-origin-when-cross-origin">`);
  writeFileSync(archivo, s);
  total++;
}
console.log(`csp: ${total} páginas`);
