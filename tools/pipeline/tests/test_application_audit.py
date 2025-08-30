# Methodology: TDD – tests for application.audit
from __future__ import annotations

import pandas as pd
from pathlib import Path

from tools.pipeline.application.audit import (
    load_consolidated_data,
    load_inflation_data,
    normalize_and_validate_data,
    detect_anomalies,
    cross_with_inflation,
    enrich_with_provider_info,
    generate_audit_report,
    run_audit
)


def test_load_consolidated_data(tmp_path):
    """Test loading consolidated data from CSV file."""
    # Create a sample CSV file
    csv_file = tmp_path / "consolidated.csv"
    data = {
        'Fecha': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'Rubro': ['Luz', 'Agua', 'Gas'],
        'Monto': [1000.0, 500.0, 300.0],
        'Moneda': ['ARS', 'ARS', 'USD']
    }
    df = pd.DataFrame(data)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    df.to_csv(csv_file, index=False)
    
    # Load the data
    loaded_df = load_consolidated_data(csv_file)
    
    # Assertions
    assert len(loaded_df) == 3
    assert 'Fecha' in loaded_df.columns
    assert 'Rubro' in loaded_df.columns
    assert 'Monto' in loaded_df.columns
    assert 'Moneda' in loaded_df.columns


def test_load_inflation_data(tmp_path):
    """Test loading inflation data from CSV file."""
    # Create a sample inflation CSV file
    csv_file = tmp_path / "inflation.csv"
    data = {
        'Date': ['2024-01-01', '2024-02-01', '2024-03-01'],
        'Inflation': [10.5, 8.2, 12.1]
    }
    df = pd.DataFrame(data)
    df.to_csv(csv_file, index=False)
    
    # Load the data
    loaded_df = load_inflation_data(csv_file)
    
    # Assertions
    assert len(loaded_df) == 3
    assert 'Date' in loaded_df.columns
    assert 'Inflation' in loaded_df.columns


def test_normalize_and_validate_data():
    """Test normalizing and validating expenses data."""
    # Create a sample DataFrame with valid data
    data = {
        'Fecha': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'Rubro': ['Luz', 'Agua', 'Gas'],
        'Monto': [1000.0, 500.0, 300.0],
        'Moneda': ['ARS', 'ARS', 'USD']
    }
    df = pd.DataFrame(data)
    
    # Normalize and validate
    normalized_df = normalize_and_validate_data(df)
    
    # Assertions
    assert len(normalized_df) == 3
    assert normalized_df['Monto'].dtype == 'float64'


def test_normalize_and_validate_data_with_invalid_entries():
    """Test normalizing and validating data removes invalid entries."""
    # Create a sample DataFrame with some invalid data
    data = {
        'Fecha': ['2024-01-15', '2024-02-20', '2024-03-10', '2024-04-05'],
        'Rubro': ['Luz', 'Agua', 'Gas', 'Luz'],
        'Monto': [1000.0, -500.0, 300.0, 0.0],  # Negative and zero amounts
        'Moneda': ['ARS', 'ARS', 'EUR', 'USD']  # Invalid currency
    }
    df = pd.DataFrame(data)
    
    # Normalize and validate
    normalized_df = normalize_and_validate_data(df)
    
    # Assertions - should only have 1 valid row (2024-01-15, Luz, 1000.0, ARS)
    assert len(normalized_df) == 1
    assert normalized_df.iloc[0]['Monto'] == 1000.0
    assert normalized_df.iloc[0]['Moneda'] == 'ARS'


def test_detect_anomalies():
    """Test anomaly detection in expenses data."""
    # Create a sample DataFrame with some anomalies
    data = {
        'Fecha': ['2024-01-15', '2024-01-15', '2024-02-20', '2024-03-10', '2024-03-16'],
        'Rubro': ['Luz', 'Luz', 'Agua', 'Gas', 'Gas'],
        'Monto': [1000.0, 1000.0, 500.0, 300.0, 5000.0],  # Two identical entries (duplicates), one outlier (5000.0)
        'Moneda': ['ARS', 'ARS', 'ARS', 'USD', 'USD']
    }
    df = pd.DataFrame(data)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    # Detect anomalies
    anomalies = detect_anomalies(df)
    
    # Assertions
    assert 'duplicates' in anomalies
    assert 'zero_negative' in anomalies
    assert 'outliers' in anomalies
    assert 'weekends' in anomalies
    assert 'intermonthly_spikes' in anomalies
    
    # Should have 2 duplicates (the two identical Luz entries)
    assert len(anomalies['duplicates']) == 2
    
    # Should have 0 zero/negative amounts
    assert len(anomalies['zero_negative']) == 0
    
    # Should have 2 weekend operations (2024-03-10 and 2024-03-16 are weekend dates)
    assert len(anomalies['weekends']) == 2


