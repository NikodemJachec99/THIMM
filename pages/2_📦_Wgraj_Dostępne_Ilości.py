# pages/2_📦_Wgraj_Dostępne_Ilości.py

import streamlit as st
from utils import process_stock_file

st.set_page_config(page_title="Wgrywanie Dostępnych Ilości", page_icon="📦", layout="wide")

st.title("📦 Krok 2: Wgraj Plik Dostępnych Ilości")

# Inicjalizacja stanu sesji
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None
    st.session_state.stock_filename = None

# Sprawdź czy jest prognoza
if st.session_state.get('forecast_data') is None:
    st.error("❌ Brak wgranej prognozy! Proszę najpierw przejść do strony '📈 Wgraj Prognozę'.")
    st.stop()

st.info(f"✅ Wybrana prognoza: **{st.session_state.forecast_filename}**")

st.markdown("""
### Wymagane kolumny w pliku:
- **numer indeksu** - numer materiału
- **DocNum** - numer dokumentu (ZP, ZS, itp.)
- **Data dostawy** - format: DD-MM-YYYY
- **Zamówione** - ilość zamówiona
- **Potwierdzone** - ilość potwierdzona
- **w magazynie** - aktualny stan magazynowy

### Obsługiwane dokumenty:
- **ZP** - Zamówienia Produkcyjne (przychód)
- **ZS** - Zamówienia Sprzedaży (rozchód)
""")

stock_file = st.file_uploader(
    "Wybierz plik dostępnych ilości",
    type=["csv", "xlsx"],
    help="Plik powinien zawierać dane o stanach magazynowych i dokumentach dla wszystkich materiałów."
)

if stock_file:
    try:
        with st.spinner("🔄 Przetwarzanie pliku..."):
            st.session_state.stock_data = process_stock_file(stock_file, stock_file.name)
            st.session_state.stock_filename = stock_file.name
        
        st.success(f"✅ Pomyślnie załadowano: **{st.session_state.stock_filename}**")
        
        # Statystyki
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            unique_materials = st.session_state.stock_data['numer indeksu'].nunique()
            st.metric("📦 Unikalnych materiałów", unique_materials)
        
        with col2:
            total_docs = len(st.session_state.stock_data)
            st.metric("📄 Dokumentów", total_docs)
        
        with col3:
            zp_count = st.session_state.stock_data['DocNum'].astype(str).str.contains('ZP', na=False).sum()
            st.metric("📥 Dokumentów ZP", zp_count)
        
        with col4:
            zs_count = st.session_state.stock_data['DocNum'].astype(str).str.contains('ZS', na=False).sum()
            st.metric("📤 Dokumentów ZS", zs_count)
        
        # Sprawdź zgodność z prognozą
        st.subheader("🔍 Analiza zgodności z prognozą")
        
        forecast_materials = set(st.session_state.forecast_data.index)
        stock_materials = set(st.session_state.stock_data['numer indeksu'].unique())
        
        common = forecast_materials & stock_materials
        only_forecast = forecast_materials - stock_materials
        only_stock = stock_materials - forecast_materials
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("✅ Wspólne materiały", len(common))
        
        with col2:
            if only_forecast:
                st.metric("⚠️ Tylko w prognozie", len(only_forecast))
                with st.expander("Zobacz listę"):
                    st.write(sorted(list(only_forecast)))
            else:
                st.metric("✅ Tylko w prognozie", 0)
        
        with col3:
            if only_stock:
                st.metric("ℹ️ Tylko w stanie", len(only_stock))
                with st.expander("Zobacz listę"):
                    st.write(sorted(list(only_stock)))
            else:
                st.metric("✅ Tylko w stanie", 0)
        
        # Podgląd danych
        st.subheader("👁️ Podgląd danych (pierwsze 20 wierszy)")
        display_cols = ['numer indeksu', 'DocNum', 'Data dostawy', 'Zamówione', 'Potwierdzone', 'w magazynie']
        st.dataframe(
            st.session_state.stock_data[display_cols].head(20),
            use_container_width=True
        )
        
        # Informacja o następnym kroku
        if len(common) > 0:
            st.success(f"🎉 **Gotowe!** Znaleziono {len(common)} wspólnych materiałów. Przejdź do Dashboard lub Analizy Szczegółowej.")
        else:
            st.warning("⚠️ Nie znaleziono wspólnych materiałów między prognozą a stanem magazynowym!")
        
    except Exception as e:
        st.error(f"❌ Błąd podczas przetwarzania pliku: {e}")
        st.exception(e)
        st.session_state.stock_data = None
        st.session_state.stock_filename = None

# Sidebar
if st.session_state.stock_filename:
    st.sidebar.success(f"✅ Stan: **{st.session_state.stock_filename}**")
    if st.session_state.stock_data is not None:
        unique_materials = st.session_state.stock_data['numer indeksu'].nunique()
        st.sidebar.info(f"📦 Materiałów: **{unique_materials}**")
else:
    st.sidebar.warning("⏳ Oczekuję na plik stanu")
