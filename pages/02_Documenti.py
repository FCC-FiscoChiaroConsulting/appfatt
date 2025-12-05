import streamlit as st
import pandas as pd
from datetime import date
import os
import re
import base64

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
# FUNZIONI UTILI
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
    """Genera il prossimo numero fattura stile FT<anno><progressivo a 3 cifre>."""
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
        "Anno",
        anni,
        index=idx_default,
        key="anno_riepilogo_emesse",
    )

    df_anno = df[df["Data"].dt.year == anno_sel]

    mesi_label = [
        "Gennaio", "Febbraio", "Marzo", "Aprile",
        "Maggio", "Giugno", "Luglio", "Agosto",
        "Settembre", "Ottobre", "Novembre", "Dicembre",
    ]

    rows = []

    # Mensili
    for m in range(1, 13):
        df_m = df_anno[df_anno["Data"].dt.month == m]
        imp_tot = df_m["Importo"].sum()
        imp_imp = df_m["Imponibile"].sum()
        iva_tot = df_m["IVA"].sum()
        rows.append(
            {
                "Periodo": mesi_label[m - 1],
                "Importo a pagare": _format_val_eur(imp_tot),
                "Imponibile": _format_val_eur(imp_imp),
                "IVA": _format_val_eur(iva_tot),
            }
        )

    # Trimestri
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
        rows.append(
            {
                "Periodo": nome,
                "Importo a pagare": _format_val_eur(imp_tot),
                "Imponibile": _format_val_eur(imp_imp),
                "IVA": _format_val_eur(iva_tot),
            }
        )

    # Annuale
    imp_tot = df_anno["Importo"].sum()
    imp_imp = df_anno["Imponibile"].sum()
    iva_tot = df_anno["IVA"].sum()
    rows.append(
        {
            "Periodo": "Annuale",
            "Importo a pagare": _format_val_eur(imp_tot),
            "Imponibile": _format_val_eur(imp_imp),
            "IVA": _format_val_eur(iva_tot),
        }
    )

    df_riep = pd.DataFrame(rows)
    st.markdown("### Prospetto riepilogativo fatture emesse")
    st.dataframe(df_riep, use_container_width=True, hide_index=True)


# ==========================
# HEADER
# ==========================
st.set_page_config(
    page_title="Documenti - Fatture Emesse",
    page_icon="📄",
    layout="wide",
)

col_logo, col_menu, col_user = st.columns([2, 5, 1])
with col_logo:
    st.markdown(
        f"<h1 style='color:{PRIMARY_BLUE};margin-bottom:0'>FISCO CHIARO CONSULTING</h1>",
        unsafe_allow_html=True,
    )
with col_menu:
    st.markdown("#### Documenti | Clienti | Dashboard")
with col_user:
    st.markdown("Operatore")

st.markdown("---")
st.subheader("Lista documenti / Fatture emesse")

# Bottone Nuova fattura
col_nuova, _ = st.columns([1, 5])
with col_nuova:
    if st.button("➕ Nuova fattura"):
        st.switch_page("03_Fattura.py")

# ==========================
# CONTATORI PER MESE
# ==========================
docs_per_month = {m: 0 for m in range(1, 13)}
df_tmp = st.session_state.documenti_emessi.copy()
if not df_tmp.empty:
    df_tmp["Data"] = pd.to_datetime(df_tmp["Data"], errors="coerce")
    for m in range(1, 13):
        docs_per_month[m] = (df_tmp["Data"].dt.month == m).sum()

# ==========================
# BARRA SUPERIORE TIPO EFFATTA
# ==========================
col_search, col_stato, col_emesse, col_ricevute, col_agg = st.columns(
    [4, 1, 1, 1, 1]
)
with col_search:
    barra_ricerca = st.text_input(
        " ",
        placeholder="Id fiscale, denominazione, causale, tag",
        label_visibility="collapsed",
    )
with col_stato:
    if st.button("STATO"):
        st.switch_page("app.py")
with col_emesse:
    st.button("EMESSE")  # siamo su EMESSE
with col_ricevute:
    if st.button("RICEVUTE"):
        st.info("Sezione RICEVUTE non ancora implementata.")
with col_agg:
    st.button("AGGIORNA")

nomi_mesi = [
    "Gennaio", "Febbraio", "Marzo", "Aprile",
    "Maggio", "Giugno", "Luglio", "Agosto",
    "Settembre", "Ottobre", "Novembre", "Dicembre",
]

mesi = ["Riepilogo"]
for m, nome in enumerate(nomi_mesi, start=1):
    n_doc = docs_per_month.get(m, 0)
    if n_doc > 0:
        mesi.append(f"{nome} ({n_doc})")
    else:
        mesi.append(nome)

