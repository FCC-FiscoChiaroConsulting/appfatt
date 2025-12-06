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
    # FORMATO EUROPEO: DD/MM/YYYY
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y", errors="coerce")
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
        pdf.cell(col_width * 0.35, row_height, label, border=1)
        pdf.cell(col_width * 0.65, row_height, value, border=1, ln=1 if last else 0)

    tipo_map = {
        "TD01": "TD01 FATTURA - B2B",
        "TD02": "TD02 ACCONTO/ANTICIPO SU FATTURA",
        "TD04": "TD04 NOTA DI CREDITO",
        "TD05": "TD05 NOTA DI DEBITO",
    }
    tipo_label = tipo_map.get(tipo_xml_codice, tipo_xml_codice)

    row_left("TIPO", tipo_label)
    row_right("CODICE DESTINATARIO", cliente.get("CodiceDestinatario", "0000000"))
    row_left("NUMERO", str(numero))
    row_right("PEC DESTINATARIO", cliente.get("PEC", ""))
    row_left("DATA", data_f.strftime("%d/%m/%Y"))
    row_right("DATA INVIO", "")
    causale = note.strip() if note else "SERVIZIO"
    row_left("CAUSALE", causale)
    row_right("IDENTIFICATIVO SDI", "")
    pdf.ln(2)

    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(10)
    pdf.cell(190 - 20, row_height, "DETTAGLIO DOCUMENTO", border=1, ln=1, fill=True)

    pdf.set_font("Helvetica", "B", 8)
    headers = ["#", "DESCRIZIONE", "U.M.", "PREZZO", "QTA", "TOTALE", "IVA %", "RIT.", "NAT."]
    widths = [8, 78, 10, 28, 12, 28, 12, 10, 14]

    pdf.set_x(10)
    for h, w in zip(headers, widths):
        pdf.cell(w, row_height, h, border=1, align="C")
    pdf.ln(row_height)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "", 8)

    righe_locali = righe if righe else [{"desc": "", "qta": 0, "prezzo": 0.0, "iva": 22}]

    for idx, r in enumerate(righe_locali, start=1):
        desc = (r.get("desc") or "").replace("\n", " ").strip()
        if len(desc) > 70:
            desc = desc[:67] + "..."
        qta = float(r.get("qta", 0) or 0)
        prezzo = float(r.get("prezzo", 0.0) or 0.0)
        iva_r = float(r.get("iva", 22) or 0.0)
        totale_riga = qta * prezzo

        pdf.set_x(10)
        pdf.cell(widths[0], row_height, str(idx), border=1, align="C")
        pdf.cell(widths[1], row_height, desc, border=1)
        pdf.cell(widths[2], row_height, "", border=1, align="C")
        pdf.cell(widths[3], row_height, _format_val_eur(prezzo), border=1, align="R")
        pdf.cell(widths[4], row_height, f"{qta:.2f}", border=1, align="R")
        pdf.cell(widths[5], row_height, _format_val_eur(totale_riga), border=1, align="R")
        pdf.cell(widths[6], row_height, f"{iva_r:.2f}", border=1, align="R")
        pdf.cell(widths[7], row_height, "", border=1, align="C")
        pdf.cell(widths[8], row_height, "", border=1, align="C")
        pdf.ln(row_height)

    pdf.ln(2)
    pdf.set_x(10)
    pdf.set_font("Helvetica", "", 8)
    pdf.cell(40, row_height, "IMPORTO", border=1)
    pdf.cell(50, row_height, _format_val_eur(imponibile), border=1, ln=1, align="R")
    pdf.set_x(10)
    pdf.cell(40, row_height, "TOTALE IMPONIBILE", border=1)
    pdf.cell(50, row_height, _format_val_eur(imponibile), border=1, ln=1, align="R")
    pdf.set_x(10)
    pdf.cell(40, row_height, "IVA (SU IMPONIBILE)", border=1)
    pdf.cell(50, row_height, _format_val_eur(iva), border=1, ln=1, align="R")
    pdf.set_x(10)
    pdf.cell(40, row_height, "IMPORTO TOTALE", border=1)
    pdf.cell(50, row_height, _format_val_eur(totale), border=1, ln=1, align="R")
    pdf.set_x(10)
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(40, row_height, "NETTO A PAGARE", border=1)
    pdf.cell(50, row_height, _format_val_eur(totale), border=1, ln=1, align="R")

    pdf.ln(3)
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(10)
    pdf.cell(190 - 20, row_height, "RIEPILOGHI", border=1, ln=1, fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 8)

    riepi_headers = ["IVA %", "NAT.", "RIFERIMENTO NORMATIVO", "IMPONIBILE", "IMPOSTA", "ESIG. IVA", "ARROT.", "SPESE ACC.", "TOTALE"]
    riepi_w = [14, 14, 40, 24, 20, 20, 14, 24, 24]

    pdf.set_x(10)
    for h, w in zip(riepi_headers, riepi_w):
        pdf.cell(w, row_height, h, border=1, align="C")
    pdf.ln(row_height)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_x(10)
    pdf.cell(riepi_w[0], row_height, "22,00", border=1, align="R")
    pdf.cell(riepi_w[1], row_height, "", border=1)
    pdf.cell(riepi_w[2], row_height, "", border=1)
    pdf.cell(riepi_w[3], row_height, _format_val_eur(imponibile), border=1, align="R")
    pdf.cell(riepi_w[4], row_height, _format_val_eur(iva), border=1, align="R")
    pdf.cell(riepi_w[5], row_height, "IMMEDIATA", border=1, align="C")
    pdf.cell(riepi_w[6], row_height, "0,00", border=1, align="R")
    pdf.cell(riepi_w[7], row_height, "0,00", border=1, align="R")
    pdf.cell(riepi_w[8], row_height, _format_val_eur(totale), border=1, align="R")
    pdf.ln(4)

    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(10)
    pdf.cell(190 - 20, row_height, "MODALITA' DI PAGAMENTO ACCETTATE: PAGAMENTO COMPLETO", border=1, ln=1, fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_x(10)

    pag_headers = ["MODALITA'", "DETTAGLI", "DATA RIF. TERMINI", "GIORNI TERMINI", "DATA SCADENZA"]
    pag_w = [30, 60, 30, 30, 40]

    for h, w in zip(pag_headers, pag_w):
        pdf.cell(w, row_height, h, border=1, align="C")
    pdf.ln(row_height)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_x(10)
    pdf.cell(pag_w[0], row_height, "CONTANTI", border=1)
    pdf.cell(pag_w[1], row_height, modalita_pagamento[:40], border=1)
    pdf.cell(pag_w[2], row_height, "", border=1)
    pdf.cell(pag_w[3], row_height, "0", border=1, align="C")
    pdf.cell(pag_w[4], row_height, "", border=1, align="C")
    pdf.ln(row_height + 2)

    pdf.set_font("Helvetica", "B", 9)
    pdf.set_x(10)
    pdf.cell(190 - 20, row_height, f"TOTALE A PAGARE EUR {_format_val_eur(totale)}", ln=1)

    pdf.set_y(-25)
    pdf.set_font("Helvetica", "I", 7)
    pdf.multi_cell(
        0, 4,
        ("Copia di cortesia priva di valore ai fini fiscali e giuridici ai sensi dell'articolo 21 del D.P.R. 633/72. "
         "L'originale del documento è consultabile presso l'indirizzo PEC o il codice SDI registrato "
         "o nell'area riservata Fatture e Corrispettivi."),
        align="C",
    )

    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return out.encode("latin1")


# ==========================
# MENÙ / NAVIGAZIONE
# ==========================
PAGINE = [
    "📊 Dashboard",
    "📝 Anagrafica azienda",
    "📋 Lista documenti",
    "➕ Crea nuova fattura",
    "📥 Download documenti",
    "📦 Carica pacchetto AdE",
    "👥 Rubrica clienti",
]

pagina_default = st.session_state.pagina_corrente
if pagina_default not in PAGINE:
    pagina_default = "📊 Dashboard"
default_index = PAGINE.index(pagina_default)

# ==========================
# SIDEBAR - PANNELLO DI CONTROLLO
# ==========================
with st.sidebar:
    st.markdown("## 🎛️ Pannello di controllo")
    st.markdown("**Fisco Chiaro Consulting**")
    st.markdown("---")
    
    pagina = st.radio(
        "Navigazione",
        PAGINE,
        index=default_index,
        label_visibility="collapsed",
    )
    st.session_state.pagina_corrente = pagina
    
    st.markdown("---")
    st.caption("Versione 1.0 | © 2025")

# ==========================
# HEADER PRINCIPALE
# ==========================
st.markdown(f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0;'>FISCO CHIARO CONSULTING</h1>", unsafe_allow_html=True)
st.markdown("**Gestione Fatture Elettroniche**")
st.markdown("---")

# ==========================
# CONTATORI DOCUMENTI PER MESE
# ==========================
docs_per_month = {m: 0 for m in range(1, 13)}
df_tmp = st.session_state.documenti_emessi.copy()
if not df_tmp.empty:
    # FORMATO EUROPEO
    df_tmp["Data"] = pd.to_datetime(df_tmp["Data"], format="%d/%m/%Y", errors="coerce")
    for m in range(1, 13):
        docs_per_month[m] = (df_tmp["Data"].dt.month == m).sum()

# ==========================
# GESTIONE PAGINE
# ==========================

if pagina == "📝 Anagrafica azienda":
    st.subheader("📝 Anagrafica azienda")
    
    st.info("Modifica qui i dati della tua azienda che verranno utilizzati nelle fatture")
    
    with st.form("form_anagrafica"):
        st.markdown("### Dati identificativi")
        
        col1, col2 = st.columns(2)
        with col1:
            denominazione = st.text_input(
                "Denominazione / Ragione Sociale",
                value=st.session_state.emittente["Denominazione"]
            )
        with col2:
            piva = st.text_input(
                "Partita IVA",
                value=st.session_state.emittente["PIVA"]
            )
        
        cf = st.text_input(
            "Codice Fiscale",
            value=st.session_state.emittente["CF"]
        )
        
        st.markdown("### Sede legale")
        
        indirizzo = st.text_input(
            "Indirizzo (Via/Piazza, numero civico)",
            value=st.session_state.emittente["Indirizzo"]
        )
        
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            cap = st.text_input("CAP", value=st.session_state.emittente["CAP"])
        with col_c2:
            comune = st.text_input("Comune", value=st.session_state.emittente["Comune"])
        with col_c3:
            provincia = st.text_input("Provincia (es. BA)", value=st.session_state.emittente["Provincia"])
        
        if st.form_submit_button("💾 Salva anagrafica", use_container_width=True, type="primary"):
            st.session_state.emittente = {
                "Denominazione": denominazione,
                "Indirizzo": indirizzo,
                "CAP": cap,
                "Comune": comune,
                "Provincia": provincia,
                "CF": cf,
                "PIVA": piva,
            }
            st.success("✅ Anagrafica azienda aggiornata con successo!")
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 📄 Anteprima dati correnti")
    
    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("**Denominazione:**")
        st.text(st.session_state.emittente["Denominazione"])
        st.markdown("**Partita IVA:**")
        st.text(st.session_state.emittente["PIVA"])
        st.markdown("**Codice Fiscale:**")
        st.text(st.session_state.emittente["CF"])
    
    with col_b:
        st.markdown("**Indirizzo:**")
        st.text(st.session_state.emittente["Indirizzo"])
        st.markdown("**Comune:**")
        st.text(f"{st.session_state.emittente['CAP']} {st.session_state.emittente['Comune']} ({st.session_state.emittente['Provincia']})")

elif pagina == "📋 Lista documenti":
    st.subheader("📋 Lista documenti")

    col_search, col_stato, col_emesse, col_ricevute, col_agg = st.columns([4, 1, 1, 1, 1])
    with col_search:
        barra_ricerca = st.text_input("", placeholder="🔍 Cerca per nome, P.IVA, numero fattura...", label_visibility="collapsed")
    with col_stato:
        if st.button("📊 STATO"):
            st.session_state.pagina_corrente = "📊 Dashboard"
            st.rerun()
    with col_emesse:
        if st.button("📤 EMESSE"):
            st.session_state.pagina_corrente = "📋 Lista documenti"
            st.rerun()
    with col_ricevute:
        if st.button("📥 RICEVUTE"):
            st.session_state.pagina_corrente = "📥 Download documenti"
            st.rerun()
    with col_agg:
        if st.button("🔄 AGGIORNA"):
            st.rerun()

    nomi_mesi = ["Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
                 "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"]

    mesi = ["📊 Riepilogo"]
    for m, nome in enumerate(nomi_mesi, start=1):
        n_doc = docs_per_month.get(m, 0)
        if n_doc > 0:
            mesi.append(f"📅 {nome} ({n_doc})")
        else:
            mesi.append(f"📅 {nome}")

    tabs = st.tabs(mesi)

    for i, tab in enumerate(tabs):
        with tab:
            if i == 0:
                crea_riepilogo_fatture_emesse(st.session_state.documenti_emessi)
                
                st.markdown("---")
                st.markdown("### 📋 Tutte le fatture emesse")
                
                df_tutte = st.session_state.documenti_emessi.copy()
                
                if df_tutte.empty:
                    st.info("Nessun documento emesso.")
                else:
                    # FORMATO EUROPEO
                    df_tutte["DataSort"] = pd.to_datetime(df_tutte["Data"], format="%d/%m/%Y", errors="coerce")
                    df_tutte = df_tutte.sort_values("DataSort", ascending=False)
                    
                    for row_index, row in df_tutte.iterrows():
                        numero = row.get("Numero", "")
                        data_doc = row.get("Data", "")
                        controparte = row.get("Controparte", "")
                        importo = float(row.get("Importo", 0) or 0)
                        tipo_xml = row.get("TipoXML", "TD01")
                        stato_doc = row.get("Stato", "Creazione")
                        pdf_path = row.get("PDF", "")

                        tipo_map = {
                            "TD01": "TD01 - Fattura",
                            "TD02": "TD02 - Acconto/Anticipo",
                            "TD04": "TD04 - Nota di credito",
                            "TD05": "TD05 - Nota di debito",
                        }
                        tipo_label = tipo_map.get(tipo_xml, tipo_xml)

                        piva_cf = ""
                        cli_df = st.session_state.clienti[st.session_state.clienti["Denominazione"] == controparte]
                        if not cli_df.empty:
                            cli_row = cli_df.iloc[0]
                            piva_val = (cli_row.get("PIVA") or "").strip()
                            cf_val = (cli_row.get("CF") or "").strip()
                            if piva_val:
                                piva_cf = piva_val
                            elif cf_val:
                                piva_cf = cf_val

                        with st.container(border=True):
                            col_icon, col_info, col_imp, col_stato, col_menu = st.columns([0.6, 4, 1.6, 1.4, 1.8])

                            with col_icon:
                                if tipo_xml == "TD01" and piva_cf:
                                    st.markdown("🟥 **B2B**")
                                else:
                                    st.markdown("📄")

                            with col_info:
                                info_lines = []
                                info_lines.append(f"**{tipo_label}**")
                                info_lines.append(f"{numero} del {data_doc}")
                                info_lines.append("")
                                info_lines.append("INVIATO A")
                                info_lines.append(controparte)
                                if piva_cf:
                                    info_lines.append(f"P.IVA/C.F. {piva_cf}")
                                info_lines.append("CAUSALE")
                                info_lines.append("SERVIZIO")
                                st.markdown("  \n".join(info_lines))

                            with col_imp:
                                st.markdown("**IMPORTO (EUR)**")
                                st.markdown(_format_val_eur(importo))
                                st.markdown("**ESIGIBILITÀ IVA**")
                                st.markdown("IMMEDIATA")

                            with col_stato:
                                st.markdown("**Stato**")
                                possibili_stati = ["Creazione", "Creato", "Inviato"]
                                if stato_doc not in possibili_stati:
                                    stato_doc = "Creazione"
                                new_stato = st.selectbox(
                                    "",
                                    possibili_stati,
                                    index=possibili_stati.index(stato_doc),
                                    key=f"stato_riep_{row_index}",
                                    label_visibility="collapsed",
                                )
                                st.session_state.documenti_emessi.loc[row_index, "Stato"] = new_stato

                            with col_menu:
                                st.markdown("**Azioni**")

                                with st.popover("⚙️ Azioni", use_container_width=True):
                                    st.markdown("**Seleziona azione**")

                                    pdf_bytes = None
                                    if pdf_path and os.path.exists(pdf_path):
                                        with open(pdf_path, "rb") as f:
                                            pdf_bytes = f.read()

                                    if st.button("👁 Visualizza", key=f"vis_riep_{row_index}", use_container_width=True):
                                        if pdf_bytes:
                                            st.markdown("Anteprima PDF:")
                                            mostra_anteprima_pdf(pdf_bytes, altezza=400)
                                        else:
                                            st.warning("PDF non disponibile")

                                    if pdf_bytes:
                                        st.download_button(
                                            "📄 Scarica PDF fattura",
                                            data=pdf_bytes,
                                            file_name=os.path.basename(pdf_path),
                                            mime="application/pdf",
                                            key=f"dl_riep_{row_index}",
                                            use_container_width=True,
                                        )
                                    else:
                                        st.info("PDF non disponibile")

                                    if st.button("📦 Scarica pacchetto", key=f"pac_riep_{row_index}", use_container_width=True):
                                        st.info("Funzione in sviluppo")

                                    if st.button("📑 Scarica PDF proforma", key=f"prof_riep_{row_index}", use_container_width=True):
                                        st.info("Funzione in sviluppo")

                                    if st.button("✏️ Modifica", key=f"mod_riep_{row_index}", use_container_width=True):
                                        st.session_state.fattura_in_modifica = row_index
                                        st.session_state.modalita_modifica = True
                                        st.session_state.pagina_corrente = "➕ Crea nuova fattura"
                                        st.rerun()

                                    if st.button("🧬 Duplica", key=f"dup_riep_{row_index}", use_container_width=True):
                                        nuovo_num = get_next_invoice_number()
                                        nuova_riga = row.copy()
                                        nuova_riga["Numero"] = nuovo_num
                                        # FORMATO EUROPEO
                                        nuova_riga["Data"] = date.today().strftime("%d/%m/%Y")
                                        st.session_state.documenti_emessi = pd.concat(
                                            [st.session_state.documenti_emessi, pd.DataFrame([nuova_riga])],
                                            ignore_index=True,
                                        )
                                        st.success(f"Fattura duplicata come {nuovo_num}.")
                                        st.rerun()

                                    if st.button("🗑 Elimina", key=f"del_riep_{row_index}", use_container_width=True, type="secondary"):
                                        st.session_state.documenti_emessi = (
                                            st.session_state.documenti_emessi.drop(row_index).reset_index(drop=True)
                                        )
                                        st.warning("Fattura eliminata.")
                                        st.rerun()

                                    if st.button("📨 Invia", key=f"inv_riep_{row_index}", use_container_width=True):
                                        st.info("Funzione in sviluppo")
            
            else:
                mese_idx = i
                df_mese = st.session_state.documenti_emessi.copy()
                if not df_mese.empty:
                    # FORMATO EUROPEO
                    df_mese["DataSort"] = pd.to_datetime(df_mese["Data"], format="%d/%m/%Y", errors="coerce")
                    df_mese = df_mese[df_mese["DataSort"].dt.month == mese_idx]

                if df_mese.empty:
                    st.info("Nessun documento in questo periodo.")
                    continue

                st.caption("Elenco fatture emesse")
                df_mese = df_mese.sort_values("DataSort", ascending=False)
                
                for row_index, row in df_mese.iterrows():
                    numero = row.get("Numero", "")
                    data_doc = row.get("Data", "")
                    controparte = row.get("Controparte", "")
                    importo = float(row.get("Importo", 0) or 0)
                    tipo_xml = row.get("TipoXML", "TD01")
                    stato_doc = row.get("Stato", "Creazione")
                    pdf_path = row.get("PDF", "")

                    tipo_map = {
                        "TD01": "TD01 - Fattura",
                        "TD02": "TD02 - Acconto/Anticipo",
                        "TD04": "TD04 - Nota di credito",
                        "TD05": "TD05 - Nota di debito",
                    }
                    tipo_label = tipo_map.get(tipo_xml, tipo_xml)

                    piva_cf = ""
                    cli_df = st.session_state.clienti[st.session_state.clienti["Denominazione"] == controparte]
                    if not cli_df.empty:
                        cli_row = cli_df.iloc[0]
                        piva_val = (cli_row.get("PIVA") or "").strip()
                        cf_val = (cli_row.get("CF") or "").strip()
                        if piva_val:
                            piva_cf = piva_val
                        elif cf_val:
                            piva_cf = cf_val

                    with st.container(border=True):
                        col_icon, col_info, col_imp, col_stato, col_menu = st.columns([0.6, 4, 1.6, 1.4, 1.8])

                        with col_icon:
                            if tipo_xml == "TD01" and piva_cf:
                                st.markdown("🟥 **B2B**")
                            else:
                                st.markdown("📄")

                        with col_info:
                            info_lines = []
                            info_lines.append(f"**{tipo_label}**")
                            info_lines.append(f"{numero} del {data_doc}")
                            info_lines.append("")
                            info_lines.append("INVIATO A")
                            info_lines.append(controparte)
                            if piva_cf:
                                info_lines.append(f"P.IVA/C.F. {piva_cf}")
                            info_lines.append("CAUSALE")
                            info_lines.append("SERVIZIO")
                            st.markdown("  \n".join(info_lines))

                        with col_imp:
                            st.markdown("**IMPORTO (EUR)**")
                            st.markdown(_format_val_eur(importo))
                            st.markdown("**ESIGIBILITÀ IVA**")
                            st.markdown("IMMEDIATA")

                        with col_stato:
                            st.markdown("**Stato**")
                            possibili_stati = ["Creazione", "Creato", "Inviato"]
                            if stato_doc not in possibili_stati:
                                stato_doc = "Creazione"
                            new_stato = st.selectbox(
                                "",
                                possibili_stati,
                                index=possibili_stati.index(stato_doc),
                                key=f"stato_{row_index}",
                                label_visibility="collapsed",
                            )
                            st.session_state.documenti_emessi.loc[row_index, "Stato"] = new_stato

                        with col_menu:
                            st.markdown("**Azioni**")

                            with st.popover("⚙️ Azioni", use_container_width=True):
                                st.markdown("**Seleziona azione**")

                                pdf_bytes = None
                                if pdf_path and os.path.exists(pdf_path):
                                    with open(pdf_path, "rb") as f:
                                        pdf_bytes = f.read()

                                if st.button("👁 Visualizza", key=f"vis_{row_index}", use_container_width=True):
                                    if pdf_bytes:
                                        st.markdown("Anteprima PDF:")
                                        mostra_anteprima_pdf(pdf_bytes, altezza=400)
                                    else:
                                        st.warning("PDF non disponibile")

                                if pdf_bytes:
                                    st.download_button(
                                        "📄 Scarica PDF fattura",
                                        data=pdf_bytes,
                                        file_name=os.path.basename(pdf_path),
                                        mime="application/pdf",
                                        key=f"dl_{row_index}",
                                        use_container_width=True,
                                    )
                                else:
                                    st.info("PDF non disponibile")

                                if st.button("📦 Scarica pacchetto", key=f"pac_{row_index}", use_container_width=True):
                                    st.info("Funzione in sviluppo")

                                if st.button("📑 Scarica PDF proforma", key=f"prof_{row_index}", use_container_width=True):
                                    st.info("Funzione in sviluppo")

                                if st.button("✏️ Modifica", key=f"mod_{row_index}", use_container_width=True):
                                    st.session_state.fattura_in_modifica = row_index
                                    st.session_state.modalita_modifica = True
                                    st.session_state.pagina_corrente = "➕ Crea nuova fattura"
                                    st.rerun()

                                if st.button("🧬 Duplica", key=f"dup_{row_index}", use_container_width=True):
                                    nuovo_num = get_next_invoice_number()
                                    nuova_riga = row.copy()
                                    nuova_riga["Numero"] = nuovo_num
                                    # FORMATO EUROPEO
                                    nuova_riga["Data"] = date.today().strftime("%d/%m/%Y")
                                    st.session_state.documenti_emessi = pd.concat(
                                        [st.session_state.documenti_emessi, pd.DataFrame([nuova_riga])],
                                        ignore_index=True,
                                    )
                                    st.success(f"Fattura duplicata come {nuovo_num}.")
                                    st.rerun()

                                if st.button("🗑 Elimina", key=f"del_{row_index}", use_container_width=True, type="secondary"):
                                    st.session_state.documenti_emessi = (
                                        st.session_state.documenti_emessi.drop(row_index).reset_index(drop=True)
                                    )
                                    st.warning("Fattura eliminata.")
                                    st.rerun()

                                if st.button("📨 Invia", key=f"inv_{row_index}", use_container_width=True):
                                    st.info("Funzione in sviluppo")

elif pagina == "➕ Crea nuova fattura":
    if st.session_state.modalita_modifica and st.session_state.fattura_in_modifica is not None:
        st.subheader("✏️ Modifica fattura esistente")
        
        fattura_da_modificare = st.session_state.documenti_emessi.loc[st.session_state.fattura_in_modifica]
        
        if not st.session_state.righe_correnti:
            st.session_state.righe_correnti = [{"desc": "SERVIZIO", "qta": 1.0, "prezzo": float(fattura_da_modificare["Imponibile"]), "iva": 22}]
        
        numero_originale = fattura_da_modificare["Numero"]
        # FORMATO EUROPEO
        data_originale = pd.to_datetime(fattura_da_modificare["Data"], format="%d/%m/%Y").date()
        controparte_originale = fattura_da_modificare["Controparte"]
        tipo_xml_originale = fattura_da_modificare["TipoXML"]
        stato_originale = fattura_da_modificare["Stato"]
    else:
        st.subheader("➕ Crea nuova fattura emessa")
        numero_originale = None

    denominazioni = ["➕ NUOVO CLIENTE"] + st.session_state.clienti["Denominazione"].tolist()

    col1, col2 = st.columns([2, 1])
    with col1:
        if st.session_state.modalita_modifica:
            current_label = controparte_originale
        else:
            current_label = st.session_state.cliente_corrente_label
            
        if current_label not in denominazioni:
            current_label = "➕ NUOVO CLIENTE"
        default_idx = denominazioni.index(current_label)
        cliente_sel = st.selectbox("👤 Seleziona cliente", denominazioni, index=default_idx)
        st.session_state.cliente_corrente_label = cliente_sel

    with col2:
        if st.button("➕ Nuovo cliente"):
            st.session_state.cliente_corrente_label = "➕ NUOVO CLIENTE"
            st.rerun()

    if cliente_sel == "➕ NUOVO CLIENTE":
        st.markdown("### 📝 Dati cliente")
        cli_den = st.text_input("Denominazione cliente")
        cli_piva = st.text_input("P.IVA")
        cli_cf = st.text_input("Codice Fiscale")
        cli_ind = st.text_input("Indirizzo (via/piazza, civico)")
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            cli_cap = st.text_input("CAP")
        with col_c2:
            cli_com = st.text_input("Comune")
        with col_c3:
            cli_prov = st.text_input("Provincia (es. BA)")

        col_x1, col_x2 = st.columns(2)
        with col_x1:
            cli_coddest = st.text_input("Codice Destinatario", value="0000000")
        with col_x2:
            cli_pec = st.text_input("PEC destinatario")

        cliente_corrente = {
            "Denominazione": cli_den,
            "PIVA": cli_piva,
            "CF": cli_cf,
            "Indirizzo": cli_ind,
            "CAP": cli_cap,
            "Comune": cli_com,
            "Provincia": cli_prov,
            "CodiceDestinatario": cli_coddest,
            "PEC": cli_pec,
        }
    else:
        riga_cli = st.session_state.clienti[st.session_state.clienti["Denominazione"] == cliente_sel].iloc[0]

        st.markdown("### 📝 Dati cliente")
        cli_den = st.text_input("Denominazione", riga_cli.get("Denominazione", ""))
        cli_piva = st.text_input("P.IVA", riga_cli.get("PIVA", ""))
        cli_cf = st.text_input("Codice Fiscale", riga_cli.get("CF", ""))
        cli_ind = st.text_input("Indirizzo (via/piazza, civico)", riga_cli.get("Indirizzo", ""))
        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            cli_cap = st.text_input("CAP", riga_cli.get("CAP", ""))
        with col_c2:
            cli_com = st.text_input("Comune", riga_cli.get("Comune", ""))
        with col_c3:
            cli_prov = st.text_input("Provincia (es. BA)", riga_cli.get("Provincia", ""))

        col_x1, col_x2 = st.columns(2)
        with col_x1:
            cli_coddest = st.text_input("Codice Destinatario", riga_cli.get("CodiceDestinatario", "0000000"))
        with col_x2:
            cli_pec = st.text_input("PEC destinatario", riga_cli.get("PEC", ""))

        cliente_corrente = {
            "Denominazione": cli_den,
            "PIVA": cli_piva,
            "CF": cli_cf,
            "Indirizzo": cli_ind,
            "CAP": cli_cap,
            "Comune": cli_com,
            "Provincia": cli_prov,
            "CodiceDestinatario": cli_coddest,
            "PEC": cli_pec,
        }

    st.markdown("---")
    st.markdown("### 📋 Dati documento")

    tipi_xml_label = [
        "TD01 - Fattura",
        "TD02 - Acconto/Anticipo su fattura",
        "TD04 - Nota di credito",
        "TD05 - Nota di debito",
    ]
    
    if st.session_state.modalita_modifica:
        tipo_idx = [t.startswith(tipo_xml_originale) for t in tipi_xml_label].index(True)
    else:
        tipo_idx = 0
        
    tipo_xml_label = st.selectbox("Tipo documento XML", tipi_xml_label, index=tipo_idx)
    tipo_xml_codice = tipo_xml_label.split(" ")[0]

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        if st.session_state.modalita_modifica:
            numero = st.text_input("Numero fattura", numero_originale, disabled=True)
        else:
            numero = st.text_input("Numero fattura", get_next_invoice_number())
    with col_n2:
        if st.session_state.modalita_modifica:
            data_f = st.date_input("Data fattura", data_originale)
        else:
            data_f = st.date_input("Data fattura", date.today())

    modalita_pagamento = st.text_input("Modalità di pagamento", value="")
    note = st.text_area("Note (causale)", value="", height=80)

    st.markdown("---")
    st.markdown("### 📝 Righe fattura")
    
    if st.button("➕ Aggiungi riga"):
        st.session_state.righe_correnti.append({"desc": "", "qta": 1.0, "prezzo": 0.0, "iva": 22})
        st.rerun()

    imponibile = 0.0
    iva_tot = 0.0

    for i, r in enumerate(st.session_state.righe_correnti):
        c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 0.5])
        with c1:
            r["desc"] = st.text_input("Descrizione", r["desc"], key=f"desc{i}")
        with c2:
            r["qta"] = st.number_input("Q.tà", min_value=0.0, value=r["qta"], key=f"qta{i}")
        with c3:
            r["prezzo"] = st.number_input("Prezzo", min_value=0.0, value=r["prezzo"], key=f"prz{i}")
        with c4:
            r["iva"] = st.selectbox("IVA %", [22, 10, 5, 4, 0], index=[22, 10, 5, 4, 0].index(r["iva"]), key=f"iva{i}")
        with c5:
            if st.button("🗑", key=f"del{i}"):
                st.session_state.righe_correnti.pop(i)
                st.rerun()

        imp_riga = r["qta"] * r["prezzo"]
        iva_riga = imp_riga * (r["iva"] / 100)
        imponibile += imp_riga
        iva_tot += iva_riga

    totale = imponibile + iva_tot

    st.markdown("---")
    col_t1, col_t2, col_t3 = st.columns(3)
    col_t1.metric("💶 Imponibile", f"EUR {_format_val_eur(imponibile)}")
    col_t2.metric("📊 IVA", f"EUR {_format_val_eur(iva_tot)}")
    col_t3.metric("💰 Totale", f"EUR {_format_val_eur(totale)}")

    if st.session_state.modalita_modifica:
        stato = st.selectbox("Stato documento", ["Creazione", "Creato", "Inviato"], 
                           index=["Creazione", "Creato", "Inviato"].index(stato_originale))
    else:
        stato = st.selectbox("Stato documento", ["Creazione", "Creato", "Inviato"])

    st.markdown("---")
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.session_state.modalita_modifica:
            btn_label = "💾 Salva modifiche"
        else:
            btn_label = "💾 Salva fattura"
            
        if st.button(btn_label, type="primary", use_container_width=True):
            if not cliente_corrente["Denominazione"]:
                st.error("⚠️ Inserisci la denominazione del cliente")
            elif not st.session_state.righe_correnti:
                st.error("⚠️ Inserisci almeno una riga")
            else:
                if (cliente_corrente["Denominazione"] and 
                    cliente_corrente["Denominazione"] not in st.session_state.clienti["Denominazione"].tolist()):
                    nuovo_cli = pd.DataFrame([{
                        "Denominazione": cliente_corrente["Denominazione"],
                        "PIVA": cliente_corrente["PIVA"],
                        "CF": cliente_corrente["CF"],
                        "Indirizzo": cliente_corrente["Indirizzo"],
                        "CAP": cliente_corrente["CAP"],
                        "Comune": cliente_corrente["Comune"],
                        "Provincia": cliente_corrente["Provincia"],
                        "CodiceDestinatario": cliente_corrente["CodiceDestinatario"],
                        "PEC": cliente_corrente["PEC"],
                        "Tipo": "Cliente",
                    }])
                    st.session_state.clienti = pd.concat([st.session_state.clienti, nuovo_cli], ignore_index=True)
                else:
                    mask = st.session_state.clienti["Denominazione"] == cliente_corrente["Denominazione"]
                    for campo in ["PIVA", "CF", "Indirizzo", "CAP", "Comune", "Provincia", "CodiceDestinatario", "PEC"]:
                        st.session_state.clienti.loc[mask, campo] = cliente_corrente[campo]

                pdf_bytes = genera_pdf_fattura(
                    numero, data_f, cliente_corrente, st.session_state.righe_correnti,
                    imponibile, iva_tot, totale, tipo_xml_codice=tipo_xml_codice,
                    modalita_pagamento=modalita_pagamento, note=note,
                )

                pdf_filename = f"{numero.replace('/', '-')}.pdf"
                pdf_path = os.path.join(PDF_DIR, pdf_filename)
                with open(pdf_path, "wb") as f:
                    f.write(pdf_bytes)

                if st.session_state.modalita_modifica:
                    idx = st.session_state.fattura_in_modifica
                    # FORMATO EUROPEO
                    st.session_state.documenti_emessi.loc[idx, "Data"] = data_f.strftime("%d/%m/%Y")
                    st.session_state.documenti_emessi.loc[idx, "Controparte"] = cliente_corrente["Denominazione"]
                    st.session_state.documenti_emessi.loc[idx, "Imponibile"] = imponibile
                    st.session_state.documenti_emessi.loc[idx, "IVA"] = iva_tot
                    st.session_state.documenti_emessi.loc[idx, "Importo"] = totale
                    st.session_state.documenti_emessi.loc[idx, "TipoXML"] = tipo_xml_codice
                    st.session_state.documenti_emessi.loc[idx, "Stato"] = stato
                    st.session_state.documenti_emessi.loc[idx, "PDF"] = pdf_path
                    
                    st.success("✅ Fattura modificata con successo!")
                    
                    st.session_state.modalita_modifica = False
                    st.session_state.fattura_in_modifica = None
                    st.session_state.righe_correnti = []
                else:
                    nuova = pd.DataFrame([{
                        "Tipo": "Emessa",
                        "Numero": numero,
                        # FORMATO EUROPEO
                        "Data": data_f.strftime("%d/%m/%Y"),
                        "Controparte": cliente_corrente["Denominazione"],
                        "Imponibile": imponibile,
                        "IVA": iva_tot,
                        "Importo": totale,
                        "TipoXML": tipo_xml_codice,
                        "Stato": stato,
                        "UUID": "",
                        "PDF": pdf_path,
                    }], columns=COLONNE_DOC)
                    st.session_state.documenti_emessi = pd.concat(
                        [st.session_state.documenti_emessi, nuova], ignore_index=True
                    )
                    st.session_state.righe_correnti = []
                    st.success("✅ Fattura salvata con successo!")

                st.download_button(
                    label="📥 Scarica PDF",
                    data=pdf_bytes,
                    file_name=pdf_filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.markdown("**Anteprima PDF**")
                mostra_anteprima_pdf(pdf_bytes, altezza=600)
    
    with col_btn2:
        if st.session_state.modalita_modifica:
            if st.button("❌ Annulla", use_container_width=True):
                st.session_state.modalita_modifica = False
                st.session_state.fattura_in_modifica = None
                st.session_state.righe_correnti = []
                st.session_state.pagina_corrente = "📋 Lista documenti"
                st.rerun()

elif pagina == "📥 Download documenti":
    st.subheader("📥 Download documenti inviati")
    st.info("🔧 Funzione in sviluppo - qui potrai scaricare i documenti inviati allo SdI")

elif pagina == "📦 Carica pacchetto AdE":
    st.subheader("📦 Carica pacchetto AdE")
    st.info("Carica il file ZIP scaricato dal cassetto fiscale dell'Agenzia delle Entrate")
    
    uploaded_zip = st.file_uploader("📁 Seleziona file ZIP", type=["zip"])
    if uploaded_zip:
        st.write("📄 File caricato:", uploaded_zip.name)
        st.info("🔧 Parsing del pacchetto in sviluppo")

elif pagina == "👥 Rubrica clienti":
    st.subheader("👥 Rubrica clienti e fornitori")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        filtra_clienti = st.checkbox("Mostra clienti", value=True)
    with col_f2:
        filtra_fornitori = st.checkbox("Mostra fornitori", value=True)

    df_c = st.session_state.clienti.copy()
    if not df_c.empty:
        mask = []
        for _, r in df_c.iterrows():
            if r["Tipo"] == "Cliente" and filtra_clienti:
                mask.append(True)
            elif r["Tipo"] == "Fornitore" and filtra_fornitori:
                mask.append(True)
            else:
                mask.append(False)
        df_c = df_c[pd.Series(mask)]
        st.dataframe(df_c, use_container_width=True)
    else:
        st.info("Nessun contatto in rubrica")

    st.markdown("---")
    st.markdown("### ➕ Aggiungi nuovo contatto")
    with st.form("nuovo_contatto"):
        col1, col2 = st.columns(2)
        with col1:
            den = st.text_input("Denominazione")
        with col2:
            piva = st.text_input("P.IVA")

        cf = st.text_input("Codice Fiscale")
        ind = st.text_input("Indirizzo")

        col_c1, col_c2, col_c3 = st.columns(3)
        with col_c1:
            cap = st.text_input("CAP")
        with col_c2:
            com = st.text_input("Comune")
        with col_c3:
            prov = st.text_input("Provincia")

        col_x1, col_x2 = st.columns(2)
        with col_x1:
            cod_dest = st.text_input("Codice Destinatario", value="0000000")
        with col_x2:
            pec = st.text_input("PEC")

        tipo = st.selectbox("Tipo", ["Cliente", "Fornitore"])

        if st.form_submit_button("💾 Salva contatto", use_container_width=True):
            nuovo = pd.DataFrame([{
                "Denominazione": den,
                "PIVA": piva,
                "CF": cf,
                "Indirizzo": ind,
                "CAP": cap,
                "Comune": com,
                "Provincia": prov,
                "CodiceDestinatario": cod_dest,
                "PEC": pec,
                "Tipo": tipo,
            }])
            st.session_state.clienti = pd.concat([st.session_state.clienti, nuovo], ignore_index=True)
            st.success("✅ Contatto salvato!")

else:
    st.subheader("📊 Dashboard")

    df_e = st.session_state.documenti_emessi
    num_emesse = len(df_e)
    tot_emesse = df_e["Importo"].sum() if not df_e.empty else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("📄 Fatture emesse", num_emesse)
    col2.metric("💰 Totale fatturato", f"EUR {_format_val_eur(tot_emesse)}")
    col3.metric("👥 Clienti attivi", len(st.session_state.clienti))

    st.markdown("---")
    
    if not df_e.empty:
        st.markdown("### 📊 Ultime fatture emesse")
        df_recenti = df_e.copy()
        # FORMATO EUROPEO
        df_recenti["DataSort"] = pd.to_datetime(df_recenti["Data"], format="%d/%m/%Y", errors="coerce")
        df_recenti = df_recenti.sort_values("DataSort", ascending=False).head(5)
        st.dataframe(df_recenti[["Numero", "Data", "Controparte", "Importo"]], use_container_width=True, hide_index=True)
    
    st.markdown("---")
    st.caption("🎛️ Fisco Chiaro Consulting - Pannello di controllo | Versione 1.0 | © 2025")
