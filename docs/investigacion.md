# Investigación previa (noviembre de 2026)

Resumen de lo que se revisó antes de diseñar el proyecto. Las versiones se tomaron de PyPI, npm y GitHub el 2026-11-18.

## Herramientas de evaluación

| Herramienta | Versión | Licencia | Uso en Ventanilla |
|---|---|---|---|
| promptfoo | 0.126.0 | MIT | Red team y regresión contra la API. Los plugins de ataque que generan con su servidor remoto se reemplazaron por casos escritos a mano (`PROMPTFOO_DISABLE_REDTEAM_REMOTE_GENERATION`) |
| DeepEval | 4.3.4 | Apache-2.0 | Juez de fidelidad con Ollama; telemetría apagada (`DEEPEVAL_TELEMETRY_OPT_OUT=1`) |
| garak | 0.17.1 | Apache-2.0 | Escaneo nocturno contra la API |
| RAGAS | 0.4.4 | Apache-2.0 | No se usa: API muy cambiante entre versiones y se superpone con DeepEval |
| Inspect AI, PyRIT, Giskard | — | — | No se usan: se superponen con lo anterior |
| Schemathesis | 4.33.4 | MIT | Fuzzing del contrato OpenAPI |

Fuentes: https://www.promptfoo.dev/docs/red-team/plugins/ · https://deepeval.com/integrations/models/ollama · https://github.com/vibrantlabsai/ragas/releases · https://github.com/NVIDIA/garak

## Juez y estadística
- Calibrar el juez contra etiquetas y reportar κ de Cohen: Shankar et al., «Who Validates the Validators?» (arXiv 2404.12272).
- Sesgos del juez (posición, longitud, preferencia por su propio estilo): Zheng et al., MT-Bench (arXiv 2306.05685). Por eso el juez es de otra familia que el modelo que redacta.
- Intervalo de Wilson para tasas con pocos casos; pass^k para seguridad (Chen et al., arXiv 2107.03374; Miller, arXiv 2411.00640).

## Estándares
- OWASP Top 10 for LLM Applications 2026 (publicado el 3 de agosto de 2026): https://genai.owasp.org/resource/owasp-genai-llm-top-10-2026/
- OWASP AI Testing Guide v1: https://owasp.org/www-project-ai-testing-guide/
- MITRE ATLAS (datos v2026.10): https://github.com/mitre-atlas/atlas-data
- NIST AI 600-1, Generative AI Profile.
- ISO/IEC 25059:2023 (calidad de sistemas de IA): https://www.iso.org/standard/80655.html
- ISO/IEC TS 42119-2:2025 (pruebas de sistemas de IA): https://www.iso.org/standard/84127.html

## Perú
- Ley 31814 y su reglamento, DS 115-2025-PCM (vigente desde el 22 de enero de 2026): https://busquedas.elperuano.pe/dispositivo/NL/2436426-1
- Ley 29733 y su nuevo reglamento, DS 016-2024-JUS.
- Res. SBS 4036-2022, Reglamento de Gestión de Reclamos y Requerimientos (15 días hábiles): https://www.sbs.gob.pe/boletin/detalleboletin/idbulletin/1248
- Libro de Reclamaciones, DS 101-2022-PCM.
- ITF: TUO de la Ley 28194, art. 13 (tasa de 0,005 % y truncamiento al múltiplo de 0,05).

## Modelos y entorno
- Runner de GitHub (repo público): 4 vCPU, 16 GB de RAM: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- Ollama 0.40.16. Con semilla y temperatura 0, la salida es estable en la misma máquina y versión, no entre sistemas operativos: https://github.com/ollama/ollama/issues/5321
- qwen3.5:2b (Apache-2.0), granite4.1:3b (Apache-2.0), embeddinggemma:300m (Gemma Terms of Use: https://ai.google.dev/gemma/terms).
