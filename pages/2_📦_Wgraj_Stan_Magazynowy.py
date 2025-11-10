# pages/2_📦_Wgraj_Stan_Magazynowy.py
import streamlit as st
import pandas as pd
from utils import normalize_stock

st.set_page_config(page_title="Wgrywanie Stanu", page_icon="📦", layout="wide")
st.title("Krok 2: Wgraj plik zapasów/stanu (Dostępne ilości)")

if st.session_state.forecast_df is None:
    st.error("Najpierw wgraj prognozę (Krok 1).")
else:
    file = st.file_uploader("Wybierz plik Excel/CSV w formacie *Dostępne ilości dd.mm.rrrr.xlsx* lub równoważny (kolumny m.in. `numer indeksu`, `ItemCode`, `nazwa`, `Data dostawy`, `Zamówione`, `Potwierdzone`, `w magazynie`).", type=["xlsx","csv"])
    if file is not None:
        try:
            if file.name.lower().endswith(".xlsx"):
                xl = pd.ExcelFile(file)
                sheet = xl.sheet_names[0]
                df = xl.parse(sheet)
            else:
                df = pd.read_csv(file, sep=';', encoding='utf-8')
            st.session_state.stock_df = df
            st.session_state.stock_file = file.name
            st.success(f"Plik stanu wczytany: **{file.name}**.")
            st.dataframe(df.head(30))
        except Exception as e:
            st.error(f"Nie udało się wczytać pliku stanu: {e}")

if st.session_state.stock_file:
    st.sidebar.success(f"Aktywny stan: **{st.session_state.stock_file}**")
