# ACTA-001 — COMITÉ DE INVERSIONES Y PATRIMONIO

**Sesión:** 001
**Fecha:** 29 de julio de 2026
**Materia sometida a comité:** Documento "Diseño del Holding Familiar v1.0" — validez de la arquitectura, timing de constitución y prioridades de asignación de capital.
**Estado:** Conclusiones **parcialmente superadas**. Ver banner de actualización.

---

## ⚠ ACTUALIZACIÓN v1.1 — 4 de agosto de 2026

Este acta se mantiene como registro histórico, pero **tres de sus conclusiones fueron modificadas** por información posterior. Leer junto con [ACTA-002](ACTA-002-estatutos-avicola-limache.md).

**1. Datos confirmados que estaban pendientes (sección 10)**

| Dato | Valor confirmado |
|---|---|
| Sociedad | Avícola Limache SpA, RUT 78.355.913-7 |
| Constitución | 11 de febrero de 2026 |
| Socios | Tomás Núñez Smith 50% (1.000 acc.) / Cristóbal Merino Lind 50% (1.000 acc.) |
| Relación entre socios | Amistad previa, sin vínculo familiar |
| Capital | $20.000 en 2.000 acciones sin valor nominal |
| Costo tributario de la participación de Tomás | $10.000 |
| Inicio de actividades | Realizado. **Verificación pendiente** hasta que haya producción efectiva |
| Régimen tributario | **Aún desconocido** — sigue siendo el dato bloqueante |

**2. Corrección de tasas.** La tasa de IDPC del régimen Pro Pyme utilizada en la sección 2 (Contador) era **incorrecta**. La tasa vigente es **12,5%** (rebaja transitoria para años comerciales 2025–2027; 15% en 2028; 25% desde 2029), condicionada al cumplimiento del calendario de cotización del empleador. La tabla correspondiente fue corregida in situ. **La conclusión de fondo no cambia**: con integración total, la carga final equivale a la tasa de Global Complementario; la tasa de IDPC solo determina cuánto capital permanece componiendo dentro de la empresa.

**3. Reordenamiento de prioridades.** ACTA-002 detectó que Avícola Limache SpA **carece de gobierno corporativo**: administración indistinta con facultades plenas y autocontratación habilitada, y libre transferibilidad de acciones. En consecuencia, **el pacto de accionistas y la modificación de estatutos desplazan al holding como prioridad**. La recomendación de la sección 8 se mantiene válida en su lógica, pero se subordina a la agenda de ACTA-002.

**4. Rectificación de un error del comité.** Se advirtió que el socio podría vetar el traspaso de acciones mediante derecho preferente. Revisados los estatutos, esa cláusula **no existe**. La advertencia era incorrecta.

---

> **Advertencia.** Las implicancias tributarias y societarias señaladas en este documento deben validarse con contador y abogado habilitados en Chile antes de cualquier ejecución. Este acta no constituye asesoría legal ni tributaria. El comité opera con información incompleta.

> **Nota de alcance.** Este documento pertenece a la línea patrimonial del proyecto (`docs/patrimonio/`) y es independiente de los ADR de arquitectura de software (`docs/adr/`). La numeración de ambas series es autónoma.

---

## Composición del comité

| # | Rol | Pregunta rectora |
|---|-----|------------------|
| 1 | CFO | ¿Es ésta la mejor utilización posible del siguiente peso? |
| 2 | Abogado Corporativo y Patrimonial | ¿Qué pasa si todo sale mal? |
| 3 | Contador Tributario Senior | ¿Existe una forma legalmente más eficiente? |
| 4 | Corporate Finance / Investment Banking | ¿Invertiría mi propio dinero aquí? |
| 5 | Devil's Advocate | ¿Qué supuesto oculto sostiene esta conclusión? |
| 6 | **Arquitecto de Patrimonio (Chief Wealth Architect)** | *Incorporado con posterioridad a esta sesión. Ver Anexo A. Participa desde la Sesión 002.* |

---

## 1. Resumen Ejecutivo

El comité **no rechaza** la arquitectura propuesta, pero **rechaza su orden de prioridades**. La conclusión central es que el documento resuelve un problema de segundo orden (estructura societaria) antes de resolver tres de primer orden:

1. **El régimen tributario de la Avícola.** Si opera bajo Pro Pyme Transparente (14 D N°8), Tomás está pagando impuesto personal sobre utilidades que no retira — es decir, financiando su propia reinversión con caja gravada. En un plan de 30 años basado en reinversión agresiva, ése es probablemente el error más caro del sistema actual, y es más urgente que el holding.
2. **El riesgo de ruina, no el de rentabilidad.** Concentración del 100% del patrimonio en un negocio con riesgo sanitario catastrófico (influenza aviar), más avales personales, más exposición no cubierta a maíz/soya en USD. El documento optimiza el crecimiento de un patrimonio que puede irse a cero.
3. **La ausencia de medición.** No existe hoy —hasta donde el comité sabe— cálculo de ROIC marginal ni de flujo de caja libre real. Toda la política de asignación de capital del documento descansa sobre un número que nadie está calculando.

