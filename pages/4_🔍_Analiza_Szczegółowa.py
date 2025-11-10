# pages/4_🔍_Analiza_Szczegółowa.py

import streamlit as st
import pandas as pd
from utils import (
    extract_material_data,
    run_as_is_simulation,
    run_optimized_simulation,
    get_year_week_from_col,
    create_comparison_chart,
    calculate_coverage
)

st.set_page_config(page_title="Analiza Szczegółowa", page_icon="🔍", layout="wide")

st.title("🔍 Analiza Szczegółowa Materiału")

# Sprawdzenie danych
if st.session_state.get('forecast_data') is None or st.session_state.get('stock_data') is None:
    st.error("❌ Brak kompletnych danych. Proszę wgrać plik prognozy i stanu magazynowego.")
    st.stop()

# Wybór materiału
forecast_df = st.session_state.forecast_data
stock_df = st.session_state.stock_data

# Lista dostępnych materiałów (wspólne w obu plikach)
available_materials = sorted(list(set(forecast_df.index) & set(stock_df['numer indeksu'].unique())))

if not available_materials:
    st.error("❌ Nie znaleziono wspólnych materiałów w prognozie i stanie magazynowym!")
    st.stop()

st.sidebar.subheader("🎯 Wybierz Materiał")
selected_material = st.sidebar.selectbox(
    "Numer materiału:",
    options=available_materials,
    index=0,
    format_func=lambda x: f"{x}"
)

# Przechowaj w sesji
st.session_state.selected_material = selected_material

