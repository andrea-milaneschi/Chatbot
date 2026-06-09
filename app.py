import io
import os
import pandas as pd

import streamlit as st

st.set_page_config(page_title="Consegne", page_icon="📦", layout="centered")

PASSWORD = "cosegne2026"

if "autenticato" not in st.session_state:
    st.session_state.autenticato = False

if not st.session_state.autenticato:
    st.title("🔒 Accesso")
    pwd = st.text_input("Password", type="password")
    if st.button("Entra", type="primary"):
        if pwd == PASSWORD:
            st.session_state.autenticato = True
            st.rerun()
        else:
            st.error("Password errata.")
    st.stop()

LOCAL_FOLDER = r"C:\Users\andre\Desktop\controllo produzione\esportazioni"
LOCAL_FILES = [
    "01_pezzi_montati.xls",
    "02_pezzi_verniciati.xls",
    "03_completati.xls",
    "da_lavorare.xls",
]


@st.cache_data(show_spinner=False)
def load_local():
    dfs = []
    for fn in LOCAL_FILES:
        path = os.path.join(LOCAL_FOLDER, fn)
        if os.path.exists(path):
            df = pd.read_excel(path, header=1)
            dfs.append(df)
    if not dfs:
        return None
    return pd.concat(dfs, ignore_index=True)


def format_data(val):
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()
    return "—" if s in ("nan", "NaT", "") else s


def cerca(df, ddt, art=None):
    ddt_col = df["Num. ddt."].astype(str).str.strip()
    mask = ddt_col == str(ddt).strip()
    if art:
        art_col = df["Cod. art."].astype(str).str.strip().str.upper()
        mask = mask & (art_col == str(art).strip().upper())
    return df[mask]


# ── UI ──────────────────────────────────────────────────────────────────────

st.title("📦 Controllo Date di Consegna")

# Caricamento dati
df = load_local()
if df is None:
    # Siamo su cloud: chiedi di caricare i file
    st.info("Carica i file Excel aggiornati per avviare la ricerca.")
    uploaded = st.file_uploader(
        "Seleziona i file .xls dal tuo PC",
        type=["xls", "xlsx"],
        accept_multiple_files=True,
    )
    if not uploaded:
        st.stop()
    dfs = []
    for f in uploaded:
        dfs.append(pd.read_excel(io.BytesIO(f.read()), header=1))
    df = pd.concat(dfs, ignore_index=True)

st.caption(f"Database caricato — {len(df)} record totali.")

st.divider()

# Ricerca
col1, col2 = st.columns([1, 2])
with col1:
    ddt_input = st.text_input("Numero DDT", placeholder="es. 1156")
with col2:
    art_input = st.text_input("Codice articolo (opzionale)", placeholder="es. GLV_LG_02312 SX")

cerca_btn = st.button("🔍 Cerca", use_container_width=True, type="primary")

if cerca_btn:
    if not ddt_input.strip():
        st.warning("Inserisci almeno il numero DDT.")
    else:
        risultati = cerca(df, ddt_input.strip(), art_input.strip() or None)

        if risultati.empty:
            st.error(f"Nessun risultato trovato per il DDT **{ddt_input}**.")
        else:
            st.success(f"Trovati **{len(risultati)}** record per DDT {ddt_input}.")
            for _, row in risultati.iterrows():
                with st.container(border=True):
                    c1, c2 = st.columns(2)
                    c1.metric("Data limite", format_data(row.get("Data limite")))
                    c2.metric("Cliente", str(row.get("Cliente", "")).strip() or "—")
                    st.write(
                        f"**Articolo:** {str(row.get('Cod. art.', '')).strip()}   "
                        f"**Ordine:** {str(row.get('Ordine', '')).strip()}"
                    )