**Recomendación preliminar:** constituir el holding es correcto y conviene hacerlo temprano (el costo de la reorganización crece con el valor de la empresa), pero **después** de definir el régimen tributario y **en paralelo** con las medidas de protección básicas. El holding no es lo que construye el patrimonio; es lo que evita perderlo.

---

## 2. Opinión individual de cada integrante

### Integrante 1 — CFO

Mi pregunta es si el siguiente peso está bien colocado. La respuesta probable es sí: una avícola en expansión con galpones y plantel incremental típicamente exhibe ROIC marginal muy superior a cualquier alternativa financiera. Si el retorno marginal sobre capital invertido en el próximo galpón es 25–35% y la alternativa es un ETF global a ~7% real, no hay discusión: reinvertir.

Pero hago dos observaciones incómodas.

**Primera:** el holding no mejora el ROIC. Ni un punto. El holding es un instrumento de riesgo, control y diferimiento fiscal. Presentarlo bajo el objetivo "crecimiento del capital" (sección 2.2 del documento) es una confusión de categorías. Su valor es *opcionalidad* y *protección*, y debe justificarse en esos términos o no justificarse.

**Segunda, y más grave:** el documento define una política de reinversión condicionada a que "la empresa mantenga retornos superiores a alternativas comparables". Ése es el criterio correcto. Pero no existe hoy el sistema que produce ese número. Sin contabilidad de costos por lote y sin separación entre capex de mantención y capex de crecimiento, el ROIC reportado es ficción. Una avícola familiar puede tener "utilidad" contable robusta y flujo de caja libre cercano a cero, porque todo se va en reponer infraestructura que se depreció mal. **Mi prioridad número uno no es la estructura: es instrumentar la medición.** Si el rendimiento marginal real resulta ser 12% y no 30%, toda la política de concentración del documento se cae.

Sobre asset allocation: el documento propone concentración total en Etapa 1. Como asignador de capital lo entiendo. Como gestor de patrimonio lo objeto — no por retorno, sino porque la función de utilidad de un patrimonio único no es lineal.

### Integrante 2 — Abogado Corporativo y Patrimonial

Mi pregunta es qué pasa si todo sale mal. Encuentro cuatro huecos.

**Aval personal.** Ninguna estructura societaria sobrevive a la firma de Tomás como avalista. Todo banco que financie expansión avícola exigirá aval. El documento declara "protección patrimonial" como objetivo 2.1 y luego construye un mecanismo que el propio modelo de financiamiento neutraliza. La protección real se juega en negociar límites y liberaciones progresivas del aval a medida que la empresa gana historial, no en la carta orgánica del holding.

**Régimen patrimonial del matrimonio.** El documento no lo menciona una sola vez. Si Tomás está casado o se casa en sociedad conyugal, la participación en las sociedades y buena parte de los frutos entran al haber social, y el diseño completo cambia — incluyendo quién administra y qué ocurre en caso de separación. Separación total de bienes o participación en los gananciales es, en costo-beneficio, probablemente la medida de protección patrimonial más eficiente disponible, y cuesta una fracción de lo que cuesta operar un holding. **Es una omisión de primer orden.**

**Sucesión.** La sección 15.C plantea las preguntas correctas y no responde ninguna. Señalo una ventaja técnica que el documento desaprovecha: la SpA en Chile admite estatutos muy flexibles, incluyendo series de acciones con derechos económicos y políticos distintos. Eso permite, más adelante, transferir propiedad económica a herederos sin ceder control operativo — un problema que en una sociedad de responsabilidad limitada es mucho más rígido de resolver. Si el holding se constituye, que se constituya como SpA con estatutos que contemplen series desde el día uno, aunque solo exista una serie emitida. Cambiar estatutos con un solo accionista es trivial; hacerlo con herederos en desacuerdo, no.

**Muerte sin testamento con la empresa operando.** Sucesión intestada, posesión efectiva, herederos que no pueden firmar. Una avícola no tolera dos meses de parálisis administrativa: los animales comen todos los días. Testamento y seguro de vida con cobertura suficiente para dar liquidez a la sucesión no son planificación de largo plazo, son continuidad operacional.

### Integrante 3 — Contador Tributario Senior

Mi pregunta es si existe una forma legalmente más eficiente. Sí, y probablemente está siendo desaprovechada hoy.

**El punto central: el régimen de la Avícola.** El artículo 14 letra D) contempla dos variantes con consecuencias opuestas para quien reinvierte:

