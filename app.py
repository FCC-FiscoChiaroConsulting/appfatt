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
# FUNZIONE DASHBOARD
# ==============================
def dashboard():
    st.title("Dashboard Documenti")
    st.info("Qui vedrai le fatture, documenti e notifiche.")

# ==============================
# ROUTER PAGINE
# ==============================
if st.session_state.page == "anagrafica":
    pagina_anagrafica()
else:
    dashboard()
