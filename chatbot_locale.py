import os
import sys
import re
import pandas as pd

DATA_FOLDER = r"C:\Users\andre\Desktop\controllo produzione\esportazioni"

FILES = [
    "01_pezzi_montati.xls",
    "02_pezzi_verniciati.xls",
    "03_completati.xls",
    "da_lavorare.xls",
]


def load_data():
    dfs = []
    for filename in FILES:
        filepath = os.path.join(DATA_FOLDER, filename)
        if os.path.exists(filepath):
            try:
                df = pd.read_excel(filepath, header=1)
                df["_source"] = filename
                dfs.append(df)
                print(f"  ✓ {filename}: {len(df)} righe")
            except Exception as e:
                print(f"  ✗ {filename}: {e}")
        else:
            print(f"  ! {filename}: non trovato")

    if not dfs:
        raise FileNotFoundError(f"Nessun file Excel trovato in {DATA_FOLDER}")

    combined = pd.concat(dfs, ignore_index=True)
    combined["_ddt_str"] = combined["Num. ddt."].astype(str).str.strip()
    combined["_art_str"] = combined["Cod. art."].astype(str).str.strip().str.upper()
    return combined


def format_data_limite(val):
    if hasattr(val, "strftime"):
        return val.strftime("%d/%m/%Y")
    s = str(val).strip()
    return "non disponibile" if s in ("nan", "NaT", "") else s


def cerca(df, num_ddt, cod_art=None):
    mask = df["_ddt_str"] == str(num_ddt).strip()
    if cod_art:
        mask = mask & (df["_art_str"] == str(cod_art).strip().upper())
    return df[mask]


def stampa_risultati(risultati):
    if risultati.empty:
        print("\n  [!] Nessun record trovato.")
        return
    print()
    for i, (_, row) in enumerate(risultati.iterrows(), 1):
        data = format_data_limite(row.get("Data limite", ""))
        cliente = str(row.get("Cliente", "")).strip()
        articolo = str(row.get("Cod. art.", "")).strip()
        ordine = str(row.get("Ordine", "")).strip()
        ddt = str(row.get("Num. ddt.", "")).strip()
        print(f"  Risultato {i}:")
        print(f"    DDT       : {ddt}")
        print(f"    Articolo  : {articolo}")
        print(f"    Data limite: {data}")
        print(f"    Cliente   : {cliente}")
        print(f"    Ordine    : {ordine}")
        print()


def estrai_ddt_e_art(testo):
    """Estrae numero DDT e codice articolo dal testo libero dell'utente."""
    testo_u = testo.upper()

    # Cerca numero DDT
    ddt = None
    m = re.search(r"DDT\s*[:#]?\s*(\S+)", testo_u)
    if m:
        ddt = m.group(1).rstrip(".,;")
    else:
        # Cerca un numero standalone
        m = re.search(r"\b(\d{3,6})\b", testo)
        if m:
            ddt = m.group(1)

    # Cerca codice articolo dopo parole chiave
    art = None
    m = re.search(r"(?:ARTICOLO|ART\.?|COD\.?|CODICE)\s*[:#]?\s*(\S+)", testo_u)
    if m:
        art = m.group(1).rstrip(".,;")

    return ddt, art


def run():
    print("=" * 60)
    print("  Chatbot Consegne — Versione Locale (senza API)")
    print("=" * 60)
    print()
    print("Caricamento database...")
    try:
        df = load_data()
    except Exception as e:
        print(f"\nErrore: {e}")
        sys.exit(1)

    print(f"\nDatabase pronto: {len(df)} record totali.")
    print()
    print("Come usarlo:")
    print("  • Scrivi il numero DDT  →  es: 'DDT 1156'")
    print("  • Con articolo          →  es: 'DDT 1156 articolo GLV_LG_02312 SX'")
    print("  • Oppure solo il numero →  es: '5249'")
    print("  • 'esci' per uscire")
    print("-" * 60)

    while True:
        try:
            testo = input("\nTu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nArrivederci!")
            break

        if not testo:
            continue
        if testo.lower() in {"esci", "exit", "quit", "q"}:
            print("\nArrivederci!")
            break

        ddt, art = estrai_ddt_e_art(testo)

        if not ddt:
            print("\n  [?] Non ho trovato un numero DDT nel testo.")
            print("      Esempio: 'DDT 1156' oppure '1156'")
            continue

        risultati = cerca(df, ddt, art)
        stampa_risultati(risultati)

        # Se ci sono più risultati senza filtro articolo, suggerisci
        if len(risultati) > 1 and not art:
            print("  [i] Ci sono più articoli per questo DDT.")
            print("      Aggiungi il codice articolo per filtrare,")
            print("      es: 'DDT", ddt, "articolo <codice>'")


if __name__ == "__main__":
    run()
