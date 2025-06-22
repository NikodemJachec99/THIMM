# utils.py

import pandas as pd
from datetime import datetime, timedelta
import re
import io
import math
import streamlit as st
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

# --- Reszta funkcji (bez zmian) ---

def get_date_range_from_week(week_str: str) -> str:
    """Konwertuje identyfikator tygodnia na zakres dat roboczych (pon-pt) zgodnie ze standardem ISO 8601."""
    year, week_num = None, None
    try:
        col_name = week_str.strip()
        match = re.search(r'\s(\d{1,2})/(\d{2})$', col_name)
        if match: week_num, year_short = map(int, match.groups()); year = 2000 + year_short
        else:
            match = re.search(r'(\d{1,2})\.(\d{4})$', col_name)
            if match: week_num, year = map(int, match.groups())
        if year is None or week_num is None: return "Nieznany format"
        start_date = datetime.strptime(f'{year}-{week_num}-1', "%G-%V-%u")
        end_date = start_date + timedelta(days=4) 
        return f"{start_date.strftime('%d.%m.%Y')} - {end_date.strftime('%d.%m.%Y')}"
    except (ValueError, TypeError): return "Błąd konwersji daty"

def read_data_file(uploaded_file, file_name: str) -> pd.DataFrame:
    """Wczytuje plik CSV lub XLSX z obiektu typu BytesIO."""
    if file_name.endswith('.csv'):
        encodings_to_try = ['utf-8', 'windows-1250', 'latin1', 'iso-8859-2']
        for encoding in encodings_to_try:
            try:
                uploaded_file.seek(0)
                df = pd.read_csv(uploaded_file, sep=';', encoding=encoding); return df
            except Exception: continue
        raise ValueError("Nie udało się odczytać pliku CSV.")
    elif file_name.endswith(('.xlsx', '.xls')):
        try:
            uploaded_file.seek(0); df = pd.read_excel(uploaded_file, dtype=str); return df
        except Exception as e: raise ValueError(f"Błąd odczytu pliku Excel: {e}")
    else: raise ValueError("Niewspierany format pliku.")

def get_year_week_from_col(col_name: str):
    col_name = str(col_name).strip()
    match = re.search(r'\s(\d{1,2})/(\d{2})$', col_name)
    if match: week, year_short = map(int, match.groups()); return 2000 + year_short, week
    match = re.search(r'(\d{1,2})\.(\d{4})$', col_name)
    if match: week, year = map(int, match.groups()); return year, week
    return None

def process_forecast_file(uploaded_file) -> pd.DataFrame:
    df = read_data_file(uploaded_file, uploaded_file.name)
    correct_material_col = 'Materialnummer'
    if correct_material_col not in df.columns: raise ValueError(f"Brak kolumny '{correct_material_col}'.")
    df.dropna(subset=[correct_material_col], inplace=True)
    df[correct_material_col] = pd.to_numeric(df[correct_material_col], errors='coerce')
    df.dropna(subset=[correct_material_col], inplace=True)
    df[correct_material_col] = df[correct_material_col].astype(int)
    week_cols = [col for col in df.columns if get_year_week_from_col(col) is not None]
    week_cols.sort(key=lambda col: get_year_week_from_col(col))
    if not week_cols: raise ValueError("Nie znaleziono kolumn z prognozą.")
    df.set_index(correct_material_col, inplace=True)
    for col in week_cols:
        if df[col].dtype == 'object': df[col] = df[col].astype(str).str.replace(',', '.', regex=False)
    return df[week_cols].fillna(0).apply(pd.to_numeric, errors='coerce').fillna(0)

