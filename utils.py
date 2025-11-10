# utils.py

import pandas as pd
from datetime import datetime, timedelta
import re
import math
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

def get_date_range_from_week(week_str: str) -> str:
    """Konwertuje identyfikator tygodnia na zakres dat roboczych (pon-pt) zgodnie ze standardem ISO 8601."""
    try:
        col_name = week_str.strip()
        match = re.search(r'\s(\d{1,2})/(\d{2})$', col_name)
        if match:
            week_num, year_short = map(int, match.groups())
            year = 2000 + year_short
        else:
            match = re.search(r'(\d{1,2})\.(\d{4})$', col_name)
            if match:
                week_num, year = map(int, match.groups())
            else:
                return "Nieznany format"
        
        if year is None or week_num is None:
            return "Nieznany format"
        
        start_date = datetime.strptime(f'{year}-{week_num}-1', "%G-%V-%u")
        end_date = start_date + timedelta(days=4)
        return f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
    except (ValueError, TypeError):
        return "Błąd konwersji daty"

def read_data_file(uploaded_file, file_name: str) -> pd.DataFrame:
    """Wczytuje plik CSV lub XLSX."""
    if file_name.endswith('.csv'):
        encodings = ['utf-8', 'windows-1250', 'latin1', 'iso-8859-2']
        for encoding in encodings:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding=encoding)
                return df
            except:
                continue
        raise ValueError("Nie udało się odczytać pliku CSV.")
    elif file_name.endswith(('.xlsx', '.xls')):
        try:
            uploaded_file.seek(0)
            df = pd.read_excel(uploaded_file)
            return df
        except Exception as e:
            raise ValueError(f"Błąd odczytu pliku Excel: {e}")
    else:
        raise ValueError("Niewspierany format pliku.")

def get_year_week_from_col(col_name: str):
    """Wyodrębnia rok i tydzień z nazwy kolumny."""
    col_name = str(col_name).strip()
    match = re.search(r'\s(\d{1,2})/(\d{2})$', col_name)
    if match:
        week, year_short = map(int, match.groups())
        return 2000 + year_short, week
    match = re.search(r'(\d{1,2})\.(\d{4})$', col_name)
    if match:
        week, year = map(int, match.groups())
        return year, week
    return None

def process_forecast_file(uploaded_file) -> pd.DataFrame:
    """Przetwarza plik prognozy."""
    df = read_data_file(uploaded_file, uploaded_file.name)
    correct_material_col = 'Materialnummer'
    
    if correct_material_col not in df.columns:
        raise ValueError(f"Brak kolumny '{correct_material_col}'.")
    
    df.dropna(subset=[correct_material_col], inplace=True)
    df[correct_material_col] = pd.to_numeric(df[correct_material_col], errors='coerce')
    df.dropna(subset=[correct_material_col], inplace=True)
    df[correct_material_col] = df[correct_material_col].astype(int)
    
    week_cols = [col for col in df.columns if get_year_week_from_col(col) is not None]
    week_cols.sort(key=lambda col: get_year_week_from_col(col))
    
    if not week_cols:
        raise ValueError("Nie znaleziono kolumn z prognozą.")
    
    df.set_index(correct_material_col, inplace=True)
    
    for col in week_cols:
        if df[col].dtype == 'object':
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
    
    return df[week_cols].fillna(0).apply(pd.to_numeric, errors='coerce').fillna(0)

def process_stock_file(uploaded_file, file_name: str) -> pd.DataFrame:
    """Przetwarza nowy plik dostępnych ilości - zwraca cały DataFrame."""
    df = read_data_file(uploaded_file, file_name)
    
    required_cols = ['numer indeksu', 'DocNum', 'Data dostawy', 'Zamówione', 'Potwierdzone', 'w magazynie']
    
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Brak wymaganej kolumny '{col}' w pliku.")
    
    # Konwersja numeru indeksu
    df['numer indeksu'] = pd.to_numeric(df['numer indeksu'], errors='coerce')
    df.dropna(subset=['numer indeksu'], inplace=True)
    df['numer indeksu'] = df['numer indeksu'].astype(int)
    
    # Konwersja dat
    df['Data dostawy'] = pd.to_datetime(df['Data dostawy'], format='%d-%m-%Y', errors='coerce')
    df['week'] = df['Data dostawy'].dt.isocalendar().week
    df['year'] = df['Data dostawy'].dt.isocalendar().year
    
    # Konwersja wartości numerycznych
    for col in ['Zamówione', 'Potwierdzone', 'w magazynie', 'Dostępne']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    return df

