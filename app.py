import streamlit as st
import pandas as pd

st.set_page_config(page_title="Gestionale Fatture", layout="wide")

# ==============================
# STATO INIZIALE
# ==============================
if "page" not in st.session_state:
    st.session_state.page = "dashboard"

if "anagrafica" not in st.session_state:
    st.session_state.anagrafica = {
        "Ragione Sociale": "",
        "P.IVA": "",
        "CF": "",
        "Indirizzo": "",
        "CAP": "",
        "Comune": "",
        "Provincia": "",
        "PEC": "",
        "Codice Destinatario": ""
    }

# finto elenco documenti se vuoto (per vedere il layout)
if "documenti_emessi" not in st.session_state:
    st.session_state.documenti_emessi = pd.DataFrame([
        {
            "Anno": 2025,
            "Mese": "Novembre",
            "Id": "TD01 - FATTURA",
            "Data": "27/11/2025",
            "Cliente": "P.IVA/C.F.",
            "Importo": 0.00,
            "Esigibilita IVA": "IMMEDIATA",
            "Stato": "Creazione",
            "PDF": None,  # qui in futuro metteremo il path / bytes del pdf
        },
        {
            "Anno": 2025,
            "Mese": "Novembre",
            "Id": "TD01 - FATTURA 1",
            "Data": "21/11/2025",
            "Cliente": "valeria giangregorio\nP.IVA/C.F. IT06951770723\nCAUSALE SERVIZIO",
            "Importo": 500.00,
            "Esigibilita IVA": "IMMEDIATA",
            "Stato": "Creato",
            "PDF": None,
        },
    ])

# ==============================
# MENU IN ALTO A DESTRA (OPERATORE)
# ==============================
st.markdown("""
    <style>
        .top-right-menu {
            position: absolute;
            top: 15px;
            right: 20px;
            font-size: 16px;
        }
        .menu-item {
            cursor: pointer;
            color: #1f77b4;
            font-weight: 600;
        }
        .menu-item:hover {
            text-decoration: underline;
        }
    </style>
    <div class="top-right-menu">
        <span class="menu-item" onclick="window.location.href='?anagrafica'">
            Operatore ▾
        </span>
    </div>
""", unsafe_allow_html=True)

# ==============================
# GESTIONE PARAMETRI URL
# ==============================
query_params = st.query_params
if "anagrafica" in query_params:
    st.session_state.page = "anagrafica"

# ==============================
# PAGINA ANAGRAFICA
# ==============================
def pagina_anagrafica():
    st.title("📇 Anagrafica Azienda")

    for campo, valore in st.session_state.anagrafica.items():
        st.session_state.anagrafica[campo] = st.text_input(
            campo,
            value=valore,
        )

    if st.button("💾 Salva Anagrafica"):
        st.success("Anagrafica salvata correttamente!")

# ==============================
# PAGINA DASHBOARD DOCUMENTI
# ==============================
def dashboard():
    st.title("📄 Documenti emessi")

    df = st.session_state.documenti_emessi

    # barra superiore (anno + tab mesi come Effatta)
    col_anno, col_mese = st.columns([1, 3])
    with col_anno:
        anni = sorted(df["Anno"].unique())
        anno_sel = st.selectbox("Anno", anni, label_visibility="collapsed")
    with col_mese:
        mesi_ordine = [
            "Riepilogo", "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio",
            "Giugno", "Luglio", "Agosto", "Settembre", "Ottobre",
            "Novembre", "Dicembre"
        ]
        # per ora usiamo solo i mesi presenti nel df + Riepilogo
        mesi_presenti = ["Riepilogo"] + sorted(df["Mese"].unique().tolist())
        tabs = st.tabs(mesi_presenti)

    # tab riepilogo = mostro tutti i mesi dell'anno
    for i, mese in enumerate(mesi_presenti):
        with tabs[i]:
            if mese == "Riepilogo":
                df_mese = df[df["Anno"] == anno_sel]
            else:
                df_mese = df[(df["Anno"] == anno_sel) & (df["Mese"] == mese)]

            if df_mese.empty:
                st.info("Nessun documento per questo periodo.")
                continue

            # intestazione colonne come in Effatta
            st.markdown(
                """
                <div style="font-weight:600; margin-top:10px; margin-bottom:5px;
                            display:flex; flex-direction:row;">
                    <div style="flex:3;">Documento</div>
                    <div style="flex:4;">Inviato a</div>
                    <div style="flex:2; text-align:right;">Importo (EUR)</div>
                    <div style="flex:2; text-align:right;">Esigibilità IVA</div>
                    <div style="flex:2; text-align:right;">Stato</div>
                    <div style="flex:2; text-align:right;">Azioni</div>
                </div>
                <hr style="margin-top:0;">
                """,
                unsafe_allow_html=True,
            )

            # riga per riga con menu azioni
            for idx, row in df_mese.iterrows():
                c1, c2, c3, c4, c5, c6 = st.columns([3, 4, 2, 2, 2, 2])

                with c1:
                    st.markdown(
                        f"**{row['Id']}**  \n"
                        f"del {row['Data']}"
                    )

                with c2:
                    st.write(row["Cliente"])

                with c3:
                    st.markdown(
                        f"<div style='text-align:right;'>{row['Importo']:,.2f}</div>",
                        unsafe_allow_html=True,
                    )

                with c4:
                    st.markdown(
                        f"<div style='text-align:right;'>{row['Esigibilita IVA']}</div>",
                        unsafe_allow_html=True,
                    )

                with c5:
                    st.markdown(
                        f"<div style='text-align:right;'>"
                        f"<button style='background-color:#1f77b4;"
                        f"color:white;border:none;padding:3px 8px;"
                        f"border-radius:3px;font-size:12px;'>"
                        f"{row['Stato']}</button></div>",
                        unsafe_allow_html=True,
                    )

                with c6:
                    azioni = [
                        "—",
                        "Visualizza",
                        "Scarica PDF Fattura",
                        "Scarica PDF Proforma",
                        "Modifica",
                        "Elimina",
                        "Duplica",
                        "Invia",
                    ]
                    scelta = st.selectbox(
                        " ",
                        azioni,
                        key=f"azione_{idx}_{mese}",
                        label_visibility="collapsed",
                    )

                    # gestione azioni base (placeholder)
                    if scelta != "—":
                        if scelta == "Visualizza":
                            if row["PDF"] is not None:
                                st.info("Qui apriremo l’anteprima PDF (st.pdf).")
                            else:
                                st.warning("PDF non ancora disponibile.")
                        elif scelta == "Scarica PDF Fattura":
                            if row["PDF"] is not None:
                                st.info("Qui metteremo lo st.download_button per il PDF.")
                            else:
                                st.warning("PDF non ancora disponibile.")
                        elif scelta == "Modifica":
                            st.info("In futuro qui porteremo alla pagina di modifica.")
                        elif scelta == "Elimina":
                            st.warning("Funzione ELIMINA da implementare (con conferma).")
                        elif scelta == "Duplica":
                            st.info("Qui potremo duplicare il documento.")
                        elif scelta == "Invia":
                            st.info("Qui integreremo invio via SDI / e-mail.")

                st.markdown("<hr>", unsafe_allow_html=True)


# ==============================
# ROUTING
# ==============================
if st.session_state.page == "anagrafica":
    pagina_anagrafica()
else:
    dashboard()
