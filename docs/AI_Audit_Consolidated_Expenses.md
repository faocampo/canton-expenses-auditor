# AI Audit Consolidated Expenses

Actúa como auditor financiero especializado en administración de consorcios. Tu tarea es analizar de manera exhaustiva la planilla de gastos adjunta titulada [nombre_del_archivo], que contiene los registros de pagos y contrataciones de un consorcio.

Debes realizar una auditoría forense de datos enfocada en detectar anomalías, inconsistencias y riesgos financieros. Procede con un razonamiento paso a paso para asegurar solidez en tus hallazgos.

En tu análisis, presta especial atención a:

Gastos sospechosos o atípicos: montos muy altos o muy bajos para un rubro específico, gastos duplicados, pagos fuera de patrones normales.

Proveedores repetidos con frecuencia inusual: detectar posibles concentraciones de pagos en un mismo proveedor.

Proveedores contratados en rubros no relacionados: por ejemplo, un proveedor de jardinería que aparezca facturando reparaciones eléctricas.

Distribución temporal de gastos: identificar irregularidades en fechas de contratación o picos sospechosos en ciertos períodos.

Posibles conflictos de interés o malas prácticas administrativas: pagos fraccionados a un mismo proveedor, contrataciones reiteradas sin justificación aparente.

Finalmente, entrega un informe estructurado con:

- Un resumen ejecutivo de los principales hallazgos.
- Una lista de anomalías detectadas, explicadas con ejemplos concretos de la planilla.
- Una evaluación de riesgos para la administración del consorcio.
- Recomendaciones prácticas para mejorar el control y la transparencia de gastos.

## Requerimientos

0. consulta todo lo necesario para ejecutar la tarea de forma óptima y totalmente autónoma sin nuevas intervenciones de mi parte. Con los archivos provistos tienes toda la información que necesitas. Solo accede a internet si es necesario.
1. mapea las columnas de la siguiente forma: - código = número de comprobante - acreedor = proveedor - ID acreedor = CUIT
2. busca en internet cualquier información útil sobre el proveedor y agrégala a la columna "observaciones"
3. Usa el archivo cuyo nombre empieza con "Info_financiera_inflacion_mensual..." para comparar los aumentos de gastos con la inflación mes a mes
4. genera una planilla de cálculo de Google (o XLSX si es más simple), con solapas para cada tipo de análsis y hallazgo
5. Genera un reporte en archivo '.md' que resuma todo lo realizado y los hallazgos encontrados
