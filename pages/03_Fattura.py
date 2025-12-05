import os
import io
from datetime import date

import pandas as pd
import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# -------------------------------------------------
# CONFIGURAZIONE PAGINA
# -------------------------------------------------
st.set_page_config(
    page_title="Crea nuova fattura emessa",
    page_icon="📄",
    layout="wide",
)

st.title("📄 Crea nuova fattura emessa")

DATA_DIR = "data"
CLIENTI_CSV = os.path.join(DATA_DIR, "clienti.csv")
FATTURE_CSV = os.path.join(DATA_DIR, "fatture.csv")
PDF_DIR = os.path.join(DATA_DIR, "fatture_pdf")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PDF_DIR, exist_ok=True)


# -------------------------------------------------
# FUNZIONI DI UTILITÀ
# -------------------------------------------------
def load_csv(path: str, columns: list) -> pd.DataFrame:
    """Carica un CSV se esiste, altrimenti crea un DataFrame vuoto con le colonne indicate."""
    if os.path.exists(path):
        df = pd.read_csv(path, dtype=str)
        # Garantisce tutte le colonne previste
        for c in columns:
            if c not in df.columns:
                df[c] = ""
        return df[columns]
    else:
        return pd.DataFrame(columns=columns)


def save_csv(df: pd.DataFrame, path: str) -> None:
    df.to_csv(path, index=False)


def next_invoice_number(fatture_df: pd.DataFrame) -> int:
    """Calcola il prossimo numero fattura (intero progressivo)."""
    if fatture_df.empty:
        return 1
    try:
        numeri = pd.to_numeric(fatture_df["numero_fattura"], errors="coerce").dropna()
        if numeri.empty:
            return 1
        return int(numeri.max()) + 1
    except Exception:
        # fallback se qualcosa è andato storto
        return 1


