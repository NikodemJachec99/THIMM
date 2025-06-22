# pages/2_📦_Wgraj_Stan_Magazynowy.py

import streamlit as st
import io

st.set_page_config(page_title="Wgrywanie Stanu", page_icon="📦", layout="wide")

st.title("Krok 2: Wgraj Plik ze Stanem Magazynowym")

# Inicjalizacja stanu sesji, jeśli nie istnieje
if 'stock_file_bytes' not in st.session_state:
    st.session_state.stock_file_bytes = None
    st.session_state.stock_filename = None

if st.session_state.get('forecast_data') is None:
    st.error("Brak wgranej prognozy! Proszę najpierw przejść do strony '📈 Wgraj Prognozę'.")
    st.stop()

st.info(f"Wybrana prognoza: **{st.session_state.forecast_filename}**")

stock_file = st.file_uploader(
    "Wybierz plik stanu magazynowego (CSV lub Excel)",
    type=["csv", "xlsx"],
    help="Plik powinien zawierać m.in. wiersz 'W magazynie' oraz dokumenty ZP/OR."
)

if stock_file:
    st.session_state.stock_file_bytes = io.BytesIO(stock_file.getvalue())
    st.session_state.stock_filename = stock_file.name
    st.success(f"Pomyślnie załadowano plik stanu: **{st.session_state.stock_filename}**")

if st.session_state.stock_filename:
    st.sidebar.success(f"Aktywny stan: **{st.session_state.stock_filename}**")
    st.sidebar.info("Przejdź do strony z wynikami, aby zobaczyć analizę.")
else:
    st.sidebar.info("Oczekuję na wgranie pliku stanu magazynowego.")