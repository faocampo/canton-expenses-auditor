# Methodology: Clean Architecture - Audit application service
"""
Audit application service for analyzing consolidated expenses data.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

import pandas as pd

from ..domain.models import ExtractedRow

logger = logging.getLogger(__name__)


def load_consolidated_data(csv_path: Path) -> pd.DataFrame:
    """Load consolidated expenses data from CSV file."""
    logger.info(f"Loading consolidated data from {csv_path}")
    df = pd.read_csv(csv_path, parse_dates=['Fecha'])
    logger.info(f"Loaded {len(df)} rows of consolidated data")
    return df


def load_inflation_data(csv_path: Path) -> pd.DataFrame:
    """Load inflation data from CSV file."""
    logger.info(f"Loading inflation data from {csv_path}")
    # Assuming the inflation CSV has columns: Date, Inflation
    df = pd.read_csv(csv_path, parse_dates=['Date'])
    logger.info(f"Loaded {len(df)} rows of inflation data")
    return df


def normalize_and_validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize and validate the consolidated expenses data."""
    logger.info("Normalizing and validating data")
    
    # Ensure required columns exist
    required_columns = ['Fecha', 'Rubro', 'Monto', 'Moneda']
    for col in required_columns:
        if col not in df.columns:
            raise ValueError(f"Required column '{col}' not found in data")
    
    # Validate data types
    df['Monto'] = pd.to_numeric(df['Monto'], errors='coerce')
    df = df.dropna(subset=['Monto'])
    
    # Validate positive amounts
    df = df[df['Monto'] > 0]
    
    # Validate currency codes
    valid_currencies = ['ARS', 'USD']
    df = df[df['Moneda'].isin(valid_currencies)]
    
    logger.info(f"Data normalized and validated. Remaining rows: {len(df)}")
    return df


def detect_anomalies(df: pd.DataFrame) -> dict:
    """Detect various anomalies in the expenses data."""
    logger.info("Detecting anomalies in expenses data")
    
    anomalies = {}
    
    # Detect duplicates
    duplicates = df[df.duplicated(subset=['Fecha', 'Rubro', 'Monto', 'Moneda'], keep=False)]
    anomalies['duplicates'] = duplicates
    
    # Detect zero/negative amounts
    zero_negative = df[df['Monto'] <= 0]
    anomalies['zero_negative'] = zero_negative
    
    # Detect outliers by category (using IQR method)
    outliers = df.copy()
    outliers['is_outlier'] = False
    
    for category in df['Rubro'].unique():
        category_data = df[df['Rubro'] == category]
        Q1 = category_data['Monto'].quantile(0.25)
        Q3 = category_data['Monto'].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        
        category_outliers = category_data[
            (category_data['Monto'] < lower_bound) | 
            (category_data['Monto'] > upper_bound)
        ]
        
        outliers.loc[outliers['Rubro'] == category, 'is_outlier'] = (
            df.loc[df['Rubro'] == category, 'Monto'].apply(
                lambda x: x < lower_bound or x > upper_bound
            )
        )
    
    anomalies['outliers'] = outliers[outliers['is_outlier']]
    
    # Detect weekend operations
    weekends = df[df['Fecha'].dt.weekday >= 5]  # 5 = Saturday, 6 = Sunday
    anomalies['weekends'] = weekends
    
    # Detect intermonthly spikes (this would require more complex analysis)
    # For now, we'll just flag this as a placeholder for more detailed analysis
    anomalies['intermonthly_spikes'] = pd.DataFrame()
    
    logger.info(f"Anomalies detected: {len(anomalies['duplicates'])} duplicates, "
                f"{len(anomalies['zero_negative'])} zero/negative amounts, "
                f"{len(anomalies['outliers'])} outliers, "
                f"{len(anomalies['weekends'])} weekend operations")
    
    return anomalies


def cross_with_inflation(expenses_df: pd.DataFrame, inflation_df: pd.DataFrame) -> pd.DataFrame:
    """Cross expenses data with inflation data."""
    logger.info("Crossing expenses data with inflation data")
    
    # Ensure Date column in inflation_df is datetime type
    inflation_df['Date'] = pd.to_datetime(inflation_df['Date'])
    
    # Merge expenses with inflation data based on date
    # This is a simplified approach - in practice, you might want to match by month/year
    result_df = expenses_df.merge(inflation_df, left_on='Fecha', right_on='Date', how='left')
    
    logger.info("Data crossed with inflation information")
    return result_df