def test_cross_with_inflation(tmp_path):
    """Test crossing expenses data with inflation data."""
    # Create sample expenses data
    expenses_data = {
        'Fecha': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'Rubro': ['Luz', 'Agua', 'Gas'],
        'Monto': [1000.0, 500.0, 300.0],
        'Moneda': ['ARS', 'ARS', 'USD']
    }
    expenses_df = pd.DataFrame(expenses_data)
    expenses_df['Fecha'] = pd.to_datetime(expenses_df['Fecha'])
    
    # Create sample inflation data
    inflation_data = {
        'Date': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'Inflation': [10.5, 8.2, 12.1]
    }
    inflation_df = pd.DataFrame(inflation_data)
    
    # Cross data
    crossed_df = cross_with_inflation(expenses_df, inflation_df)
    
    # Assertions
    assert len(crossed_df) == 3
    assert 'Inflation' in crossed_df.columns


def test_enrich_with_provider_info():
    """Test enriching data with provider information."""
    # Create a sample DataFrame
    data = {
        'Fecha': ['2024-01-15', '2024-02-20'],
        'Rubro': ['Luz', 'Agua'],
        'Monto': [1000.0, 500.0],
        'Moneda': ['ARS', 'ARS']
    }
    df = pd.DataFrame(data)
    
    # Enrich with provider info
    enriched_df = enrich_with_provider_info(df)
    
    # Assertions
    assert len(enriched_df) == 2
    assert 'Proveedor_Info' in enriched_df.columns
    assert all(enriched_df['Proveedor_Info'] == "Información no disponible")


def test_generate_audit_report():
    """Test generating audit report."""
    # Create a sample DataFrame
    data = {
        'Fecha': ['2024-01-15', '2024-01-15', '2024-02-20', '2024-03-10', '2024-03-16'],
        'Rubro': ['Luz', 'Luz', 'Agua', 'Gas', 'Gas'],
        'Monto': [1000.0, 1000.0, 500.0, 300.0, 5000.0],
        'Moneda': ['ARS', 'ARS', 'ARS', 'USD', 'USD']
    }
    df = pd.DataFrame(data)
    df['Fecha'] = pd.to_datetime(df['Fecha'])
    
    # Create sample anomalies
    anomalies = detect_anomalies(df)
    
    # Generate report
    report = generate_audit_report(df, anomalies)
    
    # Assertions
    assert isinstance(report, str)
    assert "# Informe de Auditoría de Gastos" in report
    assert "Total de gastos analizados:" in report
    assert "## Anomalías Detectadas" in report


def test_run_audit(tmp_path):
    """Test the complete audit process."""
    # Create sample consolidated data
    consolidated_file = tmp_path / "consolidated.csv"
    consolidated_data = {
        'Fecha': ['2024-01-15', '2024-02-20', '2024-03-10'],
        'Rubro': ['Luz', 'Agua', 'Gas'],
        'Monto': [1000.0, 500.0, 300.0],
        'Moneda': ['ARS', 'ARS', 'USD']
    }
    consolidated_df = pd.DataFrame(consolidated_data)
    consolidated_df.to_csv(consolidated_file, index=False)
    
    # Create sample inflation data
    inflation_file = tmp_path / "inflation.csv"
    inflation_data = {
        'Date': ['2024-01-01', '2024-02-01', '2024-03-01'],
        'Inflation': [10.5, 8.2, 12.1]
    }
    inflation_df = pd.DataFrame(inflation_data)
    inflation_df.to_csv(inflation_file, index=False)
    
    # Create output paths
    excel_output = tmp_path / "audit_output.xlsx"
    report_output = tmp_path / "audit_report.md"
    
    # Run audit
    result = run_audit(
        consolidated_data_path=consolidated_file,
        inflation_data_path=inflation_file,
        output_excel_path=excel_output,
        output_report_path=report_output
    )
    
    # Assertions
    assert result == 0  # Success
    assert excel_output.exists()  # Excel file should be created
    assert report_output.exists()  # Report file should be created