def genera_pdf_fattura(
    numero_fattura: str,
    data_fattura: date,
    cliente: dict,
    descrizione: str,
    imponibile: float,
    aliquota_iva: float,
    bollo: float,
    metodo_pagamento: str,
) -> (bytes, str):
    """
    Genera il PDF della fattura e restituisce:
    - bytes del PDF
    - nome file suggerito
    """
    iva = round(imponibile * aliquota_iva / 100, 2)
    totale = round(imponibile + iva + bollo, 2)

    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    larghezza, altezza = A4

    # Margini semplici
    x_margin = 40
    y_margin = 40

    # Intestazione
    c.setFont("Helvetica-Bold", 16)
    c.drawString(x_margin, altezza - y_margin, f"FATTURA N. {numero_fattura}")

    c.setFont("Helvetica", 10)
    c.drawString(
        x_margin,
        altezza - y_margin - 20,
        f"Data: {data_fattura.strftime('%d/%m/%Y')}",
    )

    # Dati cliente
    y = altezza - y_margin - 60
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y, "Cliente:")
    c.setFont("Helvetica", 10)
    y -= 15
    c.drawString(x_margin, y, cliente.get("ragione_sociale", ""))
    y -= 15
    c.drawString(x_margin, y, cliente.get("indirizzo", ""))
    y -= 15
    c.drawString(
        x_margin,
        y,
        f"{cliente.get('cap', '')} {cliente.get('citta', '')} ({cliente.get('provincia', '')})",
    )
    y -= 15
    piva_cf = cliente.get("piva_cf", "")
    if piva_cf:
        c.drawString(x_margin, y, f"P.IVA / C.F.: {piva_cf}")
        y -= 15

    # Descrizione
    y -= 15
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y, "Descrizione:")
    y -= 15
    c.setFont("Helvetica", 10)
    for line in descrizione.split("\n"):
        c.drawString(x_margin, y, line)
        y -= 14

    # Riepilogo economico
    y -= 20
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y, "Riepilogo:")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, f"Imponibile: € {imponibile:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 14
    c.drawString(x_margin, y, f"IVA {aliquota_iva:.0f}%: € {iva:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 14
    c.drawString(x_margin, y, f"Bollo: € {bollo:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    y -= 14
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y, f"Totale: € {totale:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))

    # Metodo di pagamento
    y -= 30
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_margin, y, "Metodo di pagamento:")
    y -= 18
    c.setFont("Helvetica", 10)
    c.drawString(x_margin, y, metodo_pagamento)

    c.showPage()
    c.save()

    pdf_bytes = buffer.getvalue()
    buffer.close()

    # nome file
    base_cliente = cliente.get("ragione_sociale", "cliente").replace(" ", "_")
    filename = f"FATTURA_{numero_fattura}_{base_cliente}.pdf"

    return pdf_bytes, filename


# -------------------------------------------------
# CARICAMENTO DATI
# -------------------------------------------------
clienti_columns = [
    "ragione_sociale",
    "piva_cf",
    "indirizzo",
    "cap",
    "citta",
    "provincia",
    "email",
    "pec",
    "codice_destinatario",
]

fatture_columns = [
    "numero_fattura",
    "data_fattura",
    "ragione_sociale",
    "piva_cf",
    "imponibile",
    "aliquota_iva",
    "bollo",
    "totale",
    "metodo_pagamento",
    "pdf_file",
]

df_clienti = load_csv(CLIENTI_CSV, clienti_columns)
df_fatture = load_csv(FATTURE_CSV, fatture_columns)

prossimo_numero = next_invoice_number(df_fatture)

# -------------------------------------------------
# FORM FATTURA
# -------------------------------------------------
with st.form("form_fattura"):
    st.subheader("Dati cliente")

    elenco_clienti = ["NUOVO"] + df_clienti["ragione_sociale"].dropna().tolist()
    scelta_cliente = st.selectbox("Cliente", elenco_clienti, index=0)

    nuovo_cliente = False
    cliente_data = {}

    if scelta_cliente == "NUOVO":
        nuovo_cliente = True
        col1, col2 = st.columns(2)
        with col1:
            ragione_sociale = st.text_input("Ragione sociale / Nome e cognome *")
            piva_cf = st.text_input("P.IVA / Codice fiscale *")
            indirizzo = st.text_input("Indirizzo", "")
            cap = st.text_input("CAP", "")
        with col2:
            citta = st.text_input("Città", "")
            provincia = st.text_input("Provincia (es. MI)", "")
            email = st.text_input("Email", "")
            pec = st.text_input("PEC", "")
            codice_destinatario = st.text_input("Codice destinatario / PEC", "")
    else:
        # Recupero cliente esistente
        row = df_clienti[df_clienti["ragione_sociale"] == scelta_cliente].iloc[0]
        cliente_data = row.to_dict()
        st.write(f"**P.IVA / C.F.**: {cliente_data.get('piva_cf', '')}")
        st.write(
            f"**Indirizzo**: {cliente_data.get('indirizzo', '')}, "
            f"{cliente_data.get('cap', '')} {cliente_data.get('citta', '')} "
            f"({cliente_data.get('provincia', '')})"
        )
        st.write(f"**Email**: {cliente_data.get('email', '')}")
        st.write(f"**PEC**: {cliente_data.get('pec', '')}")
        st.write(f"**Codice destinatario**: {cliente_data.get('codice_destinatario', '')}")

    st.markdown("---")
    st.subheader("Dati fattura")

    col1, col2, col3 = st.columns(3)
    with col1:
        numero_fattura = st.number_input(
            "Numero fattura",
            min_value=1,
            value=prossimo_numero,
            step=1,
        )
    with col2:
        data_fattura = st.date_input("Data fattura", value=date.today())
    with col3:
        aliquota_iva = st.selectbox("Aliquota IVA", [0.0, 5.0, 10.0, 22.0], index=3)

    descrizione = st.text_area("Descrizione operazione", height=120)

    col4, col5 = st.columns(2)
    with col4:
        imponibile = st.number_input(
            "Imponibile (€)",
            min_value=0.0,
            step=10.0,
            format="%.2f",
        )
    with col5:
        applica_bollo = st.checkbox("Applica bollo (2,00 € se dovuto)")
        bollo = 2.0 if applica_bollo else 0.0

    metodo_pagamento = st.text_input(
        "Metodo di pagamento / IBAN",
        value="Bonifico bancario",
    )

    submitted = st.form_submit_button("💾 Salva fattura e genera PDF")

# -------------------------------------------------
# ELABORAZIONE FORM
# -------------------------------------------------
if submitted:
    # Validazioni minime
    if scelta_cliente == "NUOVO":
        if not ragione_sociale or not piva_cf:
            st.error("Per il nuovo cliente sono obbligatori: ragione sociale e P.IVA/C.F.")
            st.stop()
        cliente_data = {
            "ragione_sociale": ragione_sociale,
            "piva_cf": piva_cf,
            "indirizzo": indirizzo,
            "cap": cap,
            "citta": citta,
            "provincia": provincia,
            "email": email,
            "pec": pec,
            "codice_destinatario": codice_destinatario,
        }

        # Salvo il nuovo cliente
        df_clienti = pd.concat(
            [df_clienti, pd.DataFrame([cliente_data])],
            ignore_index=True,
        )
        save_csv(df_clienti, CLIENTI_CSV)

    if imponibile <= 0:
        st.error("Inserisci un imponibile maggiore di zero.")
        st.stop()

    # Calcoli economici
    iva = round(imponibile * aliquota_iva / 100, 2)
    totale = round(imponibile + iva + bollo, 2)

    # Generazione PDF
    pdf_bytes, pdf_filename = genera_pdf_fattura(
        numero_fattura=str(int(numero_fattura)),
        data_fattura=data_fattura,
        cliente=cliente_data,
        descrizione=descrizione,
        imponibile=imponibile,
        aliquota_iva=aliquota_iva,
        bollo=bollo,
        metodo_pagamento=metodo_pagamento,
    )

    # Salvo PDF su disco
    pdf_path = os.path.join(PDF_DIR, pdf_filename)
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    # Salvo riga fattura
    nuova_fattura = {
        "numero_fattura": int(numero_fattura),
        "data_fattura": data_fattura.strftime("%Y-%m-%d"),
        "ragione_sociale": cliente_data.get("ragione_sociale", ""),
        "piva_cf": cliente_data.get("piva_cf", ""),
        "imponibile": f"{imponibile:.2f}",
        "aliquota_iva": f"{aliquota_iva:.2f}",
        "bollo": f"{bollo:.2f}",
        "totale": f"{totale:.2f}",
        "metodo_pagamento": metodo_pagamento,
        "pdf_file": pdf_path,
    }

    df_fatture = pd.concat(
        [df_fatture, pd.DataFrame([nuova_fattura])],
        ignore_index=True,
    )
    save_csv(df_fatture, FATTURE_CSV)

    st.success("✅ Fattura salvata e PDF generato correttamente.")

    # Bottone per scaricare il PDF
    st.download_button(
        label="⬇️ Scarica PDF fattura",
        data=pdf_bytes,
        file_name=pdf_filename,
        mime="application/pdf",
    )

    st.info("Puoi creare una nuova fattura cliccando sul pulsante qui sotto.")

    if st.button("➕ Crea nuova fattura"):
        # QUI LA VERSIONE CORRETTA: niente experimental_rerun
        st.rerun()
