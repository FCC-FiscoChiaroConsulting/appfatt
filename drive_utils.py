import os
import io
import json

import pandas as pd
import streamlit as st
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


def _get_drive_service():
    """Restituisce (service, folder_id, error). Se error != None, Drive non è utilizzabile."""
    service_json = os.getenv("GDRIVE_SERVICE_ACCOUNT_JSON")
    folder_id = os.getenv("GDRIVE_FOLDER_ID")

    if not service_json or not folder_id:
        return None, None, "Google Drive non configurato nelle variabili ambiente."

    try:
        info = json.loads(service_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=SCOPES,
        )
        service = build("drive", "v3", credentials=creds)
        return service, folder_id, None
    except Exception as e:
        return None, None, f"Errore configurazione Google Drive: {e}"


def salva_df_su_drive(df: pd.DataFrame, filename: str):
    """Salva (o aggiorna) un file Excel su Drive con nome filename."""
    service, folder_id, err = _get_drive_service()
    if err:
        # Non blocchiamo l'app se Drive non è configurato
        return False, err

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Dati")
    buffer.seek(0)

    media = MediaIoBaseUpload(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        resumable=False,
    )

    # Cerco se esiste già un file con quel nome nella cartella
    res = service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
        fields="files(id,name)",
        pageSize=1,
    ).execute()
    items = res.get("files", [])

    if items:
        file_id = items[0]["id"]
        service.files().update(fileId=file_id, media_body=media).execute()
    else:
        metadata = {"name": filename, "parents": [folder_id]}
        service.files().create(body=metadata, media_body=media).execute()

    return True, "File salvato su Drive."


def carica_df_da_drive(filename: str):
    """Scarica un Excel da Drive e lo restituisce come DataFrame."""
    service, folder_id, err = _get_drive_service()
    if err:
        return None, err

    res = service.files().list(
        q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
        fields="files(id,name)",
        pageSize=1,
    ).execute()
    items = res.get("files", [])

    if not items:
        return None, "File non trovato su Drive."

    file_id = items[0]["id"]

    fh = io.BytesIO()
    request = service.files().get_media(fileId=file_id)
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.seek(0)

    df = pd.read_excel(fh)
    return df, None


def carica_dati_iniziali_da_drive():
    """
    Se esistono i file Excel su Drive, carica:
    - ricevute_asd_ssd.xlsx  -> st.session_state.ricevute_emesse
    - prima_nota_asd_ssd.xlsx -> st.session_state.prima_nota
    - soci_asd_ssd.xlsx      -> st.session_state.soci
    Non dà errore se i file non esistono o Drive non è configurato.
    """
    # Ricevute
    if "ricevute_emesse" not in st.session_state or st.session_state.ricevute_emesse.empty:
        df, err = carica_df_da_drive("ricevute_asd_ssd.xlsx")
        if df is not None:
            # aggiungo colonna PDF vuota (i PDF non sono salvati su Drive)
            if "PDF" not in df.columns:
                df["PDF"] = None
            st.session_state.ricevute_emesse = df

    # Prima nota
    if "prima_nota" not in st.session_state or st.session_state.prima_nota.empty:
        df, err = carica_df_da_drive("prima_nota_asd_ssd.xlsx")
        if df is not None:
            st.session_state.prima_nota = df

    # Soci
    if "soci" not in st.session_state or st.session_state.soci.empty:
        df, err = carica_df_da_drive("soci_asd_ssd.xlsx")
        if df is not None:
            st.session_state.soci = df


