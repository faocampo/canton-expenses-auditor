
# PROMPT — Consolidación de Expensas desde archivos XLSX con Liquidaciones

Actúa como un desarrollador de software con experiencia en Python y análisis de datos. Genera un script en Python que cumpla con las mejores práticas de desarrollo de ese lenguaje y cumpla con los siguientes requisitos:

---

## 1) Archivos y parámetros de entrada

* **Archivos de Expensas**: múltiples planillas llamadas **“Liquidacion El Canton \[mes-año] x mail.xlsx”**, una por cada mes.

  * Fuente principal: solapa **“Gastos del Mes” (ignorando mayúsculas/acentos)**.

* **Informacion de tipo de cambio**: archivo CSV llamado **“Info Financiera - Tipo de cambio USD-ARS.csv”** que contiene la informacion de tipo de cambio oficial para cada dia (columnas "Fecha" y "Valor ARS").

* **Información de inflación intermensual**: archivo CSV llamado **“Info Financiera - Inflación intermensual.csv”** que contiene la informacion de inflación intermensual para cada mes (columnas "Fecha" y "Valor").

* **Información de inflación interanual**: archivo CSV llamado **“Info Financiera - Inflación interanual.csv”** que contiene la informacion de inflación interanual para cada mes (columnas "Fecha" y "Valor")

* **Parámetro "from_year"**: año desde el que se desea consolidar los gastos.

* **Parámetro "to_year"**: año hasta el que se desea consolidar los gastos.

* **Parámetro "append" (opcional)**: archivo CSV que contiene la informacion consolidada de gastos previa al cual se desea agregar la informacion consolidada de gastos actual.

* **Parámetro "output" (opcional)**: archivo CSV donde se escribe la salida. Si no se especifica ni tampoco el parámetro "append", se devuelve el texto plano de la salida.

---

## 2) Formato de planillas de expensas de entrada (en inglés)

* **Col A**: (empty) → ignore.
* **Col B**: Main Category (no header; a block label). Carry forward until next Category appears.
* **Col C**: Sub‑category or blank. If blank, reuse last non‑blank sub‑category. This column also has some "Total..." values, which should be ignored.
* **Col D**: Sub-Sub-Category or blank. If blank, reuse last non‑blank sub‑sub‑category.
* **Col E**: Expense Type (e.g., Bill, Check, Credit etc.).
* **Col F**: Date (dd/mm/yyyy).
* **Col G**: Num (string code/identifier).
* **Col H**: Name (payee text + CUIT somewhere inside, with or without '-' characters. Normalize to NN-NNNNNNNN-N).
  * CUIT strict token regex: r'^(20|2[3-7]|30|3[3-4])\-?(\d{8})\-?(\d)$'.
* **Col I**: Memo (description).
* **Col J**: Amount in ARS (locale es-AR, e.g., 1.685.187,00).
  * Convert to Python float using decimal dot and no thousands separators.
  * Ignore "Total..." values.

## 3) Formato de planilla (CSV) de salida

* Ubicación: en el directorio actual.
* Codificación: UTF-8.
* Delimitador: coma `,`.
* Cada fila = un gasto individual registrado en las liquidaciones.
* Columnas obligatorias: `fecha`, `categoría`, `subcategoría`, `sub-subcategoría`, `rubro`, `acreedor`, `ID acreedor`, `tipo de gasto`, `descripción (memo)`, `datos fiscales`, `monto ARS`, `monto USD`, `observaciones`, `archivo de origen`, `tipo de cambio aplicado`,

**Opciones de salida:**

* Si el parámetro `output` no se especifica ni tampoco el parámetro `append`, **se devuelve el texto plano de la salida**.
* Si el parámetro `output` se especifica, **se escribe la informacion consolidada de gastos actual al archivo CSV indicado**
* Si el parámetro `append` se especifica, **se agrega la informacion consolidada de gastos actual al archivo CSV previo** sin la fila de encabezados.

---

## 4) Detalle de Columnas obligatorias

La planilla consolidada debe contener, como mínimo, las siguientes columnas:

* **fecha** (DD/MM/YYYY).
* **código**: código de la liquidación.
* **categoría**: tipo de gasto.
* **subcategoría**: subtipo de gasto, o blanco si no hay.
* **sub-subcategoría**: subsubtipo de gasto, o blanco si no hay.
* **rubro**: rubro estandarizado según una lista de keywords.
* **acreedor**: nombre del acreedor obtenido de la planilla, columna H.
* **ID acreedor**: CUIT del proveedor normalizado, obtenido de columna H.
* **tipo de gasto**: tipo de gasto obtenido de la planilla, columna E.
* **descripción (memo)** extraida de la planilla, columna I.
* **monto ARS**
* **monto USD** (convertido al tipo de cambio oficial correspondiente al día/mes)
* **tipo de cambio**: tipo de cambio oficial correspondiente al día/mes
* **datos fiscales**: `Nombre / CUIT / Categoría tributaria / Tipo de personería (Jurídica, Física)`
* **observaciones**:
* **origen**: nombre del archivo Excel usado (para trazabilidad)

---

## 5) Procedimiento de consolidación

1. **Inventariar el listado de archivos de entrada**: listar todos los archivos Excel.

2. **Procesar Excel**: extraer todos los registros de la hoja **“gastos del mes”** (ignorando mayúsculas/acentos).

3. **Normalizar datos**:
   * Fechas en formato DD/MM/YYYY.
   * Montos normalizados a ARS con decimales estándar.
   * Conversión a USD al tipo de cambio de la fecha (fuente: archivo CSV de tipo de cambio).

