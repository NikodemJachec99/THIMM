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
if 'stock_data' not in st.session_state:
    st.session_state.stock_data = None
    st.session_state.stock_filename = None
if 'selected_material' not in st.session_state:
    st.session_state.selected_material = None

st.title("🎯 Kalkulator Zapotrzebowania Produkcyjnego")
st.subheader("Nowa Wersja - Analiza Wszystkich Indeksów! 🚀")

st.markdown("""
### 🎉 Co nowego w tej wersji?

✨ **Automatyczne przetwarzanie wszystkich indeksów** - nie musisz już wgrywać osobnych plików dla każdego materiału!

### Jak korzystać z aplikacji?

#### Krok 1: 📈 **Wgraj Prognozę**
- Wgraj plik CSV/Excel z prognozą sprzedaży
- Aplikacja automatycznie wykryje wszystkie indeksy materiałowe

#### Krok 2: 📦 **Wgraj Dostępne Ilości** 
- Wgraj nowy plik "Dostępne ilości" zawierający:
  - Stany magazynowe wszystkich indeksów
  - Dokumenty ZP (zamówienia produkcyjne)
  - Dokumenty ZS (zamówienia sprzedaży)
  - Daty dostaw i potwierdzenia

#### Krok 3: 📊 **Dashboard Zbiorczy**
- Zobacz podsumowanie wszystkich indeksów na jednym ekranie
- Szybko zidentyfikuj problemy (braki, nadmiary)
- Filtruj i sortuj według statusu

#### Krok 4: 🔍 **Szczegółowa Analiza**
- Wybierz konkretny indeks do głębszej analizy
- Zobacz szczegółową symulację AS-IS i TO-BE
- Otrzymaj rekomendacje dotyczące produkcji i przesunięć

### 📊 Nowe funkcje:

- 🎯 **Dashboard zbiorczy** - przegląd wszystkich materiałów
- 📈 **Wykresy porównawcze** - wizualizacja zapasów
- ⚠️ **System alertów** - automatyczne wykrywanie problemów
- 📉 **Analiza pokrycia** - ile tygodni zapasów masz w magazynie
- 💰 **KPI i metryki** - kluczowe wskaźniki dla każdego indeksu
- 🎨 **Kolorowe statusy** - łatwa identyfikacja problemów

---

**Aby rozpocząć, przejdź do strony `📈 Wgraj Prognozę` z menu po lewej stronie.**
""")

# Podsumowanie w sidebarze
st.sidebar.title("📋 Status Aplikacji")

if st.session_state.forecast_filename:
    st.sidebar.success(f"✅ Prognoza: **{st.session_state.forecast_filename}**")
    if st.session_state.forecast_data is not None:
        st.sidebar.info(f"📦 Liczba indeksów: **{len(st.session_state.forecast_data)}**")
else:
    st.sidebar.warning("⏳ Brak prognozy")

if st.session_state.stock_filename:
    st.sidebar.success(f"✅ Stan: **{st.session_state.stock_filename}**")
    if st.session_state.stock_data is not None:
        unique_materials = st.session_state.stock_data['numer indeksu'].nunique()
        st.sidebar.info(f"📦 Materiałów w pliku: **{unique_materials}**")
else:
    st.sidebar.warning("⏳ Brak stanu magazynowego")

if st.session_state.forecast_data is not None and st.session_state.stock_data is not None:
    st.sidebar.success("🎉 **Gotowe do analizy!**")
    st.sidebar.info("Przejdź do Dashboard lub Analizy Szczegółowej")
