# Guía técnica (Markdown) — Cómo construir un programa en **Python** para auditar gastos de consorcio y generar un **Excel** con todas las solapas

> Este documento describe **paso a paso** cómo implementar un pipeline reproducible en Python para:
> 1) **Normalizar** y **validar** la planilla consolidada de gastos.  
> 2) Detectar **anomalías** (duplicados, montos cero/negativos, outliers por rubro, operaciones en fin de semana, picos intermensuales).  
> 3) **Cruzar** el gasto mensual contra la **inflación** (archivo “Info Financiera - inflacion mensual argentina 2022 a 2025.csv”).  
> 4) **Enriquecer** con información pública de proveedores en la columna **observaciones** (opcional).  
> 5) **Exportar** un **XLSX** con múltiples **solapas** (hojas) y, opcionalmente, un informe `.md`.

---

## 1) Requisitos de entorno

- **Python** ≥ 3.10  
- Librerías:
  - `pandas`, `numpy`, `python-dateutil`
  - `openpyxl` o `xlsxwriter` (motor de escritura de Excel)
  - `matplotlib` (opcional, si quieres gráficos en PNG)
  - `requests`, `beautifulsoup4` (opcional, para enriquecimiento web de proveedores)
  - `pyyaml` (opcional, para leer configuración externa)
- Sistema operativo: Linux/macOS/Windows

### Instalación recomendada

```bash
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -U pip
pip install pandas numpy python-dateutil openpyxl xlsxwriter matplotlib requests beautifulsoup4 pyyaml
```

---

## 2) Estructura de proyecto sugerida

```
auditoria-consorcio/
├─ data/
│  ├─ consolidado_expensas_canton_2020-2025.csv
│  └─ Info Financiera - inflacion mensual argentina 2022 a 2025.csv
├─ output/
│  ├─ auditoria_resumen.xlsx
│  └─ informe_auditoria.md
├─ config/
│  └─ settings.yml
├─ src/
│  ├─ main.py
│  ├─ io_utils.py               # carga/validación/exportación
│  ├─ cleaning.py               # normalización y mapeos
│  ├─ anomalies.py              # detección de anomalías
│  ├─ inflation.py              # cruce con inflación
│  ├─ providers.py              # enriquecimiento proveedores (opcional)
│  └─ report.py                 # generación de resumen .md (opcional)
└─ README.md
```

---

## 3) Entradas y **mapeo de columnas**

(El resto del documento continúa con los apartados 3 a 11 tal como se detalló en la respuesta previa)
