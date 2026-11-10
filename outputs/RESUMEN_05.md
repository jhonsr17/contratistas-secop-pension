# Resumen del notebook 05 · ¿Cuándo se pensionaría un contratista?

**Pregunta:** si un contratista de prestación de servicios del Estado empieza a cotizar a los 25 años y mantiene el
ritmo de contratos que tuvo en SECOP II entre 2022 y 2025, ¿a qué edad completaría las semanas de la pensión?

**Regla usada (escenario principal):** hombres 1.300 semanas y edad legal 62; mujeres **1.000 semanas** y edad legal
57. Esto sale de la Sentencia C-197 de 2023 de la Corte Constitucional: desde 2026 las mujeres necesitan 1.250 semanas
y el requisito baja 25 por año hasta 1.000 en 2036. Para quien empieza hoy a los 25, la regla relevante es 1.000.
**Sensibilidad:** 1.300 semanas para todos.

## Hallazgos principales
- **El total:** la mitad de los 848.267 contratistas cotiza menos de
  23,9 semanas al año. A ese ritmo necesitaría
  54 años para juntar 1.300 semanas. Con la regla vigente, solo
  **31%** de quienes tienen género definido completaría sus semanas a su edad legal.
- **El umbral:** un hombre necesita contrato **8,1 meses al año** (35,1 semanas)
  todos los años desde los 25; una mujer, **7,2 meses** (31,25 semanas). Lo
  cumple el 29% de todos los contratistas con el umbral de hombres y el 37% con el de mujeres.
- **Estables** (40,6 semanas/año): completarían sus semanas hacia los
  **54 años** y 77% llega a tiempo. Junto con **Multientidad**
  (60% a tiempo, un grupo pequeño), son los únicos que se acercan a la pensión.
- **Intermitentes** (25,2 semanas/año): necesitarían 52 años
  para 1.300 semanas. Solo 27% llega a tiempo.
- **Ocasionales** (11,4 semanas/año): necesitarían 114 años para
  1.300 semanas (y 89 para 1.000). En la práctica **no se
  pensionan** con contratos del Estado. Son el grupo más grande (42%).
- **Género: la conclusión depende de la regla y, con la vigente, se invierte.** Con 1.000 semanas para mujeres, ellas
  llegan **más** a tiempo que los hombres: **34,5% frente a 26,1%**. Entre los Estables, 83% de mujeres
  frente a 69% de hombres. Si se exigieran 1.300 semanas también a las mujeres (sensibilidad), solo llegaría
  a tiempo el 17,1% de ellas (50% entre las Estables) y la brecha iría en contra de ellas. La versión
  anterior de este notebook usaba esa regla y concluía lo contrario.
- **Por decil de riesgo (modelo del 04, D1 = mayor riesgo):** en D1 llega a tiempo **5%** y la edad mediana de llegada es 101 años; en D10, **94%** y 50 años. El riesgo de corto plazo que predice el modelo se traduce en riesgo pensional.

## Tabla por tipo de trayectoria
| Tipo de trayectoria | Personas | Semanas/año (mediana) | Años hasta 1.300 semanas | Edad de llegada (regla vigente) | Llega a tiempo (regla vigente) | Llega a tiempo (1.300 para todos) | No llega ni a los 80 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Estables | 249.680 | 40,6 | 32 | 54 | 77% | 58% | 1% |
| Multientidad | 55.872 | 37,8 | 34 | 56 | 60% | 46% | 16% |
| Intermitentes | 184.455 | 25,2 | 52 | 69 | 27% | 14% | 32% |
| Ocasionales | 358.260 | 11,4 | 114 | 126 | 2% | 1% | 82% |
| Total | 848.267 | 23,9 | 54 | 75 | 31% | 21% | 46% |

*Semanas/año = días con contrato en 2022–2025 / 7 / años observables. Coincide con el notebook 03
(Estables 40,6; Multientidad 37,8; Intermitentes 25,1; Ocasionales 11,4). "Años hasta 1.300" es la medida neutra
(para todos); la edad de llegada y el "a tiempo" usan la regla de cada género, solo con personas con género definido.*

## Por género (escenario principal y sensibilidad)
| Tipo | Hombres (1.300): edad de llegada | Hombres: a tiempo (62) | Mujeres (1.000): edad de llegada | Mujeres: a tiempo (57) | Mujeres con 1.300: a tiempo |
|---|---:|---:|---:|---:|---:|
| Estables | 57 | 69% | 50 | 83% | 50% |
| Multientidad | 60 | 55% | 52 | 65% | 39% |
| Intermitentes | 76 | 21% | 64 | 32% | 8% |
| Ocasionales | 139 | 1% | 114 | 3% | 0% |
| Total | 83 | 26% | 69 | 35% | 17% |

## Simulador `cuando_me_pensiono(...)`
`cuando_me_pensiono(meses_por_anio, honorario_mensual, semanas_actuales=0, edad_actual=25, genero="Hombre", n_entidades=1, semanas_requeridas=None)`
devuelve las semanas exigidas (1.300 hombre, 1.000 mujer; `semanas_requeridas` permite la sensibilidad), semanas por
año, IBC (máx(40% del honorario, SMMLV 2025 = $1.423.500)), si cotiza sobre el mínimo, años que faltan, edad a la
que llega, edad legal y el tipo de trayectoria más probable.

El tipo de trayectoria lo asigna un **árbol de decisión de profundidad 3** entrenado con las etiquetas del
notebook 03 y solo tres variables que una persona puede escribir (meses de contrato al año, honorario y número de
entidades). **Exactitud en prueba: 69,8%** (exactitud balanceada 72,4%).
Sin pesos por clase la exactitud sube a 71,2%, pero el árbol nunca predice "Intermitentes", por eso usamos la
versión balanceada. Si además se conocen los contratos por año, la exactitud llegaría a 80,0%.
El honorario no entra en el árbol: lo que define el tipo son los meses al año y las entidades.

