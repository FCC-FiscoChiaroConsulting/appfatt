import streamlit as st
import pandas as pd
from datetime import date
import os
import re
from fpdf import FPDF
import base64

# ==========================
# CONFIGURAZIONE PAGINA
# ==========================
st.set_page_config(
    page_title="Fisco Chiaro Consulting - Gestione Fatture",
    layout="wide",
    page_icon="📄",
)

# NASCONDI ELEMENTI STREAMLIT DI DEFAULT
st.markdown("""
    <style>
        header {visibility: hidden;}
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        .stDeployButton {display:none;}
    </style>
""", unsafe_allow_html=True)

PRIMARY_BLUE = "#1f77b4"
PDF_DIR = "fatture_pdf"
os.makedirs(PDF_DIR, exist_ok=True)

# ==========================
# DATI EMITTENTE (AZIENDA)
# ==========================
if "emittente" not in st.session_state:
    st.session_state.emittente = {
        "Denominazione": "FISCO CHIARO CONSULTING",
        "Indirizzo": "Via/Piazza ... n. ...",
        "CAP": "00000",
        "Comune": "CITTÀ",
        "Provincia": "XX",
        "CF": "XXXXXXXXXXXX",
        "PIVA": "XXXXXXXXXXXX",
    }

# ==========================
# STATO DI SESSIONE
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

if "documenti_emessi" not in st.session_state:
    st.session_state.documenti_emessi = pd.DataFrame(columns=COLONNE_DOC)
else:
    for col in COLONNE_DOC:
        if col not in st.session_state.documenti_emessi.columns:
            st.session_state.documenti_emessi[col] = (
                0.0 if col in ["Imponibile", "IVA", "Importo"] else ""
            )

if "clienti" not in st.session_state:
    st.session_state.clienti = pd.DataFrame(columns=CLIENTI_COLONNE)
else:
    for col in CLIENTI_COLONNE:
        if col not in st.session_state.clienti.columns:
            st.session_state.clienti[col] = ""

if "righe_correnti" not in st.session_state:
    st.session_state.righe_correnti = []

if "cliente_corrente_label" not in st.session_state:
    st.session_state.cliente_corrente_label = "NUOVO"

if "pagina_corrente" not in st.session_state:
    st.session_state.pagina_corrente = "📊 Dashboard"

if "fattura_in_modifica" not in st.session_state:
    st.session_state.fattura_in_modifica = None

if "modalita_modifica" not in st.session_state:
    st.session_state.modalita_modifica = False


