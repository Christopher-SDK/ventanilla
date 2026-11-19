# Ventanilla

**Un asistente con IA para un banco ficticio, hecho para ser probado.** Es un RAG en español (comisiones, ITF, reclamos, privacidad) con 7 fallas sembradas y apagadas. La suite de pruebas atrapa las 7.

> Datos 100 % ficticios. «Banco Cuadre» no existe y Ventanilla no es un producto bancario ni un sistema certificado. Las normas peruanas se citan como referencia para diseñar las pruebas.

**English summary.** Ventanilla is a Spanish-language RAG assistant for a fictional Peruvian bank, built as a QA portfolio piece. It runs on small local models (Ollama, no API keys) and ships with seven seeded faults (hallucinated fee, fabricated citation, indirect prompt injection, data leak, role-play jailbreak, over-refusal, prompt regression). A layered suite catches all seven, covering properties, retrieval metrics, red teaming mapped to OWASP LLM Top 10 2026 and MITRE ATLAS, Peruvian banking rules, counterfactual bias, metamorphic tests, an LLM judge calibrated with Cohen's kappa, contract fuzzing, accessibility and load. CI replays recorded model calls, so every run is deterministic. A nightly job runs the models live.

**Demo:** https://christopher-sdk.github.io/ventanilla/ · **Reporte Allure:** https://christopher-sdk.github.io/ventanilla/allure/

---

## La idea en una frase

**El modelo redacta; los números y las reglas los pone el sistema.** El tarifario, el ITF y los plazos de reclamo salen de código determinista. Cada borrador del modelo pasa por un verificador antes de llegar al cliente: el monto debe existir, la cita debe ser real, no puede pedir claves, nunca dice «crédito aprobado» y nunca niega pasar con un asesor.

```
mensaje ─► guardia ─► intención ─┬─ reclamo / saldo / asesor ─────────────► respuesta fija
                                  ├─ tarifa / ITF ─► tarifario, cálculo ───► respuesta exacta
                                  └─ consulta ─► búsqueda ─► sanitizador ─► modelo ─► verificador ─► respuesta
```

## Pruébalo en tu máquina

