# ¿Se pensionarán los contratistas del Estado? Resumen de resultados (notebooks 01–04)

**Datos:** solo SECOP II (datos.gov.co): contratos de prestación de servicios firmados con personas naturales
(cédula). Los años de análisis son 2022–2025. 2020–2021 se usan solo para medir antigüedad y 2026 está incompleto.
Las únicas constantes externas son las de ley: el SMMLV de cada año y la regla del IBC del independiente
(40% del honorario, con piso de 1 SMMLV). El SMMLV de 2026 ($1.750.905, Decreto 1469 de 2025) se verificó en la web.

Todas las cifras de este resumen salen de `outputs/resultados.json` y de las tablas de `outputs/tablas/`.
La pensión está en el notebook 05: **ver `RESUMEN_05.md` y `resultados_05.json`**.

---

## 1. Trayectorias: la tabla persona-año (01)

- **Tabla:** 1.825.478 filas persona-año, que corresponden a 848.267 personas distintas entre 2022 y 2025.
- **Personas activas por año:** 402.755 en 2022, 437.494 en 2023, 471.549 en 2024 y 513.680 en 2025.
- **Método:** se toman los contratos firmados en *t−1* y *t*, se recortan al año *t*, se unen los intervalos
  solapados (ordenar + máximo acumulado del fin) y se cuentan los días de forma inclusiva.
  Meses = días × 12 / días del año.

**Validación contra el hallazgo previo de 2024.** Se reproduce, y una revisión independiente lo confirmó persona por
persona con otro método.

| Cifra 2024 | Esperado | Obtenido |
|---|---|---|
| Personas activas | 471.547 | 471.549 |
| Meses cubiertos: mediana (p25 – p75) | 7,9 (4,1 – 10,3) | 7,93 (4,13 – 10,33) |
| Con 11 meses o más | 13,2% | 13,2% (62.231 personas) |
| Con menos de 6 meses | 36,1% | 36,05% |
| Honorario mensual mediano | $3,95M | $3,95M |
| Cotiza sobre el mínimo | 37,5% | 37,4% |
| Semanas al año (mediana) | 34,4 | **34,6** |
| Años para llegar a 1.300 semanas | 37,8 | **37,6** |

El 34,4 previo sale de convertir la mediana ya redondeada (7,9 meses) a semanas. La cifra exacta es 34,6 semanas al
año, es decir, 37,6 años para llegar a 1.300 semanas.

**Sensibilidad de las definiciones** (documentada en el 01):
- **"11 meses" se mide en días.** Equivale a 336 días en 2024. Si se usaran meses calendario (por ejemplo, del
  1-feb al 31-dic), el 13,2% subiría a 14,7%.
- **El IBC usa la mediana del honorario, no la suma de contratos simultáneos.** Con la suma, el porcentaje que
  cotiza sobre el mínimo en 2024 baja de 37,4% a 36,5%. Según cómo se mensualice el honorario, queda entre 36,5% y
  38,7%.

## 2. Exploración (02)

| Año | Mediana de meses | % menos de 6 meses | % 11 meses o más | Honorario mediano | % cotiza sobre el mínimo | Años a 1.300 semanas (mediana) |
|---|---|---|---|---|---|---|
| 2022 | 10,0 | 28,5% | 25,4% | $3,35M | 31,1% | 29,9 |
| 2023 | 9,3 | 25,4% | 17,7% | $3,56M | 36,3% | 32,3 |
| 2024 | 7,9 | 36,1% | 13,2% | $3,95M | 37,4% | 37,6 |
| 2025 | 9,0 | 27,0% | 17,6% | $4,06M | 40,0% | 33,1 |

- **2024 es el peor año.** Coincide con el primer año de los nuevos gobiernos locales. 2022 se ve mejor porque, por
  la Ley de Garantías, muchas entidades firmaron en enero contratos para todo el año.
- **Cotizar sobre el mínimo es cada vez más común:** pasa de 31% a 40% entre 2022 y 2025. El SMMLV subió 42% y el
  honorario mediano solo 21%.
- **Género.** Mujeres y hombres tienen los mismos meses de contrato. La brecha agregada de honorario es de solo
  1–2%, pero es un **efecto de composición**: dentro de cada tipo de contrato la brecha es mayor (1,8% en apoyo a la
  gestión, 5,4% en profesionales y 6,7% en "otro"). Es descriptivo: no controla cargo ni experiencia.
