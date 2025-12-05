import streamlit as st
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from io import BytesIO
import base64

# ------------------------------------------
# FUNZIONE PER GENERARE IL PDF
# ------------------------------------------
def genera_pdf_fattura(dati):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    # Margini
    x_left = 30
    x_right = 410
    y = 800

    # --------------------------
    # INTESTAZIONE AZIENDA
    # --------------------------
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x_left, y, dati["azienda_nome"])

    c.setFont("Helvetica", 10)
    c.drawString(x_left, y-15, dati["azienda_indirizzo"])
    c.drawString(x_left, y-30, f"{dati['azienda_cap']} {dati['azienda_citta']} ({dati['azienda_prov']}) IT")
    c.drawString(x_left, y-45, f"CODICE FISCALE {dati['azienda_cf']}")
    c.drawString(x_left, y-60, f"PARTITA IVA {dati['azienda_piva']}")

    # --------------------------
    # INTESTAZIONE CLIENTE
    # --------------------------
    c.setFont("Helvetica-Bold", 12)
    c.drawRightString(565, y, "Spett.le")
    c.drawRightString(565, y-15, dati["cliente_nome"])

    c.setFont("Helvetica", 10)
    c.drawRightString(565, y-30, dati["cliente_indirizzo"])
    c.drawRightString(565, y-45, f"{dati['cliente_cap']} {dati['cliente_citta']} ({dati['cliente_prov']}) IT")
    c.drawRightString(565, y-60, f"PARTITA IVA {dati['cliente_piva']}")

    # --------------------------
    # DATI DOCUMENTO
    # --------------------------
    y = 700
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "DATI DOCUMENTO")
    c.line(x_left, y-2, 565, y-2)

    c.setFont("Helvetica", 10)
    c.drawString(x_left, y-20, "TIPO")
    c.drawString(x_left+120, y-20, dati["tipo_documento"])

    c.drawString(x_left, y-40, "NUMERO")
    c.drawString(x_left+120, y-40, str(dati["numero"]))

    c.drawString(x_left, y-60, "DATA")
    c.drawString(x_left+120, y-60, dati["data"])

    c.drawString(x_left, y-80, "CAUSALE")
    c.drawString(x_left+120, y-80, dati["causale"])

    # --------------------------
    # DATI TRASMISSIONE
    # --------------------------
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_right, y, "DATI TRASMISSIONE")
    c.line(x_right, y-2, 565, y-2)

    c.setFont("Helvetica", 10)
    c.drawString(x_right, y-20, "CODICE DESTINATARIO")
    c.drawString(x_right+140, y-20, dati["codice_destinatario"])

    c.drawString(x_right, y-40, "PEC DESTINATARIO")
    c.drawString(x_right+140, y-40, dati["pec_destinatario"])

    # --------------------------
    # DETTAGLIO FATTURA
    # --------------------------
    y = 560
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "DETTAGLIO DOCUMENTO")
    c.line(x_left, y-2, 565, y-2)

    c.setFont("Helvetica-Bold", 10)
    y -= 20
    c.drawString(x_left, y, "#")
    c.drawString(x_left+20, y, "DESCRIZIONE")
    c.drawString(x_left+260, y, "PREZZO")
    c.drawString(x_left+330, y, "QTA")
    c.drawString(x_left+380, y, "TOTALE")
    c.drawString(x_left+450, y, "IVA %")

    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(x_left, y, "1")
    c.drawString(x_left+20, y, dati["descrizione"])
    c.drawString(x_left+260, y, str(dati["prezzo_unitario"]))
    c.drawString(x_left+330, y, "1,00")
    c.drawString(x_left+380, y, str(dati["imponibile"]))
    c.drawString(x_left+450, y, str(dati["iva_percentuale"]))

    # --------------------------
    # RIEPILOGO
    # --------------------------
    y -= 60
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x_left, y, f"IMPORTO = {dati['imponibile']}")
    y -= 15
    c.drawString(x_left, y, f"TOTALE IMPONIBILE = {dati['imponibile']}")
    y -= 15
    c.drawString(x_left, y, f"IVA (SU € {dati['imponibile']}) + {dati['iva_valore']}")
    y -= 15
    c.drawString(x_left, y, f"IMPORTO TOTALE = {dati['totale']}")

    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(colors.blue)
    c.drawString(x_left, y, f"NETTO A PAGARE = {dati['totale']}")
    c.setFillColor(colors.black)

    # Nota finale
    c.setFont("Helvetica", 8)
    c.drawString(
        100, 50,
        "Copia di cortesia priva di valore ai fini fiscali - Art. 21 DPR 633/72"
    )

    c.save()
    buffer.seek(0)
    return buffer


# ------------------------------------------
# FUNZIONE PER MOSTRARE IL PDF IN STREAMLIT
# ------------------------------------------
def mostra_pdf(buffer):
    pdf_bytes = buffer.getvalue()
    b64 = base64.b64encode(pdf_bytes).decode()
    pdf_display = f"""
        <iframe width="100%" height="600"
        src="data:application/pdf;base64,{b64}" type="application/pdf"></iframe>
    """
    st.markdown(pdf_display, unsafe_allow_html=True)


# ------------------------------------------
# STREAMLIT – PAGINA DI TEST
# ------------------------------------------
st.title("Anteprima generatore fattura PDF")

# Dati esempio
dati = {
    "azienda_nome": "GLOBAL BUSINESS SRL",
    "azienda_indirizzo": "VIA CARULLI 90",
    "azienda_cap": "70121",
    "azienda_citta": "BARI",
    "azienda_prov": "BA",
    "azienda_cf": "07707940727",
    "azienda_piva": "07707940727",

    "cliente_nome": "giangregorio valeria",
    "cliente_indirizzo": "VIA FAENZA 159",
    "cliente_cap": "70019",
    "cliente_citta": "TRIGGIANO",
    "cliente_prov": "BA",
    "cliente_piva": "06951770723",

    "tipo_documento": "TD01 FATTURA - B2B",
    "numero": 1,
    "data": "21/11/2025",
    "causale": "SERVIZIO",

    "codice_destinatario": "0000000",
    "pec_destinatario": "",

    "descrizione": "servizio",
    "prezzo_unitario": "409,83606557",
    "imponibile": "409,84",
    "iva_percentuale": "22,00",
    "iva_valore": "90,16",
    "totale": "500,00"
}

pdf_buffer = genera_pdf_fattura(dati)

st.subheader("Download PDF")
st.download_button("Scarica PDF", data=pdf_buffer.getvalue(), file_name="fattura.pdf")

st.subheader("Anteprima PDF")
mostra_pdf(pdf_buffer)
