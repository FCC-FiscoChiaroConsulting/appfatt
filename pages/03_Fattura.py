import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
from datetime import date, datetime, timedelta
import os
import uuid
import base64
import pandas as pd

PRIMARY_BLUE = "#1f77b4"

# ==========================
# DATI AZIENDA DA ANAGRAFICA
# ==========================
def get_dati_azienda_da_sessione():
    ana = st.session_state.get("anagrafica", None)
    if not ana:
        # fallback se l’anagrafica non è ancora stata compilata
        return {
            "nome": "GLOBAL BUSINESS SRL",
            "indirizzo": "VIA CARULLI 90",
            "cap": "70121",
            "citta": "BARI",
            "prov": "BA",
            "cf": "07707940727",
            "piva": "07707940727",
            "pec": "",
            "codice_dest": "0000000",
        }
    return {
        "nome": ana.get("Ragione Sociale", "") or "GLOBAL BUSINESS SRL",
        "indirizzo": ana.get("Indirizzo", "") or "VIA CARULLI 90",
        "cap": ana.get("CAP", "") or "70121",
        "citta": ana.get("Comune", "") or "BARI",
        "prov": ana.get("Provincia", "") or "BA",
        "cf": ana.get("CF", "") or ana.get("P.IVA", "") or "00000000000",
        "piva": ana.get("P.IVA", "") or "00000000000",
        "pec": ana.get("PEC", "") or "",
        "codice_dest": ana.get("Codice Destinatario", "") or "0000000",
    }


AZIENDA = get_dati_azienda_da_sessione()

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

# ==========================
# INIZIALIZZAZIONE SESSION_STATE
# ==========================
if "documenti_emessi" not in st.session_state:
    st.session_state.documenti_emessi = pd.DataFrame(columns=COLONNE_DOC)
else:
    for col in COLONNE_DOC:
        if col not in st.session_state.documenti_emessi.columns:
            st.session_state.documenti_emessi[col] = (
                0.0 if col in ["Imponibile", "IVA", "Importo"] else ""
            )