- **Nacional frente a territorial (2024):**

  | | Mediana de meses | Honorario mediano | Cotiza sobre el mínimo |
  |---|---|---|---|
  | Nacional | 9,2 | $4,49M | 25% |
  | Territorial | 7,3 | $3,51M | 45% |

- **Ubicación.** Las entidades con sede en Bogotá contratan al 37% de las personas. Esto incluye a las entidades
  nacionales y no es dónde vive la persona.
- **Estacionalidad.** La contratación se concentra en **enero y febrero**. En los años normales el pico es febrero.
  En los años de Ley de Garantías todo se adelanta a enero (279 mil contratos en ene-2022 y 455 mil en ene-2026) y
  luego hay un vacío: de marzo a junio de 2022 el promedio fue de unos 3 mil contratos al mes, frente a 60 mil en
  2023.

## 3. Tipos de trayectoria: clustering (03)

- **Modelo:** K-means con k = 4 y `n_init = 20`, sobre 848.267 personas y 12 variables estandarizadas.
- **Estabilidad:** el ARI con otras semillas es de 0,999 y en una submuestra del 50% es de 0,997. Con `n_init = 1`
  puede caer en otro óptimo (ARI 0,44), por eso se usan 20 inicializaciones.
- **Silueta:** 0,193 con k = 4, frente a 0,186 con k = 3 y 0,155 con k = 5. Es un máximo local pequeño.
- **Contra un GMM:** concordancia baja (ARI 0,13) y silueta del GMM de 0,09.
- **Conclusión:** las trayectorias son un **continuo**. Los clusters sirven para resumir y no son grupos naturales.

| Tipo | Personas | % | Años activos (de 4) | Meses/año observable | Entidades/año | Huecos/año | Honorario mediano | % años cotiza mínimo | Semanas/año (mediana) | Activo en 2025 |
|---|---|---|---|---|---|---|---|---|---|---|
| **Estables** | 249.680 | 29,4% | 3,1 | 9,0 | 1,04 | 0,32 | $4,13M | 29% | 40,6 | 89% |
| **Multientidad** | 55.872 | 6,6% | 2,9 | 8,1 | 1,90 | 0,45 | $4,96M | 17% | 37,8 | 78% |
| **Intermitentes** | 184.455 | 21,7% | 2,1 | 5,9 | 1,03 | 1,00 | $2,98M | 53% | 25,2 | 59% |
| **Ocasionales** | 358.260 | 42,2% | 1,4 | 2,9 | 1,01 | 0,05 | $3,28M | 46% | 11,4 | 39% |

- **Estables:** un contrato largo al año con la misma entidad. La mitad de sus contratos son con entidades
  nacionales.
- **Multientidad:** en promedio casi 2 entidades por año, y la mitad (49,8%) trabaja con 2 o más. Tienen el
  honorario más alto.
- **Intermitentes:** contratos cortos con huecos. Son sobre todo territoriales y muchos dejan de aparecer después de
  2023. En la cohorte de 2022 pasan de 8,5 meses en 2022 a 2,7 meses en 2024.
- **Ocasionales:** 1 o 2 años con pocos meses. El 23% entra en 2025, así que una parte son recién llegados con un solo
  año observado.

## 4. ¿Qué predice la continuidad? Modelo supervisado (04)

- **Objetivo:** tener 9 meses o más de contrato en *t+1*, usando solo variables de *t*.
- **Validación:** solo hacia adelante. Se entrena con 2022→2023 y se valida con 2023→2024.
- **Prueba:** el modelo se entrena con los dos pares y se evalúa una sola vez en 2024→2025 (471.549 personas,
  tasa base de 48,0%).
- **Sin leakage:**
  - No se usan `estado_contrato`, `valor_pagado`, `dias_adicionados_total` ni nada de *t+1*.
  - El *target encoding* de la entidad usa solo pares anteriores: fuera de fold dentro de 2022→2023.
  - Las categorías, la calibración, el umbral y el modelo final se eligen en validación.

