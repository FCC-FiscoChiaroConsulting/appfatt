import streamlit as st

st.set_page_config(page_title="Anagrafica Azienda", page_icon="📇", layout="wide")
PRIMARY_BLUE = "#1f77b4"

# ==========================
# STATO INIZIALE
# ==========================
if "anagrafica" not in st.session_state:
    st.session_state.anagrafica = {
        # DATI FISCALI BASE
        "Ragione Sociale": "",
        "Forma Giuridica": "PERSONA GIURIDICA",
        "P.IVA": "",
        "CF": "",
        "Indirizzo": "",
        "CAP": "",
        "Comune": "",
        "Provincia": "",
        "PEC": "",
        "Codice Destinatario": "",
    }

ana = st.session_state.anagrafica

# ==========================
# HEADER
# ==========================
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>Anagrafica Azienda</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("Dati fiscali | Documenti | Dashboard")
with col_user:
    st.markdown("👤 Operatore")

st.markdown("---")
st.subheader("Dati fiscali")

# ==========================
# FORM ANAGRAFICA
# ==========================
with st.form("form_anagrafica"):
    col1, col2 = st.columns(2)
    with col1:
        ana["Ragione Sociale"] = st.text_input(
            "Denominazione / Ragione sociale", value=ana["Ragione Sociale"]
        )
        ana["P.IVA"] = st.text_input("P.IVA", value=ana["P.IVA"])
        ana["CF"] = st.text_input("Codice Fiscale", value=ana["CF"])
    with col2:
        ana["Forma Giuridica"] = st.selectbox(
            "Forma Giuridica",
            ["PERSONA GIURIDICA", "PERSONA FISICA", "ALTRO"],
            index=0 if ana.get("Forma Giuridica", "PERSONA GIURIDICA") == "PERSONA GIURIDICA" else 1,
        )
        ana["PEC"] = st.text_input("PEC", value=ana["PEC"])
        ana["Codice Destinatario"] = st.text_input(
            "Codice Destinatario", value=ana["Codice Destinatario"]
        )

    st.markdown("---")
    st.subheader("Sede / indirizzo")
    col3, col4 = st.columns(2)
    with col3:
        ana["Indirizzo"] = st.text_input("Indirizzo", value=ana["Indirizzo"])
        ana["CAP"] = st.text_input("CAP", value=ana["CAP"])
    with col4:
        ana["Comune"] = st.text_input("Comune", value=ana["Comune"])
        ana["Provincia"] = st.text_input("Provincia (sigla)", value=ana["Provincia"])

    salvato = st.form_submit_button("💾 Salva anagrafica", use_container_width=True)

if salvato:
    st.session_state.anagrafica = ana
    st.success("Anagrafica azienda salvata correttamente.")

st.markdown("---")
st.subheader("Riepilogo")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.write(f"**Ragione Sociale**: {ana['Ragione Sociale']}")
    st.write(f"**Forma Giuridica**: {ana['Forma Giuridica']}")
    st.write(f"**P.IVA / CF**: {ana['P.IVA']} / {ana['CF']}")
with col_r2:
    st.write(
        f"**Sede**: {ana['Indirizzo']} - {ana['CAP']} {ana['Comune']} ({ana['Provincia']})"
    )
    st.write(f"**PEC / SDI**: {ana['PEC']} / {ana['Codice Destinatario']}")

st.caption("I dati vengono riutilizzati automaticamente per la compilazione delle fatture.")