def extract_material_data(stock_df: pd.DataFrame, material_number: int):
    """Wyodrębnia dane dla konkretnego materiału z pliku stanu."""
    material_data = stock_df[stock_df['numer indeksu'] == material_number].copy()
    
    if material_data.empty:
        raise ValueError(f"Nie znaleziono danych dla materiału {material_number}")
    
    # Stan magazynowy (pierwsza wartość, bo jest taka sama dla wszystkich wierszy)
    current_stock = float(material_data['w magazynie'].iloc[0])
    
    # Dokumenty ZP (zamówienia produkcyjne)
    zp_df = material_data[material_data['DocNum'].astype(str).str.upper().str.contains('ZP', na=False)]
    zp_df = zp_df[zp_df['Zamówione'] > 0]
    weekly_zp_income = zp_df.groupby(['year', 'week'])['Zamówione'].sum()
    
    # Standardowa partia (z pierwszego ZP)
    standard_batch = None
    if not zp_df.empty:
        zp_sorted = zp_df.sort_values(by='Data dostawy')
        standard_batch = float(zp_sorted.iloc[0]['Zamówione'])
    
    # Dokumenty ZS (zamówienia sprzedaży) - ale używamy kolumny Potwierdzone
    zs_df = material_data[material_data['DocNum'].astype(str).str.upper().str.contains('ZS', na=False)]
    zs_df = zs_df[zs_df['Potwierdzone'] > 0]
    weekly_zs_consumption = zs_df.groupby(['year', 'week'])['Potwierdzone'].sum()
    
    return current_stock, weekly_zp_income, weekly_zs_consumption, standard_batch

def run_as_is_simulation(current_stock, forecast_series, aligned_income, aligned_consumption):
    """Symulacja AS-IS - obecny plan bez korekt."""
    simulation_data = []
    stock = current_stock
    
    for i in range(len(forecast_series) - 1):
        stock_at_start = stock
        income_zp = aligned_income.iloc[i]
        consumption_zs = aligned_consumption.iloc[i]
        demand_forecast = forecast_series.iloc[i]
        demand_next_week = forecast_series.iloc[i+1]
        
        stock_after_all = stock_at_start + income_zp - (demand_forecast + consumption_zs)
        
        # Analiza problemu
        decision = "✅ OK"
        if stock_after_all < demand_next_week:
            decision = "🔴 BRAK"
        elif i + 3 < len(forecast_series) and income_zp > 0:
            three_week_buffer = demand_next_week + forecast_series.iloc[i+2] + forecast_series.iloc[i+3]
            if stock_after_all > three_week_buffer:
                decision = "🟡 NADMIAR"
        
        row = {
            "Tydzień (pon-pt)": get_date_range_from_week(forecast_series.index[i]),
            "Tydzień": str(forecast_series.index[i]).strip(),
            "Zapas początek": stock_at_start,
            "Przychód ZP": income_zp,
            "Rozchód ZS": consumption_zs,
            "Popyt (prognoza)": demand_forecast,
            "Zapas koniec": stock_after_all,
            "Bufor (nast. tydz.)": demand_next_week,
            "Status": decision
        }
        simulation_data.append(row)
        stock = stock_after_all
    
    return simulation_data

def run_optimized_simulation(current_stock, forecast_series, aligned_income, aligned_consumption, batch_size):
    """Symulacja TO-BE - zoptymalizowany plan."""
    simulation_data = []
    stock = current_stock
    future_adjustments = {}
    
    for i in range(len(forecast_series) - 1):
        week_name = forecast_series.index[i]
        postponed = future_adjustments.get(week_name, 0)
        original_income = aligned_income.iloc[i]
        current_income = original_income + postponed
        
        demand_forecast = forecast_series.iloc[i]
        demand_next_week = forecast_series.iloc[i+1]
        consumption_zs = aligned_consumption.iloc[i]
        
        stock_at_start = stock
        stock_after = stock_at_start + current_income - (demand_forecast + consumption_zs)
        
        action = ""
        
        # Logika optymalizacji
        if stock_after < demand_next_week:
            deficit = demand_next_week - stock_after
            needed = (math.ceil(deficit / batch_size) * batch_size) if batch_size and batch_size > 0 else deficit
            action = f"🔴 PRODUKCJA: +{needed:,.0f}"
            stock = stock_after + needed
        elif i + 3 < len(forecast_series) and original_income > 0:
            stock_without_zp = stock_after - original_income
            three_week_buffer = demand_next_week + forecast_series.iloc[i+2] + forecast_series.iloc[i+3]
            
            if (stock_after > three_week_buffer) and (stock_without_zp >= demand_next_week):
                target_week = "Poza horyzontem"
                temp_stock = stock_without_zp
                
                for k in range(i + 1, len(forecast_series) - 1):
                    temp_stock += (aligned_income.iloc[k] + future_adjustments.get(forecast_series.index[k], 0)) - (aligned_consumption.iloc[k] + forecast_series.iloc[k])
                    if temp_stock < forecast_series.iloc[k+1]:
                        target_week = forecast_series.index[k].strip()
                        break
                
                future_adjustments[target_week] = future_adjustments.get(target_week, 0) + original_income
                action = f"🟡➡️ PRZESUNIĘTO: {original_income:,.0f} na {target_week}"
                current_income -= original_income
                stock = stock_without_zp
            else:
                stock = stock_after
        else:
            stock = stock_after
        
        if postponed > 0:
            action += f" 🟡⬅️ PRZYJĘTO: {postponed:,.0f}"
        
        row = {
            "Tydzień (pon-pt)": get_date_range_from_week(week_name),
            "Tydzień": str(week_name).strip(),
            "Zapas początek": stock_at_start,
            "Przychód ZP": current_income,
            "Rozchód ZS": consumption_zs,
            "Popyt (prognoza)": demand_forecast,
            "Akcja": action.strip(),
            "Zapas koniec": stock,
            "Bufor (nast. tydz.)": demand_next_week
        }
        simulation_data.append(row)
    
    return simulation_data

