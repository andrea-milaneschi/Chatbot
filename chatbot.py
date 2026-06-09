import os
import sys
import json
import pandas as pd
import anthropic

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
    # Normalize key columns
    combined["_ddt_str"] = combined["Num. ddt."].astype(str).str.strip()
    combined["_art_str"] = combined["Cod. art."].astype(str).str.strip().str.upper()
    return combined


def cerca_consegna(df, num_ddt=None, cod_art=None):
    mask = pd.Series([True] * len(df), index=df.index)

    if num_ddt is not None:
        ddt_query = str(num_ddt).strip()
        mask = mask & (df["_ddt_str"] == ddt_query)

    if cod_art is not None:
        art_query = str(cod_art).strip().upper()
        mask = mask & (df["_art_str"] == art_query)

    subset = df[mask]
    if subset.empty:
        return []

    results = []
    for _, row in subset.iterrows():
        data_limite = row.get("Data limite", "")
        # Convert date objects to string
        if hasattr(data_limite, "strftime"):
            data_limite = data_limite.strftime("%d/%m/%Y")
        else:
            data_limite = str(data_limite).strip()
        if data_limite in ("nan", "NaT", ""):
            data_limite = "non disponibile"

        results.append({
            "ddt": str(row.get("Num. ddt.", "")).strip(),
            "articolo": str(row.get("Cod. art.", "")).strip(),
            "data_limite": data_limite,
            "cliente": str(row.get("Cliente", "")).strip(),
            "ordine": str(row.get("Ordine", "")).strip(),
            "file": row.get("_source", ""),
        })

    return results


TOOLS = [
    {
        "name": "cerca_consegna",
        "description": (
            "Cerca la data di consegna (data limite) nel database degli ordini. "
            "Usa questo strumento ogni volta che l'utente menziona un numero DDT "
            "o un codice articolo."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "num_ddt": {
                    "type": "string",
                    "description": "Numero DDT (Documento Di Trasporto) da cercare",
                },
                "cod_art": {
                    "type": "string",
                    "description": "Codice articolo da cercare (opzionale)",
                },
            },
            "required": ["num_ddt"],
        },
    }
]

SYSTEM = """Sei un assistente per il controllo delle consegne di un'azienda produttrice.
Hai accesso a un database che contiene DDT, codici articolo, date limite di consegna, clienti e ordini.

Regole:
- Rispondi SEMPRE in italiano.
- Quando l'utente cita un numero DDT (o un codice articolo), usa SUBITO lo strumento cerca_consegna.
- Presenta i risultati in modo chiaro: data limite, cliente, articolo, ordine.
- Se ci sono più articoli sullo stesso DDT, elencali tutti.
- Se non ci sono risultati, di' all'utente che il DDT non è stato trovato.
- Sii conciso e professionale."""


def run():
    print("=" * 60)
    print("  Chatbot Consegne — Controllo Produzione")
    print("=" * 60)
    print()
    print("Caricamento database in corso...")
    try:
        df = load_data()
    except Exception as exc:
        print(f"\nErrore: {exc}")
        sys.exit(1)

    print(f"\nDatabase pronto: {len(df)} record caricati.")
    print("\nEsempi di domande:")
    print("  • 'Qual è la data di consegna del DDT 1156?'")
    print("  • 'DDT 5249 articolo MCM17152'")
    print("  • 'data limite ddt 2345'")
    print("\nDigita 'esci' per uscire.")
    print("-" * 60)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("\nATTENZIONE: variabile ANTHROPIC_API_KEY non impostata.")
        print("Imposta la variabile d'ambiente prima di avviare il chatbot.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    messages = []

    while True:
        try:
            user_input = input("\nTu: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\nArrivederci!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"esci", "exit", "quit", "q"}:
            print("\nArrivederci!")
            break

        messages.append({"role": "user", "content": user_input})

        # Agentic loop
        while True:
            response = client.messages.create(
                model="claude-opus-4-8",
                max_tokens=1024,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
            )

            if response.stop_reason == "end_turn":
                for block in response.content:
                    if block.type == "text":
                        print(f"\nAssistente: {block.text}")
                messages.append({"role": "assistant", "content": response.content})
                break

            if response.stop_reason == "tool_use":
                messages.append({"role": "assistant", "content": response.content})

                tool_results = []
                for block in response.content:
                    if block.type == "tool_use" and block.name == "cerca_consegna":
                        args = block.input
                        risultati = cerca_consegna(
                            df,
                            num_ddt=args.get("num_ddt"),
                            cod_art=args.get("cod_art"),
                        )
                        if risultati:
                            content = json.dumps(risultati, ensure_ascii=False, indent=2)
                        else:
                            content = "Nessun risultato trovato."
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": content,
                        })

                messages.append({"role": "user", "content": tool_results})
            else:
                break


if __name__ == "__main__":
    run()
