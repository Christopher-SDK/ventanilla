import { defineConfig } from 'vite';
import { readdirSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';

// Páginas: el inicio, una por falla y la 404 (las genera scripts/generar.mjs desde los datos del repo).
const raiz = import.meta.dirname;
const entradas = { inicio: resolve(raiz, 'index.html'), hallazgos: resolve(raiz, 'hallazgos/index.html'), noEncontrada: resolve(raiz, '404.html') };
if (existsSync(resolve(raiz, 'falla'))) {
  for (const slug of readdirSync(resolve(raiz, 'falla'))) entradas['falla-' + slug] = resolve(raiz, 'falla', slug, 'index.html');
}

export default defineConfig(({ command }) => ({
  base: command === 'build' ? '/ventanilla/' : '/',
  publicDir: 'publico',
  server: { host: '127.0.0.1' },
  build: { outDir: 'dist', emptyOutDir: true, rollupOptions: { input: entradas } },
}));
