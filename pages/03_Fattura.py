import streamlit as st
import pandas as pd
from datetime import date
import os
import re
from fpdf import FPDF
import base64

PRIMARY_BLUE = "#1f77b4"

PDF_DIR = "fatture_pdf"
os.makedirs(PDF_DIR, exist_ok=True)

# ==========================
# DATI EMITTENTE
# ==========================
EMITTENTE = {
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


# ==========================
# FUNZIONI
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
<iframe src="data:application/pdf;base64,{b64_pdf}"
        width="100%" height="{altezza}" type="application/pdf">
</iframe>
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
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    row_height = 6

    # EMITTENTE
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, EMITTENTE["Denominazione"], ln=1)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, EMITTENTE["Indirizzo"], ln=1)
    pdf.cell(
        0,
        5,
        f'{EMITTENTE["CAP"]} {EMITTENTE["Comune"]} ({EMITTENTE["Provincia"]}) IT',
        ln=1,
    )
    pdf.cell(0, 5, f'CODICE FISCALE {EMITTENTE["CF"]}', ln=1)
    pdf.cell(0, 5, f'PARTITA IVA {EMITTENTE["PIVA"]}', ln=1)

    # CLIENTE A DESTRA
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
    pdf.cell(
        0,
        5,
        f"{cliente.get('CAP','')} {cliente.get('Comune','')} ({cliente.get('Provincia','')}) IT",
        ln=1,
    )

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

    # DETTAGLIO DOCUMENTO
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

    # IMPORTI
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

    # RIEPILOGHI
    pdf.ln(3)
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)

    pdf.set_x(10)
    pdf.cell(190 - 20, row_height, "RIEPILOGHI", border=1, ln=1, fill=True)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 8)
    riepi_headers = [
        "IVA %",
        "NAT.",
        "RIFERIMENTO NORMATIVO",
        "IMPONIBILE",
        "IMPOSTA",
        "ESIG. IVA",
        "ARROT.",
        "SPESE ACC.",
        "TOTALE",
    ]
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

    # MODALITÀ PAGAMENTO
    pdf.set_fill_color(31, 119, 180)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 9)

    pdf.set_x(10)
    pdf.cell(
        190 - 20,
        row_height,
        "MODALITA' DI PAGAMENTO ACCETTATE: PAGAMENTO COMPLETO",
        border=1,
        ln=1,
        fill=True,
    )

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

    # FOOTER
    pdf.set_y(-25)
    pdf.set_font("Helvetica", "I", 7)
    pdf.multi_cell(
        0,
        4,
        (
            "Copia di cortesia priva di valore ai fini fiscali e giuridici ai sensi dell'articolo 21 del D.P.R. 633/72. "
            "L'originale del documento è consultabile presso l'indirizzo PEC o il codice SDI registrato "
            "o nell'area riservata Fatture e Corrispettivi."
        ),
        align="C",
    )

    out = pdf.output(dest="S")
    if isinstance(out, (bytes, bytearray)):
        return bytes(out)
    return out.encode("latin1")


# ==========================
# HEADER PAGINA FATTURA
# ==========================
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>FISCO CHIARO CONSULTING</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("#### Nuova Fattura | Clienti | Documenti")
with col_user:
    st.markdown("Operatore")

st.markdown("---")

col_back, col_void = st.columns([1, 5])
with col_back:
    if st.button("⬅ Torna alla lista documenti"):
        st.switch_page("pages/02_Documenti.py")

st.subheader("🧾 Crea nuova fattura emessa")

# ==========================
# FORM FATTURA
# ==========================
denominazioni = ["NUOVO"] + st.session_state.clienti["Denominazione"].tolist()

col1, col2 = st.columns([2, 1])
with col1:
    current_label = st.session_state.cliente_corrente_label
    if current_label not in denominazioni:
        current_label = "NUOVO"
    default_idx = denominazioni.index(current_label)
    cliente_sel = st.selectbox(
        "Cliente",
        denominazioni,
        index=default_idx,
    )
    st.session_state.cliente_corrente_label = cliente_sel

with col2:
    if st.button("➕ Nuovo cliente"):
        st.session_state.cliente_corrente_label = "NUOVO"
        st.experimental_rerun()