# ==========================
# FUNZIONI DI SUPPORTO
# ==========================
def _format_val_eur(val: float) -> str:
    return (
        f"{val:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


def mostra_anteprima_pdf(pdf_bytes: bytes, altezza: int = 600) -> None:
    b64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
    pdf_display = f"""
    <iframe src="data:application/pdf;base64,{b64_pdf}" width="100%" height="{altezza}" type="application/pdf"></iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)


def get_next_invoice_number() -> str:
    year = date.today().year
    prefix = f"FT{year}"
    df = st.session_state.documenti_emessi
    seq = 1
    if not df.empty:
        mask = df["Numero"].astype(str).str.startswith(prefix)
        if mask.any():
            existing = df.loc[mask, "Numero"].astype(str)
            max_seq = 0
            for num in existing:
                m = re.search(rf"{prefix}(\d+)$", num)
                if m:
                    s = int(m.group(1))
                    if s > max_seq:
                        max_seq = s
            seq = max_seq + 1
    return f"{prefix}{seq:03d}"


def crea_riepilogo_fatture_emesse(df: pd.DataFrame) -> None:
    if df.empty:
        st.info("Nessuna fattura emessa per creare il riepilogo.")
        return

    df = df.copy()
    df["Data"] = pd.to_datetime(df["Data"], errors="coerce")
    anni = sorted(df["Data"].dt.year.dropna().unique())
    if not anni:
        st.info("Nessuna data valida sulle fatture emesse.")
        return

    anno_default = date.today().year
    if anno_default not in anni:
        anno_default = anni[-1]
    idx_default = list(anni).index(anno_default)

    anno_sel = st.selectbox(
        "Anno", anni, index=idx_default, key="anno_riepilogo_emesse"
    )
    df_anno = df[df["Data"].dt.year == anno_sel]

    mesi_label = [
        "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
        "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre",
    ]

    rows = []
    for m in range(1, 13):
        df_m = df_anno[df_anno["Data"].dt.month == m]
        imp_tot = df_m["Importo"].sum()
        imp_imp = df_m["Imponibile"].sum()
        iva_tot = df_m["IVA"].sum()
        rows.append({
            "Periodo": mesi_label[m - 1],
            "Importo a pagare": _format_val_eur(imp_tot),
            "Imponibile": _format_val_eur(imp_imp),
            "IVA": _format_val_eur(iva_tot),
        })

    trimestri = {
        "1° Trimestre": [1, 2, 3],
        "2° Trimestre": [4, 5, 6],
        "3° Trimestre": [7, 8, 9],
        "4° Trimestre": [10, 11, 12],
    }
    for nome, months in trimestri.items():
        df_q = df_anno[df_anno["Data"].dt.month.isin(months)]
        imp_tot = df_q["Importo"].sum()
        imp_imp = df_q["Imponibile"].sum()
        iva_tot = df_q["IVA"].sum()
        rows.append({
            "Periodo": nome,
            "Importo a pagare": _format_val_eur(imp_tot),
            "Imponibile": _format_val_eur(imp_imp),
            "IVA": _format_val_eur(iva_tot),
        })

    imp_tot = df_anno["Importo"].sum()
    imp_imp = df_anno["Imponibile"].sum()
    iva_tot = df_anno["IVA"].sum()
    rows.append({
        "Periodo": "Annuale",
        "Importo a pagare": _format_val_eur(imp_tot),
        "Imponibile": _format_val_eur(imp_imp),
        "IVA": _format_val_eur(iva_tot),
    })

    df_riep = pd.DataFrame(rows)
    st.markdown("### 📊 Prospetto riepilogativo fatture emesse")
    st.dataframe(df_riep, use_container_width=True, hide_index=True)


# ==========================
# GENERAZIONE PDF FATTURA
# ==========================
def genera_pdf_fattura(
    numero: str,
    data_f: date,
    cliente: dict,
    righe: list,
    imponibile: float,
    iva: float,
    totale: float,
    tipo_xml_codice: str = "TD01",
    modalita_pagamento: str = "",
    note: str = "",
) -> bytes:
    """PDF di cortesia con layout tipo Effatta."""
    EMITTENTE = st.session_state.emittente
    
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    row_height = 6

    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, EMITTENTE["Denominazione"], ln=1)
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, EMITTENTE["Indirizzo"], ln=1)
    pdf.cell(0, 5, f'{EMITTENTE["CAP"]} {EMITTENTE["Comune"]} ({EMITTENTE["Provincia"]}) IT', ln=1)
    pdf.cell(0, 5, f'CODICE FISCALE {EMITTENTE["CF"]}', ln=1)
    pdf.cell(0, 5, f'PARTITA IVA {EMITTENTE["PIVA"]}', ln=1)

    current_y = pdf.get_y()
    pdf.set_xy(120, current_y)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(0, 5, "Spett.le", ln=1)
    pdf.set_x(120)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 5, cliente.get("Denominazione", ""), ln=1)
    pdf.set_font("Helvetica", "", 9)

    indirizzo_cli = cliente.get("Indirizzo", "")
    if indirizzo_cli:
        pdf.set_x(120)
        pdf.cell(0, 5, indirizzo_cli, ln=1)

    pdf.set_x(120)
    pdf.cell(0, 5, f"{cliente.get('CAP','')} {cliente.get('Comune','')} ({cliente.get('Provincia','')}) IT", ln=1)

    if cliente.get("PIVA"):
        pdf.set_x(120)
        pdf.cell(0, 5, f"P.IVA {cliente.get('PIVA','')}", ln=1)
    elif cliente.get("CF"):
        pdf.set_x(120)
        pdf.cell(0, 5, f"CF {cliente.get('CF','')}", ln=1)

    pdf.ln(6)

    left_x = 10
    right_x = 110
    col_width = 90

    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_xy(left_x, pdf.get_y())
    pdf.cell(col_width, row_height, "DATI DOCUMENTO", border=1, ln=0, fill=True)
    pdf.set_xy(right_x, pdf.get_y())
    pdf.cell(col_width, row_height, "DATI TRASMISSIONE", border=1, ln=1, fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)

    def row_left(label: str, value: str):
        pdf.set_x(left_x)
        pdf.cell(col_width * 0.25, row_height, label, border=1)
        pdf.cell(col_width * 0.75, row_height, value, border=1, ln=0)

    def row_right(label: str, value: str, last: bool = True):
        pdf.set_x(right_x)
        pdf.cell(col_width * 0.25, row_height, label, border=1)
