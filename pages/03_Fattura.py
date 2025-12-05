import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
from datetime import date, datetime
import os
import uuid
import base64
import pandas as pd

# ==========================
# CONFIGURAZIONE AZIENDA (fissa)
# ==========================
AZIENDA = {
    "nome": "GLOBAL BUSINESS SRL",
    "indirizzo": "VIA CARULLI 90",
    "cap": "70121",
    "citta": "BARI",
    "prov": "BA",
    "cf": "07707940727",
    "piva": "07707940727",
}

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


# ==========================
# FUNZIONI DI SUPPORTO
# ==========================
def get_next_invoice_number() -> str:
    """Genera il prossimo numero fattura in formato FT<anno><progressivo a 3 cifre>."""
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
# GENERAZIONE PDF
# ==========================
def genera_pdf_fattura(dati):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    x_left = 30
    x_right = 410
    y = 800

    # INTESTAZIONE AZIENDA
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_left, y, dati["azienda_nome"])

    c.setFont("Helvetica", 10)
    c.drawString(x_left, y - 15, dati["azienda_indirizzo"])
    c.drawString(
        x_left,
        y - 30,
        f"{dati['azienda_cap']} {dati['azienda_citta']} ({dati['azienda_prov']}) IT",
    )
    c.drawString(x_left, y - 45, f"CODICE FISCALE {dati['azienda_cf']}")
    c.drawString(x_left, y - 60, f"PARTITA IVA {dati['azienda_piva']}")

    # INTESTAZIONE CLIENTE
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(565, y, "Spett.le")
    c.drawRightString(565, y - 15, dati["cliente_nome"])

    c.setFont("Helvetica", 10)
    c.drawRightString(565, y - 30, dati["cliente_indirizzo"])
    c.drawRightString(
        565,
        y - 45,
        f"{dati['cliente_cap']} {dati['cliente_citta']} ({dati['cliente_prov']}) IT",
    )
    if dati["cliente_piva"]:
        c.drawRightString(565, y - 60, f"PARTITA IVA {dati['cliente_piva']}")
    else:
        c.drawRightString(565, y - 60, f"CODICE FISCALE {dati['cliente_cf']}")

    # DATI DOCUMENTO
    y = 700
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "DATI DOCUMENTO")
    c.line(x_left, y - 2, 565, y - 2)

    c.setFont("Helvetica", 10)
    c.drawString(x_left, y - 20, "TIPO")
    c.drawString(x_left + 120, y - 20, dati["tipo_documento"])

    c.drawString(x_left, y - 40, "NUMERO")
    c.drawString(x_left + 120, y - 40, str(dati["numero"]))

    c.drawString(x_left, y - 60, "DATA")
    c.drawString(x_left + 120, y - 60, dati["data"])

    c.drawString(x_left, y - 80, "CAUSALE")
    c.drawString(x_left + 120, y - 80, dati["causale"])

    # DATI TRASMISSIONE
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_right, y, "DATI TRASMISSIONE")
    c.line(x_right, y - 2, 565, y - 2)

    c.setFont("Helvetica", 10)
    c.drawString(x_right, y - 20, "CODICE DESTINATARIO")
    c.drawString(x_right + 140, y - 20, dati["codice_destinatario"])

    c.drawString(x_right, y - 40, "PEC DESTINATARIO")
    c.drawString(x_right + 140, y - 40, dati["pec_destinatario"])

    # DETTAGLIO DOCUMENTO
    y = 560
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "DETTAGLIO DOCUMENTO")
    c.line(x_left, y - 2, 565, y - 2)

    c.setFont("Helvetica-Bold", 10)
    y -= 20
    c.drawString(x_left, y, "#")
    c.drawString(x_left + 20, y, "DESCRIZIONE")
    c.drawString(x_left + 260, y, "PREZZO")
    c.drawString(x_left + 330, y, "QTA")
    c.drawString(x_left + 380, y, "TOTALE")
    c.drawString(x_left + 450, y, "IVA %")

    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(x_left, y, "1")
    c.drawString(x_left + 20, y, dati["descrizione"])
    c.drawString(x_left + 260, y, dati["prezzo_unitario"])
    c.drawString(x_left + 330, y, "1,00")
    c.drawString(x_left + 380, y, dati["imponibile"])
    c.drawString(x_left + 450, y, dati["iva_percentuale"])

    # RIEPILOGO IMPORTI
    y -= 60
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_left, y, f"IMPORTO = {dati['imponibile']}")
    y -= 15
    c.drawString(x_left, y, f"TOTALE IMPONIBILE = {dati['imponibile']}")
    y -= 15
    c.drawString(
        x_left, y, f"IVA (SU € {dati['imponibile']}) + {dati['iva_valore']}"
    )
    y -= 15
    c.drawString(x_left, y, f"IMPORTO TOTALE = {dati['totale']}")
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.blue)
    c.drawString(x_left, y, f"NETTO A PAGARE = {dati['totale']}")
    c.setFillColor(colors.black)

    # NOTA FINALE
    c.setFont("Helvetica", 8)
    c.drawString(
        100,
        50,
        "Copia di cortesia priva di valore ai fini fiscali e giuridici - Art. 21 DPR 633/72",
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
        <ModalitaPagamento>MP05</ModalitaPagamento>
        <ImportoPagamento>{dati['totale_num']:.2f}</ImportoPagamento>
      </DettaglioPagamento>
    </DatiPagamento>
  </FatturaElettronicaBody>
</p:FatturaElettronica>
"""
    return xml


# ==========================
# SALVATAGGIO SU DISCO
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
        [
            st.session_state.documenti_emessi,
            pd.DataFrame([nuova_riga]),
        ],
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

st.title("Nuova fattura")

col_header1, col_header2 = st.columns([3, 1])
with col_header1:
    st.caption("Creazione fattura PDF di cortesia + XML SdI (bozza)")
with col_header2:
    if st.button("⬅ Torna a Documenti"):
        st.switch_page("02_Documenti.py")

numero_default = get_next_invoice_number()
data_default = date.today()

with st.form("form_fattura"):
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

    st.subheader("Dati documento")
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

    st.markdown("---")
    st.subheader("Dati trasmissione")
    codice_destinatario = st.text_input("Codice destinatario", "0000000")
    pec_destinatario = st.text_input("PEC destinatario (se B2C/B2B via PEC)", "")

    submitted = st.form_submit_button("💾 Salva fattura e genera PDF + XML")

if submitted:
    data_str = data_doc.strftime("%d/%m/%Y")

    dati = {
        "azienda_nome": AZIENDA["nome"],
        "azienda_indirizzo": AZIENDA["indirizzo"],
        "azienda_cap": AZIENDA["cap"],
        "azienda_citta": AZIENDA["citta"],
        "azienda_prov": AZIENDA["prov"],
        "azienda_cf": AZIENDA["cf"],
        "azienda_piva": AZIENDA["piva"],
        "cliente_nome": cliente_nome,
        "cliente_indirizzo": cliente_indirizzo,
        "cliente_cap": cliente_cap,
        "cliente_citta": cliente_citta,
        "cliente_prov": cliente_prov,
        "cliente_piva": cliente_piva,
        "cliente_cf": cliente_cf,
        "tipo_documento": "TD01 FATTURA - B2B" if cliente_piva else "TD01 FATTURA - B2C",
        "numero": numero,
        "data": data_str,
        "causale": causale,
        "codice_destinatario": codice_destinatario,
        "pec_destinatario": pec_destinatario,
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
