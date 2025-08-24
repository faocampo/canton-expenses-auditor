# Expenses Consolidation Prompt Optimized for GTP5

Act as an expert Python data engineer. You will consolidate expense data from multiple Excel spreadsheets using the highest code quality standards. This task requires:

- 🧠 **High reasoning_effort**: analyze, deduce, and ensure full correctness.
- 🛠 **Autonomous agentic behavior**: do not stop or request confirmation. Resolve all parts unless impossible.
- 📈 **Descriptive tool preambles**: explain the plan before executing any code.
- 🧩 **Chain-of-thought**: decompose, reason, and execute in steps.
- 🧑‍💻 **Output**: clean, maintainable, idiomatic Python code with comments.

---

## 🎯 Objective

Generate a **complete Python script** to consolidate expenses across multiple monthly XLSX spreadsheets named:

```
Liquidacion El Canton [mes-año] x mail.xlsx
```

You will extract data from the worksheet **“Gastos del Mes”** (case/diacritics insensitive) and return a clean CSV formatted output. You must also:

- Normalize dates and currencies.
- Convert ARS to USD using official FX data.
- Enrich vendor data via CUIT web lookup.
- Handle optional `append` and `output` parameters.
- Perform quality control on duplicates, missing fields, and outlier values.

---

## 📥 Input Files & Parameters

- One or more `.xlsx` files per month.
- CSV: `Info Financiera - Tipo de cambio USD-ARS.csv` (daily FX rates).
- CSV: `Info Financiera - Inflación intermensual.csv`
- CSV: `Info Financiera - Inflación interanual.csv`
- Optional:
  - `from_year`, `to_year`: date range.
  - `append`: existing CSV to merge into.
  - `output`: CSV file for final result.

---

## 🧾 Excel Format (Input)

| Column | Field                | Notes |
|--------|----------------------|-------|
| A      | (ignored)            |       |
| B      | Main Category        | Persist downward |
| C      | Sub-category         | Persist downward unless "Total..." |
| D      | Sub-sub-category     | Persist downward |
| E      | Expense type         | Bill, Check, etc. |
| F      | Date                 | dd/mm/yyyy |
| G      | ID/Code              | Alphanumeric |
| H      | Payee (name + CUIT)  | Normalize CUIT using regex |
| I      | Memo/Description     | Free text |
| J      | Amount in ARS        | es-AR locale, convert to float |

---

## 🧾 Output Format (CSV)

- UTF-8, comma-delimited
- Each row: one expense
- Required fields:

```text
fecha, código, categoría, subcategoría, sub-subcategoría, rubro, acreedor, ID acreedor, tipo de gasto, descripción, monto ARS, monto USD, tipo de cambio, datos fiscales, observaciones, origen
```

- CUIT fiscal data: query `https://www.cuitonline.com/search/{CUIT}` → extract:
  - Name
  - CUIT
  - Tax category
  - Entity type

---

## 🔍 Quality Controls

Mark in `observaciones`:
- Duplicates
- Missing fields
- Anomalous amounts

---

## 📄 Example Output

```csv
Fecha,Código,Categoría,Subcategoría,Sub-subcategoría,Rubro,Acreedor,ID Acreedor,Tipo de Gasto,Descripción,Monto ARS,Monto USD,Tipo de Cambio,Datos Fiscales,Observaciones,Origen
01/11/2020,I-50-2,A-Administración,Correo y mensajeria,,Autopista del Sol SA,30-54667567-6,Check,Tic. varios - Peajes,335,34,102.5,"Autopista del Sol SA / 30-54667567-6 / Responsable Inscripto / Persona Jurídica",,Liquidacion el Canton 01-2022 x mail.xlsx
...
```

---

## ✅ Execution Plan (For Codex AI)

1. Rephrase user request and outline solution plan.
2. Load and parse input spreadsheets.
3. Extract and normalize all required fields.
4. Enrich data (CUIT lookup, FX conversion).
5. Merge with existing file if `append` is set.
6. Export to CSV if `output` is set; else print to stdout.
7. Annotate observations.

Always format code for **clarity and readability**:
- Use type hints
- Modular functions
- Descriptive variable names
- Inline comments
- Exception handling

Avoid asking for clarification. Assume reasonable defaults and document assumptions in code comments.

**Proceed when ready.**
