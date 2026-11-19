// La guardia de Ventanilla en el navegador: misma normalización y mismas reglas que
// src/ventanilla/dominio/texto.py y guardia.py. tests/web/test_guardia_paridad.py exige veredictos idénticos.
const INVISIBLES = /[​-‏‪-‮⁠-⁤﻿­]/gu;
const LEET = { 0: 'o', 1: 'i', 3: 'e', 4: 'a', 5: 's', 7: 't', '@': 'a', $: 's' };

export function normalizar(texto, leet = false) {
  let t = texto.replace(INVISIBLES, '').normalize('NFKD').replace(/\p{M}/gu, '').toLowerCase();
  if (leet) t = t.replace(/[013457@$]/g, (c) => LEET[c]);
  return t.replace(/\s+/gu, ' ').trim();
}

function decodificados(texto) {
  const salida = [];
  for (const bloque of texto.match(/[A-Za-z0-9+/]{16,}={0,2}/g) || []) {
    try {
      const b = bloque + '='.repeat((4 - (bloque.length % 4)) % 4);
      const bytes = Uint8Array.from(atob(b), (c) => c.charCodeAt(0));
      salida.push(normalizar(new TextDecoder('utf-8', { fatal: true }).decode(bytes)));
    } catch { /* no es base64 o no es texto */ }
  }
  return salida;
}

export function crearGuardia(reglas) {
  const compiladas = reglas.map((r) => ({ ...r, re: new RegExp(r.patron, 'u') }));
  return function revisar(texto) {
    const candidatos = [normalizar(texto), normalizar(texto, true), ...decodificados(texto)];
    for (const c of candidatos) {
      for (const r of compiladas) if (r.re.test(c)) return { permitido: false, categoria: r.categoria, regla: r.patron };
    }
    return { permitido: true, categoria: '', regla: '' };
  };
}