- **14 D N°8 (Pro Pyme Transparente):** la empresa no paga Impuesto de Primera Categoría; el resultado se atribuye al dueño, que tributa Global Complementario sobre el 100% de la utilidad **aunque no la retire**. Requiere estar constituida exclusivamente por contribuyentes de impuestos finales — es decir, **un holding como socio es incompatible con este régimen**.
- **14 D N°3 (Pro Pyme General):** la empresa paga IDPC, el impuesto final se difiere hasta el retiro efectivo, y admite personas jurídicas entre sus socios.

La implicancia numérica es decisiva. Ilustro con utilidad tributable de 100 y reinversión total:

| | 14 D N°8 Transparente | 14 D N°3 General |
|---|---|---|
| Impuesto en la empresa | 0 | **12,5** (tasa transitoria 2025–2027) |
| Impuesto personal ese año | GC sobre 100 → ~35 | 0 (no hay retiro) |
| **Caja que sale del sistema** | **~35** | **12,5** |
| Capital que sigue componiendo | 65 | **87,5** |
| Impuesto final posterior | — | GC al retirar, con crédito 100% por el IDPC pagado |

*(Cifras ilustrativas, no un cálculo del caso concreto. La tasa de GC depende del tramo efectivo de Tomás, dato aún no disponible.)*

**Corregido en v1.1.** La tasa Pro Pyme vigente es 12,5% para los años comerciales 2025, 2026 y 2027; 15% en 2028; 25% desde 2029, salvo nueva prórroga. Está condicionada al cumplimiento del calendario de cotización del empleador (1% en 2025, 3,5% en 2026, 4,5% en 2027, 5% en 2028) — **verificar que la Avícola lo esté cumpliendo**. La diferencia con el régimen transparente es aún mayor de lo estimado originalmente: **87,5 vs 65 de capital componiendo**.

La carga *total* eventual es comparable. Lo que cambia es **cuándo** se paga. Diez puntos adicionales de utilidad reinvirtiéndose cada año, a un ROIC del 20% durante 30 años, no es una diferencia marginal: es la diferencia entre dos patrimonios de órdenes de magnitud distintos. **El diferimiento es el motor de la composición, y el régimen transparente lo apaga.**

Por eso sostengo: si la Avícola está hoy en transparente, salir de ahí vale más que constituir el holding. Y salir de transparente y constituir el holding son, convenientemente, el mismo movimiento — porque incorporar una persona jurídica como socia fuerza la salida.

**Sobre el timing de aporte.** Aportar las acciones al holding constituye una reorganización empresarial. Para que no genere efecto tributario debe cumplir requisitos, entre ellos que exista legítima razón de negocios y que se mantenga el costo tributario de los activos aportados (art. 64 del Código Tributario). Esto exige análisis caso a caso. Lo que sí es aritméticamente cierto: cuanto mayor sea la brecha entre valor económico y costo tributario de la Avícola, mayor la exposición y más complejo el ejercicio. **Hoy esa brecha es pequeña. En cinco años, no.**

**Sobre costos.** Un holding implica contabilidad, F29 mensual, F22, honorarios y gastos societarios recurrentes. A patrimonios pequeños destruye valor. La afirmación del documento de que "el sistema debe funcionar con $20 millones y con $5.000 millones" es incorrecta.

**Mala práctica que señalo sin que se me pregunte:** el documento contempla que el holding "administre liquidez" y sea un centro patrimonial. Debe quedar prohibido desde el día uno canalizar gastos personales a través de cualquier sociedad. Además de exponer a gastos rechazados, contamina la contabilidad que después se necesitará para una eventual venta o due diligence.

### Integrante 4 — Corporate Finance / Investment Banking

Mi pregunta es si invertiría mi propio dinero aquí. Con la información disponible, no puedo responder — y eso ya es un hallazgo.

**Naturaleza del activo.** Una avícola es un negocio de proteína animal: commodity, márgenes estructuralmente finos, intensivo en capital, con riesgo sanitario binario. Los múltiplos de salida en el sector suelen ubicarse en rangos bajos de EBITDA, muy lejos de negocios con activos intangibles. **Consecuencia estratégica:** en este activo la creación de valor viene de volumen y eficiencia operativa, no de expansión de múltiplo. Si el plan de 30 años contempla una salida relevante, hay que construir deliberadamente lo que hace subir el múltiplo — contratos de largo plazo, marca, integración vertical, diversificación de clientes, contabilidad auditable — y nada de eso ocurre por accidente.