tabs = st.tabs(mesi)
idx_mese = date.today().month

# ==========================
# LISTA EMESSE
# ==========================
df_e_all = st.session_state.documenti_emessi.copy()

# selettore anno (sopra i tab)
if not df_e_all.empty:
    df_e_all["Data"] = pd.to_datetime(df_e_all["Data"], errors="coerce")
    anni = sorted(df_e_all["Data"].dt.year.dropna().unique())
else:
    anni = []

if anni:
    anno_default = date.today().year
    if anno_default not in anni:
        anno_default = anni[-1]
    idx_anno_default = list(anni).index(anno_default)
    col_anno, _ = st.columns([1, 5])
    with col_anno:
        anno_sel = st.selectbox(
            "Anno",
            anni,
            index=idx_anno_default,
            key="anno_lista",
        )
    df_e_all = df_e_all[df_e_all["Data"].dt.year == anno_sel]

if df_e_all.empty:
    st.info("Nessun documento emesso per l'anno selezionato.")
else:
    # Tab Riepilogo
    with tabs[0]:
        crea_riepilogo_fatture_emesse(df_e_all)

    # Tab mese corrente
    with tabs[idx_mese]:
        df_e = df_e_all.copy()
        df_e = df_e[df_e["Data"].dt.month == idx_mese]

        if barra_ricerca:
            mask = (
                df_e["Numero"]
                .astype(str)
                .str.contains(barra_ricerca, case=False, na=False)
                | df_e["Controparte"]
                .astype(str)
                .str.contains(barra_ricerca, case=False, na=False)
            )
            df_e = df_e[mask]

        if df_e.empty:
            st.info("Nessun documento emesso per il mese selezionato.")
        else:
            st.caption("Elenco fatture emesse (vista tipo Effatta)")
            df_e = df_e.sort_values("Data", ascending=False)

            for _, row in df_e.iterrows():
                row_index = row.name
                data_doc = pd.to_datetime(row["Data"])
                tipo_xml = (row.get("TipoXML", "") or "TD01").upper()
                tipo_label = f"{tipo_xml} - FATTURA"

                importo = float(row.get("Importo", 0.0) or 0.0)
                controparte = row.get("Controparte", "")
                stato_corrente = row.get("Stato", "Creazione") or "Creazione"
                pdf_path = row.get("PDF", "")

                # Recupero P.IVA / CF da rubrica
                piva_cf = ""
                cli_df = st.session_state.clienti[
                    st.session_state.clienti["Denominazione"] == controparte
                ]
                if not cli_df.empty:
                    cli_row = cli_df.iloc[0]
                    piva_val = (cli_row.get("PIVA") or "").strip()
                    cf_val = (cli_row.get("CF") or "").strip()
                    if piva_val:
                        piva_cf = piva_val
                    elif cf_val:
                        piva_cf = cf_val

                with st.container():
                    st.markdown("---")
                    col_icon, col_info, col_imp, col_stato, col_menu = st.columns(
                        [0.6, 4, 1.6, 1.4, 1.8]
                    )

                    # ICONA
                    with col_icon:
                        if tipo_xml == "TD01" and piva_cf:
                            st.markdown("🟥 **B2B**")
                        else:
                            st.markdown("📄")

                    # BLOCCO CENTRALE
                    with col_info:
                        info_lines = []
                        info_lines.append(f"**{tipo_label}**")
                        info_lines.append(
                            f"{row['Numero']} del {data_doc.strftime('%d/%m/%Y')}"
                        )
                        info_lines.append("")
                        info_lines.append("**INVIATO A**")
                        info_lines.append(controparte)
                        if piva_cf:
                            info_lines.append(f"P.IVA/C.F. {piva_cf}")
                        info_lines.append("CAUSALE")
                        info_lines.append("SERVIZIO")
                        st.markdown("  \n".join(info_lines))

                    # IMPORTO + ESIGIBILITÀ
                    with col_imp:
                        st.markdown("**IMPORTO (EUR)**")
                        st.markdown(_format_val_eur(importo))
                        st.markdown("**ESIGIBILITÀ IVA**")
                        st.markdown("IMMEDIATA")

                    # STATO
                    with col_stato:
                        st.markdown("**Stato**")
                        possibili_stati = ["Creazione", "Creato", "Inviato"]
                        if stato_corrente not in possibili_stati:
                            stato_corrente = "Creazione"
                        new_stato = st.selectbox(
                            "",
                            possibili_stati,
                            index=possibili_stati.index(stato_corrente),
                            key=f"stato_{row_index}",
                            label_visibility="collapsed",
                        )
                        st.session_state.documenti_emessi.loc[
                            row_index, "Stato"
                        ] = new_stato

                    # MENU AZIONI
                    with col_menu:
                        st.markdown("**Azioni**")
                        with st.popover("▼", use_container_width=True):
                            st.markdown("**Seleziona azione**")

                            # Visualizza
                            if st.button("👁 Visualizza", key=f"vis_{row_index}"):
                                if pdf_path and os.path.exists(pdf_path):
                                    with open(pdf_path, "rb") as f:
                                        pdf_bytes = f.read()
                                    st.markdown("Anteprima PDF:")
                                    mostra_anteprima_pdf(pdf_bytes, altezza=400)
                                else:
                                    st.warning("PDF non disponibile su disco.")

                            # Scarica pacchetto (placeholder)
                            if st.button(
                                "📦 Scarica pacchetto", key=f"pac_{row_index}"
                            ):
                                st.info(
                                    "Funzione 'Scarica pacchetto' non ancora implementata."
                                )

                            # Scarica PDF fattura
                            if st.button(
                                "📄 Scarica PDF fattura", key=f"fatt_{row_index}"
                            ):
                                if pdf_path and os.path.exists(pdf_path):
                                    with open(pdf_path, "rb") as f:
                                        pdf_bytes = f.read()
                                    st.download_button(
                                        "📥 Download PDF",
                                        data=pdf_bytes,
                                        file_name=os.path.basename(pdf_path),
                                        mime="application/pdf",
                                        key=f"dl_{row_index}",
                                    )
                                else:
                                    st.warning("PDF non disponibile su disco.")

                            # Scarica PDF proforma (placeholder)
                            if st.button(
                                "📑 Scarica PDF proforma", key=f"prof_{row_index}"
                            ):
                                st.info(
                                    "Funzione 'PDF proforma' non ancora implementata."
                                )

                            # Modifica (placeholder)
                            if st.button("✏️ Modifica", key=f"mod_{row_index}"):
                                st.info(
                                    "Funzione modifica non ancora implementata in questa versione."
                                )

                            # Duplica
                            if st.button("🧬 Duplica", key=f"dup_{row_index}"):
                                nuovo_num = get_next_invoice_number()
                                nuova_riga = row.copy()
                                nuova_riga["Numero"] = nuovo_num
                                nuova_riga["Data"] = str(date.today())
                                st.session_state.documenti_emessi = pd.concat(
                                    [
                                        st.session_state.documenti_emessi,
                                        pd.DataFrame([nuova_riga]),
                                    ],
                                    ignore_index=True,
                                )
                                st.success(f"Fattura duplicata come {nuovo_num}.")
                                st.rerun()

                            # Elimina
                            if st.button("🗑 Elimina", key=f"del_{row_index}"):
                                st.session_state.documenti_emessi = (
                                    st.session_state.documenti_emessi
                                    .drop(row_index)
                                    .reset_index(drop=True)
                                )
                                st.warning("Fattura eliminata.")
                                st.rerun()

                            # Invia (placeholder)
                            if st.button("📨 Invia", key=f"inv_{row_index}"):
                                st.info(
                                    "Funzione invio a SdI non ancora implementata."
                                )

