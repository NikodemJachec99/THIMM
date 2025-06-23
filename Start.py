# Start.py

import streamlit as st

st.set_page_config(
    page_title="Kalkulator Zapotrzebowania",
    page_icon="⚙️",
    layout="wide"
)

# Inicjalizacja stanu sesji
if 'forecast_data' not in st.session_state:
    st.session_state.forecast_data = None
    st.session_state.forecast_filename = None
if 'stock_file_bytes' not in st.session_state:
    st.session_state.stock_file_bytes = None
    st.session_state.stock_filename = None

st.title("Witaj w Kalkulatorze Zapotrzebowania Produkcyjnego!")
st.subheader("I JAK TA PODOBA SIĘ??????🤗🤗🤗")

st.markdown("""
### Jak korzystać z aplikacji?

Aplikacja została podzielona na 3 logiczne kroki, reprezentowane przez osobne strony w menu po lewej stronie.

1.  **📈 Wgraj Prognozę**
    - Na tej stronie należy wgrać plik `.csv` lub `.xlsx` z prognozą sprzedaży od klienta.
    - Po poprawnym załadowaniu pliku, jego nazwa pojawi się w panelu bocznym.

2.  **📦 Wgraj Stan Magazynowy**
    - Po wgraniu prognozy, przejdź na tę stronę, aby wgrać plik `.csv` lub `.xlsx` ze stanem magazynowym dla konkretnego indeksu.
    - Aplikacja pokaże, która prognoza jest aktualnie aktywna.

3.  **📊 Wyniki i Optymalizacja**
    - To jest główna strona z raportami. Pojawią się na niej wyniki tylko wtedy, gdy oba pliki (prognoza i stan) zostały poprawnie załadowane.
    - Znajdziesz tu dwie tabele:
        - **Diagnoza (AS-IS):** Pokazuje problemy w obecnym planie.
        - **Optymalizacja (TO-BE):** Prezentuje rekomendowany, skorygowany plan.

**Aby rozpocząć, przejdź do strony `📈 Wgraj Prognozę` z menu po lewej stronie.**
""")

st.sidebar.success("Wybierz stronę, aby rozpocząć.")