if "clienti" not in st.session_state:
    st.session_state.clienti = pd.DataFrame(
        columns=[
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
    )

if "anagrafica" not in st.session_state:
    st.session_state.anagrafica = {
        "Ragione Sociale": AZIENDA["nome"],
        "P.IVA": AZIENDA["piva"],
        "CF": AZIENDA["cf"],
        "Indirizzo": AZIENDA["indirizzo"],
        "CAP": AZIENDA["cap"],
        "Comune": AZIENDA["citta"],
        "Provincia": AZIENDA["prov"],
        "PEC": AZIENDA["pec"],
        "Codice Destinatario": AZIENDA["codice_dest"],
    }


# ==========================
# FUNZIONI DI SUPPORTO
# ==========================
def get_next_invoice_number() -> str:
    year = date.today().year
    prefix = f"FT{year}"
    df = st.session_state.documenti_emessi
    seq = 1
    if not df.empty:
        mask = df["Numero"].astype(str).str.startswith(prefix)
        if mask.any():
            import re

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


def format_eur(val: float) -> str:
    return (
        f"{val:,.2f}"
        .replace(",", "X")
        .replace(".", ",")
        .replace("X", ".")
    )


# ==========================
# GENERAZIONE PDF – LAYOUT COME MODELLO
# ==========================
def genera_pdf_fattura(dati):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    PAGE_W, PAGE_H = A4
    x_left = 30
    x_right = PAGE_W - 30
    blu = colors.HexColor("#0070c0")

    # ---------- INTESTAZIONE AZIENDA + CLIENTE ----------
    y = PAGE_H - 60

    # Azienda
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x_left, y, dati["azienda_nome"])
    c.setFont("Helvetica", 10)
    c.drawString(x_left, y - 14, dati["azienda_indirizzo"])
    c.drawString(
        x_left,
        y - 28,
        f"{dati['azienda_cap']} {dati['azienda_citta']} ({dati['azienda_prov']}) IT",
    )
    c.drawString(x_left, y - 42, f"CODICE FISCALE {dati['azienda_cf']}")
    c.drawString(x_left, y - 56, f"PARTITA IVA {dati['azienda_piva']}")

    # Cliente
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x_right, y, "Spett.le")
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(x_right, y - 14, dati["cliente_nome"])
    c.setFont("Helvetica", 10)
    c.drawRightString(x_right, y - 28, dati["cliente_indirizzo"])
    c.drawRightString(
        x_right,
        y - 42,
        f"{dati['cliente_cap']} {dati['cliente_citta']} ({dati['cliente_prov']}) IT",
    )
    if dati["cliente_piva"]:
        c.drawRightString(x_right, y - 56, f"PARTITA IVA {dati['cliente_piva']}")
    else:
        c.drawRightString(x_right, y - 56, f"CODICE FISCALE {dati['cliente_cf']}")

    # ---------- BARRA DATI DOCUMENTO + DATI TRASMISSIONE ----------
    y = PAGE_H - 140
    mid_x = x_left + (x_right - x_left) / 2

    c.setFillColor(blu)
    c.rect(x_left, y, (mid_x - x_left), 18, fill=1, stroke=0)
    c.rect(mid_x, y, (x_right - mid_x), 18, fill=1, stroke=0)

    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_left + 4, y + 4, "DATI DOCUMENTO")
    c.drawString(mid_x + 4, y + 4, "DATI TRASMISSIONE")

    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    y -= 18
    row_h = 14

    # colonna sinistra
    c.drawString(x_left + 4, y, "TIPO")
    c.drawString(x_left + 80, y, dati["tipo_documento"])

    c.drawString(x_left + 4, y - row_h, "NUMERO")
    c.drawString(x_left + 80, y - row_h, str(dati["numero"]))

    c.drawString(x_left + 4, y - 2 * row_h, "DATA")
    c.drawString(x_left + 80, y - 2 * row_h, dati["data"])

    c.drawString(x_left + 4, y - 3 * row_h, "CAUSALE")
    c.drawString(x_left + 80, y - 3 * row_h, dati["causale"])

    # colonna destra
    x_rt = mid_x + 4
    c.drawString(x_rt, y, "CODICE DESTINATARIO")
    c.drawString(x_rt + 120, y, dati["codice_destinatario"])

    c.drawString(x_rt, y - row_h, "PEC DESTINATARIO")
    c.drawString(x_rt + 120, y - row_h, dati["pec_destinatario"])

    c.drawString(x_rt, y - 2 * row_h, "DATA INVIO")
    c.drawString(x_rt + 120, y - 2 * row_h, dati.get("data_invio", "") or "")

    c.drawString(x_rt, y - 3 * row_h, "IDENTIFICATIVO SDI")
    c.drawString(x_rt + 120, y - 3 * row_h, dati.get("id_sdi", "") or "")

    # ---------- DETTAGLIO DOCUMENTO ----------
    y = y - 3 * row_h - 30

    c.setFillColor(blu)
    c.rect(x_left, y, (x_right - x_left), 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_left + 4, y + 4, "DETTAGLIO DOCUMENTO")

    y -= 18
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 9)

    col_x = {
        "#": x_left + 4,
        "DESCRIZIONE": x_left + 24,
        "U.M.": x_left + 230,
        "PREZZO": x_left + 270,
        "QTA": x_left + 340,
        "TOTALE": x_left + 390,
        "IVA %": x_left + 450,
        "RIT.": x_left + 500,
        "NAT.": x_left + 530,
    }
    for label, xpos in col_x.items():
        c.drawString(xpos, y, label)

    # riga dettaglio
    y -= 14
    c.setFont("Helvetica", 9)
    c.drawString(col_x["#"], y, "1")
    c.drawString(col_x["DESCRIZIONE"], y, dati["descrizione"])
    c.drawRightString(col_x["PREZZO"] + 60, y, dati["prezzo_unitario"])
    c.drawRightString(col_x["QTA"] + 30, y, "1,00")
    c.drawRightString(col_x["TOTALE"] + 60, y, dati["imponibile"])
    c.drawRightString(col_x["IVA %"] + 40, y, dati["iva_percentuale"])

    # ---------- RIEPILOGO IMPORTI (blocchetto sinistra) ----------
    y -= 40
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_left + 4, y, f"IMPORTO = {dati['imponibile']}")
    y -= 14
    c.drawString(x_left + 4, y, f"TOTALE IMPONIBILE = {dati['imponibile']}")
    y -= 14
    c.drawString(
        x_left + 4,
        y,
        f"IVA (SU € {dati['imponibile']}) + {dati['iva_valore']}",
    )
    y -= 14
    c.drawString(x_left + 4, y, f"IMPORTO TOTALE = {dati['totale']}")

    y -= 18
    c.setFont("Helvetica-Bold", 11)
    c.setFillColor(blu)
    c.drawString(x_left + 4, y, f"NETTO A PAGARE = {dati['totale']}")
    c.setFillColor(colors.black)

    # ---------- RIEPILOGHI ----------
    y -= 40
    c.setFillColor(blu)
    c.rect(x_left, y, (x_right - x_left), 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x_left + 4, y + 4, "RIEPILOGHI")

    y -= 18
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 7)
    headers = [
        ("IVA %", x_left + 4),
        ("NAT.", x_left + 50),
        ("RIFERIMENTO NORMATIVO", x_left + 90),
        ("IMPONIBILE", x_left + 240),
        ("IMPOSTA", x_left + 310),
        ("ESIG. IVA", x_left + 380),
        ("ARROT.", x_left + 450),
        ("SPESE", x_left + 490),
        ("ACC.", x_left + 530),
        ("TOTALE", x_left + 570),
    ]
    for label, xpos in headers:
        c.drawString(xpos, y, label)

    y -= 12
    c.setFont("Helvetica", 7)
    c.drawString(x_left + 4, y, dati["iva_percentuale"])
    c.drawRightString(x_left + 290, y, dati["imponibile"])
    c.drawRightString(x_left + 360, y, dati["iva_valore"])
    c.drawString(x_left + 380, y, "IMMEDIATA")
    c.drawRightString(x_left + 470, y, "0,00")
    c.drawRightString(x_left + 510, y, "0,00")
    c.drawRightString(x_left + 550, y, "0,00")
    c.drawRightString(x_left + 610, y, dati["totale"])

    # ---------- MODALITÀ DI PAGAMENTO ----------
    y -= 40
    c.setFillColor(blu)
    c.rect(x_left, y, (x_right - x_left), 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        x_left + 4,
        y + 4,
        f"MODALITÀ DI PAGAMENTO ACCETTATE: {dati['pagamento_descrizione']}",
    )

    y -= 18
    c.setFillColor(blu)
    c.rect(x_left, y, (x_right - x_left), 18, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x_left + 4, y + 4, "MODALITA'")
    c.drawString(x_left + 120, y + 4, "DETTAGLI")
    c.drawString(x_left + 300, y + 4, "DATA RIF. TERMINI")
    c.drawString(x_left + 410, y + 4, "GIORNI TERMINI")
    c.drawString(x_left + 510, y + 4, "DATA SCADENZA")

    y -= 18
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    c.drawString(x_left + 4, y, dati["modalita_pagamento"])
    c.drawString(x_left + 120, y, dati["dettagli_pagamento"])
    c.drawString(x_left + 300, y, dati["data_rif_term"])
    c.drawRightString(x_left + 460, y, str(dati["giorni_termine"]))
    c.drawString(x_left + 510, y, dati["data_scadenza"])

    y -= 20
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(x_right, y, f"TOTALE A PAGARE EUR {dati['totale']}")

    # ---------- NOTE FINALI ----------
    c.setFont("Helvetica", 7)
    c.drawCentredString(
        PAGE_W / 2,
        40,
        "Copia di cortesia priva di valore ai fini fiscali e giuridici ai sensi dell'articolo 21 del D.P.R. 633/72.",
    )
    c.drawCentredString(
        PAGE_W / 2,
        28,
        "L'originale del documento è consultabile presso l'indirizzo PEC o codice SDI da Lei registrato",
    )
    c.drawCentredString(
        PAGE_W / 2,
        16,
        "o nella sua Area riservata web Fatture e Corrispettivi.",
    )

    c.save()
    buffer.seek(0)
    return buffer