**El riesgo que nadie nombró.** El costo de alimento representa la mayoría del costo de producción, y está denominado en maíz y soya con precio internacional en dólares. El precio de venta es en pesos, en mercado local. Estructuralmente, **la Avícola es una posición apalancada corta en granos y corta en dólar**. Eso no es una opinión, es contabilidad. Un movimiento adverso simultáneo de grano y tipo de cambio puede comprimir el margen a negativo sin que nada operacional haya fallado. Ese riesgo es cubrible, al menos parcialmente, mediante compras a plazo, contratos de suministro o instrumentos de cobertura. El documento tiene una "Política de Riesgo" de cuatro líneas que no lo menciona.

**Sobre valoración y ROIC.** Insisto con el CFO: exijo el desglose de capex. FCF = EBITDA − capex de mantención − variación de capital de trabajo − impuestos. En avicultura el capex de mantención es alto y se confunde rutinariamente con crecimiento, lo que infla el ROIC aparente. Sin ese desglose, "reinvertir agresivamente porque el ROIC es alto" puede significar "reinvertir agresivamente en reponer lo que se está gastando".

**Sobre el WACC implícito.** Se habla de que toda inversión compita por el capital, pero no se define contra qué tasa. Sin una tasa de descuento explícita —costo de la deuda de la empresa más una prima por riesgo del proyecto— la comparación entre "otro galpón" y "un ETF" no es una comparación, es una preferencia.

### Integrante 5 — Devil's Advocate

Mi trabajo es destruir lo anterior. Empiezo por lo que todos aceptaron sin examinar.

**Supuesto oculto 1 — que el ROIC alto persiste.** Todo el comité razonó sobre "ROIC marginal 25–35%". En proteína animal, los retornos supranormales atraen capacidad y se comprimen. Además, este mercado tiene incumbentes con escala e integración vertical que un productor mediano no puede replicar. El escenario más probable a 30 años no es "la avícola compone al 30% indefinidamente"; es "compone bien durante 5–8 años y luego converge". El documento —y el CFO— tratan la Etapa 1 como si su duración fuera conocida. No lo es, y el error de estimarla mal es asimétrico: sobreextenderse en concentración es mucho más caro que diversificar un año antes de tiempo.

**Supuesto oculto 2 — que el marco tributario de 2026 existirá en 2056.** El contador acaba de construir el argumento más fuerte de la sesión sobre diferimiento. Pero el sistema chileno cambió sustantivamente en 2014 y en 2020, y la presión reformista es permanente. **Si la justificación principal del holding es fiscal, la estructura es frágil por diseño.** Propongo un principio rector que el documento no tiene: *toda decisión estructural debe justificarse por razones no tributarias — control, protección, gobierno, liquidez — y tratar el beneficio fiscal como un residuo agradable, no como la tesis.* Con ese filtro, el holding sigue justificándose. Pero por otras razones, y eso importa para cómo se diseña.

**Supuesto oculto 3 — que existe un patrimonio que proteger dentro de 30 años.** Chile enfrentó brotes de influenza aviar en 2023. Un brote implica despoblamiento sanitario, zonas de restricción y meses sin ingreso, con la estructura de costos corriendo igual. Combínese eso con: 100% del patrimonio en el negocio, avales personales firmados, y deuda de expansión. El resultado no es "un mal año". Es ruina personal. **El documento dedica quince secciones a optimizar la trayectoria de un patrimonio y ninguna a garantizar que sobreviva al evento que estadísticamente lo termina.**

**Sesgo detectado.** El documento exhibe sesgo de construcción: diseñar una arquitectura patrimonial de 20 años es intelectualmente gratificante; contratar un seguro sanitario, revisar el régimen matrimonial, hacer testamento y montar contabilidad de costos es tedioso. El documento hizo lo entretenido y postergó lo que salva. Añado que se autoevaluó 9,5/10, lo cual es un dato sobre el autor, no sobre el documento.

**Escenario extremo que nadie planteó.** Tomás muere a los 45 con la avícola apalancada, el holding constituido y sin testamento. Los herederos reciben acciones de un holding que controla una empresa que ninguno sabe operar, con avales que se ejecutan contra la masa hereditaria. El holding, en ese escenario, **agravó** el problema: añadió una capa societaria más que liquidar. Un holding sin plan de sucesión no es protección, es complejidad adicional heredada.

**Objeción al contador.** El argumento de diferimiento es correcto, pero incompleto: asume que Tomás no necesita retirar. Si el gasto personal obliga a retiros relevantes todos los años, el diferimiento aplica solo al remanente y el beneficio se reduce proporcionalmente. Nadie preguntó cuánto gasta Tomás al año. Sin ese número, la tabla del contador es una ilustración, no un cálculo.

---

## 3. Debate

**CFO → Devil's Advocate:** Acepto la objeción sobre persistencia del ROIC. Pero tu conclusión implícita —diversificar antes— tiene un costo real: cada peso que sale del negocio a un 30% de retorno marginal para ir a un ETF al 7% destruye valor esperado. No podés tratar la diversificación como gratis.