| Modelo (prueba 2024→2025) | AUC validación | ROC-AUC | PR-AUC | F1 | Exactitud balanceada |
|---|---|---|---|---|---|
| Dummy | 0,500 | 0,500 | 0,480 | 0,649 | 0,500 |
| **Persistencia (score = meses en t)** | 0,712 | **0,724** | 0,676 | 0,626 | 0,672 |
| Persistencia, umbral fijo de 9 meses | – | 0,724 | 0,676 | 0,635 | 0,675 |
| Contrato vigente al 31-dic (desempate por meses) | 0,731 | 0,697 | 0,653 | 0,673 | 0,652 |
| Días ya firmados para t+1 (desempate por meses) | 0,734 | 0,736 | 0,692 | 0,640 | 0,681 |
| **Logística con 5 variables de persona** | 0,742 | **0,736** | 0,679 | 0,531 | 0,630 |
| Logística completa | 0,729 | 0,730 | 0,687 | 0,591 | 0,648 |
| **Random Forest (modelo final: mayor AUC en validación)** | **0,756** | **0,733** | **0,697** | 0,556 | 0,639 |
| LightGBM, persona + entidad | 0,751 | 0,721 | 0,682 | 0,483 | 0,612 |
| LightGBM, solo persona | 0,749 | 0,732 | 0,695 | 0,505 | 0,634 |
| LightGBM, persona + contexto del año | – | 0,733 | 0,692 | 0,472 | 0,620 |

**Lectura honesta:**
- **El ML le gana muy poco a la persistencia.** El modelo final logra +0,009 de ROC-AUC y +0,021 de PR-AUC. Una
  logística de 5 variables, o la regla de "días ya firmados", rinde lo mismo. Con un año de historia, la continuidad
  es **poco predecible** (AUC ≈ 0,73).
- **En F1 y exactitud balanceada, los modelos quedan por debajo de la persistencia.** El umbral se eligió en un año
  de validación atípico.
- **Las variables de entidad no ayudan, y el contexto electoral no se puede estimar** con solo dos años de
  entrenamiento.
- **Calibrar con un año atípico empeora.**
  - La isotónica aprendida en 2023→2024 (tasa base de 35%) baja la probabilidad media en 2025 a 24%, cuando la tasa
    real fue 48%. El Brier del Random Forest empeora de 0,221 a 0,269.
  - Sin calibrar, la probabilidad media es de 38%.
  - Por eso `data_intermedia/riesgo_2024_2025.parquet` lleva la probabilidad **sin calibrar**. Esta decisión se tomó
    después de ver la prueba y se declara en el notebook.
- **Lo que más pesa** (gain de LightGBM): meses cubiertos en *t* (42%), días sin contrato al cierre del año (18%) y
  renovación histórica de la entidad (10%).
- **Con información de fin de año** (contratos ya firmados para *t+1*), el AUC sube a 0,738.
- **Equidad:** el AUC es igual para hombres y mujeres (0,72). El grupo con género "No Definido" es el peor
  calibrado.

**El hallazgo que sí sirve: el modelo separa el riesgo, sobre todo en los extremos.** Convención: D1 = mayor riesgo.

| Decil | D1 | D2 | D3 | D4 | D5 | D6 | D7 | D8 | D9 | D10 |
|---|---|---|---|---|---|---|---|---|---|---|
| Tasa real de continuidad en 2025 (modelo) | **8,7%** | 22,5% | 35,9% | 42,6% | 50,2% | 53,8% | 54,4% | 61,7% | 67,6% | **82,5%** |
| Misma tasa ordenando solo por meses en 2024 | 22,1% | 23,7% | 30,1% | 34,3% | 41,1% | 49,6% | 61,7% | 69,2% | 72,5% | 75,5% |
| % que no aparece en 2025 | 67,9% | 39,4% | 25,8% | 25,8% | 22,6% | 17,3% | 22,4% | 18,9% | 13,4% | 6,5% |

En el 10% de mayor riesgo solo el 9% continúa y dos de cada tres desaparecen de SECOP II. Ordenando solo por meses,
ese decil tendría un 22% de continuidad: el modelo identifica mejor a quienes están en riesgo, aunque casi no mejore
el AUC.

## 5. Pensión (05)