4. **Datos fiscales**: buscar CUIT en sitio web `https://www.cuitonline.com/search/{CUIT}`, extraer nombre, categoría tributaria, tipo de persona y completar columna.

5. **Consolidar todo** en un solo CSV.

6. **Control de calidad**:

   * Duplicados → marcar en **observaciones**.
   * Campos faltantes → dejar vacío y anotar en **observaciones**.
   * Montos atípicos → marcar con "[Monto atípico] en observaciones".

---

## 6) Ejemplo de tabla consolidada (ficticia, 5 filas)

```CSV
Fecha,código,Categoría,Sub-categoría,Sub-sub-categoría,rubro,acreedor,ID acreedor,tipo de gasto,descripción, monto ARS , monto USD , tipo de cambio ,datos fiscales,observaciones,origen
01/11/2020,I-50-2,A-Administración,Correo y mensajeria,,Autopista del Sol SA,30-54667567-6,Check,Tic. varios - Peajes,335,34,,DIRECCION NACIONAL DE VIALIDAD / 30-54667567-6 / Persona Jurídica / Ganancias: Sicore-Impto.a Las Ganancias ,Liquidacion el Canton 01-2022 x mail.xlsx
04/11/2020,FA-C0000200000909,A-Administración,Correo y mensajeria,,Perrot,Walter Elido,20-22518145-5,Bill,Transfer - Servicio de cadetería,2.900,290,,
30/11/2020,M158,A-Administración,Correo y mensajeria,,Correo Of.de la R.A.SA,30-70857483-6,Check,Tck 153852  Cartas Documento,1.280,128,,
01/11/2020,I-50-5,A-Administración,Correo y mensajeria,,,Check,C0000200000737 - Impresión de plano,170,17,,
01/11/2020,I-50-8,A-Administración,Correo y mensajeria,,,Check,C0000200000753 - Impresión de plano,200,20,,
16/11/2020,FA-B000300004691,A-Administración,Correo y mensajeria,,,Bill,Transfer - Cartuchos para impresora de Administración,8.600,860,,
26/11/2020,FA-B000600000851,A-Administración,Correo y mensajeria,,,Bill,Transfer - Artículos de librería para Administración,9.110,911,,
04/11/2020,FA-B0000500000044,A-Administración,Administración,,,Bill,Transfer - Servicios de administración 10/2020,645.959,64.596,,
24/11/2020,FA-B0000500000044,A-Administración,Otros honorarios Asoc. Civil,Asesoramiento legal integral,,Bill,Transfer - Honorarios por asesoramiento legal 11/2020,56.486,5.649,,
02/11/2020,FA-C0000300000234,A-Administración,Otros honorarios Asoc. Civil,Otros Honorarios,,Bill,Transfer - Honorarios por confección de RG 3369 10/2020,23.917,2.392,,
02/11/2020,FA-B000200000208,A-Administración,Otros honorarios Asoc. Civil,Otros Honorarios,,Bill,Transfer - Honorarios por servicio de veeduria 11/2020,157.300,15.730,,
03/11/2020,FA-B0000600001194,A-Administración,Otros honorarios Asoc. Civil,Otros Honorarios,,Bill,Transfer - Honorarios por asesoramiento Res. 400 subdivisión de tierras 10-2020,34.570,3.457,,
05/11/2020,C0001000000142,A-Administración,Otros honorarios Asoc. Civil,Otros Honorarios,,Bill,Transfer- Honorarios por asesoramiento contable 10/2020,6.000,600,,
30/11/2020,FA-C0000200000120,A-Administración,Otros honorarios Asoc. Civil,Otros Honorarios,,Bill,Transfer - Honorarios por gestión y asesoramiento Res. 400 subdivisión de tierra 11/2020,125.000,12.500,,
30/11/2020,C0001000000145,A-Administración,Otros honorarios Asoc. Civil,Otros Honorarios,,Bill,Transfer- Honorarios por asesoramiento contable 11/2020,8.100,810,,
27/11/2020,FA-C0000300000072,A-Administración,Otros honorarios Asoc. Civil,Honorarios asistente obras,,Bill,Transfer - Honorarios por asistencia en obras 11/2020,62.491,6.249,,
```

---

## 7) Resultado esperado

Si el parámetro `append` no se especifica, se genera un archivo CSV nuevo con el nombre **"Gastos\_Consolidados\_[from_year]-[to_year].csv"**.

Si el parámetro `append` se especifica, se agrega la informacion consolidada de gastos actual al archivo CSV previo sin la fila de encabezados.


## 8) Crea los scripts bash para ejecutar el programa y los tests.

### Script de ejecución del programa

El script se llama **"run_program.sh"** y debe:

* Crear/activar un entorno virtual Python.
* Instalar las dependencias del proyecto.
* Ejecutar el programa con los parámetros proporcionados.

### Script de ejecución de tests

El script se llama **"run_tests.sh"** y debe:

* Crear/activar un entorno virtual Python.
* Instalar las dependencias del proyecto.
* Ejecutar los tests con los parámetros proporcionados.

### Ejemplo de uso

```bash
./run_program.sh --inputs expenses --fx "docs/Info Financiera - Tipo de cambio USD-ARS.csv" --from-year 2020 --to-year 2025 --output output/consolidado_expensas_canton_2020-2025.csv --debug
```

```bash
./run_tests.sh
```