**Devil's Advocate → CFO:** No la trato como gratis. La trato como **prima de seguro**. Vos estás maximizando valor esperado; yo estoy minimizando probabilidad de ruina. Son objetivos distintos y el segundo domina, porque la ruina es absorbente: no hay recuperación desde cero cuando además hay avales ejecutados. Un 30% anual sobre un patrimonio que tiene 3% de probabilidad anual de irse a cero tiene un valor esperado geométrico mucho peor que el aritmético que estás calculando.

**Corporate Finance → ambos:** Los dos están discutiendo la magnitud sin haber definido la unidad. Vuelvo a mi punto: no sabemos el ROIC marginal real porque no sabemos el capex de mantención. Si el número verdadero es 12% en lugar de 30%, la discusión se termina sola y el Devil's Advocate gana sin necesidad de invocar la ruina. **Sugiero que la disputa quede formalmente suspendida hasta tener el dato.**

**CFO:** Concedido. Retiro mi objeción como categórica y la reformulo como condicional al dato.

**Contador → Devil's Advocate:** Sobre tu crítica al diferimiento. Es válida y la incorporo: el beneficio es proporcional a la fracción no retirada. Pero eso refuerza mi punto sobre el régimen transparente en lugar de debilitarlo — porque en transparente Tomás tributa sobre el 100% independientemente de lo que retire. Cuanto mayor la fracción reinvertida, peor es transparente. Y este perfil es de reinversión agresiva.

**Abogado → Contador:** De acuerdo con el diagnóstico, pero cuidado con la secuencia que estás proponiendo. Constituir el holding para salir de transparente es usar una estructura permanente para resolver un problema que tiene solución directa: el cambio de régimen. Si la única razón para el holding fuera ésa, sería desproporcionado. Sostengo que el holding se justifica de todos modos —control, sucesión mediante series de acciones, incorporación de futuras empresas sin reorganizar— pero quiero que quede en acta que **la razón tributaria no debe ser la razón principal**, exactamente por el argumento de fragilidad regulatoria del Integrante 5.

**Devil's Advocate → Abogado:** Registro que coincidimos, lo cual me obliga a examinarlo. Encuentro un contraargumento a mí mismo: si el marco tributario cambia, un holding ya constituido es más fácil de adaptar que uno por constituir, porque la reorganización futura ocurriría con la empresa ya valorizada. Es decir, la incertidumbre regulatoria es un argumento a favor de constituir temprano, no en contra. Retiro parcialmente mi objeción sobre fragilidad: aplica al *diseño de detalle*, no al *timing*.

**Corporate Finance → Abogado:** Añado un argumento no tributario que nadie mencionó y que a mí, como comprador potencial, me importa mucho: **una estructura limpia vale dinero en una venta**. Un comprador que hace due diligence sobre una sociedad donde se mezclaron gastos personales, activos no operacionales y préstamos entre partes relacionadas descuenta el precio o exige escrows. Separar operación de patrimonio desde temprano no es solo protección: es preparación de la salida, y se traduce en múltiplo.

**Contador:** Ése es el mejor argumento pro-holding de la sesión, y es completamente independiente de la legislación tributaria vigente. Lo suscribo.

**Devil's Advocate — objeción final:** Todo el comité convergió en "constituir el holding temprano". Antes de cerrar, exijo que quede consignado lo siguiente: el comité **no** está diciendo que el holding sea la acción más urgente. Está diciendo que es barata ahora y cara después. Son cosas distintas. Si Tomás sale de esta reunión y dedica los próximos tres meses a la arquitectura societaria sin haber contratado un seguro sanitario, revisado su régimen matrimonial ni calculado su FCF real, el comité habrá fracasado.

*Acordado por unanimidad.*

---

## 4. Puntos de acuerdo

1. La separación conceptual entre operación, patrimonio y asignación de capital es correcta y es el aporte real del documento v1.0.
2. El holding se justifica principalmente por razones **no tributarias**: control, sucesión, incorporación de futuras empresas y limpieza para una eventual venta. El beneficio fiscal es un residuo, no la tesis.
3. **El timing favorece constituir temprano.** El costo de la reorganización crece con la brecha entre valor económico y costo tributario de la Avícola.
4. La afirmación de escalabilidad simétrica ("de $20 millones a $5.000 millones") es falsa. Existe un umbral mínimo bajo el cual la estructura destruye valor.
5. Las secciones 8 a 12 del documento no son políticas: no contienen umbrales, gatillos ni responsables. Una política se distingue de una intención en que puede violarse de forma verificable.
6. Falta instrumentación. Sin capex de mantención separado, sin FCF real y sin ROIC marginal, la política de asignación de capital carece de insumo.
7. Faltan tres protecciones básicas: seguro (sanitario, responsabilidad civil, vida), definición del régimen patrimonial matrimonial, y testamento.
8. La exposición a maíz/soya en USD contra ingresos en CLP es un riesgo material, cubrible y no abordado.
9. Prohibición absoluta de canalizar gastos personales por cualquier sociedad, desde el día uno.

