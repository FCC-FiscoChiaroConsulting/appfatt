import streamlit as st
import pandas as pd

st.set_page_config(page_title="Anagrafica Azienda", page_icon="📇", layout="wide")
PRIMARY_BLUE = "#1f77b4"

if "anagrafica" not in st.session_state:
    st.session_state.anagrafica = {
        "Ragione Sociale": "", "P.IVA": "", "CF": "", "Indirizzo": "",
        "CAP": "", "Comune": "", "Provincia": "", "PEC": "", "Codice Destinatario": ""
    }

col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(f'<h1 style="color:{PRIMARY_BLUE};margin-bottom:0;">FISCO CHIARO CONSULTING</h1>', unsafe_allow_html=True)
with col_menu:
    st.markdown("Anagrafica azienda | Documenti | Dashboard")
with col_user:
    st.button("Operatore")

st.markdown("---")
st.title("Anagrafica Azienda")
st.markdown("Compila i dati della tua azienda. Verranno riutilizzati per le fatture.")

with st.form("form_anagrafica"):
    for campo, valore in st.session_state.anagrafica.items():
        st.session_state.anagrafica[campo] = st.text_input(campo, value=valore)
    salvato = st.form_submit_button("Salva Anagrafica")

if salvato:
    st.success("Anagrafica salvata correttamente in memoria dell'app.")

st.markdown("---")
st.subheader("Riepilogo anagrafica")
ana = st.session_state.anagrafica
col1, col2 = st.columns(2)
with col1:
    st.write(f"**Ragione Sociale**: {ana['Ragione Sociale']}")
    st.write(f"**P.IVA**: {ana['P.IVA']}")
    st.write(f"**CF**: {ana['CF']}")
    st.write(f"**PEC**: {ana['PEC']}")
with col2:
    st.write(f"**Indirizzo**: {ana['Indirizzo']}")
    st.write(f"**CAP**: {ana['CAP']}")
    st.write(f"**Comune**: {ana['Comune']} ({ana['Provincia']})")
    st.write(f"**Codice Destinatario**: {ana['Codice Destinatario']}")

st.caption("I dati rimangono caricati finché la sessione Streamlit è attiva.")