def process_stock_file(uploaded_file, file_name: str) -> (int, float, pd.Series, pd.Series, float):
    df = read_data_file(uploaded_file, file_name)
    required_cols = ['Dokument', 'Dostępne', 'Data dostawy', 'Potwierdzone', 'Odbiorca/Dostawca', 'Zamówione']
    for col in required_cols:
        if col not in df.columns: raise ValueError(f"Brak wymaganej kolumny '{col}'.")
    material_number = None
    if not df['Dokument'].empty:
        match = re.search(r'\d+', str(df['Dokument'].iloc[0]))
        if match: material_number = int(match.group(0))
    if material_number is None: raise ValueError("Nie odnaleziono numeru indeksu.")
    df['Dostępne'] = df['Dostępne'].astype(str).str.replace(',', '.', regex=False)
    in_stock_row = df[df['Odbiorca/Dostawca'].astype(str).str.strip() == 'W magazynie']
    current_on_hand_stock = 0.0
    if not in_stock_row.empty:
        stock_val = pd.to_numeric(in_stock_row['Dostępne'].iloc[0], errors='coerce')
        current_on_hand_stock = 0.0 if pd.isna(stock_val) else stock_val
    else: st.warning("Uwaga: Nie znaleziono wiersza 'W magazynie'.")
    df['Data dostawy'] = pd.to_datetime(df['Data dostawy'], dayfirst=True, errors='coerce')
    df['week'] = df['Data dostawy'].dt.isocalendar().week
    df['year'] = df['Data dostawy'].dt.isocalendar().year
    df['Zamówione'] = df['Zamówione'].astype(str).str.replace(',', '.', regex=False)
    df['Potwierdzone'] = df['Potwierdzone'].astype(str).str.replace(',', '.', regex=False)
    df['qty_zamowione'] = pd.to_numeric(df['Zamówione'], errors='coerce').fillna(0)
    df['qty_potwierdzone'] = pd.to_numeric(df['Potwierdzone'], errors='coerce').fillna(0)
    zp_df = df[df['Dokument'].astype(str).str.upper().str.contains('ZP', na=False)]
    weekly_zp_income = zp_df[zp_df['qty_zamowione'] > 0].groupby(['year', 'week'])['qty_zamowione'].sum()
    or_df = df[df['Dokument'].astype(str).str.upper().str.contains('OR', na=False) & (df['qty_potwierdzone'] > 0)]
    weekly_or_consumption = or_df.groupby(['year', 'week'])['qty_potwierdzone'].sum()
    standard_batch_size = None
    zp_with_qty = zp_df[zp_df['qty_zamowione'] > 0].sort_values(by='Data dostawy')
    if not zp_with_qty.empty: standard_batch_size = zp_with_qty.iloc[0]['qty_zamowione']
    return material_number, float(current_on_hand_stock), weekly_zp_income, weekly_or_consumption, standard_batch_size

def run_as_is_simulation(current_stock, forecast_series, aligned_income, aligned_consumption):
    simulation_data = []
    stock = current_stock
    for i in range(len(forecast_series) - 1):
        stock_at_start = stock
        income_zp, consumption_or = aligned_income.iloc[i], aligned_consumption.iloc[i]
        demand_forecast, demand_next_week = forecast_series.iloc[i], forecast_series.iloc[i+1]
        stock_after_all_events = stock_at_start + income_zp - (demand_forecast + consumption_or)
        decision = "✅ OK"
        if stock_after_all_events < demand_next_week: decision = "🔴 BRAK"
        elif i + 3 < len(forecast_series) and income_zp > 0:
            if stock_after_all_events > (demand_next_week + forecast_series.iloc[i+2] + forecast_series.iloc[i+3]):
                decision = "🟡 NADMIAR"
        row = { "Tydzień (pon-pt)": get_date_range_from_week(forecast_series.index[i]), "Tydzień (numer)": str(forecast_series.index[i]).strip(), "Zapas na pocz. tyg.": stock_at_start, "Przychód (ZP)": income_zp, "Rozchód (OR)": consumption_or, "Popyt (prognoza)": demand_forecast, "Zapas na kon. tyg.": stock_after_all_events, "Bufor (popyt nast. tyg.)": demand_next_week, "Problem?": decision }
        simulation_data.append(row)
        stock = stock_after_all_events
    return simulation_data

