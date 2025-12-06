import streamlit as st

st.set_page_config(page_title="Anagrafica Azienda", page_icon="📇", layout="wide")
PRIMARY_BLUE = "#1f77b4"

# ==========================
# STATO INIZIALE
# ==========================
if "anagrafica" not in st.session_state:
    st.session_state.anagrafica = {
        # DATI FISCALI
        "Ragione Sociale": "",
        "Forma Giuridica": "PERSONA GIURIDICA",
        "P.IVA": "",
        "CF": "",
        "Regime Fiscale": "",
        "Riferimento Amministrazione": "",
        "Codice Destinatario": "",
        "PEC": "",
        # SEDE / ATTIVITÀ PRINCIPALE
        "Indirizzo": "",
        "CAP": "",
        "Comune": "",
        "Provincia": "",
        "Nazione": "IT",
        # RAPPRESENTANTE LEGALE (OPZIONALE)
        "RL_Nome": "",
        "RL_Cognome": "",
        "RL_DataNascita": "",
        "RL_Sesso": "",
        "RL_NazioneNascita": "",
        "RL_ComuneNascita": "",
        "RL_ProvinciaNascita": "",
        "RL_CF": "",
        "RL_Email": "",
        "RL_Telefono": "",
    }

ana = st.session_state.anagrafica

# ==========================
# HEADER
# ==========================
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f'<h1 style="color:{PRIMARY_BLUE};margin-bottom:0;">FISCO CHIARO CONSULTING</h1>',
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("**Anagrafica azienda** | Documenti | Dashboard")
with col_user:
    st.markdown("👤 Operatore")

st.markdown("---")
st.title("📋 Anagrafica Azienda")

with st.form("form_anagrafica"):
    # ==========================
    # BLOCCO 1 – DATI FISCALI
    # ==========================
    st.subheader("Dati fiscali")
    col1, col2, col3 = st.columns(3)
    with col1:
        ana["Ragione Sociale"] = st.text_input(
            "Denominazione / Ragione sociale", value=ana["Ragione Sociale"]
        )
        ana["Forma Giuridica"] = st.selectbox(
            "Soggetto",
            ["PERSONA GIURIDICA", "PERSONA FISICA", "ALTRO"],
            index=0 if ana["Forma Giuridica"] == "PERSONA GIURIDICA" else 1,
        )
    with col2:
        ana["P.IVA"] = st.text_input("Partita IVA", value=ana["P.IVA"])
        ana["CF"] = st.text_input("Codice Fiscale", value=ana["CF"])
    with col3:
        ana["Regime Fiscale"] = st.text_input(
            "Regime fiscale (es. RF01, RF19)", value=ana["Regime Fiscale"]
        )
        ana["Riferimento Amministrazione"] = st.text_input(
            "Riferimento Amministrazione", value=ana["Riferimento Amministrazione"]
        )

    col4, col5 = st.columns(2)
    with col4:
        ana["Codice Destinatario"] = st.text_input(
            "Codice SDI / Destinatario", value=ana["Codice Destinatario"]
        )
    with col5:
        ana["PEC"] = st.text_input("PEC", value=ana["PEC"])

    st.markdown("---")

    # ==========================
    # BLOCCO 2 – SEDE / ATTIVITÀ
    # ==========================
    st.subheader("Attività principale / Sede")
    col6, col7 = st.columns(2)
    with col6:
        ana["Indirizzo"] = st.text_input("Indirizzo completo", value=ana["Indirizzo"])
        ana["CAP"] = st.text_input("CAP", value=ana["CAP"])
    with col7:
        ana["Comune"] = st.text_input("Comune", value=ana["Comune"])
        ana["Provincia"] = st.text_input("Provincia (sigla)", value=ana["Provincia"])
    ana["Nazione"] = st.text_input("Nazione", value=ana["Nazione"])

    st.markdown("---")

    # ==========================
    # BLOCCO 3 – RAPPRESENTANTE LEGALE (OPZIONALE)
    # ==========================
    with st.expander("Dati rappresentante legale (opzionale)", expanded=False):
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            ana["RL_Nome"] = st.text_input("Nome", value=ana["RL_Nome"])
            ana["RL_Cognome"] = st.text_input("Cognome", value=ana["RL_Cognome"])
        with col_b:
            ana["RL_DataNascita"] = st.text_input(
                "Data di nascita (gg/mm/aaaa)", value=ana["RL_DataNascita"]
            )
            ana["RL_Sesso"] = st.selectbox(
                "Sesso", ["", "M", "F"], index=["", "M", "F"].index(ana["RL_Sesso"])
            )
        with col_c:
            ana["RL_NazioneNascita"] = st.text_input(
                "Nazione di nascita", value=ana["RL_NazioneNascita"]
            )
            ana["RL_ComuneNascita"] = st.text_input(
                "Comune di nascita", value=ana["RL_ComuneNascita"]
            )
        with col_d:
            ana["RL_ProvinciaNascita"] = st.text_input(
                "Provincia di nascita (sigla)", value=ana["RL_ProvinciaNascita"]
            )
            ana["RL_CF"] = st.text_input("Codice Fiscale RL", value=ana["RL_CF"])

        col_e, col_f = st.columns(2)
        with col_e:
            ana["RL_Email"] = st.text_input("Email RL", value=ana["RL_Email"])
        with col_f:
            ana["RL_Telefono"] = st.text_input("Telefono RL", value=ana["RL_Telefono"])

    # ==========================
    # SALVATAGGIO
    # ==========================
    salvato = st.form_submit_button("💾 Salva Anagrafica", use_container_width=True)

if salvato:
    st.session_state.anagrafica = ana
    st.success("Anagrafica aggiornata correttamente!")
    st.rerun()

# ==========================
# RIEPILOGO COMPATTO
# ==========================
st.markdown("---")
st.subheader("📊 Riepilogo sintetico")
col_r1, col_r2 = st.columns(2)
with col_r1:
    st.write(f"**Ragione Sociale**: {ana['Ragione Sociale']}")
    st.write(f"**P.IVA / CF**: {ana['P.IVA']} / {ana['CF']}")
    st.write(f"**Regime Fiscale**: {ana['Regime Fiscale']}")
with col_r2:
    st.write(f"**Sede**: {ana['Indirizzo']} - {ana['CAP']} {ana['Comune']} ({ana['Provincia']}) {ana['Nazione']}")
    st.write(f"**PEC / SDI**: {ana['PEC']} / {ana['Codice Destinatario']}")

st.caption("Questi dati verranno usati automaticamente per le fatture PDF e XML.")
