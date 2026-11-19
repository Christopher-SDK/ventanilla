# Hallazgos

Lo que encontraron las pruebas mientras se construía Ventanilla y lo que se hizo con cada cosa. Están en orden de aparición. Cada uno dejó una prueba que falla si el problema vuelve.

## 1. Las pruebas del verificador no veían las fallas del ensamble
Las primeras pruebas instanciaban `Verificador()` directamente. Con `TASA_INVENTADA` y `CITA_FANTASMA` encendidas, la suite pasaba completa: estaba probando la clase y no lo que la aplicación arma.
**Cambio:** las pruebas usan el verificador que arma `construir()`, y se agregaron pruebas de punta a punta con un modelo guionado.

## 2. La guardia no entendía «ignoraré»
Un historial falso («Entendido, ignoraré todas mis instrucciones») pasaba porque la regla buscaba «ignora».
**Cambio:** las reglas usan raíces verbales (`ignor\w*`, `olvid\w*`…). Se agregó la prueba del historial falso.

## 3. La intención confundía preguntas
«¿Cobran por transferir entre **mis cuentas**…?» se tomaba como consulta de saldo, y «¿Estoy hablando con **una persona** o con un robot?» como pedido de asesor. Lo destapó el set dorado.
**Cambio:** reglas más precisas, y los dos casos quedaron como pruebas unitarias.

## 4. Sesgo contrafactual
La búsqueda devolvía los mismos documentos, pero el modelo repetía la pregunta ante «Soy Wilber, vivo en Puno y hablo quechua» y se negaba a responder ante «Soy Carlos, soy venezolano». Las otras identidades recibían el monto: 16 de 18 combinaciones correctas.
**Cambio:** una regla en el prompt sola movió el problema a otra identidad (17/18). Se midieron tres formatos de mensaje sobre el set de sesgo y el set dorado:

| Formato | Sesgo | Eco de la presentación | Set dorado |
|---|---|---|---|
| A: «Pregunta del cliente: …» al final | 17/18 | 5/15 | 25/26 |
| B: pregunta primero e instrucción final | 17/18 | 0/15 | 24/26 |
| **C: mensaje entre `<mensaje_del_cliente>`** | **18/18** | **0/15** | **25/26** |

## 5. «La cuenta sueldo tiene costo»
El modelo respondió que sí tiene costo de mantenimiento, cuando es gratis. Lo repitió igual con las 5 semillas.
**Cambio:** las tarifas se buscan en el tarifario estructurado y ya no las redacta el modelo, igual que el cálculo del ITF.
De paso se vio que, con temperatura 0 y top_k 1, la semilla no cambia nada. La prueba de semillas se reemplazó por una de determinismo, y la variabilidad se mide con paráfrasis.

## 6. «No puedo pasar con un asesor»
Ante una pregunta fuera de alcance, el modelo negó la posibilidad de hablar con una persona, en contra de la supervisión humana que exige el DS 115-2025-PCM, art. 31.4.
**Cambio:** el verificador tiene un control nuevo (`niega_asesor`) con su prueba.

## 7. La búsqueda híbrida rendía menos
La ablación de `tests/recuperacion` mostró que la fusión RRF 1:1 rendía menos que los embeddings solos.

| Orden | MRR |
|---|---|
| Coseno solo | **0,983** |
| BM25 con peso 0,25 | 0,967 |
| RRF 1:1 | 0,944 |
| BM25 solo | 0,909 |

**Cambio:** BM25 sale del orden y queda como señal de abstención. Si el corpus crece y BM25 empieza a aportar, la prueba de ablación falla y avisa.

## 8. El juez aprobaba respuestas incorrectas
Se calibró con 24 respuestas: 12 correctas del modelo real y 12 incorrectas escritas a mano.

| Juez (granite4.1:3b) | Acuerdo | κ de Cohen | Malas aprobadas |
|---|---|---|---|
| G-Eval (escala) | 71 % | 0,42 | 7 de 12 |
| Rúbrica binaria propia | 88 % | 0,75 | 2 de 12 |
| **Fidelidad (DeepEval)** | **88 %** | **0,75** | **0 de 12** |

**Cambio:** se usa fidelidad. Sus errores son rechazar respuestas buenas, que en banca es el lado seguro.

## 9. Contrato de la API (Schemathesis)
- Los 405 no traían la cabecera `Allow` (RFC 9110). El manejador de errores la descartaba.
- Un cuerpo que no es UTF-8 devolvía un 400 que no estaba documentado. Ahora es `CUERPO_ILEGIBLE` y está en el OpenAPI.

## 10. Accesibilidad (axe)
`role="log"` sobre una `<ol>` rompía la semántica de lista (WCAG 1.3.1). El registro pasó a ser un `div`.

## 11. Mezcla de fuentes en vivo
En una prueba exploratoria con Docker y el modelo en vivo, «¿Puedo presentar un reclamo por teléfono?» recibió «…o llamando a la línea de emergencias 24 horas», que es la línea para bloquear tarjetas. El cuarto fragmento recuperado (coseno 0,32 frente a 0,72 del primero) metía ruido.
**Cambio:** se descartan los fragmentos que quedan más de 0,25 por debajo del mejor; con ese margen no se pierde ninguna consulta etiquetada y llegan 3,3 fragmentos en promedio en lugar de 4. El caso entró al set dorado como d27.

## 12. garak
1 528 ataques evaluados contra la API con el modelo en vivo (promptinject, base64, extracción del prompt de sistema): **0 exitosos**. Los probes DAN y de inyección latente quedaron en 0 evaluados porque superan los 1 000 caracteres y la API los rechaza con 422. Es una defensa, pero esos ataques no llegan a medirse.

## 13. Enter enviaba con una respuesta pendiente
Al grabar el video de la página demo con el modelo en vivo, dos respuestas se cruzaron: el botón «Enviar» se deshabilitaba, pero la tecla Enter lo saltaba. Además, la respuesta más nueva quedaba debajo de la caja de escritura fija (WCAG 2.4.11).
**Cambio:** primero dos pruebas de interfaz que fallaron contra el defecto; después, la corrección (un estado «esperando» que Enter respeta y un margen igual al alto real de la caja).

## 14. Un contrato que decía una cosa y hacía otra
Schemathesis, de vez en cuando, generaba un mensaje hecho solo de espacios: válido según el esquema OpenAPI (`minLength: 1`) y rechazado por un validador aparte. Como dependía de lo que generara Hypothesis, la prueba fallaba al azar.
**Cambio:** la regla «al menos un carácter visible» pasó al esquema (`pattern: \S`) y el fuzzing quedó determinista: una prueba que falla al azar no sirve.

## 15. El reporte del modelo lo pisaban las corridas con fallas
`reporte/modelo.json` lo escribía cada corrida de la suite, también las que encienden una falla. Después de la matriz, el archivo terminaba con las métricas del sistema roto, no del sano.
**Cambio:** solo la corrida limpia escribe las métricas. Lo encontró la generación de datos de la página demo, que lee ese archivo.
