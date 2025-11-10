# Start.py
import streamlit as st

st.set_page_config(page_title="Kalkulator Zapotrzebowania (All-SKU)", page_icon="⚙️", layout="wide")

# Init session state
for key, default in {
    "forecast_df": None,
    "forecast_file": None,
    "stock_df": None,
    "stock_file": None,
    "results": None,
    "summary": None,
    "weeks": None,
    "tobe": None
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

st.title("Kalkulator Zapotrzebowania — wersja dostosowana do nowego pliku *Dostępne ilości*")
st.markdown("""
Ta wersja działa **dla wszystkich indeksów jednocześnie**.  
Kroki:
1. **📈 Wgraj Prognozę** (plik Excel `Forecast.xlsx` – arkusz *Lieferantenforecast*).
2. **📦 Wgraj Zapas/Stan** (plik Excel w formacie *Dostępne ilości dd.mm.rrrr.xlsx*).
3. **📊 Wyniki** – zestawienie AS-IS, braki i proponowana produkcja (zaokrąglona do partii).
""")

st.info("Z menu po lewej przejdź do kroku 1.")
st.sidebar.success("Wybierz stronę, aby rozpocząć.")