## 5. Puntos de desacuerdo (no resueltos)

| Tema | Posición A | Posición B | Estado |
|---|---|---|---|
| Ritmo de diversificación | CFO / Corp. Finance: concentrar mientras ROIC marginal supere alternativas | Abogado / Devil's Advocate: extraer un colchón fijo fuera del perímetro de riesgo desde ya, sin importar el ROIC | **Suspendido** hasta conocer ROIC marginal real y FCF |
| Urgencia del holding | Contador: alta, ligada al cambio de régimen | Abogado: media; el cambio de régimen tiene solución directa | Parcialmente resuelto: se constituye temprano, pero no es prioridad #1 |
| Peso del argumento fiscal | Contador: el diferimiento es el motor de la composición | Devil's Advocate: diseñar sobre normativa mutable es frágil | **Resuelto por síntesis:** justificar por razones no tributarias, capturar el beneficio fiscal como consecuencia |

## 6. Riesgos detectados

**Catastróficos (probabilidad baja, impacto terminal)**

- Brote sanitario con despoblamiento y restricción de zona, sobre patrimonio 100% concentrado y con avales personales vigentes.
- Fallecimiento o incapacidad de Tomás sin testamento, con la empresa operando y apalancada.
- Ejecución de avales personales por incumplimiento de la sociedad operativa.

**Estructurales (probabilidad alta, impacto acumulativo)**

- Régimen tributario subóptimo drenando caja reinvertible cada año.
- Compresión del margen por movimiento adverso de granos y tipo de cambio.
- Convergencia del ROIC a la media sectorial antes de lo supuesto, con capital ya comprometido en expansión.
- Decisiones de asignación de capital tomadas sobre ROIC contable inflado por capex de mantención mal clasificado.

**De ejecución**

- Costo recurrente del holding superando su beneficio a patrimonios bajos.
- Contaminación contable por mezcla de gastos personales y societarios, con impacto en valoración futura.
- Riesgo de reorganización cuestionada si no se acredita legítima razón de negocios.

## 7. Escenarios

### Conservador

Se posterga el holding. Se ejecuta primero: definición de régimen tributario, seguros, régimen matrimonial, testamento, instrumentación contable. Se extrae anualmente una fracción fija de utilidad fuera del perímetro de riesgo, en instrumentos líquidos, aunque el ROIC del negocio sea superior.

- *Ventaja:* elimina los riesgos terminales primero.
- *Desventaja:* la reorganización futura será más cara; se sacrifica composición.
- *Adecuado si:* el FCF real resulta bajo, o si hay socios y estructura poco clara.

### Moderado — **recomendado por el comité**

Se ejecutan en paralelo dos vías. Vía A (protección, inmediata): seguros, régimen matrimonial, testamento, límites al aval. Vía B (estructura, 6–12 meses): definición de régimen tributario y constitución del holding como SpA con estatutos flexibles, aprovechando que la Avícola aún tiene valorización baja. Se mantiene reinversión mayoritaria en la Avícola, con una fracción fija de utilidad extraída anualmente como reserva de supervivencia, tratada como prima de seguro y no como inversión.

- *Ventaja:* captura la ventana barata de reorganización sin postergar la protección.
- *Desventaja:* exige ejecutar dos frentes simultáneos con recursos limitados.

### Agresivo

Reinversión cercana al 100% en la Avícola mientras el ROIC marginal supere el umbral, holding constituido de inmediato, apalancamiento activo para acelerar expansión, diversificación postergada a la Etapa 3 del documento.

- *Ventaja:* máximo valor esperado aritmético si el ROIC persiste.
- *Desventaja:* maximiza simultáneamente la probabilidad de ruina.
- *Condición del comité:* solo viable **si** existen previamente seguro sanitario contratado, cobertura de insumos, y liberación o acotamiento de avales personales — es decir, si el riesgo de cola está cerrado por otra vía.

## 8. Recomendación final del comité

**Escenario Moderado, con la siguiente secuencia estricta:**

1. **Primero, medir.** Nada del documento v1.0 es ejecutable sin FCF real y ROIC marginal. Sin esos números, las políticas 9 y 10 son declaraciones de fe.
2. **Segundo, no morir.** Seguros, régimen matrimonial, testamento, acotamiento del aval. Costo bajo, impacto terminal. Estas medidas dominan al holding en costo-beneficio y el documento las omitió por completo.
3. **Tercero, definir el régimen tributario.** Es la decisión con mayor impacto compuesto a 30 años y es previa a la estructura, porque la condiciona.
4. **Cuarto, constituir el holding.** Como SpA, con estatutos que contemplen series de acciones desde el origen, y con la justificación documentada en razones de negocio —control, incorporación de futuras empresas, preparación para venta— y no en el ahorro fiscal.
5. **Quinto, convertir las secciones 8–12 en políticas reales,** con umbral numérico, gatillo y consecuencia. Ejemplo mínimo de forma: *"Liquidez fuera del perímetro operativo ≥ 6 meses de gasto personal + 3 meses de costo operacional de la Avícola. Si cae bajo el umbral, se suspende toda nueva inversión hasta reponerla."*