# ==========================
# GENERAZIONE XML SEMPLIFICATO
# ==========================
def genera_xml_fattura(dati) -> str:
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<p:FatturaElettronica versione="FPR12"
 xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"
 xmlns:ds="http://www.w3.org/2000/09/xmldsig#">
  <FatturaElettronicaHeader>
    <DatiTrasmissione>
      <IdTrasmittente>
        <IdPaese>IT</IdPaese>
        <IdCodice>{AZIENDA['piva']}</IdCodice>
      </IdTrasmittente>
      <ProgressivoInvio>00001</ProgressivoInvio>
      <FormatoTrasmissione>FPR12</FormatoTrasmissione>
      <CodiceDestinatario>{dati['codice_destinatario']}</CodiceDestinatario>
      <PECDestinatario>{dati['pec_destinatario']}</PECDestinatario>
    </DatiTrasmissione>
    <CedentePrestatore>
      <DatiAnagrafici>
        <IdFiscaleIVA>
          <IdPaese>IT</IdPaese>
          <IdCodice>{AZIENDA['piva']}</IdCodice>
        </IdFiscaleIVA>
        <CodiceFiscale>{AZIENDA['cf']}</CodiceFiscale>
        <Anagrafica>
          <Denominazione>{AZIENDA['nome']}</Denominazione>
        </Anagrafica>
        <RegimeFiscale>RF01</RegimeFiscale>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>{AZIENDA['indirizzo']}</Indirizzo>
        <CAP>{AZIENDA['cap']}</CAP>
        <Comune>{AZIENDA['citta']}</Comune>
        <Provincia>{AZIENDA['prov']}</Provincia>
        <Nazione>IT</Nazione>
      </Sede>
    </CedentePrestatore>
    <CessionarioCommittente>
      <DatiAnagrafici>
        <CodiceFiscale>{dati['cliente_cf']}</CodiceFiscale>
        <Anagrafica>
          <Denominazione>{dati['cliente_nome']}</Denominazione>
        </Anagrafica>
      </DatiAnagrafici>
      <Sede>
        <Indirizzo>{dati['cliente_indirizzo']}</Indirizzo>
        <CAP>{dati['cliente_cap']}</CAP>
        <Comune>{dati['cliente_citta']}</Comune>
        <Provincia>{dati['cliente_prov']}</Provincia>
        <Nazione>IT</Nazione>
      </Sede>
    </CessionarioCommittente>
  </FatturaElettronicaHeader>
  <FatturaElettronicaBody>
    <DatiGenerali>
      <DatiGeneraliDocumento>
        <TipoDocumento>TD01</TipoDocumento>
        <Divisa>EUR</Divisa>
        <Data>{datetime.strptime(dati['data'], "%d/%m/%Y").date().isoformat()}</Data>
        <Numero>{dati['numero']}</Numero>
        <Causale>{dati['causale']}</Causale>
      </DatiGeneraliDocumento>
    </DatiGenerali>
    <DatiBeniServizi>
      <DettaglioLinee>
        <NumeroLinea>1</NumeroLinea>
        <Descrizione>{dati['descrizione']}</Descrizione>
        <Quantita>1.00</Quantita>
        <PrezzoUnitario>{dati['imponibile_num']:.2f}</PrezzoUnitario>
        <PrezzoTotale>{dati['imponibile_num']:.2f}</PrezzoTotale>
        <AliquotaIVA>{dati['iva_percent_num']:.2f}</AliquotaIVA>
      </DettaglioLinee>
      <DatiRiepilogo>
        <AliquotaIVA>{dati['iva_percent_num']:.2f}</AliquotaIVA>
        <ImponibileImporto>{dati['imponibile_num']:.2f}</ImponibileImporto>
        <Imposta>{dati['iva_val_num']:.2f}</Imposta>
        <EsigibilitaIVA>I</EsigibilitaIVA>
      </DatiRiepilogo>
    </DatiBeniServizi>
    <DatiPagamento>
      <CondizioniPagamento>TP01</CondizioniPagamento>
      <DettaglioPagamento>
        <ModalitaPagamento>{dati['modalita_pagamento_codice']}</ModalitaPagamento>
        <DataRiferimentoTerminiPagamento>{datetime.strptime(dati['data_rif_term'], "%d/%m/%Y").date().isoformat()}</DataRiferimentoTerminiPagamento>
        <GiorniTerminiPagamento>{dati['giorni_termine']}</GiorniTerminiPagamento>
        <DataScadenzaPagamento>{datetime.strptime(dati['data_scadenza'], "%d/%m/%Y").date().isoformat()}</DataScadenzaPagamento>
        <ImportoPagamento>{dati['totale_num']:.2f}</ImportoPagamento>
      </DettaglioPagamento>
    </DatiPagamento>
  </FatturaElettronicaBody>
