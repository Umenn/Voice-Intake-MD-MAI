"""
Text developer — juridic strict Romanian + Russian bilingual output.
Takes raw transcript + extracted data dict → formal official narrative text.

The context (facts) is always preserved, only the language/style is elevated.
Output: {"text_ro": "...", "text_ru": "..."}
"""

import json
from openai import OpenAI
from config import OPENAI_API_KEY

_client = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        if not OPENAI_API_KEY:
            raise RuntimeError(
                "OPENAI_API_KEY lipseste din .env. "
                "Adaugati cheia la voice_intake/.env sau la robo_cop_bot/.env"
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ── System prompts per document type ──────────────────────────────────────────

_PROMPTS = {

    "plangere": (
        "Ești un jurist expert în dreptul penal al Republicii Moldova, specializat în redactarea "
        "plângerilor penale. Primești datele extrase dintr-o declarație verbală și transcrierea "
        "originală. Redactează un text narativ juridic complet pentru secțiunea 'Descrierea "
        "evenimentului' dintr-o plângere penală.\n\n"
        "REGULI STRICTE:\n"
        "1. Stilul este juridic strict — fraze pasive, terminologie penală precisă (infracțiune, "
        "prejudiciu material, faptuitor, victimă, bunuri sustrase, etc.).\n"
        "2. Toate faptele din declarație se păstrează integral — nu adăuga, nu inventa nimic.\n"
        "3. Dacă victima a menționat detalii spațiale, temporale sau circumstanțiale, include-le.\n"
        "4. Persoana victimei este la persoana I plural formal sau la persoana a III-a (ex: 'petentul declară că...').\n"
        "5. Returnează EXCLUSIV JSON valid cu câmpurile: text_ro, text_ru.\n"
        "6. text_ru este traducerea fidelă în rusă cu același stil juridic.\n"
        "7. Lungimea: minim 3 paragrafe, maxim 8 paragrafe."
    ),

    "declaratie": (
        "Ești un jurist expert în dreptul penal al Republicii Moldova, specializat în redactarea "
        "declarațiilor de victimă. Primești datele extrase și transcrierea originală. Redactează "
        "textul narativ al declarației, la persoana I (victima vorbește).\n\n"
        "REGULI STRICTE:\n"
        "1. Persoana I: 'Subsemnatul/a declar că...', 'La data de...', 'M-am deplasat...' etc.\n"
        "2. Stil oficial dar clar — evitați limbajul colocvial fără a deveni inaccesibil.\n"
        "3. Toate faptele păstrate exact — cronologie clară, detalii precise.\n"
        "4. Includeți orice detalii fizice despre faptuitor, vehicule, dialoguri menționate.\n"
        "5. Returnează EXCLUSIV JSON valid cu câmpurile: text_ro, text_ru.\n"
        "6. text_ru este traducerea fidelă în rusă.\n"
        "7. Lungimea: minim 3 paragrafe."
    ),

    "proces_verbal": (
        "Ești un jurist expert în dreptul penal al Republicii Moldova, specializat în redactarea "
        "proceselor-verbale de sesizare. Scrii la persoana a III-a, din perspectiva ofițerului "
        "de serviciu care consemnează sesizarea.\n\n"
        "REGULI STRICTE:\n"
        "1. Stil impersonal oficial: 'Ofițerul de serviciu a consemnat că...', 'Din cele relatate reiese că...'.\n"
        "2. Terminologie CPP: sesizare, infracțiune, persoană vătămată, învinuit, cercetare penală.\n"
        "3. Toate faptele păstrate integral.\n"
        "4. Returnează EXCLUSIV JSON valid cu câmpurile: text_ro, text_ru.\n"
        "5. text_ru este traducerea fidelă în rusă cu același stil.\n"
        "6. Lungimea: minim 2 paragrafe."
    ),

    "nota_explicativa": (
        "Ești un jurist expert în dreptul penal al Republicii Moldova, specializat în redactarea "
        "notelor explicative. Aceasta este declarația persoanei audiate (posibil suspect sau "
        "persoană de interes). Scrii la persoana I, din perspectiva persoanei audiate.\n\n"
        "REGULI STRICTE:\n"
        "1. Persoana I: 'Subsemnatul/a explic că...', 'La momentul indicat mă aflam...'.\n"
        "2. Stil formal dar uman — persoana audiată explică propria versiune.\n"
        "3. Include justificările, alibiul, versiunea proprie a evenimentelor.\n"
        "4. Nu judeca și nu adăuga interpretări — redai fidel ce a declarat persoana.\n"
        "5. Returnează EXCLUSIV JSON valid cu câmpurile: text_ro, text_ru.\n"
        "6. text_ru este traducerea fidelă în rusă.\n"
        "7. Lungimea: minim 3 paragrafe."
    ),

    "sesizare_penala": (
        "Ești un jurist expert în dreptul penal al Republicii Moldova, specializat în redactarea "
        "sesizărilor penale adresate procuraturii. Scrii la persoana a III-a, din perspectiva "
        "Inspectoratului de Poliție care sesizează organul de urmărire penală.\n\n"
        "REGULI STRICTE:\n"
        "1. Stil juridic strict: 'Inspectoratul de Poliție... sesizează Procuratura...', "
        "'Din informațiile acumulate rezultă că...', 'se solicită pornirea urmăririi penale'.\n"
        "2. Referințe la normele CPP și CP ale RM când e relevant (ex: art. 186 CP — furt).\n"
        "3. Structură: fapta → circumstanțele → prejudiciul → temeiul legal → solicitarea.\n"
        "4. Ton formal-imperativ caracteristic actelor de sesizare.\n"
        "5. Returnează EXCLUSIV JSON valid cu câmpurile: text_ro, text_ru.\n"
        "6. text_ru este traducerea fidelă în rusă cu același stil.\n"
        "7. Lungimea: minim 4 paragrafe."
    ),
}

_DEFAULT_PROMPT = _PROMPTS["declaratie"]


def develop(transcript: str, extracted: dict, doc_type: str = "declaratie") -> dict:
    """
    Generate juridic strict bilingual narrative from transcript + extracted data.

    Args:
        transcript: raw Whisper output
        extracted:  structured data dict from extractor.py
        doc_type:   template name (plangere / declaratie / proces_verbal /
                    nota_explicativa / sesizare_penala)

    Returns:
        {"text_ro": "...", "text_ru": "...", "error": None}
    """
    system = _PROMPTS.get(doc_type, _DEFAULT_PROMPT)

    # Build a rich user message with all available context
    summary_lines = []
    label_map = {
        "tip_incident":        "Tip incident",
        "data_incident":       "Data",
        "ora_incident":        "Ora",
        "locul_incident":      "Loc",
        "locul_detalii":       "Detalii loc",
        "victima_nume":        "Victima / Persoana (Nume)",
        "victima_prenume":     "Victima / Persoana (Prenume)",
        "victima_idnp":        "IDNP",
        "victima_adresa":      "Adresa",
        "victima_telefon":     "Telefon",
        "faptuitor_descriere": "Descripție faptuitor",
        "faptuitor_detalii":   "Detalii faptuitor",
        "martori":             "Martori",
        "bunuri_sustrase":     "Bunuri sustrase",
        "valoare_estimata":    "Valoare estimată (MDL)",
        "rezumat":             "Rezumat inițial",
        "alte_detalii":        "Alte detalii",
        "masuri_solicitate":   "Solicită",
        "versiunea_proprie":   "Versiunea proprie",
        "justificari":         "Justificări / Alibi",
        "temeiul_legal":       "Temei legal",
    }
    for key, label in label_map.items():
        val = extracted.get(key, "").strip()
        if val:
            summary_lines.append(f"- {label}: {val}")

    user_msg = (
        f"TIP DOCUMENT: {doc_type}\n\n"
        f"DATE EXTRASE:\n" + "\n".join(summary_lines) +
        f"\n\nTRANSCRIERE ORIGINALĂ (voce):\n\"\"\"\n{transcript}\n\"\"\"\n\n"
        "Redactează textul narativ juridic strict, bilingv (text_ro + text_ru). "
        "Returnează EXCLUSIV un obiect JSON cu exact două câmpuri: text_ro și text_ru."
    )

    try:
        resp = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.2,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        result = json.loads(raw)
        return {
            "text_ro": result.get("text_ro", ""),
            "text_ru": result.get("text_ru", ""),
            "error":   None,
        }
    except Exception as exc:
        return {
            "text_ro": "",
            "text_ru": "",
            "error":   str(exc),
        }
