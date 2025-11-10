# pages/1_📈_Wgraj_Prognozę.py
import streamlit as st
import pandas as pd
from utils import normalize_forecast

st.set_page_config(page_title="Wgrywanie Prognozy", page_icon="📈", layout="wide")
st.title("Krok 1: Wgraj plik z prognozą (Forecast)")

file = st.file_uploader("Wybierz plik `Forecast.xlsx` (arkusz: *Lieferantenforecast*) lub CSV z kolumną `Materialnummer` i tygodniami `KW ..`", type=["xlsx","csv"])

if file is not None:
    try:
        if file.name.lower().endswith(".xlsx"):
            # Spróbuj domyślnego arkusza
            xl = pd.ExcelFile(file)
            sheet = "Lieferantenforecast" if "Lieferantenforecast" in xl.sheet_names else xl.sheet_names[0]
            df = xl.parse(sheet)
        else:
            df = pd.read_csv(file, sep=';', encoding='utf-8')
        forecast_map, week_cols = normalize_forecast(df)
        st.session_state.forecast_df = df
        st.session_state.weeks = week_cols
        st.session_state.forecast_file = file.name
        st.success(f"Prognoza wczytana: **{file.name}**. Zidentyfikowano tygodnie: {', '.join(week_cols)}.")
        st.dataframe(df.head(20))
    except Exception as e:
        st.error(f"Nie udało się wczytać prognozy: {e}")

if st.session_state.forecast_file:
    st.sidebar.success(f"Aktywna prognoza: **{st.session_state.forecast_file}**")
