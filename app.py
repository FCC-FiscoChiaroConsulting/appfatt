import streamlit as st

st.set_page_config(
    page_title="Fisco Chiaro Consulting - Fatturazione elettronica",
    layout="wide",
    page_icon="📄",
)

PRIMARY_BLUE = "#1f77b4"

# HEADER
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>FISCO CHIARO CONSULTING</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("#### Dashboard | Clienti | Documenti")


st.markdown("---")

st.subheader("📊 Dashboard")

st.write(
    """
Benvenuta nell'app di fatturazione **Fisco Chiaro Consulting**.

Da qui puoi:
- vedere e gestire le fatture emesse,
- creare una nuova fattura,
- gestire la rubrica clienti/fornitori (dalla pagina Documenti).
"""
)

col1, col2 = st.columns(2)
with col1:
    if st.button("📄 Vai ai documenti / fatture emesse"):
        st.switch_page("pages/02_Documenti.py")

with col2:
    if st.button("🧾 Crea nuova fattura"):
        st.switch_page("pages/03_Fattura.py")
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestionale Fatture", layout="wide")

# ==============================
# STATO INIZIALE
# ==============================
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

if "anagrafica" not in st.session_state:
    st.session_state.anagrafica = {
        "Ragione Sociale": "",
        "P.IVA": "",
        "CF": "",
        "Indirizzo": "",
        "CAP": "",
        "Comune": "",
        "Provincia": "",
        "PEC": "",
        "Codice Destinatario": ""
    }

# ==============================
# MENU IN ALTO A DESTRA
# ==============================
st.markdown("""
    <style>
        .top-right-menu {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 16px;
        }
        .menu-item {
            cursor: pointer;
            color: #1f77b4;
            font-weight: 600;
        }
        .menu-item:hover {
            text-decoration: underline;
        }
    </style>
    <div class="top-right-menu">
        <span class="menu-item" onclick="window.location.href='?anagrafica'">Operatore ▾</span>
    </div>
""", unsafe_allow_html=True)

# ==============================
# CONTROLLO CLICK MENU
# ==============================
query_params = st.query_params

if "anagrafica" in query_params:
    st.session_state.page = "anagrafica"

# ==============================
# FUNZIONE PAGINA ANAGRAFICA
# ==============================
def pagina_anagrafica():
    st.title("📇 Anagrafica Azienda")

    for campo, valore in st.session_state.anagrafica.items():
        st.session_state.anagrafica[campo] = st.text_input(
            campo,
            value=valore
        )

    if st.button("💾 Salva Anagrafica"):
        st.success("Anagrafica salvata correttamente!")

# ==============================
# ROUTER PAGINE
# ==============================
if st.session_state.page == "anagrafica":
    pagina_anagrafica()
else:
    dashboard()

st.markdown("---")
st.caption(
    "Fisco Chiaro Consulting – Emesse gestite dall'app, PDF generati automaticamente."
)