Reglas simplificadas:
- SI entidades al año ≤ 1,42 Y meses de contrato al año ≤ 5,04 → **Ocasionales**
- SI entidades al año ≤ 1,42 Y 5,04 < meses de contrato al año ≤ 8,98 → **Intermitentes**
- SI entidades al año ≤ 1,42 Y meses de contrato al año > 8,98 → **Estables**
- SI entidades al año > 1,42 → **Multientidad**

Ejemplos:
- *Profesional con contrato casi todo el año* (11,0 meses/año, $5,0M, Mujer, 28 años, 150 semanas): necesita 1.000 semanas; 47,8 semanas/año, faltan 17,8 años → llega a los 46 (edad legal 57); con 1.300 semanas llegaría a los 52; tipo más probable: Estables.
- *Apoyo a la gestión con huecos entre contratos* (6,5 meses/año, $2,2M, Hombre, 25 años, 0 semanas): necesita 1.300 semanas; 28,3 semanas/año, faltan 46,0 años → llega a los 71 (edad legal 62); tipo más probable: Intermitentes.
- *Contratista ocasional (un contrato corto al año)* (3,0 meses/año, $3,0M, Mujer, 30 años, 100 semanas): necesita 1.000 semanas; 13,0 semanas/año, faltan 69,0 años → llega a los 99 (edad legal 57); con 1.300 semanas llegaría a los 122; tipo más probable: Ocasionales.

## Tres casos reales (anonimizados, k ≥ 10)
1. **Estables (Mujer)**, honorario ≈ $4,0M/mes (cotiza sobre el 40% del honorario; patrón compartido por 10 personas). 2022: 12 m (2+ c) · 2023: 12 m (2+ c) · 2024: 12 m (1 c) · 2025: 2 m (1 c). Ritmo: 41,3 semanas/año → empezando a los 25, completaría sus 1.000 semanas a los **49 años** (edad legal 57). Con 1.300 semanas llegaría a los 56. A la edad legal tendría 1.000 semanas.
2. **Intermitentes (Mujer)**, honorario ≈ $3,0M/mes (cotiza sobre 1 SMMLV; patrón compartido por 18 personas). 2022: 11 m (2+ c) · 2023: 11 m (2+ c) · 2024: 1 m (1 c) · 2025: 0 m (0 c). Ritmo: 25,0 semanas/año → empezando a los 25, completaría sus 1.000 semanas a los **65 años** (edad legal 57). Con 1.300 semanas llegaría a los 77. A la edad legal tendría 800 semanas.
3. **Ocasionales (Mujer)**, honorario ≈ $3,5M/mes (cotiza sobre 1 SMMLV; patrón compartido por 10 personas). 2022: 3 m (1 c) · 2023: 7 m (1 c) · 2024: 0 m (0 c) · 2025: 0 m (0 c). Ritmo: 10,9 semanas/año → empezando a los 25, necesitaría **92 años**: no llegaría. A la edad legal tendría 348 semanas.

Sin entidad, identificador, fechas, departamento ni objeto. Para que el patrón no apunte a una persona (SECOP II
publica el nombre del contratista), los meses se redondean al mes, los contratos por año tienen tope "2+" y el
honorario se redondea a $500.000; cada patrón publicado lo comparten **al menos 10 contratistas**.

## Figuras
- `outputs/figs/05_edad_pension_por_cluster.png`: Edad mediana a la que cada tipo de trayectoria completaría sus semanas (hombres 1.300, mujeres 1.000), con rango intercuartílico y edades legales.
- `outputs/figs/05_semanas_requeridas.png`: % de contratistas que cotiza al menos X semanas por año, con los umbrales de hombres (35,1), mujeres con la regla vigente (31,3) y mujeres con 1.300 (40,6, sensibilidad).
- `outputs/figs/05_a_tiempo_por_genero.png`: % que completa sus semanas a la edad legal, por tipo de trayectoria y género, con la sensibilidad de 1.300 semanas para mujeres.
- `outputs/figs/05_pension_por_decil.png`: % que llega a tiempo y edad mediana de llegada por decil de riesgo del modelo del notebook 04 (D1 = mayor riesgo).
- `outputs/figs/05_simulador_curva.png`: Curvas del simulador (hombres 1.300, mujeres 1.000): edad de llegada según los meses de contrato al año, con la mediana de cada cluster.
- `outputs/figs/05_casos_reales.png`: Línea de tiempo 2022–2025 de los tres casos reales anonimizados (k ≥ 10) y su proyección.

## Limitaciones
- Los tiempos son una **cota superior**: no vemos el empleo formal entre contratos, los contratos en SECOP I ni el
  trabajo con privados, que también cotizan.
- La cobertura de SECOP II era baja en 2020–2021 (muchas entidades seguían en SECOP I).
- Se extrapolan 4 años a toda una vida laboral; quien entra en 2025 solo tiene un año observable.
- Suponemos que cada semana con contrato se cotiza de verdad (si no se paga la planilla, las semanas son menos).
- Semanas = días / 7; con meses de 30 días (Colpensiones) serían ~1,4% menos.
- Regla de mujeres: 1.000 semanas es el punto de llegada de la C-197 de 2023 (en 2036); quien se pensione antes
  necesita más. La sensibilidad con 1.300 acota el resultado. Verificar la norma vigente antes de presentar.
- Supuestos fijos: inicio a los 25 y SMMLV de 2025.