**El comité califica el documento v1.0 como una declaración de filosofía correcta, no como una arquitectura ejecutable.** Su déficit no es de dirección estratégica sino de especificidad y de orden de prioridades.

## 9. Plan de acción

### Corto plazo (0–3 meses)

- [ ] Determinar el régimen tributario vigente de la Avícola y evaluar con contador el cambio, cuantificando el efecto en caja de los próximos 5 años.
- [ ] Contratar o revisar coberturas: sanitaria/pecuaria, responsabilidad civil, y seguro de vida dimensionado para dar liquidez a la sucesión y cubrir avales vigentes.
- [ ] Definir formalmente el régimen patrimonial matrimonial con abogado.
- [ ] Otorgar testamento.
- [ ] Inventariar todos los avales y garantías personales firmados a la fecha.
- [ ] Instrumentar contabilidad de costos: separar capex de mantención de capex de crecimiento; calcular FCF de los últimos 24 meses.
- [ ] Establecer y hacer cumplir la separación absoluta de gastos personales y societarios.

### Mediano plazo (3–18 meses)

- [ ] Calcular ROIC y ROIC marginal por proyecto de expansión, con tasa de descuento explícita.
- [ ] Constituir el holding como SpA con estatutos preparados para series de acciones; evaluar con asesores la vía y el momento del aporte de la participación en la Avícola.
- [ ] Si existen socios: pacto de accionistas con derecho preferente, fórmula de valorización, cláusulas de salida y de fallecimiento/incapacidad.
- [ ] Diseñar cobertura de insumos (compras a plazo, contratos de suministro o instrumentos financieros) para acotar la exposición a granos y tipo de cambio.
- [ ] Formalizar la política de distribución de utilidades con porcentajes objetivo y proceso de revisión anual.
- [ ] Establecer la reserva de supervivencia fuera del perímetro de riesgo, con monto objetivo definido.

### Largo plazo (18 meses–10 años)

- [ ] Revisión anual del ROIC marginal como gatillo objetivo del paso de Etapa 2 a Etapa 3.
- [ ] Construir deliberadamente los atributos que expanden múltiplo de salida: contratos de largo plazo, diversificación de clientes, contabilidad auditable, dependencia reducida del fundador.
- [ ] Incorporar gobierno corporativo formal —acta anual del comité, política de partes relacionadas— antes de que la complejidad lo exija.
- [ ] Revisión estructural cada 3 años o ante cambio normativo relevante.

## 10. Información adicional requerida

El comité considera **provisionales** todas las conclusiones anteriores hasta disponer de:

**Crítico (bloquea conclusiones)**

1. ⬜ **Régimen tributario actual de la Avícola:** 14 A, 14 D N°3 o 14 D N°8. — **PENDIENTE. Único bloqueante que queda.**
2. ✅ **Estructura de propiedad** — *Resuelto (ACTA-002):* 50/50 entre Tomás Núñez Smith y Cristóbal Merino Lind, 1.000 acciones cada uno. Socios por amistad. La inconsistencia del documento v1.0 queda confirmada: **sí hay socio**, y el diagrama de un solo dueño era erróneo.
3. ⬜ Ingresos, EBITDA y capex, con capex separado en mantención vs. crecimiento. — *Aún no aplicable: producción no iniciada. **Montar la instrumentación antes del primer lote**.*
4. ⬜ Deuda vigente y detalle de avales/garantías personales firmadas.
5. ⬜ Estado civil y régimen patrimonial de Tomás.
6. ⬜ Gasto personal anual de Tomás y monto de retiros efectivos.

**Importante**

7. ✅ **Costo tributario de la participación** — *Resuelto:* $10.000 (1.000 acciones a $10 c/u). Utilidades retenidas: nulas o mínimas, sociedad constituida en febrero de 2026. **La ventana de reorganización está en su punto más barato.**
8. ✅ **Capital efectivo** — *Resuelto:* $20.000. Muy por debajo del límite de 85.000 UF. Elegibilidad Pro Pyme no está en riesgo por capital.
9. ⬜ Estructura de costos: peso del alimento y política de compra de insumos.
10. ⬜ Qué es "Taurus" y en qué etapa se encuentra.
11. ⬜ Contratos de venta: concentración de clientes y plazos.