# ==========================
# DOWNLOAD VELOCE PDF
# ==========================
st.markdown("### 📄 Download rapido PDF fatture emesse")
df_e = st.session_state.documenti_emessi
if df_e.empty:
    st.caption("Nessuna fattura emessa salvata nell'app.")
else:
    df_e_pdf = df_e[df_e["PDF"] != ""]
    if df_e_pdf.empty:
        st.caption("Le fatture emesse non hanno ancora PDF associati.")
    else:
        numeri = df_e_pdf["Numero"].tolist()
        scelta_num = st.selectbox("Seleziona fattura emessa", numeri)
        if scelta_num:
            riga = df_e_pdf[df_e_pdf["Numero"] == scelta_num].iloc[0]
            pdf_path = riga["PDF"]
            if os.path.exists(pdf_path):
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()
                st.download_button(
                    label=f"📥 Scarica PDF fattura {scelta_num}",
                    data=pdf_bytes,
                    file_name=os.path.basename(pdf_path),
                    mime="application/pdf",
                )
                st.markdown("#### Anteprima PDF")
                mostra_anteprima_pdf(pdf_bytes, altezza=500)
            else:
                st.warning("Il file PDF indicato non esiste più sul disco.")

st.markdown("---")
st.caption(
    "Fisco Chiaro Consulting – Fatture emesse gestite dall'app, PDF caricati/associati."
)
