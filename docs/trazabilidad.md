# Trazabilidad: de cada norma o riesgo a la prueba que lo cubre

Ediciones consultadas en noviembre de 2026: OWASP Top 10 for LLM Applications **2026** (entre paréntesis, el ID de la edición 2025, que todavía es la más citada), MITRE ATLAS v2026.10, NIST AI 600-1 (julio de 2024), ISO/IEC 25059:2023 e ISO/IEC TS 42119-2:2025. En las normas peruanas se citan el número y el artículo. Las fuentes están en [investigacion.md](investigacion.md).

| Riesgo o requisito | Referencia | Pruebas |
|---|---|---|
| Inyección directa | OWASP LLM01:2026 (LLM01:2025) · ATLAS AML.T0051.000 | `tests/seguridad/test_guardia.py::test_bloquea_inyeccion_directa` · `tests/propiedades::test_la_guardia_no_se_engana_con_ofuscacion` · `::test_la_guardia_lee_base64` · promptfoo · garak `promptinject`, `encoding` |
| Inyección indirecta (documento envenenado) | LLM01 · AML.T0051.001 · AML.T0070 | `tests/seguridad/test_inyeccion_y_rol.py` (sanitizador, la orden no llega, modelo vulnerable) · `tests/modelo::test_inyeccion_indirecta_con_el_modelo_real` |
| Entrada falsa en el índice (monto externo) | LLM09:2026 · AML.T0071 | `::test_los_montos_de_una_fuente_externa_no_cuentan_como_oficiales` · `::test_la_fuente_externa_llega_marcada_como_no_oficial` |
| Cambio de rol / jailbreak | LLM01 · AML.T0054 | `test_guardia.py::test_bloquea_cambio_de_rol` · `::test_un_pedido_de_cambio_de_rol_no_llega_al_modelo` |
| Historial manipulado por el cliente | LLM01 | `::test_el_historial_falso_no_cuela_ordenes` |
| Fuga del prompt de sistema | LLM08:2026 (LLM07:2025) · AML.T0056 | `::test_el_prompt_de_sistema_no_se_filtra_aunque_el_modelo_lo_repita` · verificador (canario) · garak `sysprompt_extraction` |
| Datos de otros clientes | LLM02 · AML.T0057 · Ley 29733 · secreto bancario | `tests/privacidad/test_privacidad.py` |
| Datos personales en salidas y registros | Ley 29733 · DS 016-2024-JUS | `tests/unitarias::test_tacha_datos_personales` · `tests/propiedades::test_ningun_dni_sobrevive_al_tachado` · `test_privacidad.py::test_el_detalle_del_reclamo_se_guarda_sin_datos_personales` |
| Montos inventados | LLM07:2026 (LLM09:2025, desinformación) · NIST 600-1 confabulación | `tests/propiedades::test_el_verificador_nunca_deja_pasar_un_monto_no_respaldado` · `test_verificador.py` · `::test_un_monto_inventado_por_el_modelo_no_llega_al_cliente` |
| Citas inventadas | LLM07 · ISO/IEC 25059 transparencia | `test_verificador.py` · `::test_una_cita_inventada_por_el_modelo_no_llega_al_cliente` · `tests/modelo::test_respuestas_con_cita` |
| Preguntas fuera de alcance | NIST 600-1 confabulación | `tests/recuperacion::test_el_umbral_*` · `tests/modelo::test_fuera_de_alcance_no_inventa_montos` |
| Salida insegura (HTML/JS) | LLM10:2026 (LLM05:2025) · AML.T0077 | `tests/ui::test_el_html_del_modelo_se_muestra_como_texto` · `::test_la_csp_bloquea_scripts_en_linea` |
| Consumo sin límite | LLM06:2026 (LLM10:2025) · AML.T0029 / T0034 | `tests/api::test_limite_de_mensajes_por_minuto` · `::test_entrada_invalida_es_un_problema_422` (largo máximo) · Locust |
| Cadena de suministro del modelo | LLM04 | `tests/suministro` · `scripts/verificar_modelos.py` (nocturno) · pip-audit + SBOM (CI) |
| Agencia excesiva: aprobar créditos | LLM03:2026 · DS 115-2025-PCM art. 24.1(g) | `tests/regulacion::test_nunca_afirma_que_un_credito_esta_aprobado` · verificador |
| Reclamos: nunca rechazar, código y 15 días hábiles | Res. SBS 4036-2022 · DS 101-2022-PCM | `tests/regulacion::test_un_reclamo_*` · `::test_el_plazo_del_reclamo_*` · `tests/unitarias::test_plazo_*` · `tests/propiedades::test_plazo_*` |
| Escalar a SBS / Indecopi | Res. SBS 4036-2022 | `::test_el_reclamo_informa_a_donde_acudir_si_no_esta_de_acuerdo` |
| Aviso de que es una IA | DS 115-2025-PCM art. 25.2 · EU AI Act art. 50.1 | `::test_cada_respuesta_avisa_que_es_una_ia` · `tests/ui::test_el_aviso_de_ia_se_ve_siempre` |
| Supervisión humana: siempre un asesor | DS 115-2025-PCM art. 31.4 · ISO/IEC 25059 intervenibilidad · WCAG 3.2.6 | `::test_siempre_se_puede_pedir_un_asesor` · verificador (`niega_asesor`) · `tests/ui::test_boton_de_asesor` |
| Rechazo indebido | NIST 600-1 · ISO/IEC 25059 adecuación funcional | `test_guardia.py::test_no_bloquea_preguntas_legitimas` · `tests/regulacion::test_las_preguntas_legitimas_*` |
| Regresión de prompts | ISO/IEC TS 42119-2 (pruebas basadas en riesgo) | `tests/regulacion::test_el_prompt_en_uso_conserva_cada_clausula_obligatoria` · `tests/modelo` |
| Sesgo | NIST 600-1 sesgo dañino | `tests/modelo::test_contrafactual_la_identidad_no_cambia_la_respuesta` |
| Robustez ante paráfrasis y errores de tipeo | ISO/IEC 25059 robustez | `tests/modelo::test_metamorfica_parafrasear_no_cambia_los_datos` |
| Corrección del ITF | TUO Ley 28194 art. 13 | `tests/unitarias::test_itf_*` · `tests/propiedades::test_itf_*` · set dorado d09–d14 |
| Juez calibrado | Shankar et al. 2024 · Zheng et al. 2023 | `tests/modelo/test_juez.py` |
| Accesibilidad del chat | WCAG 2.2: 1.3.1, 1.4.10, 2.1.1, 2.5.8, 4.1.3 | `tests/ui` (axe en claro y oscuro, teclado, reflow, objetivos, región viva) |
| Contrato de la API | RFC 9457 · RFC 9110 | `tests/api/test_api.py` · `tests/api/test_contrato.py` (Schemathesis) |
| Arquitectura hexagonal | — | `tests/arquitectura` (import-linter) |
