"""
Structured case-fact extraction using GPT-4o-mini.
Input:  raw transcript (Romanian / Russian / English) + doc_type
Output: JSON with all fields needed to fill a police report template
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
                "Adaugati cheia la voice_intake/.env sau robo_cop_bot/.env"
            )
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


# ── Base system instruction ────────────────────────────────────────────────────

_BASE_SYSTEM = (
    "Ești un asistent AI specializat în extragerea datelor din declarații verbale la poliție "
    "în Republica Moldova. Extrage toate informațiile relevante și returnează-le ca JSON valid. "
    "Răspunde EXCLUSIV cu JSON — fără text înainte sau după. "
    "Câmpurile lipsă lasă ca string gol \"\". "
    "Data și ora trebuie să fie în format DD.MM.YYYY și respectiv HH:MM. "
    "Dacă persoana vorbește în rusă sau engleză, extrage oricum câmpurile și completează valorile în română."
)

# ── Field schemas per document type ──────────────────────────────────────────

_SCHEMA_VICTIM = {
    "tip_incident":         "tipul infracțiunii (ex: furt, jaf, agresiune, vandalism, escrocherie, altul)",
    "data_incident":        "data incidentului DD.MM.YYYY",
    "ora_incident":         "ora incidentului HH:MM",
    "locul_incident":       "adresa sau descrierea locului",
    "locul_detalii":        "detalii suplimentare despre loc (etaj, apartament, etc.)",
    "victima_nume":         "numele de familie al victimei",
    "victima_prenume":      "prenumele victimei",
    "victima_idnp":         "IDNP / serie buletin",
    "victima_data_nastere": "data nașterii victimei DD.MM.YYYY",
    "victima_telefon":      "telefonul victimei",
    "victima_adresa":       "adresa de domiciliu a victimei",
    "faptuitor_descriere":  "descrierea fizică a făptuitorului (înălțime, constituție, vârstă, trăsături)",
    "faptuitor_detalii":    "alte detalii despre faptuitor (voce, acțiuni, vehicul, îmbrăcăminte, etc.)",
    "martori":              "lista martorilor dacă există (nume, contact)",
    "bunuri_sustrase":      "lista bunurilor sustrase sau deteriorate",
    "valoare_estimata":     "valoarea estimată a prejudiciului în MDL",
    "alte_detalii":         "alte informații relevante menționate",
    "rezumat":              "rezumat complet și clar al incidentului în 3-5 propoziții",
    "masuri_solicitate":    "ce solicită victima (investigație, reținere, recuperare bunuri, etc.)",
}

_SCHEMA_NOTA_EXPLICATIVA = {
    "tip_incident":        "tipul faptei pentru care persoana este audiată",
    "data_incident":       "data faptei DD.MM.YYYY",
    "ora_incident":        "ora faptei HH:MM",
    "locul_incident":      "locul unde persoana se afla la momentul faptei",
    "victima_nume":        "numele persoanei audiate (de familie)",
    "victima_prenume":     "prenumele persoanei audiate",
    "victima_idnp":        "IDNP / serie buletin al persoanei audiate",
    "victima_data_nastere":"data nașterii persoanei audiate DD.MM.YYYY",
    "victima_telefon":     "telefonul persoanei audiate",
    "victima_adresa":      "adresa de domiciliu a persoanei audiate",
    "versiunea_proprie":   "versiunea proprie a evenimentelor — ce spune persoana că s-a întâmplat",
    "justificari":         "justificările oferite, alibiul, unde se afla la momentul faptei",
    "martori":             "martori menționați de persoana audiată",
    "alte_detalii":        "alte informații relevante oferite de persoana audiată",
    "rezumat":             "rezumatul explicației persoanei în 2-4 propoziții",
}

_SCHEMA_SESIZARE_PENALA = {
    "tip_incident":         "tipul infracțiunii ce urmează a fi sesizate",
    "data_incident":        "data infracțiunii DD.MM.YYYY",
    "ora_incident":         "ora infracțiunii HH:MM",
    "locul_incident":       "locul unde s-a produs infracțiunea",
    "victima_nume":         "numele de familie al persoanei vătămate",
    "victima_prenume":      "prenumele persoanei vătămate",
    "victima_idnp":         "IDNP al persoanei vătămate",
    "victima_telefon":      "telefonul persoanei vătămate",
    "victima_adresa":       "adresa persoanei vătămate",
    "faptuitor_descriere":  "descrierea fizică a presupusului infractor dacă e cunoscut",
    "faptuitor_detalii":    "alte date cunoscute despre presupusul infractor",
    "martori":              "martori disponibili",
    "bunuri_sustrase":      "bunuri sustrase sau prejudiciu material",
    "valoare_estimata":     "valoarea estimată a prejudiciului în MDL",
    "temeiul_legal":        "articolele din CP/CPP incidente dacă sunt menționate",
    "alte_detalii":         "probe, circumstanțe agravante sau alte elemente relevante",
    "rezumat":              "rezumatul faptei sesizate în 3-5 propoziții",
    "masuri_solicitate":    "solicitarea adresată procuraturii (pornire urmărire penală, etc.)",
}

_SCHEMA_RAPORT_GO = {
    "tip_incident":         "tipul sesizării / faptei (ex: furt, agresiune, accident, tulburarea ordinii)",
    "data_incident":        "data evenimentului DD.MM.YYYY",
    "ora_incident":         "ora evenimentului HH:MM",
    "locul_incident":       "adresa unde s-a produs evenimentul",
    "victima_prenume":      "prenumele persoanei implicate / sesizante",
    "victima_nume":         "numele de familie al persoanei implicate",
    "victima_telefon":      "telefonul persoanei implicate",
    "masuri_intreprinse":   "măsuri operative întreprinse la fața locului",
    "text_razvtat_ro":      "descrierea completă a evenimentului, acțiunilor ofițerului și concluzii",
    "ofiters_prenume":      "prenumele ofițerului care raportează",
    "ofiters_nume":         "numele de familie al ofițerului care raportează",
}

_SCHEMA_RAPORT_PIERDERE = {
    "tip_incident":         "tipul pierderii (acte, bunuri, vehicul, altele)",
    "data_incident":        "data constatării pierderii DD.MM.YYYY",
    "ora_incident":         "ora constatării HH:MM",
    "locul_incident":       "locul unde s-a constatat lipsa",
    "victima_prenume":      "prenumele persoanei care sesizează",
    "victima_nume":         "numele de familie",
    "victima_idnp":         "IDNP / buletin",
    "victima_telefon":      "telefon",
    "bunuri_sustrase":      "lista bunurilor / actelor pierdute",
    "valoare_estimata":     "valoarea estimată MDL dacă e cazul",
    "text_razvtat_ro":      "descrierea circumstanțelor pierderii și măsuri luate",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
}

_SCHEMA_RAPORT_DROGURI = {
    "data_incident":        "data predării substanței DD.MM.YYYY",
    "ora_incident":         "ora predării HH:MM",
    "locul_incident":       "locul predării",
    "victima_prenume":      "prenumele persoanei care predă substanța",
    "victima_nume":         "numele persoanei care predă",
    "victima_idnp":         "IDNP",
    "victima_data_nastere": "data nașterii DD.MM.YYYY",
    "victima_adresa":       "adresa domiciliu",
    "substanta_descriere":  "descrierea substanței predate (aspect, cantitate, ambalaj)",
    "text_razvtat_ro":      "descrierea completă a circumstanțelor predării și măsuri luate",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
}

_SCHEMA_RAPORT_TRANSMITERE = {
    "numar_dosar":          "numărul materialului REI",
    "tip_incident":         "tipul faptei pentru care a fost înregistrat materialul",
    "data_incident":        "data faptei DD.MM.YYYY",
    "locul_incident":       "locul faptei",
    "victima_prenume":      "prenumele petentului / victimei",
    "victima_nume":         "numele petentului / victimei",
    "sector_destinatie":    "sectorul / instituția unde se transmite (ex: SP-4, Procuratură)",
    "text_razvtat_ro":      "motivul transmiterii și circumstanțele relevante",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
}

_SCHEMA_RAPORT_CAUTARE = {
    "data_incident":        "data dispariției DD.MM.YYYY",
    "ora_incident":         "ora dispariției sau ultima vedere HH:MM",
    "locul_incident":       "locul de unde a dispărut persoana",
    "victima_prenume":      "prenumele persoanei dispărute",
    "victima_nume":         "numele persoanei dispărute",
    "victima_idnp":         "IDNP al persoanei dispărute",
    "victima_data_nastere": "data nașterii DD.MM.YYYY",
    "victima_adresa":       "adresa domiciliu",
    "victima_telefon":      "telefonul sesizantului",
    "faptuitor_descriere":  "descrierea fizică a persoanei dispărute (înălțime, îmbrăcăminte, semne distinctive)",
    "text_razvtat_ro":      "circumstanțele dispariției și măsuri deja întreprinse",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
}

_SCHEMA_NOTA_INFORMATIVA = {
    "sursa_informatiei":    "sursa: apelul 112 / adresare directă / patrulare / informator",
    "tip_incident":         "tipul evenimentului raportat",
    "data_incident":        "data evenimentului DD.MM.YYYY",
    "ora_incident":         "ora evenimentului HH:MM",
    "locul_incident":       "locul evenimentului",
    "victima_prenume":      "prenumele persoanei implicate / sesizante",
    "victima_nume":         "numele persoanei implicate",
    "text_razvtat_ro":      "descrierea detaliată a evenimentului și informațiilor culese",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
}

_SCHEMA_INTERPELARE = {
    "numar_dosar":          "numărul materialului REI",
    "data_incident":        "data evenimentului DD.MM.YYYY",
    "ora_incident":         "ora evenimentului HH:MM",
    "tip_incident":         "tipul evenimentului",
    "locul_incident":       "locul evenimentului",
    "institutie_tip":       "tipul adresantului (Administrației / Directorului / Conducătorului)",
    "institutie_nume":      "denumirea instituției interpelate",
    "institutie_adresa":    "adresa instituției",
    "date_solicitate":      "ce anume se solicită de la instituție (documente, înregistrări, date persoane)",
    "text_razvtat_ro":      "detalii suplimentare sau context",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
    "ofiters_telefon":      "telefonul ofițerului executor",
}

_SCHEMA_PRELUNGIRE = {
    "numar_dosar":          "numărul materialului REI-2",
    "data_inregistrare":    "data înregistrării materialului DD.MM.YYYY",
    "tip_incident":         "tipul faptei",
    "data_incident":        "data faptei DD.MM.YYYY",
    "victima_prenume":      "prenumele petentului",
    "victima_nume":         "numele petentului",
    "text_razvtat_ro":      "motivele pentru care se solicită prelungirea termenului",
    "ofiters_prenume":      "prenumele ofițerului",
    "ofiters_nume":         "numele ofițerului",
    "sef_prenume_nume":     "numele șefului IP Botanica (implicit: Sergiu ERHAN)",
}

_SCHEMA_DECIZIE_CLASARE = {
    "numar_dosar":          "numărul materialului REI-2",
    "data_inregistrare":    "data înregistrării materialului DD.MM.YYYY",
    "tip_incident":         "tipul faptei sesizate",
    "data_incident":        "data faptei DD.MM.YYYY",
    "victima_prenume":      "prenumele petentului",
    "victima_nume":         "numele petentului",
    "victima_data_nastere": "data nașterii petentului DD.MM.YYYY",
    "text_razvtat_ro":      "constatarea ofițerului, analiza probelor, calificarea juridică, concluzie",
    "concluzie_1":          "prima propunere (ex: 1. Controlul interior de încetat în baza art. 275 pct.3 CPP RM)",
    "ofiters_prenume":      "prenumele ofițerului de investigații",
    "ofiters_nume":         "numele ofițerului de investigații",
}

_SCHEMAS = {
    "plangere":            _SCHEMA_VICTIM,
    "declaratie":          _SCHEMA_VICTIM,
    "proces_verbal":       _SCHEMA_VICTIM,
    "nota_explicativa":    _SCHEMA_NOTA_EXPLICATIVA,
    "sesizare_penala":     _SCHEMA_SESIZARE_PENALA,
    "raport_go":           _SCHEMA_RAPORT_GO,
    "raport_pierdere":     _SCHEMA_RAPORT_PIERDERE,
    "raport_droguri":      _SCHEMA_RAPORT_DROGURI,
    "raport_transmitere":  _SCHEMA_RAPORT_TRANSMITERE,
    "raport_cautare":      _SCHEMA_RAPORT_CAUTARE,
    "nota_informativa":    _SCHEMA_NOTA_INFORMATIVA,
    "interpelare":         _SCHEMA_INTERPELARE,
    "prelungire":          _SCHEMA_PRELUNGIRE,
    "decizie_clasare":     _SCHEMA_DECIZIE_CLASARE,
}

_DEFAULT_SCHEMA = _SCHEMA_VICTIM


def extract(transcript: str, doc_type: str = "declaratie") -> dict:
    """
    Extract structured case data from a police statement transcript.

    Args:
        transcript: raw transcript text (any language)
        doc_type:   template id — determines which fields to extract

    Returns:
        dict with all fields from the appropriate schema
    """
    schema = _SCHEMAS.get(doc_type, _DEFAULT_SCHEMA)

    # Adapt system prompt for special doc types
    extra = ""
    if doc_type == "nota_explicativa":
        extra = " Persoana audiată poate fi un suspect sau o persoană de interes — extrage versiunea sa."
    elif doc_type == "sesizare_penala":
        extra = " Aceasta este o sesizare penală — extrage elementele care fundamentează sesizarea."

    system = _BASE_SYSTEM + extra

    user_msg = (
        "Schema câmpurilor de extras:\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n\nTranscrierea declarației:\n\"\"\"\n"
        + transcript
        + "\n\"\"\""
    )

    response = _get_client().chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user_msg},
        ],
        temperature=0.1,
        response_format={"type": "json_object"},
    )
    raw  = response.choices[0].message.content
    data = json.loads(raw)
    # Ensure every schema field is present (default empty string)
    for key in schema:
        data.setdefault(key, "")
    return data


def format_for_review(data: dict, doc_type: str = "declaratie") -> str:
    """Human-readable summary of extracted data for UI review step."""
    lines = ["*Date extrase:*\n"]

    # Labels common to all doc types
    label_map = {
        "tip_incident":        "Tip incident",
        "data_incident":       "Data",
        "ora_incident":        "Ora",
        "locul_incident":      "Locul",
        "victima_nume":        "Nume",
        "victima_prenume":     "Prenume",
        "victima_idnp":        "IDNP",
        "victima_telefon":     "Telefon",
        "victima_adresa":      "Adresa",
        "faptuitor_descriere": "Descriere faptuitor",
        "faptuitor_detalii":   "Detalii faptuitor",
        "martori":             "Martori",
        "bunuri_sustrase":     "Bunuri sustrase",
        "valoare_estimata":    "Valoare estimată (MDL)",
        "versiunea_proprie":   "Versiunea proprie",
        "justificari":         "Justificări / Alibi",
        "temeiul_legal":       "Temei legal",
        "rezumat":             "Rezumat",
        "alte_detalii":        "Alte detalii",
        "masuri_solicitate":   "Solicită",
    }

    for key, label in label_map.items():
        val = data.get(key, "").strip()
        if val:
            lines.append(f"- *{label}:* {val}")

    return "\n".join(lines)
