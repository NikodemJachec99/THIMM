# pages/3_📊_Wyniki_i_Optymalizacja.py
import streamlit as st
import pandas as pd
from utils import (
    normalize_forecast, normalize_stock, union_weeks,
    simulate_all, build_summary, compute_batch_sizes, simulate_with_extra, export_report
)

st.set_page_config(page_title="Wyniki i Optymalizacja", page_icon="📊", layout="wide")
st.title("Krok 3: Wyniki — AS-IS i propozycja działań dla wszystkich indeksów")

if st.session_state.forecast_df is None or st.session_state.stock_df is None:
    st.warning("Wgraj najpierw prognozę i stan.")
    st.stop()

# Przygotowanie danych
forecast_map, week_cols = normalize_forecast(st.session_state.forecast_df)
init_stock_map, incoming_map, itemcode_map = normalize_stock(st.session_state.stock_df)

# Horyzont = unia tygodni z prognozy i dostaw
weeks_union = union_weeks(forecast_map, incoming_map)
st.write(f"**Horyzont tygodni:** {', '.join(weeks_union)}")

# Symulacja AS-IS
results = simulate_all(init_stock_map, forecast_map, incoming_map, weeks_union)

# Rozmiary partii/serii
batch_map = compute_batch_sizes(st.session_state.stock_df)

# Tabela podsumowująca
summary = build_summary(results, itemcode_map=itemcode_map, batch_map=batch_map)

st.subheader("Podsumowanie (dla wszystkich indeksów)", divider="green")
st.dataframe(summary, use_container_width=True)

# Symulacja TO-BE: dogenerowanie brakującej ilości w tygodniu pierwszego deficytu
extra_map = {}
for _, row in summary.iterrows():
    req = float(row['ProposedProduction'])
    if req>0:
        kw = row['FirstShortageWeek'] if row['FirstShortageWeek'] else (weeks_union[0] if weeks_union else None)
        if kw:
            extra_map[row['Materialnummer']] = (kw, req)
tobe = simulate_with_extra(results, weeks_union, extra_map)

# Eksport raportu (Summary + karty indeksów z AS-IS i TO-BE)
if st.button("📥 Pobierz raport Excel (Summary + szczegóły AS-IS/TO-BE)"):
    path = export_report(summary, results, tobe, "Raport_THIMM_All_SKU.xlsx")
    with open(path, "rb") as f:
        st.download_button("Pobierz Raport", f, file_name="Raport_THIMM_All_SKU.xlsx")

# Wskazówki
with st.expander("Założenia i mapowanie kolumn — kliknij, aby rozwinąć"):
    st.markdown("""
    **Prognoza** (`Forecast.xlsx`):
    - Oczekiwane kolumny: `Materialnummer` oraz kolumny tygodniowe w formacie `KW nn/yy`.
    - Jeśli nazwy są inne, aplikacja podejmie próbę automatycznego wykrycia tygodni i kolumny materiału.

    **Zapas/Stan** (`Dostępne ilości`):
    - Kluczowe kolumny: `numer indeksu` → *Materialnummer*, `ItemCode`, `nazwa` (ZP/ZS/OR), `Data dostawy`, `Zamówione`, `Potwierdzone`, `w magazynie`.
    - Dostawy liczymy tak:
        - `ZP` → kolumna **Zamówione**,
        - `ZS/OR` → kolumna **Potwierdzone**,
        - jeśli typ jest inny → **Potwierdzone** (jeśli >0) w przeciwnym razie **Zamówione**.
    - Startowy stan magazynu bierzemy jako maksymalny `w magazynie` dla danego indeksu (przyjmujemy, że wartości są stałe w obrębie indeksu).

    **Symulacja**:
    - AS-IS: `stock[t] = stock[t-1] + incoming[t] - forecast[t]`.
    - Deficyt = minimum stanu w horyzoncie poniżej zera; **RequiredReplenishment** = `max(0, -min_stock)`.
    - Proponowana produkcja (**ProposedProduction**) — zaokrąglona do partii (jeśli da się ją wyestymować z wielkości ZP), wstrzyknięta w tygodniu pierwszego deficytu.
    """)