**Nuevos, incorporados en v1.1**

12. ⬜ Origen y monto de los fondos invertidos por cada socio a la fecha (¿aporte, préstamo de socios o deuda bancaria?).
13. ⬜ Existencia del Registro de Accionistas propio de la sociedad.
14. ⬜ Existencia de acuerdos verbales entre socios no documentados.

---

## Anexo A — Incorporación del Integrante 6: Arquitecto de Patrimonio

Con posterioridad al cierre de esta sesión se acuerda incorporar un sexto integrante permanente al comité. **No participó en las deliberaciones de la Sesión 001**; se registra aquí su mandato y su primera observación retroactiva.

### Mandato

No es especialista en una disciplina. Su misión es asegurar que cada decisión sea coherente con la arquitectura patrimonial de 20–30 años, evitando **optimizaciones locales que compliquen el sistema completo**. No reemplaza al CFO, al abogado ni al contador: los arbitra cuando sus óptimos parciales entran en conflicto con el óptimo del sistema.

### Preguntas rectoras

1. ¿Esta decisión obliga a reestructurar el holding en cinco años?
2. ¿Escala cuando existan cinco empresas y no una?
3. ¿Facilita la entrada de nuevos socios o inversionistas?
4. ¿Hace más sencilla una futura venta o sucesión?
5. ¿Es consistente con la visión de Family Office?

### Criterio de decisión

Ante empate entre alternativas, prefiere la que **preserva opcionalidad** aunque sacrifique eficiencia inmediata. El costo de una estructura sobredimensionada es lineal (honorarios recurrentes); el costo de una estructura subdimensionada es escalonado (reorganización con la empresa ya valorizada). La asimetría favorece construir un escalón por encima de la necesidad presente — sin llegar a construir tres.

### Observación retroactiva sobre la Sesión 001

El comité convergió correctamente en el *timing* pero razonó el holding como estructura para **una** empresa con activos adjuntos. Para cinco empresas, el patrón correcto es **una sociedad operativa por unidad de negocio, colgando todas del mismo holding**, sin participaciones cruzadas entre operativas y sin activos productivos (inmuebles, marcas, maquinaria relevante) dentro de las sociedades operativas. Consecuencias que la Sesión 001 no consignó:

- **Inmuebles y propiedad intelectual no deben quedar en la Avícola.** Si el terreno o los galpones son propiedad de la sociedad operativa, quedan expuestos al riesgo operacional *y* se venden junto con el negocio en una eventual salida, cuando probablemente Tomás querría conservarlos y arrendarlos. Separarlos hoy es barato; separarlos después de valorizados es un evento tributario.
- **La sección 5 del documento v1.0 asigna al holding la administración de liquidez e inversiones financieras.** A escala de cinco empresas eso mezcla dos funciones distintas —control societario y gestión de portafolio— en una sola entidad, y complica la entrada de un inversionista que quiera exponerse a una operativa sin exponerse al portafolio personal. Debe evaluarse desde ya si el vehículo de inversiones financieras se separa del vehículo de control.
- **La entrada de un inversionista externo debe ocurrir a nivel de la sociedad operativa, nunca del holding.** El holding es el perímetro de la familia. Si el documento v1.0 no lo declara explícitamente, la primera ronda de capital lo va a decidir por defecto y mal.

Estos tres puntos se someten formalmente a la Sesión 002.

---

## Control del documento

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 2026-07-29 | Acta inicial de la Sesión 001. Anexo A: incorporación del Integrante 6. |
| 1.1 | 2026-08-04 | Banner de actualización. Corrección de tasa Pro Pyme (25% → 12,5%). Sección 10 actualizada con datos confirmados. Rectificación del error sobre derecho preferente. Subordinación de prioridades a ACTA-002. |

**Documento fuente analizado:** "Diseño del Holding Familiar — Arquitectura Patrimonial Estratégica v1.0" (julio 2026).
**Sesión posterior:** [ACTA-002 — Auditoría de estatutos de Avícola Limache SpA](ACTA-002-estatutos-avicola-limache.md) (2026-08-04).
**Próxima sesión:** 003 — condicionada al resultado de la conversación con el socio y a la determinación del régimen tributario.

**Fuentes consultadas**

- [Regímenes Tributarios — SII](https://www.sii.cl/destacados/renta/2025/regimenes_renta2025.html)
- [Régimen Pro Pyme Transparente 14 D N°8 — Edig](https://edig.cl/2020/10/07/regimen-pro-pyme-transparente-14-d-n8/)
- [Régimen Pro Pyme General 14 D N°3 — Edig](https://edig.cl/2020/10/07/regimen-pro-pyme-general-14-d-n-3/)
- [Holding operacional vs patrimonial en Chile — Lofwork](https://www.lofwork.cl/holding-operacional-vs-patrimonial/)