def enrich_with_provider_info(df: pd.DataFrame) -> pd.DataFrame:
    """Enrich data with public provider information."""
    logger.info("Enriching data with provider information")
    
    # This would involve web scraping or API calls to get provider info
    # For now, we'll add a placeholder column
    df['Proveedor_Info'] = "Información no disponible"
    
    logger.info("Data enriched with provider information")
    return df


def generate_audit_report(df: pd.DataFrame, anomalies: dict) -> str:
    """Generate a markdown audit report."""
    logger.info("Generating audit report")
    
    report = []
    report.append("# Informe de Auditoría de Gastos\n")
    report.append(f"Total de gastos analizados: {len(df)}\n")
    
    report.append("## Anomalías Detectadas\n")
    
    if len(anomalies['duplicates']) > 0:
        report.append(f"- Duplicados: {len(anomalies['duplicates'])} registros encontrados\n")
    else:
        report.append("- Duplicados: No se encontraron registros duplicados\n")
    
    if len(anomalies['zero_negative']) > 0:
        report.append(f"- Montos cero/negativos: {len(anomalies['zero_negative'])} registros encontrados\n")
    else:
        report.append("- Montos cero/negativos: No se encontraron registros con montos cero/negativos\n")
    
    if len(anomalies['outliers']) > 0:
        report.append(f"- Valores atípicos: {len(anomalies['outliers'])} registros encontrados\n")
    else:
        report.append("- Valores atípicos: No se encontraron valores atípicos\n")
    
    if len(anomalies['weekends']) > 0:
        report.append(f"- Operaciones en fin de semana: {len(anomalies['weekends'])} registros encontrados\n")
    else:
        report.append("- Operaciones en fin de semana: No se encontraron operaciones en fin de semana\n")
    
    logger.info("Audit report generated")
    return "\n".join(report)


def export_to_excel_with_sheets(dataframes: Dict[str, pd.DataFrame], output_path: Path) -> None:
    """
    Export multiple DataFrames to an Excel file with separate sheets.
    
    Args:
        dataframes: Dictionary mapping sheet names to DataFrames
        output_path: Path where the Excel file will be saved
    """
    logger.info(f"Exporting data to Excel file: {output_path}")
    with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
        for sheet_name, df in dataframes.items():
            if df is not None and not df.empty:
                df.to_excel(writer, sheet_name=sheet_name, index=False)
            else:
                # Create empty DataFrame for empty sheets
                pd.DataFrame().to_excel(writer, sheet_name=sheet_name, index=False)
    logger.info(f"Excel file exported successfully with {len(dataframes)} sheets")


def run_audit(
    consolidated_data_path: Path,
    inflation_data_path: Path,
    output_excel_path: Path,
    output_report_path: Path = None
) -> int:
    """
    Run the complete audit process on consolidated expenses data.
    
    Args:
        consolidated_data_path: Path to the consolidated expenses CSV file
        inflation_data_path: Path to the inflation data CSV file
        output_excel_path: Path where the audit results Excel file will be saved
        output_report_path: Optional path where the markdown audit report will be saved
        
    Returns:
        0 on success, non-zero on error
    """
    try:
        # Load data
        expenses_df = load_consolidated_data(consolidated_data_path)
        inflation_df = load_inflation_data(inflation_data_path)
        
        # Normalize and validate data
        normalized_df = normalize_and_validate_data(expenses_df)
        
        # Detect anomalies
        anomalies = detect_anomalies(normalized_df)
        
        # Cross with inflation data
        inflated_df = cross_with_inflation(normalized_df, inflation_df)
        
        # Enrich with provider information
        enriched_df = enrich_with_provider_info(inflated_df)
        
        # Export to Excel with multiple sheets
        export_to_excel_with_sheets(
            dataframes={
                'Gastos_Normalizados': normalized_df,
                'Anomalias': anomalies['duplicates'],
                'Valores_Atipicos': anomalies['outliers'],
                'Operaciones_Fin_de_Semana': anomalies['weekends'],
                'Datos_Enriquecidos': enriched_df
            },
            output_path=output_excel_path
        )
        
        # Generate audit report if requested
        if output_report_path:
            report = generate_audit_report(normalized_df, anomalies)
            with open(output_report_path, 'w') as f:
                f.write(report)
        
        logger.info("Audit process completed successfully")
        return 0
        
    except Exception as e:
        logger.error(f"Audit process failed: {e}")
        return 1