if cliente_sel == "NUOVO":
    cli_den = st.text_input("Denominazione cliente")
    cli_piva = st.text_input("P.IVA")
    cli_cf = st.text_input("Codice Fiscale")
    cli_ind = st.text_input("Indirizzo (via/piazza, civico)")
    colc1, colc2, colc3 = st.columns(3)
    with colc1:
        cli_cap = st.text_input("CAP")
    with colc2:
        cli_com = st.text_input("Comune")
    with colc3:
        cli_prov = st.text_input("Provincia (es. BA)")
    colx1, colx2 = st.columns(2)
    with colx1:
        cli_cod_dest = st.text_input("Codice Destinatario", value="0000000")
    with colx2:
        cli_pec = st.text_input("PEC destinatario")
    cliente_corrente = {
        "Denominazione": cli_den,
        "PIVA": cli_piva,
        "CF": cli_cf,
        "Indirizzo": cli_ind,
        "CAP": cli_cap,
        "Comune": cli_com,
        "Provincia": cli_prov,
        "CodiceDestinatario": cli_cod_dest,
        "PEC": cli_pec,
    }
else:
    riga_cli = st.session_state.clienti[
        st.session_state.clienti["Denominazione"] == cliente_sel
    ].iloc[0]
    cli_den = st.text_input("Denominazione", riga_cli.get("Denominazione", ""))
    cli_piva = st.text_input("P.IVA", riga_cli.get("PIVA", ""))
    cli_cf = st.text_input("Codice Fiscale", riga_cli.get("CF", ""))
    cli_ind = st.text_input(
        "Indirizzo (via/piazza, civico)", riga_cli.get("Indirizzo", "")
    )
    colc1, colc2, colc3 = st.columns(3)
    with colc1:
        cli_cap = st.text_input("CAP", riga_cli.get("CAP", ""))
    with colc2:
        cli_com = st.text_input("Comune", riga_cli.get("Comune", ""))
    with colc3:
        cli_prov = st.text_input("Provincia (es. BA)", riga_cli.get("Provincia", ""))
    colx1, colx2 = st.columns(2)
    with colx1:
        cli_cod_dest = st.text_input(
            "Codice Destinatario", riga_cli.get("CodiceDestinatario", "0000000")
        )
    with colx2:
        cli_pec = st.text_input("PEC destinatario", riga_cli.get("PEC", ""))
    cliente_corrente = {
        "Denominazione": cli_den,
        "PIVA": cli_piva,
        "CF": cli_cf,
        "Indirizzo": cli_ind,
        "CAP": cli_cap,
        "Comune": cli_com,
        "Provincia": cli_prov,
        "CodiceDestinatario": cli_cod_dest,
        "PEC": cli_pec,
    }

tipi_xml_label = [
    "TD01 - Fattura",
    "TD02 - Acconto/Anticipo su fattura",
    "TD04 - Nota di credito",
    "TD05 - Nota di debito",
]
tipo_xml_label = st.selectbox("Tipo documento (XML)", tipi_xml_label, index=0)
tipo_xml_codice = tipo_xml_label.split(" ")[0]

coln1, coln2 = st.columns(2)
with coln1:
    numero = st.text_input("Numero fattura", get_next_invoice_number())
with coln2:
    data_f = st.date_input("Data fattura", date.today())

modalita_pagamento = st.text_input(
    "Modalità di pagamento (es. Bonifico bancario su IBAN ...)",
    value="",
)
note = st.text_area(
    "Note / causale (verrà riportata in PDF come CAUSALE)", value="", height=80
)

st.markdown("### Righe fattura")
if st.button("➕ Aggiungi riga"):
    st.session_state.righe_correnti.append(
        {"desc": "", "qta": 1.0, "prezzo": 0.0, "iva": 22}
    )
    st.experimental_rerun()

