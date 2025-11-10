# pages/1_📈_Wgraj_Prognozę.py

import streamlit as st
from utils import process_forecast_file

st.set_page_config(page_title="Wgrywanie Prognozy", page_icon="📈", layout="wide")

st.title("📈 Krok 1: Wgraj Plik z Prognozą")

# Inicjalizacja stanu sesji
if 'forecast_data' not in st.session_state:
    st.session_state.forecast_data = None
    st.session_state.forecast_filename = None

st.markdown("""
### Instrukcje:
1. Plik powinien zawierać kolumnę **'Materialnummer'** z numerami indeksów
2. Kolumny tygodniowe w formacie: **KW XX/YY** lub **XX.YYYY**
3. Obsługiwane formaty: **CSV** (separator `;`) lub **Excel**
""")

forecast_file = st.file_uploader(
    "Wybierz plik prognozy",
    type=["csv", "xlsx"],
    help="Plik powinien zawierać kolumnę 'Materialnummer' oraz kolumny z tygodniowymi prognozami."
)

if forecast_file:
    try:
        with st.spinner("🔄 Przetwarzanie pliku prognozy..."):
            st.session_state.forecast_data = process_forecast_file(forecast_file)
            st.session_state.forecast_filename = forecast_file.name
        
        st.success(f"✅ Pomyślnie załadowano: **{st.session_state.forecast_filename}**")
        
        # Statystyki
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📦 Liczba indeksów", len(st.session_state.forecast_data))
        with col2:
            st.metric("📅 Tygodni prognozy", len(st.session_state.forecast_data.columns))
        with col3:
            total_demand = st.session_state.forecast_data.sum().sum()
            st.metric("📊 Całkowity popyt", f"{total_demand:,.0f}")
        
        # Podgląd danych
        st.subheader("👁️ Podgląd danych (pierwsze 10 wierszy)")
        st.dataframe(
            st.session_state.forecast_data.head(10).style.format("{:,.0f}"),
            use_container_width=True
        )
        
        # Informacja o następnym kroku
        st.info("👉 **Następny krok:** Przejdź do strony '📦 Wgraj Dostępne Ilości'")
        
    except Exception as e:
        st.error(f"❌ Błąd podczas przetwarzania pliku: {e}")
        st.session_state.forecast_data = None
        st.session_state.forecast_filename = None

# Sidebar
if st.session_state.forecast_filename:
    st.sidebar.success(f"✅ Prognoza: **{st.session_state.forecast_filename}**")
    if st.session_state.forecast_data is not None:
        st.sidebar.info(f"📦 Indeksów: **{len(st.session_state.forecast_data)}**")
else:
    st.sidebar.warning("⏳ Oczekuję na plik prognozy")
