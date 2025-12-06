import streamlit as st
import pandas as pd
from datetime import date

# Config pagina
st.set_page_config(
    page_title="Gestionale Fatture - Fisco Chiaro Consulting",
    page_icon="📑",
    layout="wide",
)

PRIMARY_BLUE = "#1f77b4"

# ==========================
# COSTANTI E STATO
# ==========================
COLONNE_DOC = [
    "Tipo",
    "Numero",
    "Data",
    "Controparte",
    "Imponibile",
    "IVA",
    "Importo",
    "TipoXML",
    "Stato",
    "UUID",
    "PDF",
]

CLIENTI_COLONNE = [
    "Denominazione",
    "PIVA",
    "CF",
    "Indirizzo",
    "CAP",
    "Comune",
    "Provincia",
    "CodiceDestinatario",
    "PEC",
    "Tipo",
]

# Inizializzazione documenti
if "documenti_emessi" not in st.session_state:
    st.session_state.documenti_emessi = pd.DataFrame(columns=COLONNE_DOC)
else:
    for col in COLONNE_DOC:
        if col not in st.session_state.documenti_emessi.columns:
            st.session_state.documenti_emessi[col] = (
                0.0 if col in ["Imponibile", "IVA", "Importo"] else ""
            )

# Inizializzazione rubrica clienti
if "clienti" not in st.session_state:
    st.session_state.clienti = pd.DataFrame(columns=CLIENTI_COLONNE)
else:
    for col in CLIENTI_COLONNE:
        if col not in st.session_state.clienti.columns:
            st.session_state.clienti[col] = ""

# ==========================
# HEADER
# ==========================
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>FISCO CHIARO CONSULTING</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("#### Dashboard | Documenti | Clienti")
with col_user:
    st.markdown("Operatore")

st.markdown("---")

# Barra tipo Effatta
col_search, col_stato, col_emesse, col_ricevute, col_agg = st.columns(
    [4, 1, 1, 1, 1]
)

with col_search:
    st.text_input(
        " ",
        placeholder="Id fiscale, denominazione, causale, tag",
        label_visibility="collapsed",
    )

with col_stato:
    st.button("STATO")  # siamo già qui

with col_emesse:
    if st.button("EMESSE"):
        st.switch_page("pages/02_Documenti.py")

with col_ricevute:
    if st.button("RICEVUTE"):
        st.info("Sezione RICEVUTE non ancora implementata.")

with col_agg:
    st.button("AGGIORNA")

# ==========================
# CONTENUTO DASHBOARD
# ==========================
st.subheader("Stato generale")

df = st.session_state.documenti_emessi

if df.empty:
    st.info(
        "Non ci sono ancora documenti emessi. Crea la prima fattura dalla sezione EMESSE."
    )
else:
    df_copy = df.copy()
    df_copy["Data"] = pd.to_datetime(df_copy["Data"], errors="coerce")
    today = date.today()

    totale_anno = df_copy[df_copy["Data"].dt.year == today.year]["Importo"].sum()
    totale_mese = df_copy[
        (df_copy["Data"].dt.year == today.year)
        & (df_copy["Data"].dt.month == today.month)
    ]["Importo"].sum()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Fatturato anno corrente",
            f"€ {totale_anno:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        )
    with col2:
        st.metric(
            "Fatturato mese corrente",
            f"€ {totale_mese:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        )
    with col3:
        st.metric("Numero documenti emessi", int(len(df_copy)))

    st.markdown("### Ultimi documenti emessi")
    df_show = df_copy.sort_values("Data", ascending=False).head(10)
    st.dataframe(
        df_show[
            [
                "Tipo",
                "Numero",
                "Data",
                "Controparte",
                "Imponibile",
                "IVA",
                "Importo",
                "Stato",
            ]
        ],
        use_container_width=True,
    )

st.markdown("---")
st.caption("Dashboard STATO – gestionale fatture Fisco Chiaro Consulting")