Necesitas **Python 3.13 y [uv](https://docs.astral.sh/uv/)**. No necesitas Ollama ni GPU: las pruebas usan las respuestas grabadas del modelo.

```bash
git clone https://github.com/Christopher-SDK/ventanilla.git
cd ventanilla
uv sync --all-extras
uv run playwright install chromium
uv run pytest            # 282 pruebas, 0 fallas, ~10 s
```

### Enciende una falla y mira cómo la suite la atrapa

Las fallas vienen en el código, apagadas. No subes ni configuras nada: solo agregas `--falla NOMBRE` (igual en macOS, Linux y Windows).

```bash
uv run pytest tests/seguridad/test_verificador.py --falla TASA_INVENTADA
```

| Falla | Qué hace | Prueba rápida (1–2 s) |
|---|---|---|
| `TASA_INVENTADA` | El verificador deja pasar montos que no están en el tarifario | `tests/seguridad/test_verificador.py` |
| `CITA_FANTASMA` | Deja pasar citas a documentos que no se recuperaron | `tests/seguridad/test_verificador.py` |
| `INYECCION_INDIRECTA` | Las órdenes escondidas en un documento llegan al modelo | `tests/seguridad/test_inyeccion_y_rol.py` |
| `FUGA_DE_DATOS` | Muestra cuentas de otro cliente si su DNI aparece en el mensaje | `tests/privacidad` |
| `JUEGO_DE_ROL` | La guardia ya no detecta pedidos de cambio de rol | `tests/seguridad/test_guardia.py` |
| `RECHAZO_EXCESIVO` | Bloquea pedidos legítimos con palabras como «clave» o «reclamo» | `tests/regulacion` |
| `REGRESION_DE_PROMPT` | El prompt v2 perdió «responde solo con las fuentes» y «ofrece un asesor» | `tests/regulacion` |

**Que falle es la prueba de que funciona.** Sin `--falla`, todo pasa.

Para ver las 7 a la vez: `uv run python scripts/matriz.py` (≈1 min).

### Conversa con el asistente

Con [Ollama](https://ollama.com) instalado:

```bash
ollama pull qwen3.5:2b-q4_K_M && ollama pull embeddinggemma:300m
VENTANILLA_MODO=auto uv run uvicorn ventanilla.adaptadores.api:app_desde_entorno --factory --port 8080
```

Abre http://localhost:8080. También puedes usar Docker: `docker compose up --build` descarga los modelos la primera vez (~2,5 GB).

**Windows (PowerShell):** los comandos de `uv` son los mismos. Para las variables de entorno usa `$env:VENTANILLA_MODO="auto"` antes de `uv run uvicorn …`.

## Capas de prueba

| Capa | Qué prueba | Herramientas | Referencia |
|---|---|---|---|
| Unitarias | Montos, ITF, datos personales, intención, días hábiles | pytest | TUO Ley 28194 art. 13; Res. SBS 4036-2022 |
| Propiedades | Miles de entradas generadas: ITF, plazos, RRF, tachado, guardia ofuscada, verificador | Hypothesis | — |
| Recuperación | recall@4 = 1,0 y MRR ≥ 0,9 en 30 consultas etiquetadas; ablación de BM25; umbral de abstención | pytest | ISO/IEC 25059 (corrección funcional) |
| Seguridad | Inyección directa e indirecta, cambio de rol, citas y montos inventados, fuga del prompt, historial falso | pytest, modelo vulnerable de prueba | OWASP LLM01/02/05/07/08/09; ATLAS AML.T0051, T0054, T0056, T0070, T0071 |
| Privacidad | Secreto bancario entre clientes, tachado en reclamos y salidas | pytest | Ley 29733; DS 016-2024-JUS |
| Regulación | Reclamos con código y 15 días hábiles, aviso de IA, asesor humano, crédito nunca aprobado, contrato del prompt | pytest | Res. SBS 4036-2022; DS 115-2025-PCM arts. 24, 25, 31 |
| Modelo real | Set dorado, fuera de alcance, metamórficas, sesgo contrafactual, determinismo, inyección con el modelo real | pytest + grabaciones; intervalo de Wilson | NIST AI 600-1; ISO/IEC 25059 (robustez) |
| Juez LLM | Calibrado con 47 etiquetas: κ ≥ 0,6 y cero respuestas malas aprobadas | DeepEval (fidelidad) + rúbrica binaria, con granite4.1 | Shankar et al. 2024; Zheng et al. 2023 |
| API y contrato | RFC 9457, límite por IP, sesiones, SSE verificado, fuzzing del OpenAPI | pytest, Schemathesis | OWASP LLM10:2026 (consumo) |
| Interfaz | XSS desde la salida del modelo, axe (claro/oscuro), teclado, reflow 320 px, objetivos 24 px | Playwright, axe-core | WCAG 2.2 (1.3.1, 1.4.10, 2.5.8, 4.1.3) |
| Arquitectura | El dominio no conoce adaptadores ni la red; las fallas solo se cablean en la configuración | import-linter | — |
| Suministro | Modelos fijados por digest y licencia; grabaciones solo de modelos fijados; pip-audit y SBOM | pytest, pip-audit | OWASP LLM04 |
| Red team | 73 casos: ataques, preguntas legítimas y set dorado contra la API | promptfoo | OWASP LLM01; ATLAS |
| Carga | 20 usuarios: p95 ≤ 300 ms y 0 fallas (con respuestas grabadas) | Locust | — |
| Nocturno | Modelos en vivo en Linux, verificación de digests, garak | Ollama, garak | NIST AI RMF (Measure) |
| Página demo | La guardia del navegador decide igual que la de Python (paridad con 200 casos generados); los datos de la demo salen del sistema real con cada falla encendida | pytest, Node, Hypothesis | — |

La trazabilidad completa, prueba por prueba, está en [docs/trazabilidad.md](docs/trazabilidad.md).

## Lo que encontraron las pruebas (y qué se hizo)

Esto no salió del diseño inicial: lo encontraron las propias pruebas. El detalle está en [docs/hallazgos.md](docs/hallazgos.md).

- **Sesgo contrafactual.** Con «Soy Wilber, vivo en Puno y hablo quechua» o «Soy Carlos, venezolano», el modelo repetía la pregunta o se negaba a responder, aunque la búsqueda le daba los mismos documentos que a los demás. Probé tres formatos de mensaje y gané con el mensaje entre etiquetas: pasó de 16/18 a 18/18, con 0 ecos.
- **El modelo dijo que la cuenta sueldo tiene costo** (es gratis), y lo repitió con las 5 semillas. Las tarifas pasaron a salir del tarifario estructurado y ya no del modelo.
- **El juez G-Eval aprobaba 7 de 12 respuestas incorrectas** (κ 0,42). Medí tres opciones y elegí la que no aprueba ninguna mala: fidelidad de DeepEval, κ 0,75.
- **En Linux el juez bajó a κ 0,583.** La misma calibración daba otro resultado en otro hardware. Amplié las etiquetas de 24 a 47 y combiné fidelidad con una rúbrica binaria: κ 0,657, sin ninguna respuesta mala aprobada. El criterio no se tocó.
- **El modelo mandaba a la SBS a quien pedía borrar sus datos** (eso es un derecho ARCO ante el banco). Se ajustó el corte por relevancia y el caso entró al set dorado.
- **La búsqueda híbrida rendía menos que los embeddings solos** (MRR 0,944 frente a 0,983). BM25 quedó solo como señal de abstención, y la ablación sigue en la suite.
- **Schemathesis** encontró que la API perdía la cabecera `Allow` en los 405 y devolvía un 400 que no estaba documentado.
- **axe** encontró `role="log"` sobre una lista ordenada.
- **Una prueba exploratoria con el modelo en vivo** mostró que mezclaba la «línea de emergencias» de tarjetas al responder sobre reclamos por teléfono. Se agregó un corte por relevancia y el caso entró al set dorado.

## Cómo es reproducible

- Las llamadas al modelo se guardan en `grabaciones/` con el hash de la petición completa (modelo, mensajes y opciones). En la CI, `VENTANILLA_MODO=reproducir` falla si falta una grabación: nunca llama al modelo a escondidas.
- Temperatura 0 y top_k 1. La variabilidad se mide con paráfrasis y no con semillas, porque con esta configuración la semilla no cambia nada (hay una prueba que lo confirma).
- `modelos.lock.json` fija cada modelo por su digest. El job nocturno compara lo que descarga Ollama con ese archivo.
- `scripts/podar_grabaciones.py` borra las grabaciones que ninguna corrida usa.

| Modo | Qué hace |
|---|---|
| `reproducir` (por defecto) | Solo grabaciones. Si falta una, falla y explica cómo crearla |
| `auto` | Usa la grabación si existe; si no, llama a Ollama y la guarda |
| `grabar` | Siempre llama a Ollama y guarda |
| `vivo` | Llama a Ollama sin guardar (job nocturno) |

## Modelos

| Rol | Modelo | Licencia |
|---|---|---|
| Redacta | `qwen3.5:2b-q4_K_M` | Apache-2.0 |
| Juez | `granite4.1:3b` (otra familia, para que el juez no favorezca su propio estilo) | Apache-2.0 |
| Embeddings | `embeddinggemma:300m` | Gemma Terms of Use (no es OSI; la alternativa Apache es `qwen3-embedding:0.6b`) |

## Estructura

```
src/ventanilla/
  dominio/       dinero, ITF, guardia, verificador, datos personales, intención, reclamos, tarifario, búsqueda
  aplicacion.py  el caso de uso «responder»
  puertos.py     lo que el dominio necesita: modelo, embeddings, clientes
  adaptadores/   Ollama, grabadora, API (FastAPI), clientes
  fallas/        las 7 fallas sembradas (solo se cablean en configuracion.py)
  prompts/       sistema-v1 (en uso) y sistema-v2 (la regresión)
corpus/          documentos del banco ficticio (uno externo, envenenado a propósito)
evals/           set dorado, ataques, metamórficas, sesgo, fuera de alcance, juez, promptfoo, garak
tests/           una carpeta por capa
grabaciones/     respuestas grabadas del modelo
scripts/         matriz, carga, poda de grabaciones, verificación de modelos, generador de promptfoo
```

## Límites conocidos

- Es un modelo de 2B parámetros en CPU. Las respuestas que redacta pueden ser torpes; por eso los datos críticos no dependen de él.
- La guardia es por reglas. Atrapa los ataques conocidos y sus variantes (tildes, mayúsculas, leetspeak, base64, caracteres invisibles), pero no reemplaza un clasificador entrenado. garak la pone a prueba cada noche.
- El juez se calibró con 47 casos. Alcanza para descartar un mal juez, pero no para afirmar que uno es excelente.
- El límite de mensajes y las sesiones viven en memoria: con varias réplicas, irían a Redis o al API gateway.

## Licencia

MIT. Ver [LICENSE](LICENSE).