def create_comparison_chart(as_is_df: pd.DataFrame, optimized_df: pd.DataFrame, material_number: int):
    """Tworzy interaktywny wykres porównawczy z Plotly."""
    fig = go.Figure()
    
    # Linia AS-IS
    fig.add_trace(go.Scatter(
        x=as_is_df['Tydzień'],
        y=as_is_df['Zapas koniec'],
        mode='lines+markers',
        name='AS-IS (bez korekt)',
        line=dict(color='red', width=2, dash='dash'),
        marker=dict(size=8)
    ))
    
    # Linia TO-BE
    fig.add_trace(go.Scatter(
        x=optimized_df['Tydzień'],
        y=optimized_df['Zapas koniec'],
        mode='lines+markers',
        name='TO-BE (zoptymalizowany)',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))
    
    # Linia zerowa
    fig.add_hline(y=0, line_dash="solid", line_color="black", line_width=1)
    
    fig.update_layout(
        title=f'Porównanie Stanu Zapasów: AS-IS vs TO-BE<br>Materiał: {material_number}',
        xaxis_title='Tydzień',
        yaxis_title='Zapas na koniec tygodnia [szt.]',
        hovermode='x unified',
        height=500,
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )
    
    return fig

def calculate_coverage(stock: float, avg_weekly_demand: float) -> float:
    """Oblicza pokrycie zapasów w tygodniach."""
    if avg_weekly_demand > 0:
        return stock / avg_weekly_demand
    return float('inf')

def analyze_all_materials(forecast_df: pd.DataFrame, stock_df: pd.DataFrame):
    """Analizuje wszystkie materiały i zwraca podsumowanie."""
    results = []
    
    for material in forecast_df.index:
        try:
            current_stock, weekly_zp, weekly_zs, batch = extract_material_data(stock_df, material)
            forecast_series = forecast_df.loc[material]
            
            # Podstawowe statystyki
            total_demand = forecast_series.sum()
            avg_demand = forecast_series.mean()
            max_demand = forecast_series.max()
            
            # Pokrycie
            coverage = calculate_coverage(current_stock, avg_demand)
            
            # Symulacja AS-IS
            aligned_income = pd.Series(0.0, index=forecast_series.index)
            aligned_consumption = pd.Series(0.0, index=forecast_series.index)
            
            for col in forecast_series.index:
                parsed = get_year_week_from_col(col)
                if parsed:
                    year, week = parsed
                    if (year, week) in weekly_zp.index:
                        aligned_income[col] = weekly_zp[(year, week)]
                    if (year, week) in weekly_zs.index:
                        aligned_consumption[col] = weekly_zs[(year, week)]
            
            as_is_data = run_as_is_simulation(current_stock, forecast_series, aligned_income, aligned_consumption)
            as_is_df = pd.DataFrame(as_is_data)
            
            # Wykryj problemy
            has_shortage = any('BRAK' in status for status in as_is_df['Status'])
            has_excess = any('NADMIAR' in status for status in as_is_df['Status'])
            
            status = "✅ OK"
            if has_shortage:
                status = "🔴 BRAKI"
            elif has_excess:
                status = "🟡 NADMIAR"
            
            results.append({
                'Materiał': material,
                'Stan magazynowy': current_stock,
                'Popyt całkowity': total_demand,
                'Śr. popyt tyg.': avg_demand,
                'Pokrycie [tyg.]': coverage,
                'Partia std.': batch if batch else 0,
                'Status': status,
                'Braki': has_shortage,
                'Nadmiar': has_excess
            })
            
        except Exception as e:
            results.append({
                'Materiał': material,
                'Stan magazynowy': 0,
                'Popyt całkowity': 0,
                'Śr. popyt tyg.': 0,
                'Pokrycie [tyg.]': 0,
                'Partia std.': 0,
                'Status': f"❌ BŁĄD: {str(e)[:30]}",
                'Braki': False,
                'Nadmiar': False
            })
    
    return pd.DataFrame(results)