try:
    # Wyodrębnienie danych
    current_stock, weekly_zp, weekly_zs, batch_size = extract_material_data(stock_df, selected_material)
    forecast_series = forecast_df.loc[selected_material]
    
    # Nagłówek z KPI
    st.header(f"📦 Materiał: `{selected_material}`", divider="blue")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("💼 Stan magazynowy", f"{current_stock:,.0f}")
    
    with col2:
        total_demand = forecast_series.sum()
        st.metric("📊 Popyt całkowity", f"{total_demand:,.0f}")
    
    with col3:
        avg_demand = forecast_series.mean()
        st.metric("📈 Śr. popyt tyg.", f"{avg_demand:,.1f}")
    
    with col4:
        coverage = calculate_coverage(current_stock, avg_demand)
        if coverage == float('inf'):
            st.metric("⏱️ Pokrycie", "∞")
        else:
            st.metric("⏱️ Pokrycie", f"{coverage:.1f} tyg.")
    
    with col5:
        if batch_size:
            st.metric("📦 Partia std.", f"{batch_size:,.0f}")
        else:
            st.metric("📦 Partia std.", "Brak")
    
    st.divider()
    
    # Przygotowanie danych do symulacji
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
    
    # Symulacje
    as_is_data = run_as_is_simulation(current_stock, forecast_series, aligned_income, aligned_consumption)
    df_as_is = pd.DataFrame(as_is_data)
    
    optimized_data = run_optimized_simulation(current_stock, forecast_series, aligned_income, aligned_consumption, batch_size)
    df_optimized = pd.DataFrame(optimized_data)
    
    # Wykres porównawczy
    st.subheader("📈 Wizualizacja Porównawcza", divider="green")
    
    fig = create_comparison_chart(df_as_is, df_optimized, selected_material)
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # Tabele
    tab1, tab2 = st.tabs(["🔴 Plan AS-IS (Diagnoza)", "✅ Plan TO-BE (Optymalizacja)"])
    
    with tab1:
        st.markdown("""
        ### 📋 Diagnoza Obecnego Planu (AS-IS)
        Ta symulacja pokazuje, co się stanie, jeśli **nie wprowadzisz żadnych zmian** w obecnym planie produkcyjnym.
        """)
        
        # Statystyki AS-IS
        col1, col2, col3 = st.columns(3)
        
        with col1:
            shortage_count = sum('BRAK' in status for status in df_as_is['Status'])
            st.metric("🔴 Tygodni z brakami", shortage_count)
        
        with col2:
            excess_count = sum('NADMIAR' in status for status in df_as_is['Status'])
            st.metric("🟡 Tygodni z nadmiarem", excess_count)
        
        with col3:
            ok_count = sum('OK' in status for status in df_as_is['Status'])
            st.metric("✅ Tygodni OK", ok_count)
        
        # Tabela AS-IS
        def style_as_is(row):
            if 'BRAK' in row['Status']:
                return ['background-color: #ffcdd2'] * len(row)
            elif 'NADMIAR' in row['Status']:
                return ['background-color: #fff9c4'] * len(row)
            else:
                return ['background-color: #c8e6c9'] * len(row)
        
        styled_as_is = df_as_is.style.format({
            'Zapas początek': '{:,.0f}',
            'Przychód ZP': '{:,.0f}',
            'Rozchód ZS': '{:,.0f}',
            'Popyt (prognoza)': '{:,.0f}',
            'Zapas koniec': '{:,.0f}',
            'Bufor (nast. tydz.)': '{:,.0f}'
        }).apply(style_as_is, axis=1)
        
        st.dataframe(styled_as_is, use_container_width=True, height=500)
        
        # Legenda
        with st.expander("📖 Legenda kolumn"):
            st.markdown("""
            - **Tydzień (pon-pt)**: Zakres dat tygodnia roboczego
            - **Zapas początek**: Stan magazynu na początku tygodnia
            - **Przychód ZP**: Planowane dostawy z produkcji (dokumenty ZP)
            - **Rozchód ZS**: Potwierdzony rozchód (dokumenty ZS)
            - **Popyt (prognoza)**: Prognozowany popyt z pliku prognozy
            - **Zapas koniec**: Przewidywany stan na koniec tygodnia
            - **Bufor (nast. tydz.)**: Popyt w następnym tygodniu (do oceny czy zapas wystarczy)
            - **Status**: 
                - 🔴 BRAK - zapas nie pokryje popytu następnego tygodnia
                - 🟡 NADMIAR - zapas znacznie przekracza potrzeby
                - ✅ OK - stan optymalny
            """)
    
    with tab2:
        st.markdown("""
        ### ✅ Zoptymalizowany Plan (TO-BE)
        Ta symulacja pokazuje **rekomendowany plan** z automatycznymi korektami w celu uniknięcia braków i redukcji nadmiarów.
        """)
        
        # Statystyki TO-BE
        col1, col2, col3 = st.columns(3)
        
        with col1:
            production_count = sum('PRODUKCJA' in str(action) for action in df_optimized['Akcja'])
            st.metric("🔴 Akcji produkcji", production_count)
        
        with col2:
            postpone_count = sum('PRZESUNIĘTO' in str(action) for action in df_optimized['Akcja'])
            st.metric("🟡 Przesunięć", postpone_count)
        
        with col3:
            min_stock = df_optimized['Zapas koniec'].min()
            st.metric("📊 Min. zapas", f"{min_stock:,.0f}")
        
        # Tabela TO-BE
        def style_to_be(row):
            action = str(row['Akcja'])
            if 'PRODUKCJA' in action:
                return ['background-color: #c8e6c9'] * len(row)
            elif 'PRZESUNIĘTO' in action or 'PRZYJĘTO' in action:
                return ['background-color: #fff9c4'] * len(row)
            else:
                return [''] * len(row)
        
        styled_to_be = df_optimized.style.format({
            'Zapas początek': '{:,.0f}',
            'Przychód ZP': '{:,.0f}',
            'Rozchód ZS': '{:,.0f}',
            'Popyt (prognoza)': '{:,.0f}',
            'Zapas koniec': '{:,.0f}',
            'Bufor (nast. tydz.)': '{:,.0f}'
        }).apply(style_to_be, axis=1)
        
        st.dataframe(styled_to_be, use_container_width=True, height=500)
        
        # Legenda
        with st.expander("📖 Legenda akcji korygujących"):
            st.markdown("""
            - **🔴 PRODUKCJA**: Należy uruchomić produkcję o podanej wielkości
            - **🟡➡️ PRZESUNIĘTO**: Zaplanowana dostawa ZP została przesunięta na późniejszy termin
            - **🟡⬅️ PRZYJĘTO**: W tym tygodniu przyjęto dostawę przesuniętą z wcześniejszego terminu
            - **Brak akcji**: Nie są potrzebne żadne korekty
            
            **Kolory wierszy:**
            - 🟢 Zielony - tydzień z akcją produkcji
            - 🟡 Żółty - tydzień z przesunięciem dostaw
            - Biały - brak akcji
            """)
    
    st.divider()
    
    # Eksport danych
    st.subheader("💾 Eksport Danych")
    
    col1, col2 = st.columns(2)
    
    with col1:
        csv_as_is = df_as_is.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button(
            label="📥 Pobierz AS-IS (CSV)",
            data=csv_as_is,
            file_name=f"as_is_{selected_material}.csv",
            mime="text/csv"
        )
    
    with col2:
        csv_to_be = df_optimized.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
        st.download_button(
            label="📥 Pobierz TO-BE (CSV)",
            data=csv_to_be,
            file_name=f"to_be_{selected_material}.csv",
            mime="text/csv"
        )

except Exception as e:
    st.error(f"❌ Wystąpił błąd podczas analizy materiału {selected_material}: {e}")
    st.exception(e)

# Sidebar - szybka nawigacja
st.sidebar.divider()
st.sidebar.subheader("🔄 Szybka nawigacja")
if st.sidebar.button("◀️ Poprzedni materiał"):
    current_idx = available_materials.index(selected_material)
    if current_idx > 0:
        st.session_state.selected_material = available_materials[current_idx - 1]
        st.rerun()

if st.sidebar.button("Następny materiał ▶️"):
    current_idx = available_materials.index(selected_material)
    if current_idx < len(available_materials) - 1:
        st.session_state.selected_material = available_materials[current_idx + 1]
        st.rerun()

st.sidebar.info(f"Materiał {available_materials.index(selected_material) + 1} z {len(available_materials)}")
