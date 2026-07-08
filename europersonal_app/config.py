"""Configurația aplicației EUROPERSONAL — Documente IGM.

AUTENTIFICAREA se face acum cu utilizator + parolă (baza de date users.db).
Cont implicit pentru testare: admin / 1337. Utilizatori noi se adaugă din
aplicație (sidebar, doar admin). PAROLA de mai jos NU se mai folosește
(păstrată doar pentru compatibilitate).
"""
VERSION = "1.2.0 (untested)"
PAROLA = "europersonal2026"
PORT = 8501  # portul serverului local Streamlit

# Etichetele celor 4 acte obligatorii la crearea dosarului
UPLOAD_LABELS = {
    "CIM": "CIM — Contract Individual de Muncă",
    "CONTRACT_COMODAT": "CONTRACT COMODAT (sau Contract de Locațiune)",
    "PROCURA": "PROCURA",
    "PASAPORT": "PAȘAPORT (scan)",
}

# Traduceri EN pentru funcții uzuale (pt. CIM bilingv) — completați după nevoie
JOB_TITLES_EN = {
    "Muncitor necalificat în agricultură": "Unskilled agricultural worker",
    "Curier livrator": "Delivery courier",
    "Muncitor necalificat în construcții": "Unskilled construction worker",
    "Muncitor necalificat": "Unskilled worker",
    "Bucătar": "Cook",
    "Ajutor de bucătar": "Kitchen helper",
    "Croitor": "Tailor",
    "Cusător": "Sewing machine operator",
    "Operator în producție": "Production operator",
    "Hamal": "Loader",
    "Măcelar": "Butcher",
    "Brutar": "Baker",
}