def run_optimized_simulation(current_stock, forecast_series, aligned_income, aligned_consumption, batch_size):
    simulation_data = []
    stock = current_stock
    future_zp_adjustments = {}
    for i in range(len(forecast_series) - 1):
        week_name = forecast_series.index[i]
        postponed_income = future_zp_adjustments.get(week_name, 0)
        original_income_zp = aligned_income.iloc[i]
        current_week_income = original_income_zp + postponed_income
        demand_forecast, demand_next_week = forecast_series.iloc[i], forecast_series.iloc[i+1]
        consumption_or = aligned_consumption.iloc[i]
        stock_at_start = stock
        stock_after_events = stock_at_start + current_week_income - (demand_forecast + consumption_or)
        action_message = ""
        if stock_after_events < demand_next_week:
            deficit = demand_next_week - stock_after_events
            needed_quantity = (math.ceil(deficit / batch_size) * batch_size) if batch_size and batch_size > 0 else deficit
            action_message = f"🔴 PRODUKCJA: +{needed_quantity:,.0f}".replace(',', ' ')
            stock = stock_after_events + needed_quantity
        elif i + 3 < len(forecast_series) and original_income_zp > 0:
            stock_without_zp = stock_after_events - original_income_zp
            three_week_demand_buffer = demand_next_week + forecast_series.iloc[i+2] + forecast_series.iloc[i+3]
            if (stock_after_events > three_week_demand_buffer) and (stock_without_zp >= demand_next_week):
                target_week_id = "Poza horyzontem"
                temp_stock = stock_without_zp
                for k in range(i + 1, len(forecast_series) - 1):
                    temp_stock += (aligned_income.iloc[k] + future_zp_adjustments.get(forecast_series.index[k], 0)) - (aligned_consumption.iloc[k] + forecast_series.iloc[k])
                    if temp_stock < forecast_series.iloc[k+1]:
                        target_week_id = forecast_series.index[k].strip(); break
                future_zp_adjustments[target_week_id] = future_zp_adjustments.get(target_week_id, 0) + original_income_zp
                action_message = f"🟡➡️ PRZESUNIĘTO: {original_income_zp:,.0f} na {target_week_id}".replace(',', ' ')
                current_week_income -= original_income_zp
                stock = stock_without_zp
            else: stock = stock_after_events
        else: stock = stock_after_events
        if postponed_income > 0:
            action_message += f" 🟡⬅️ PRZYJĘTO: {postponed_income:,.0f}".replace(',', ' ')
        row = { "Tydzień (pon-pt)": get_date_range_from_week(week_name), "Tydzień (numer)": str(week_name).strip(), "Zapas na pocz. tyg.": stock_at_start, "Przychód (ZP)": current_week_income, "Rozchód (OR)": consumption_or, "Popyt (prognoza)": demand_forecast, "Akcja Korygująca": action_message.strip(), "Zapas na kon. tyg.": stock, "Bufor (popyt nast. tyg.)": demand_next_week }
        simulation_data.append(row)
    return simulation_data


def create_comparison_chart(as_is_df: pd.DataFrame, optimized_df: pd.DataFrame) -> str:
    """Tworzy i zapisuje wykres porównawczy stanu zapasów."""
    
    plt.style.use('seaborn-v0_8-whitegrid')
    fig, ax = plt.subplots(figsize=(14, 7))

    # Dane AS-IS
    ax.plot(
        as_is_df['Tydzień (numer)'], 
        as_is_df['Zapas na kon. tyg.'], 
        color='red', 
        linestyle='--', 
        marker='o', 
        label='Plan AS-IS (bez korekt)'
    )

    # Dane TO-BE (zoptymalizowane)
    ax.plot(
        optimized_df['Tydzień (numer)'], 
        optimized_df['Zapas na kon. tyg.'], 
        color='green', 
        linestyle='-', 
        marker='o', 
        label='Plan TO-BE (Zoptymalizowany)',
        linewidth=2.5
    )

    # Linia zerowa jako punkt odniesienia
    ax.axhline(0, color='black', linewidth=0.8, linestyle='-')

    # Tytuły i etykiety
    ax.set_title('Porównanie Stanu Zapasów: Plan AS-IS vs. TO-BE', fontsize=18, pad=20)
    ax.set_xlabel('Tydzień Prognozy', fontsize=12)
    ax.set_ylabel('Przewidywany Zapas na Koniec Tygodnia [szt.]', fontsize=12)
    
    # Formatowanie osi Y dla lepszej czytelności
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: format(int(x), ',')))
    
    # Obrót etykiet osi X
    plt.xticks(rotation=45, ha='right')
    
    # Legenda
    ax.legend(fontsize=12)
    
    # Dopasowanie układu i zapisanie pliku
    fig.tight_layout()
    chart_filename = "stock_comparison_chart.png"
    plt.savefig(chart_filename)
    plt.close(fig) # Zamknięcie figury, aby zwolnić pamięć
    
    return chart_filename