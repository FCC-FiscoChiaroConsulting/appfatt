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
        "Gennaio",
        "Febbraio",
        "Marzo",
        "Aprile",
        "Maggio",
        "Giugno",
        "Luglio",
        "Agosto",
        "Settembre",
        "Ottobre",
        "Novembre",
        "Dicembre",
    ]

    rows = []

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
barra_ricerca = ""
tabs = None
idx_mese = date.today().month

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
    # siamo già sulle emesse
    st.button("EMESSE")
with col_ricevute:
    st.button("RICEVUTE")  # placeholder
with col_agg:
    st.button("AGGIORNA")

nomi_mesi = [
    "Gennaio",
    "Febbraio",
    "Marzo",
    "Aprile",
    "Maggio",
    "Giugno",
    "Luglio",
    "Agosto",
    "Settembre",
    "Ottobre",
    "Novembre",
    "Dicembre",
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

                    # MENU AZIONI A TENDINA
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
                                st.rerun()  # ✅ aggiornato

                            # Elimina
                            if st.button("🗑 Elimina", key=f"del_{row_index}"):
                                st.session_state.documenti_emessi = (
                                    st.session_state.documenti_emessi
                                    .drop(row_index)
                                    .reset_index(drop=True)
                                )
                                st.warning("Fattura eliminata.")
                                st.rerun()  # ✅ aggiornato

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
# ==========================
# MENÙ / NAVIGAZIONE
# ==========================
PAGINE = [
    "Lista documenti",
    "Crea nuova fattura",
    "Download (documenti inviati)",
    "Carica pacchetto AdE",
    "Rubrica",
    "Dashboard",
]

pagina_default = st.session_state.pagina_corrente
if pagina_default not in PAGINE:
    pagina_default = "Dashboard"
default_index = PAGINE.index(pagina_default)

with st.sidebar:
    st.markdown("### 📄 Documenti")
    pagina = st.radio(
        "",
        PAGINE,
        index=default_index,
        label_visibility="collapsed",
    )

st.session_state.pagina_corrente = pagina

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
    st.markdown("#### Dashboard | Clienti | Documenti")
with col_user:
    st.markdown("Operatore")

st.markdown("---")

# ==========================
# CONTATORI DOCUMENTI PER MESE (per le tab tipo "Novembre (2)")
# ==========================
docs_per_month = {m: 0 for m in range(1, 13)}
df_tmp = st.session_state.documenti_emessi.copy()
if not df_tmp.empty:
    df_tmp["Data"] = pd.to_datetime(df_tmp["Data"], errors="coerce")
    for m in range(1, 13):
        docs_per_month[m] = (df_tmp["Data"].dt.month == m).sum()

# ==========================
# BARRA STATO / EMESSE / RICEVUTE
# ==========================
barra_ricerca = ""
tabs = None
idx_mese = date.today().month

if pagina in [
    "Lista documenti",
    "Crea nuova fattura",
    "Download (documenti inviati)",
    "Carica pacchetto AdE",
]:
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
            st.session_state.pagina_corrente = "Dashboard"
            st.rerun()
    with col_emesse:
        if st.button("EMESSE"):
            st.session_state.pagina_corrente = "Lista documenti"
            st.rerun()
    with col_ricevute:
        if st.button("RICEVUTE"):
            st.session_state.pagina_corrente = "Download (documenti inviati)"
            st.rerun()
    with col_agg:
        st.button("AGGIORNA")

    nomi_mesi = [
        "Gennaio",
        "Febbraio",
        "Marzo",
        "Aprile",
        "Maggio",
        "Giugno",
        "Luglio",
        "Agosto",
        "Settembre",
        "Ottobre",
        "Novembre",
        "Dicembre",
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
# LISTA DOCUMENTI (EMESSE)
# ==========================
if pagina == "Lista documenti":
    st.subheader("Lista documenti")

    df_e_all = st.session_state.documenti_emessi.copy()

    # selettore anno
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
        st.stop()

    if tabs is not None:
        with tabs[0]:
            crea_riepilogo_fatture_emesse(df_e_all)

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

                        # ICONA A SINISTRA (PDF / B2B)
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

                        # MENU A TENDINA AZIONI
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
                                if st.button(
                                    "✏️ Modifica", key=f"mod_{row_index}"
                                ):
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
                                        st.session_state.documenti_emessi.drop(
                                            row_index
                                        ).reset_index(drop=True)
                                    )
                                    st.warning("Fattura eliminata.")
                                    st.rerun()

                                # Invia (placeholder)
                                if st.button("📨 Invia", key=f"inv_{row_index}"):
                                    st.info(
                                        "Funzione invio a SdI non ancora implementata."
                                    )

    st.markdown("### 📄 Download PDF fatture emesse")
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

# ==========================
# CREA NUOVA FATTURA
# ==========================
elif pagina == "Crea nuova fattura":
    st.subheader("Crea nuova fattura emessa")

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
            st.rerun()

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
            cli_prov = st.text_input(
                "Provincia (es. BA)", riga_cli.get("Provincia", "")
            )
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
    note = st.text_area("Note / causale (verrà riportata in PDF come CAUSALE)", value="", height=80)

    st.markdown("### Righe fattura")
    if st.button("➕ Aggiungi riga"):
        st.session_state.righe_correnti.append(
            {"desc": "", "qta": 1.0, "prezzo": 0.0, "iva": 22}
        )
        st.rerun()

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
                st.rerun()

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
                            "CodiceDestinatario": cliente_corrente[
                                "CodiceDestinatario"
                            ],
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

# ==========================
# ALTRE PAGINE
# ==========================
elif pagina == "Download (documenti inviati)":
    st.subheader("Download documenti inviati")
    st.info(
        "Area placeholder: qui potrai elencare e scaricare i documenti inviati allo SdI."
    )

elif pagina == "Carica pacchetto AdE":
    st.subheader("Carica pacchetto AdE (ZIP da cassetto fiscale)")
    uploaded_zip = st.file_uploader(
        "Carica file ZIP (fatture + metadati)", type=["zip"]
    )
    if uploaded_zip:
        st.write("Nome file caricato:", uploaded_zip.name)
        st.info("Parsing del pacchetto non ancora implementato in questa versione.")

elif pagina == "Rubrica":
    st.subheader("Rubrica (Clienti / Fornitori)")

    colf1, colf2 = st.columns(2)
    with colf1:
        filtra_clienti = st.checkbox("Mostra clienti", value=True)
    with colf2:
        filtra_fornitori = st.checkbox("Mostra fornitori", value=True)

    with st.form("nuovo_contatto"):
        col1, col2 = st.columns(2)
        with col1:
            den = st.text_input("Denominazione")
        with col2:
            piva = st.text_input("P.IVA")
        cf = st.text_input("Codice Fiscale")
        ind = st.text_input("Indirizzo (via/piazza, civico)")
        colc1, colc2, colc3 = st.columns(3)
        with colc1:
            cap = st.text_input("CAP")
        with colc2:
            com = st.text_input("Comune")
        with colc3:
            prov = st.text_input("Provincia (es. BA)")
        colx1, colx2 = st.columns(2)
        with colx1:
            cod_dest = st.text_input("Codice Destinatario", value="0000000")
        with colx2:
            pec = st.text_input("PEC destinatario")
        tipo = st.selectbox("Tipo", ["Cliente", "Fornitore"])
        if st.form_submit_button("💾 Salva contatto"):
            nuovo = pd.DataFrame(
                [
                    {
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
                    }
                ]
            )
            st.session_state.clienti = pd.concat(
                [st.session_state.clienti, nuovo],
                ignore_index=True,
            )
            st.success("Contatto salvato")

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
        st.info("Nessun contatto in rubrica.")

else:
    st.subheader("Dashboard")
    df_e = st.session_state.documenti_emessi
    num_emesse = len(df_e)
    tot_emesse = df_e["Importo"].sum() if not df_e.empty else 0.0
    col1, col2 = st.columns(2)
    col1.metric("Fatture emesse (app)", num_emesse)
    col2.metric("Totale emesso", f"EUR {_format_val_eur(tot_emesse)}")

st.markdown("---")
st.caption(
    "Fisco Chiaro Consulting – Emesse gestite dall'app, PDF generati automaticamente."
)

st.markdown("---")
st.caption("Fisco Chiaro Consulting – Emesse gestite dall'app, PDF generati automaticamente.")