</p:FatturaElettronica>
"""
    return xml


# ==========================
# SALVATAGGIO E REGISTRAZIONE
# ==========================
def salva_su_file(pdf_buffer: BytesIO, xml_string: str, numero: str):
    base_dir = os.path.join("Documenti", "Fatture")
    os.makedirs(base_dir, exist_ok=True)

    pdf_path = os.path.join(base_dir, f"{numero}.pdf")
    xml_path = os.path.join(base_dir, f"{numero}.xml")

    with open(pdf_path, "wb") as f:
        f.write(pdf_buffer.getvalue())

    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(xml_string)

    return pdf_path, xml_path


def registra_in_documenti(dati, pdf_path: str):
    nuova_riga = {
        "Tipo": "Fattura",
        "Numero": dati["numero"],
        "Data": dati["data"],
        "Controparte": dati["cliente_nome"],
        "Imponibile": dati["imponibile_num"],
        "IVA": dati["iva_val_num"],
        "Importo": dati["totale_num"],
        "TipoXML": "TD01",
        "Stato": "Creazione",
        "UUID": str(uuid.uuid4()),
        "PDF": pdf_path,
    }

    st.session_state.documenti_emessi = pd.concat(
        [st.session_state.documenti_emessi, pd.DataFrame([nuova_riga])],
        ignore_index=True,
    )


def mostra_pdf(buffer: BytesIO, altezza: int = 600):
    pdf_bytes = buffer.getvalue()
    b64 = base64.b64encode(pdf_bytes).decode()
    iframe = f"""
        <iframe width="100%" height="{altezza}"
        src="data:application/pdf;base64,{b64}" type="application/pdf"></iframe>
    """
    st.markdown(iframe, unsafe_allow_html=True)


# ==========================
# UI STREAMLIT – NUOVA FATTURA
# ==========================
st.set_page_config(
    page_title="Nuova Fattura",
    page_icon="🧾",
    layout="wide",
)

# Header
col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>FISCO CHIARO CONSULTING</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("#### Nuova fattura | Documenti | Dashboard")
with col_user:
    if st.button("Operatore"):
        st.switch_page("pages/01_Anagrafica_Azienda.py")

st.markdown("---")

col_h1, col_h2 = st.columns([3, 1])
with col_h1:
    st.subheader("Nuova fattura")
    st.caption("Creazione fattura PDF di cortesia + XML SdI (bozza)")
with col_h2:
    if st.button("⬅ Torna a Documenti"):
        st.switch_page("pages/02_Documenti.py")

numero_default = get_next_invoice_number()
data_default = date.today()

with st.form("form_fattura"):
    # ------------------- DATI CLIENTE -------------------
    st.subheader("Dati cliente")
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        cliente_nome = st.text_input("Denominazione / Nome cliente", "")
        cliente_indirizzo = st.text_input("Indirizzo", "")
        cliente_cap = st.text_input("CAP", "")
    with col_c2:
        cliente_citta = st.text_input("Comune", "")
        cliente_prov = st.text_input("Provincia (sigla)", "")
        cliente_piva = st.text_input("Partita IVA (se B2B)", "")
        cliente_cf = st.text_input("Codice fiscale (se privato)", "")

    # ------------------- DATI DOCUMENTO -------------------
    st.subheader("Dati documento")

    col_td1, col_td2 = st.columns(2)
    with col_td1:
        tipo_fattura = st.selectbox(
            "Tipologia fattura",
            ["B2B", "Privato", "PA"],
            index=0,
        )
    with col_td2:
        pass

    col_d1, col_d2, col_d3 = st.columns(3)
    with col_d1:
        numero = st.text_input("Numero fattura", numero_default)
    with col_d2:
        data_doc = st.date_input("Data", value=data_default, format="DD/MM/YYYY")
    with col_d3:
        causale = st.text_input("Causale", "SERVIZIO")

    col_t1, col_t2 = st.columns([3, 2])
    with col_t1:
        descrizione = st.text_area("Descrizione", "servizio")
    with col_t2:
        imponibile_num = st.number_input(
            "Imponibile (EUR)", min_value=0.0, value=409.84, step=10.0
        )
        iva_percent_num = st.number_input(
            "Aliquota IVA %", min_value=0.0, value=22.0, step=1.0
        )

    iva_val_num = round(imponibile_num * iva_percent_num / 100, 2)
    totale_num = round(imponibile_num + iva_val_num, 2)

    st.markdown("---")
    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.metric("Imponibile", format_eur(imponibile_num))
    with col_r2:
        st.metric("IVA", format_eur(iva_val_num))
    with col_r3:
        st.metric("Totale", format_eur(totale_num))

    # ------------------- PAGAMENTO -------------------
    st.markdown("---")
    st.subheader("Pagamento")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        pagamento_descrizione = st.text_input(
            "Descrizione condizioni pagamento",
            "PAGAMENTO COMPLETO",
        )
        modalita_pagamento = st.selectbox(
            "Modalità",
            ["CONTANTI", "BONIFICO", "CARTA", "ALTRO"],
        )
        dettagli_pagamento = st.text_input(
            "Dettagli pagamento (es. IBAN, carta, contanti alla consegna)",
            "",
        )
    with col_p2:
        giorni_termine = st.number_input(
            "Giorni termini",
            min_value=0,
            value=0,
            step=1,
        )
        data_rif_term = st.date_input(
            "Data riferimento termini",
            value=data_doc,
            format="DD/MM/YYYY",
        )

    # ------------------- DATI TRASMISSIONE -------------------
    st.markdown("---")
    st.subheader("Dati trasmissione")

    codice_destinatario = st.text_input(
        "Codice destinatario",
        AZIENDA["codice_dest"],
    )
    pec_destinatario = st.text_input(
        "PEC destinatario (se B2C/B2B via PEC)",
        AZIENDA["pec"],
    )

    submitted = st.form_submit_button("💾 Salva fattura e genera PDF + XML")

# ==========================
# ELABORAZIONE SUBMIT
# ==========================
if submitted:
    data_str = data_doc.strftime("%d/%m/%Y")
    data_rif_term_str = data_rif_term.strftime("%d/%m/%Y")
    data_scadenza = data_rif_term + timedelta(days=giorni_termine)
    data_scadenza_str = data_scadenza.strftime("%d/%m/%Y")

    # Label tipo documento (solo per stampa)
    if tipo_fattura == "B2B":
        tipo_doc_label = "TD01 FATTURA - B2B"
    elif tipo_fattura == "Privato":
        tipo_doc_label = "TD01 FATTURA - B2C"
    else:
        tipo_doc_label = "TD01 FATTURA - PA"

    # Mappatura modalità pagamento -> codice FatturaPA
    mappa_mp = {
        "CONTANTI": "MP01",
        "BONIFICO": "MP05",
        "CARTA": "MP08",
        "ALTRO": "MP02",
    }
    modalita_pagamento_codice = mappa_mp.get(modalita_pagamento, "MP02")

    dati = {
        # azienda
        "azienda_nome": AZIENDA["nome"],
        "azienda_indirizzo": AZIENDA["indirizzo"],
        "azienda_cap": AZIENDA["cap"],
        "azienda_citta": AZIENDA["citta"],
        "azienda_prov": AZIENDA["prov"],
        "azienda_cf": AZIENDA["cf"],
        "azienda_piva": AZIENDA["piva"],
        # cliente
        "cliente_nome": cliente_nome,
        "cliente_indirizzo": cliente_indirizzo,
        "cliente_cap": cliente_cap,
        "cliente_citta": cliente_citta,
        "cliente_prov": cliente_prov,
        "cliente_piva": cliente_piva,
        "cliente_cf": cliente_cf,
        # documento
        "tipo_documento": tipo_doc_label,
        "numero": numero,
        "data": data_str,
        "causale": causale,
        # trasmissione
        "codice_destinatario": codice_destinatario,
        "pec_destinatario": pec_destinatario,
        "data_invio": "",
        "id_sdi": "",
        # riga dettaglio
        "descrizione": descrizione,
        "prezzo_unitario": format_eur(imponibile_num),
        "imponibile": format_eur(imponibile_num),
        "iva_percentuale": f"{iva_percent_num:.2f}".replace(".", ","),
        "iva_valore": format_eur(iva_val_num),
        "totale": format_eur(totale_num),
        "imponibile_num": imponibile_num,
        "iva_percent_num": iva_percent_num,
        "iva_val_num": iva_val_num,
        "totale_num": totale_num,
        # pagamento
        "pagamento_descrizione": pagamento_descrizione,
        "modalita_pagamento": modalita_pagamento,
        "dettagli_pagamento": dettagli_pagamento,
        "giorni_termine": giorni_termine,
        "data_rif_term": data_rif_term_str,
        "data_scadenza": data_scadenza_str,
        "modalita_pagamento_codice": modalita_pagamento_codice,
    }

    pdf_buffer = genera_pdf_fattura(dati)
    xml_string = genera_xml_fattura(dati)
    pdf_path, xml_path = salva_su_file(pdf_buffer, xml_string, numero)
    registra_in_documenti(dati, pdf_path)

    st.success(
        f"Fattura {numero} creata, salvata in '{pdf_path}' e registrata in Documenti.\n"
        f"XML salvato in '{xml_path}'."
    )

    st.markdown("### Anteprima PDF")
    mostra_pdf(pdf_buffer, altezza=600)

    st.markdown("### Download file")
    st.download_button(
        "📥 Scarica PDF",
        data=pdf_buffer.getvalue(),
        file_name=f"{numero}.pdf",
        mime="application/pdf",
    )
    st.download_button(
        "📥 Scarica XML",
        data=xml_string.encode("utf-8"),
        file_name=f"{numero}.xml",
        mime="application/xml",
    )