imponibile = 0.0
iva_tot = 0.0
for i, r in enumerate(st.session_state.righe_correnti):
    c1, c2, c3, c4, c5 = st.columns([4, 1, 1, 1, 0.5])
    with c1:
        r["desc"] = st.text_input("Descrizione", r["desc"], key=f"desc_{i}")
    with c2:
        r["qta"] = st.number_input(
            "Q.tà", min_value=0.0, value=r["qta"], key=f"qta_{i}"
        )
    with c3:
        r["prezzo"] = st.number_input(
            "Prezzo", min_value=0.0, value=r["prezzo"], key=f"prz_{i}"
        )
    with c4:
        r["iva"] = st.selectbox(
            "IVA%",
            [22, 10, 5, 4, 0],
            index=[22, 10, 5, 4, 0].index(r["iva"]),
            key=f"iva_{i}",
        )
    with c5:
        if st.button("🗑️", key=f"del_{i}"):
            st.session_state.righe_correnti.pop(i)
            st.experimental_rerun()

    imp_riga = r["qta"] * r["prezzo"]
    iva_riga = imp_riga * r["iva"] / 100
    imponibile += imp_riga
    iva_tot += iva_riga

totale = imponibile + iva_tot

col_t1, col_t2, col_t3 = st.columns(3)
col_t1.metric("Imponibile", f"EUR {_format_val_eur(imponibile)}")
col_t2.metric("IVA", f"EUR {_format_val_eur(iva_tot)}")
col_t3.metric("Totale", f"EUR {_format_val_eur(totale)}")

stato = st.selectbox("Stato", ["Creazione", "Creato", "Inviato"])

if st.button("💾 Salva fattura emessa", type="primary"):
    if not cliente_corrente["Denominazione"]:
        st.error("Inserisci almeno la denominazione del cliente.")
    elif not st.session_state.righe_correnti:
        st.error("Inserisci almeno una riga di fattura.")
    else:
        # salvataggio cliente in rubrica
        if (
            cliente_corrente["Denominazione"]
            and cliente_corrente["Denominazione"]
            not in st.session_state.clienti["Denominazione"].tolist()
        ):
            nuovo_cli = pd.DataFrame(
                [
                    {
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
                    }
                ]
            )
            st.session_state.clienti = pd.concat(
                [st.session_state.clienti, nuovo_cli],
                ignore_index=True,
            )
        else:
            mask = (
                st.session_state.clienti["Denominazione"]
                == cliente_corrente["Denominazione"]
            )
            for campo in [
                "PIVA",
                "CF",
                "Indirizzo",
                "CAP",
                "Comune",
                "Provincia",
                "CodiceDestinatario",
                "PEC",
            ]:
                st.session_state.clienti.loc[mask, campo] = cliente_corrente[campo]

        # PDF
        pdf_bytes = genera_pdf_fattura(
            numero,
            data_f,
            cliente_corrente,
            st.session_state.righe_correnti,
            imponibile,
            iva_tot,
            totale,
            tipo_xml_codice=tipo_xml_codice,
            modalita_pagamento=modalita_pagamento,
            note=note,
        )
        pdf_filename = f"{numero.replace('/', '_')}.pdf"
        pdf_path = os.path.join(PDF_DIR, pdf_filename)
        with open(pdf_path, "wb") as f:
            f.write(pdf_bytes)

        nuova = pd.DataFrame(
            [
                {
                    "Tipo": "Emessa",
                    "Numero": numero,
                    "Data": str(data_f),
                    "Controparte": cliente_corrente["Denominazione"],
                    "Imponibile": imponibile,
                    "IVA": iva_tot,
                    "Importo": totale,
                    "TipoXML": tipo_xml_codice,
                    "Stato": stato,
                    "UUID": "",
                    "PDF": pdf_path,
                }
            ],
            columns=COLONNE_DOC,
        )
        st.session_state.documenti_emessi = pd.concat(
            [st.session_state.documenti_emessi, nuova],
            ignore_index=True,
        )

        st.session_state.righe_correnti = []

        st.success("✅ Fattura emessa salvata e PDF generato.")
        st.download_button(
            label="📥 Scarica subito il PDF",
            data=pdf_bytes,
            file_name=pdf_filename,
            mime="application/pdf",
        )
        st.markdown("#### Anteprima PDF generato")
        mostra_anteprima_pdf(pdf_bytes, altezza=600)

st.markdown("---")
st.caption("Fisco Chiaro Consulting – Emesse gestite dall'app, PDF generati automaticamente.")