**Ver `RESUMEN_05.md` y `resultados_05.json`**, de otro agente. Si el 05 se ejecutó antes de las 19:11, hay que
volver a ejecutarlo: el 04 regeneró `riesgo_2024_2025.parquet` (modelo final: Random Forest; D1 = mayor riesgo) y el
03 regeneró `clusters_personas.parquet` (misma partición, ARI ≈ 1).

---

## Figuras (`outputs/figs/`, 200 dpi)

| Archivo | Qué muestra | Diapositiva sugerida |
|---|---|---|
| `02_distribucion_meses_cubiertos_2024.png` | Histograma de meses con contrato en 2024: mediana de 7,9; 36% con menos de 6 meses; 13% con 11 o más | El problema: el contratista típico no trabaja todo el año |
| `02_evolucion_tramos_meses_por_anio.png` | Tramos de meses por año, 2022–2025; 2024 es el peor | Evolución y efecto del ciclo político |
| `02_serie_mensual_contratos_firmados.png` | Contratos firmados por mes, 2020–sep 2026: picos en enero y febrero, vacíos por la Ley de Garantías | Por qué hay huecos: el calendario de contratación |
| `02_cotiza_sobre_minimo.png` | Distribución del honorario frente al umbral de 2,5 SMMLV, y % que cotiza sobre el mínimo por año | Cotizar sobre el mínimo |
| `02_nacional_vs_territorial.png` | Meses, honorario y % sobre el mínimo, nacional frente a territorial | Brecha territorial |
| `02_brecha_genero_meses_honorario.png` | Meses iguales por género; brecha de honorario dentro de cada tipo de contrato | Género (efecto de composición) |
| `02_top_departamentos_2024.png` | Top 12 departamentos por ubicación de la entidad | Contexto geográfico (anexo) |
| `03_kmeans_codo_silueta.png` | Codo y silueta (media ± desviación) para k = 2…8 | Método de clustering |
| `03_perfil_clusters.png` | Tamaño, meses, huecos y honorario de los 4 tipos | Los 4 tipos de trayectoria |
| `03_trayectoria_media_por_cluster.png` | Meses por año de la cohorte de 2022, por tipo | Cómo evoluciona cada tipo |
| `03_pca_2d_clusters.png` | PCA 2D con centroides: las trayectorias forman un continuo | Método / anexo |
| `04_curvas_roc_pr.png` | ROC y PR: el ML apenas supera a la persistencia | Resultado honesto del modelo |
| `04_deciles_riesgo.png` | Tasa real de continuidad por decil (D1 de 9% frente a D10 de 82%) comparada con la persistencia | **Diapositiva clave del modelo** |
| `04_matriz_confusion_calibracion.png` | Matriz de confusión y calibración (sin calibrar frente a isotónica) | Anexo: el cambio de prevalencia |
| `04_importancia_variables.png` | Importancia por gain | ¿Qué predice la continuidad? |
| `04_shap_resumen.png`, `04_shap_dependencia_top3.png` | SHAP: dirección de los efectos | Anexo de interpretabilidad |

## Limitaciones

1. **Cobertura parcial de cada persona.** No vemos SECOP I, el empleo formal ni otros ingresos. Los meses sin
   contrato son una **cota superior** de los huecos reales, y los años hasta la pensión, una cota superior del tiempo.
2. **Pocos años.** 2020–2021 tienen baja cobertura de SECOP II, así que la historia útil son 4 años y el modelo se
   entrena con solo dos pares de años. Los choques de año, como el ciclo electoral o los gobiernos locales nuevos,
   no se pueden aprender.
3. **Definiciones sensibles.** Los umbrales están en días/año (ver el 01), el honorario es la mediana por contrato y
   la fecha fin incluye prórrogas. Los contratos cedidos (0,5%) quedan a nombre del contratista original.
4. **Censura.** Quien entra en 2025 solo tiene un año observado. Esto infla el grupo de Ocasionales.
5. **Clusters.** Las siluetas son bajas, así que los grupos resumen un continuo y dependen del método (K-means
   frente a GMM).
6. **Género.** El 22% de las filas persona-año no tiene género definido.
7. **Leakage.** No encontramos fugas hacia la prueba. Las variables de fin de año, como los contratos ya firmados
   para *t+1*, se dejaron fuera del modelo principal y se reportan como sensibilidad.
