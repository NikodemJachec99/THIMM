# pages/3_📊_Wyniki_i_Optymalizacja.py

import streamlit as st
import pandas as pd
import io
from utils import (
    process_stock_file, 
    run_as_is_simulation, 
    run_optimized_simulation, 
    get_year_week_from_col,
    create_comparison_chart
)

st.set_page_config(page_title="Wyniki i Optymalizacja", page_icon="📊", layout="wide")

st.title("Krok 3: Wyniki Analizy i Propozycja Optymalizacji")

# Sprawdzenie, czy wszystkie potrzebne dane są w sesji
if st.session_state.get('forecast_data') is None or st.session_state.get('stock_file_bytes') is None:
    st.error("Brak kompletnych danych. Proszę wgrać plik prognozy i stanu magazynowego na odpowiednich stronach.")
    st.stop()

# Główna logika aplikacji
try:
    forecast_df = st.session_state.forecast_data
    stock_file_bytes = st.session_state.stock_file_bytes
    stock_filename = st.session_state.stock_filename
    
    # Przetworzenie pliku stanu magazynowego
    material_number, current_stock, weekly_zp_income, weekly_or_consumption, batch_size = process_stock_file(stock_file_bytes, stock_filename)
    
    st.header(f"Analiza dla indeksu: `{material_number}`", divider="blue")
    st.write(f"Rzeczywisty bieżący stan magazynowy ('W magazynie'): **{current_stock:,.2f}**".replace(',', ' ').replace('.', ','))
    if batch_size:
        st.write(f"Wykryta standardowa partia produkcyjna (z pierwszego ZP): **{batch_size:,.2f}**".replace(',', ' ').replace('.', ','))

    if material_number not in forecast_df.index:
        st.error(f"Błąd: Nie znaleziono materiału `{material_number}` w pliku z prognozą.")
    else:
        forecast_series = forecast_df.loc[material_number]
        
        aligned_income = pd.Series(0.0, index=forecast_series.index)
        aligned_consumption = pd.Series(0.0, index=forecast_series.index)
        for col_name in forecast_series.index:
            parsed_info = get_year_week_from_col(col_name)
            if parsed_info:
                year, week = parsed_info
                if (year, week) in weekly_zp_income.index: aligned_income[col_name] = weekly_zp_income[(year, week)]
                if (year, week) in weekly_or_consumption.index: aligned_consumption[col_name] = weekly_or_consumption[(year, week)]
        
        # --- POPRAWIONA KOLEJNOŚĆ ---
        # 1. NAJPIERW URUCHOM OBIE SYMULACJE I STWÓRZ OBIE TABELE DANYCH
        as_is_data = run_as_is_simulation(current_stock, forecast_series, aligned_income, aligned_consumption)
        df_as_is = pd.DataFrame(as_is_data)

        optimized_data = run_optimized_simulation(current_stock, forecast_series, aligned_income, aligned_consumption, batch_size)
        df_optimized = pd.DataFrame(optimized_data)

        # 2. DOPIERO TERAZ, MAJĄC DANE, STWÓRZ I WYŚWIETL WYKRES
        st.header("Wizualne Porównanie Planów", divider="green")
        with st.spinner("Generowanie wykresu porównawczego..."):
            chart_file = create_comparison_chart(df_as_is, df_optimized)
            st.image(chart_file)
        
        # 3. WYŚWIETL TABELĘ DIAGNOSTYCZNĄ (AS-IS)
        st.header("1. Diagnoza Bieżącego Planu (AS-IS)", divider="gray")
        st.info("Ta symulacja pokazuje problemy, które wystąpią, jeśli obecny plan **nie zostanie** zmieniony.")
        st.dataframe(df_as_is.style.format(formatter="{:,.2f}", subset=pd.IndexSlice[:, df_as_is.columns[2:-1]])
                    .apply(lambda r: ['background-color: #FFCDD2'] * len(r) if "BRAK" in r["Problem?"] 
                            else ['background-color: #FFF9C4'] * len(r) if "NADMIAR" in r["Problem?"] 
                            else [''] * len(r), axis=1), use_container_width=True)

        # 4. WYŚWIETL TABELĘ OPTYMALIZACYJNĄ (TO-BE)
        st.header("2. Propozycja Zoptymalizowanego Planu (TO-BE)", divider="blue")
        st.info("Ta symulacja pokazuje rekomendowany, skorygowany plan. Poniższa tabela zawiera wszystkie niezbędne akcje i ich wpływ na stan magazynowy.")
        
        with st.expander("Kliknij, aby zobaczyć legendę tabeli TO-BE"):
            st.markdown("""
            - **Akcja Korygująca**: Informuje o działaniach podjętych przez algorytm w celu optymalizacji planu:
                - `🔴 PRODUKCJA`: Wskazuje na konieczność uruchomienia produkcji o podanej ilości.
                - `🟡➡️ PRZESUNIĘTO`: Informuje, że zaplanowana na ten tydzień dostawa ZP została wirtualnie przesunięta na wskazany, późniejszy termin.
                - `🟡⬅️ PRZYJĘTO`: Informuje, że w tym tygodniu wirtualnie przyjęto dostawę ZP, która została przesunięta z wcześniejszego terminu.
            """)
        
        def style_actions(row):
            style = [''] * len(row)
            action = row["Akcja Korygująca"]
            if "PRODUKCJA" in action: style = ['background-color: #C8E6C9'] * len(row) # Green
            elif "PRZESUNIĘTO" in action or "PRZYJĘTO" in action: style = ['background-color: #FFFACD'] * len(row) # Yellow
            return style
        st.dataframe(df_optimized.style.format(formatter="{:,.2f}", subset=["Zapas na pocz. tyg.", "Przychód (ZP)", "Rozchód (OR)", "Popyt (prognoza)", "Zapas na kon. tyg.", "Bufor (popyt nast. tyg.)"])
                    .apply(style_actions, axis=1), use_container_width=True)

except Exception as e:
    st.error(f"Wystąpił nieoczekiwany błąd podczas generowania raportu: {e}")
    st.exception(e)