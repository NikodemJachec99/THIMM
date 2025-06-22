# pages/1_📈_Wgraj_Prognozę.py

import streamlit as st
from utils import process_forecast_file
import pandas as pd

st.set_page_config(page_title="Wgrywanie Prognozy", page_icon="📈", layout="wide")

st.title("Krok 1: Wgraj Plik z Prognozą")

# Inicjalizacja stanu sesji, jeśli nie istnieje
if 'forecast_data' not in st.session_state:
    st.session_state.forecast_data = None
    st.session_state.forecast_filename = None

forecast_file = st.file_uploader(
    "Wybierz plik prognozy (CSV lub Excel)",
    type=["csv", "xlsx"],
    help="Plik powinien zawierać kolumnę 'Materialnummer' oraz kolumny z tygodniowymi prognozami."
)

if forecast_file:
    try:
        with st.spinner("Przetwarzanie pliku prognozy..."):
            st.session_state.forecast_data = process_forecast_file(forecast_file)
            st.session_state.forecast_filename = forecast_file.name
        st.success(f"Pomyślnie załadowano i przetworzono plik: **{st.session_state.forecast_filename}**")
        st.write("Podgląd wczytanych danych (pierwsze 5 wierszy):")
        st.dataframe(st.session_state.forecast_data.head())
    except Exception as e:
        st.error(f"Błąd podczas przetwarzania pliku prognozy: {e}")
        st.session_state.forecast_data = None
        st.session_state.forecast_filename = None

if st.session_state.forecast_filename:
    st.sidebar.success(f"Aktywna prognoza: **{st.session_state.forecast_filename}**")
    st.sidebar.info("Przejdź do następnego kroku, aby wgrać stan magazynowy.")
else:
    st.sidebar.info("Oczekuję na wgranie pliku prognozy.")