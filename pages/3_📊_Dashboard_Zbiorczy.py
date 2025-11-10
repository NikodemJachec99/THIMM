# pages/3_📊_Dashboard_Zbiorczy.py

import streamlit as st
import pandas as pd
from utils import analyze_all_materials

st.set_page_config(page_title="Dashboard Zbiorczy", page_icon="📊", layout="wide")

st.title("📊 Dashboard Zbiorczy - Wszystkie Materiały")

# Sprawdzenie danych
if st.session_state.get('forecast_data') is None or st.session_state.get('stock_data') is None:
    st.error("❌ Brak kompletnych danych. Proszę wgrać plik prognozy i stanu magazynowego.")
    st.stop()

# Główna analiza
try:
    with st.spinner("🔄 Analizuję wszystkie materiały..."):
        summary_df = analyze_all_materials(
            st.session_state.forecast_data,
            st.session_state.stock_data
        )
    
    # KPI na górze
    st.subheader("📈 Kluczowe Wskaźniki")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        total_materials = len(summary_df)
        st.metric("📦 Materiałów", total_materials)
    
    with col2:
        ok_count = (summary_df['Status'] == '✅ OK').sum()
        st.metric("✅ OK", ok_count, delta=f"{ok_count/total_materials*100:.1f}%")
    
    with col3:
        shortage_count = summary_df['Braki'].sum()
        st.metric("🔴 Braki", shortage_count, delta=f"{shortage_count/total_materials*100:.1f}%", delta_color="inverse")
    
    with col4:
        excess_count = summary_df['Nadmiar'].sum()
        st.metric("🟡 Nadmiar", excess_count, delta=f"{excess_count/total_materials*100:.1f}%")
    
    with col5:
        total_stock_value = summary_df['Stan magazynowy'].sum()
        st.metric("💰 Całk. zapas", f"{total_stock_value:,.0f}")
    
    st.divider()
    
    # Filtry
    st.subheader("🔍 Filtrowanie i Wyszukiwanie")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.multiselect(
            "Status:",
            options=['✅ OK', '🔴 BRAKI', '🟡 NADMIAR'],
            default=['✅ OK', '🔴 BRAKI', '🟡 NADMIAR']
        )
    
    with col2:
        min_coverage = st.number_input("Min. pokrycie [tyg.]:", min_value=0.0, value=0.0, step=0.5)
    
    with col3:
        max_coverage = st.number_input("Max. pokrycie [tyg.]:", min_value=0.0, value=100.0, step=0.5)
    
    # Filtrowanie
    filtered_df = summary_df[
        (summary_df['Status'].isin(status_filter)) &
        (summary_df['Pokrycie [tyg.]'] >= min_coverage) &
        (summary_df['Pokrycie [tyg.]'] <= max_coverage)
    ]
    
    # Sortowanie
    sort_by = st.selectbox(
        "Sortuj według:",
        options=['Materiał', 'Stan magazynowy', 'Popyt całkowity', 'Pokrycie [tyg.]', 'Status'],
        index=4
    )
    
    sort_order = st.radio("Kolejność:", ['Rosnąco', 'Malejąco'], horizontal=True)
    ascending = (sort_order == 'Rosnąco')
    
    filtered_df = filtered_df.sort_values(by=sort_by, ascending=ascending)
    
    st.divider()
    
    # Wyświetlenie tabeli
    st.subheader(f"📋 Lista Materiałów ({len(filtered_df)} z {len(summary_df)})")
    
    # Funkcja stylistyki
    def style_status(row):
        status = row['Status']
        if '🔴' in status:
            return ['background-color: #ffcdd2'] * len(row)
        elif '🟡' in status:
            return ['background-color: #fff9c4'] * len(row)
        elif '✅' in status:
            return ['background-color: #c8e6c9'] * len(row)
        else:
            return [''] * len(row)
    
    # Formatowanie
    display_df = filtered_df.copy()
    
    styled_df = display_df.style.format({
        'Stan magazynowy': '{:,.0f}',
        'Popyt całkowity': '{:,.0f}',
        'Śr. popyt tyg.': '{:,.1f}',
        'Pokrycie [tyg.]': '{:.1f}',
        'Partia std.': '{:,.0f}'
    }).apply(style_status, axis=1)
    
    st.dataframe(styled_df, use_container_width=True, height=600)
    
    # Statystyki przefiltrowanych
    if len(filtered_df) > 0:
        st.divider()
        st.subheader("📊 Statystyki przefiltrowanych materiałów")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Śr. pokrycie", f"{filtered_df['Pokrycie [tyg.]'].mean():.1f} tyg.")
        
        with col2:
            st.metric("Śr. stan mag.", f"{filtered_df['Stan magazynowy'].mean():,.0f}")
        
        with col3:
            st.metric("Całk. popyt", f"{filtered_df['Popyt całkowity'].sum():,.0f}")
        
        with col4:
            st.metric("Śr. partia", f"{filtered_df['Partia std.'].mean():,.0f}")
    
    # Eksport
    st.divider()
    
    csv = filtered_df.to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
    st.download_button(
        label="💾 Pobierz jako CSV",
        data=csv,
        file_name="dashboard_summary.csv",
        mime="text/csv"
    )
    
    # Przycisk do szczegółowej analizy
    st.divider()
    st.info("💡 **Wskazówka:** Aby zobaczyć szczegółową analizę konkretnego materiału, przejdź do strony '🔍 Analiza Szczegółowa'")

except Exception as e:
    st.error(f"❌ Wystąpił błąd podczas analizy: {e}")
    st.exception(e)
