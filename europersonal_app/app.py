"""EUROPERSONAL — Generator documente IGM. Versiunea 1.2.0

Pornire recomandată:  python launcher.py   (iconiță în tray)
Pornire directă:      streamlit run app.py
Autentificare implicită (testare): admin / 1337
"""
import io
import zipfile
from datetime import date, datetime
from pathlib import Path

import streamlit as st

import config
from utils import auth, storage
from utils.contract_parser import parse_contract
from utils.validators import check_address_vs_contract, check_package_consistency
from generators import (AVAILABLE_DOCUMENTS, PACKAGE_DOCUMENTS,
                        generate_package_zip)
from models import (Accommodation, Country, Employment, PackageMeta,
                    PassportData, WorkerPackage, fmt_date)

def _secret(key: str, default: str = "") -> str:
    """Citește din st.secrets fără a crăpa dacă secrets.toml lipsește."""
    try:
        return str(st.secrets.get(key, default))
    except Exception:
        return default


# Streamlit Community Cloud montează codul sub /mount/src — detecție automată
IS_CLOUD = Path("/mount/src").exists() or _secret("deployment") == "cloud"

storage.ensure_folders()
auth.init_db(seed_user=_secret("admin_user", "admin"),
             seed_pass=_secret("admin_password", "1337"))

st.set_page_config(page_title="EUROPERSONAL — Documente IGM", page_icon="📄",
                   layout="wide", initial_sidebar_state="expanded")

# ════════════════════════════════════════════════════════ STIL

st.markdown("""
<style>
/* spațiere generală */
.block-container { padding-top: 1.5rem; }
h3 { margin-top: .4rem; }

/* butoane mari, rotunjite (culorile rămân pe tema activă — light sau dark) */
.stButton > button, .stDownloadButton > button {
    border-radius: 10px; font-weight: 600; padding: .55rem 1.2rem;
}

/* carduri: doar contur + umbră, fundalul rămâne al temei (merge și pe dark) */
div[data-testid="stMain"] div[data-testid="stExpander"] {
    border: 1px solid rgba(128,128,128,.35);
    border-radius: 12px;
}

/* insigna pașilor — culori proprii, vizibilă pe orice temă */
.step-badge {
    display: inline-block; background: #0D3B66; color: #fff;
    border-radius: 50%; width: 1.7rem; height: 1.7rem; text-align: center;
    line-height: 1.7rem; font-weight: 700; margin-right: .5rem;
}

/* ── sidebar albastru (brand) ─────────────────────────────────────────
   Textul e alb DOAR pentru elementele de afișare, NU pentru câmpurile
   de introducere — acestea au fundal alb forțat + text închis, deci
   rămân lizibile indiferent de tema light/dark. */
section[data-testid="stSidebar"] { background: #0D3B66; }
section[data-testid="stSidebar"] :is(h1,h2,h3,h4,p,span,label,strong,em,small,li,summary) {
    color: #F1F5F9;
}
section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] textarea {
    color: #1A202C !important;
    background: #FFFFFF !important;
    caret-color: #1A202C;
}
section[data-testid="stSidebar"] div[data-testid="stExpander"] {
    background: rgba(255,255,255,.07);
    border: 1px solid rgba(255,255,255,.3);
    border-radius: 10px;
}
section[data-testid="stSidebar"] hr { border-color: rgba(255,255,255,.35); }
section[data-testid="stSidebar"] .stButton > button {
    border: 1px solid rgba(255,255,255,.5);
    background: rgba(255,255,255,.08);
}
</style>
""", unsafe_allow_html=True)


def step(n: int, title: str):
    st.markdown(f'<h3><span class="step-badge">{n}</span>{title}</h3>',
                unsafe_allow_html=True)


# ════════════════════════════════════════════════════════ AUTENTIFICARE

if "user" not in st.session_state:
    _, mid, _ = st.columns([1, 1.2, 1])
    with mid:
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.markdown("## 📄 EUROPERSONAL")
        st.caption("Generator documente IGM — autentificare")
        with st.form("login"):
            u = st.text_input("Utilizator", placeholder="admin")
            p = st.text_input("Parola", type="password", placeholder="••••")
            if st.form_submit_button("🔓 Intră în aplicație",
                                     use_container_width=True, type="primary"):
                user = auth.verify_user(u, p)
                if user:
                    st.session_state["user"] = user
                    st.rerun()
                else:
                    st.error("Utilizator sau parolă greșită.")
        st.caption(f"v{config.VERSION} · sesiunea rămâne activă cât timp tabul e deschis")
    st.stop()

USER = st.session_state["user"]

# ════════════════════════════════════════════════════════ NAVIGARE

NAV = [
    "➕ CREAZĂ DOSAR NOU",
    "📝 GENEREAZĂ DOCUMENT SEPARAT",
    "📊 IMPORT DIN EXCEL",
    "📚 EXEMPLE ACTE CANDIDAȚI",
    "📦 ACTE GATA PENTRU DEPUNERE",
    "📩 DECIZII ȘI INVITAȚII OBȚINUTE",
]

with st.sidebar:
    st.markdown("## 📄 EUROPERSONAL")
    st.caption("Documente IGM · Bangladesh & Nepal")
    page = st.radio("Meniu", NAV, label_visibility="collapsed")
    if IS_CLOUD:
        st.warning("☁️ Versiune CLOUD: dosarele NU persistă între reporniri — "
                   "descărcați ZIP-urile imediat după generare!")
    st.divider()
    st.markdown(f"👤 **{USER['username']}** ({USER['role']})")
    if st.button("🚪 Deconectare", use_container_width=True):
        del st.session_state["user"]
        st.rerun()
    if USER["role"] == "admin":
        with st.expander("➕ Utilizator nou"):
            nu = st.text_input("Utilizator nou", key="new_user")
            np_ = st.text_input("Parola nouă", type="password", key="new_pass")
            if st.button("Crează utilizator", key="btn_new_user"):
                try:
                    auth.add_user(nu, np_)
                    st.success(f"Utilizator „{nu}” creat.")
                except ValueError as e:
                    st.error(str(e))
    st.divider()
    st.caption(f'"EUROPERSONAL" SRL · IDNO 1016600043760\nv{config.VERSION}')

ss = st.session_state
ss.setdefault("contract_address", None)
ss.setdefault("contract_details", {})

# ════════════════════════════════════════════════════════ ȚĂRI (favorite)

COUNTRY_OPTIONS = [
    "★ NEPAL",
    "★ BANGLADESH",
    "India (în curând)",
    "Sri Lanka (în curând)",
    "Uzbekistan (în curând)",
    "Turcia (în curând)",
]


def country_select(label: str = "Țara", key: str = "country") -> str | None:
    """Dropdown cu Nepal/Bangladesh ca favorite (★). Returnează 'NEPAL'/'BANGLADESH'
    sau None dacă s-a ales o țară nesuportată încă."""
    choice = st.selectbox(label, COUNTRY_OPTIONS, key=key,
                          help="Nepal și Bangladesh sunt complet suportate. "
                               "Alte țări se adaugă la cerere.")
    if choice.startswith("★"):
        return choice.replace("★", "").strip()
    st.warning(f"„{choice.replace(' (în curând)', '')}” nu este încă suportată — "
               "momentan doar ★ Nepal și ★ Bangladesh.")
    return None


# ════════════════════════════════════════════════════════ FORMULARE COMUNE

def passport_form(is_bd: bool, key_prefix: str = "", sections: set | None = None) -> dict:
    """Câmpurile de pașaport, reutilizate în dosar + documente separate.

    sections: subset din {PASS_MIN, PASS_DATES, PASS_FULL, BD2}; None = toate.
    """
    S = sections or {"PASS_MIN", "PASS_DATES", "PASS_FULL", "BD2"}
    k = lambda name: f"{key_prefix}{name}"
    out = {"passport_number": "", "dob": None, "doi": None, "doe": None,
           "pob": "", "sex": "M", "authority": "", "personal_no": "",
           "father": None, "mother": None, "perm_addr": None}

    cols = st.columns(4)
    i = 0
    if "PASS_MIN" in S:
        out["passport_number"] = cols[i].text_input(
            "Nr. pașaport *", placeholder="A19775898", key=k("pn")).strip().upper(); i += 1
        out["doe"] = cols[i].date_input("Valabil până la *", value=None,
                                        min_value=date.today(),
                                        format="DD.MM.YYYY", key=k("doe")); i += 1
    if "PASS_DATES" in S:
        out["dob"] = cols[i].date_input("Data nașterii *", value=None,
                                        min_value=date(1950, 1, 1), max_value=date.today(),
                                        format="DD.MM.YYYY", key=k("dob")); i += 1
    if "PASS_FULL" in S:
        out["doi"] = cols[i % 4].date_input("Data eliberării", value=None,
                                            format="DD.MM.YYYY", key=k("doi"))
        c2 = st.columns(4)
        out["pob"] = c2[0].text_input("Locul nașterii *", placeholder="CUMILLA / PANCHTHAR",
                                      key=k("pob")).strip().upper()
        out["sex"] = c2[1].selectbox("Sex", ["M", "F"], key=k("sex"))
        out["authority"] = c2[2].text_input(
            "Eliberat de", value="DHAKA" if is_bd else "MOFA, DEPARTMENT OF PASSPORTS",
            key=k("auth")).strip().upper()
        out["personal_no"] = c2[3].text_input("Nr. personal", key=k("pno")).strip()
    if "BD2" in S:
        if is_bd:
            b = st.columns(3)
            out["father"] = b[0].text_input("Prenume tată (pag. 2) *",
                                            placeholder="ABDUL MOMIN", key=k("fa")).strip().upper()
            out["mother"] = b[1].text_input("Prenume mamă (pag. 2)",
                                            placeholder="KOHINUR BEGUM", key=k("mo")).strip().upper()
            out["perm_addr"] = b[2].text_input("Adresă permanentă (pag. 2)",
                                               key=k("pa")).strip().upper()
        else:
            st.caption("🇳🇵 Nepal: câmpurile tată/mamă/adresă rămân goale — conform exemplelor corecte.")
    return out


def build_package(country: str, surname: str, given_name: str, pdata: dict,
                  address: str = "-", contract_type: str = "locațiune",
                  contract_number: str = "F/N", contract_date=None,
                  job_title: str = "-", job_title_en: str = "",
                  occupation_code: str = "", demers_number: str = "-",
                  demers_date=None, cim_number: str = "-", cim_date=None) -> WorkerPackage:
    """Construiește pachetul; câmpurile necolectate primesc valori neutre."""
    is_bd = country == "BANGLADESH"
    return WorkerPackage(
        passport=PassportData(
            surname=surname, given_name=given_name, country=Country(country),
            date_of_birth=pdata.get("dob") or date(1990, 1, 1),
            place_of_birth=pdata.get("pob") or "-",
            sex=pdata.get("sex") or "M",
            passport_number=pdata.get("passport_number") or "-",
            personal_no=pdata.get("personal_no") or None,
            date_of_issue=pdata.get("doi") or date.today(),
            date_of_expiry=pdata.get("doe") or date.today(),
            issuing_authority=pdata.get("authority")
                or ("DHAKA" if is_bd else "MOFA, DEPARTMENT OF PASSPORTS"),
            father_name=(pdata.get("father") or ("-" if is_bd else None)),
            mother_name=pdata.get("mother") or None,
            permanent_address=pdata.get("perm_addr") or None),
        accommodation=Accommodation(address=address or "-", contract_type=contract_type,
                                    contract_number=contract_number,
                                    contract_date=contract_date or date.today()),
        employment=Employment(job_title=job_title or "-", job_title_en=job_title_en,
                              occupation_code=occupation_code),
        meta=PackageMeta(demers_number=demers_number or "-",
                         demers_date=demers_date or date.today(),
                         cim_number=cim_number or "-",
                         cim_date=cim_date or date.today()),
    )


# ════════════════════════════════════════════════════════ 1. CREAZĂ DOSAR NOU

def page_dosar_nou():
    st.header("➕ Crează dosar nou")
    st.caption("Fluxul complet: date lucrător → acte → cazare → pașaport & funcție → generare pachet")

    step(1, "Date lucrător")
    c1, c2, c3 = st.columns([2, 2, 1.4])
    surname = c1.text_input("Numele (Surname — exact ca în pașaport) *",
                            placeholder="UDDIN").strip().upper()
    given_name = c2.text_input("Prenumele (Given Name) *",
                               placeholder="MD MAIN").strip().upper()
    with c3:
        country = country_select()
    if country is None:
        st.stop()
    is_bd = country == "BANGLADESH"
    full_name = f"{surname} {given_name}".strip()

    step(2, "Acte obligatorii (4)")
    uploads = {}
    u1, u2 = st.columns(2)
    for col, keys in ((u1, ("CIM", "CONTRACT_COMODAT")), (u2, ("PROCURA", "PASAPORT"))):
        with col:
            for key in keys:
                uploads[key] = st.file_uploader(config.UPLOAD_LABELS[key],
                                                type=["docx", "pdf", "jpg", "jpeg", "png"],
                                                key=f"up_{key}")

    if uploads["CONTRACT_COMODAT"] is not None and uploads["CONTRACT_COMODAT"].name.lower().endswith((".docx", ".pdf")):
        try:
            result = parse_contract(uploads["CONTRACT_COMODAT"].getvalue(),
                                    uploads["CONTRACT_COMODAT"].name)
            if result["addresses"]:
                st.success("✅ Adresă extrasă automat din Contractul de Comodat")
                chosen = st.selectbox("Adrese găsite (alegeți cea corectă):", result["addresses"])
                if ss.get("contract_address") != chosen:
                    ss["contract_address"] = chosen
                    ss["contract_details"] = {k: v for k, v in result.items()
                                              if k.startswith("contract_")}
            elif not result["text_found"]:
                st.warning("Contract scanat fără strat de text — introduceți adresa manual mai jos.")
            else:
                st.warning("Nu am găsit adresa în contract — introduceți-o manual mai jos.")
        except Exception as e:
            st.error(f"Eroare la citirea contractului: {e}")

    step(3, "Adresa de cazare (din Contract de Comodat)")
    address = st.text_input("Adresa folosită în TOATE documentele (editabilă) *",
                            value=ss.get("contract_address") or "",
                            placeholder="mun. Chișinău, str. București, nr. 83, ap. 9").strip()
    warn = check_address_vs_contract(address, ss.get("contract_address")) if address else None
    if warn:
        st.warning(warn)

    det = ss.get("contract_details", {})
    k1, k2, k3 = st.columns(3)
    contract_type = k1.selectbox("Tip contract", ["locațiune", "comodat"],
                                 index=1 if det.get("contract_type") == "comodat" else 0)
    contract_number = k2.text_input("Nr. contract", value=det.get("contract_number", "F/N")).strip()
    default_cd = None
    if det.get("contract_date"):
        try:
            default_cd = datetime.strptime(det["contract_date"], "%d.%m.%Y").date()
        except ValueError:
            pass
    contract_date = k3.date_input("Data contract *", value=default_cd, format="DD.MM.YYYY")

    step(4, "Pașaport & funcție")
    pdata = passport_form(is_bd)
    st.markdown("**Funcția / Poziția** (folosită în CIM și în DEMERS)")
    j1, j2, j3 = st.columns(3)
    job_title = j1.text_input("Funcția (RO) *", placeholder="Curier livrator").strip()
    job_title_en = j2.text_input("Funcția (EN, pentru CIM)",
                                 value=config.JOB_TITLES_EN.get(job_title, ""),
                                 placeholder="Delivery courier").strip()
    occupation_code = j3.text_input("Cod CORM", placeholder="962101").strip()
    m1, m2, m3, m4 = st.columns(4)
    demers_number = m1.text_input("Nr. demers *", placeholder="8B/25").strip()
    demers_date = m2.date_input("Data demers", value=date.today(), format="DD.MM.YYYY")
    cim_number = m3.text_input("Nr. CIM *", placeholder="8B/26", value=demers_number).strip()
    cim_date = m4.date_input("Data CIM", value=date.today(), format="DD.MM.YYYY")

    step(5, "Verificare & generare")
    missing = []
    if not surname: missing.append("Numele")
    if not given_name: missing.append("Prenumele")
    for key, up in uploads.items():
        if up is None:
            missing.append(config.UPLOAD_LABELS[key].split(" — ")[0])
    if not address: missing.append("Adresa de cazare")
    if not contract_date: missing.append("Data contractului")
    if not pdata["passport_number"]: missing.append("Nr. pașaport")
    if not pdata["dob"]: missing.append("Data nașterii")
    if not pdata["doe"]: missing.append("Valabilitatea pașaportului")
    if not job_title: missing.append("Funcția")
    if not demers_number: missing.append("Nr. demers")
    if not cim_number: missing.append("Nr. CIM")
    if is_bd and not pdata["father"]: missing.append("Prenume tată (obligatoriu Bangladesh)")

    if missing:
        st.info("Pentru generare completați: " + ", ".join(missing))
        return

    try:
        package = build_package(country, surname, given_name, pdata,
                                address=address, contract_type=contract_type,
                                contract_number=contract_number, contract_date=contract_date,
                                job_title=job_title, job_title_en=job_title_en,
                                occupation_code=occupation_code,
                                demers_number=demers_number, demers_date=demers_date,
                                cim_number=cim_number, cim_date=cim_date)
    except Exception as e:
        st.error(f"Eroare de validare: {e}")
        return

    st.markdown(f"""
| | |
|---|---|
| **Dosar** | {package.passport.full_name} ({package.passport.country_ro}) |
| **Adresa de cazare** | {package.accommodation.address} |
| **Contract** | {contract_type} nr. {contract_number} din {fmt_date(contract_date)} |
| **Funcția** | {job_title} / {job_title_en or "—"} |
""")
    selected_docs = st.multiselect("Documente de generat (pachetul standard preselectat):",
                                   list(AVAILABLE_DOCUMENTS.keys()),
                                   default=PACKAGE_DOCUMENTS)

    if st.button("📦 Crează dosarul și generează pachetul", type="primary",
                 use_container_width=True, disabled=not selected_docs):
        with st.spinner("Se generează documentele..."):
            storage.create_dosar(full_name, country)
            for key, up in uploads.items():
                storage.save_upload(full_name, key, up.getvalue(), up.name)
            zip_bytes, filenames = generate_package_zip(package, selected_docs)
            files = {}
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                for n in zf.namelist():
                    files[n] = zf.read(n)
                    storage.save_generated(full_name, n, files[n])
            zip_name = f"PACHET_{storage._safe_name(full_name)}.zip"
            storage.save_generated(full_name, zip_name, zip_bytes)
            storage.update_meta(full_name, adresa_cazare=address,
                                status="acte generate — de verificat",
                                generat_la=datetime.now().strftime("%d.%m.%Y %H:%M"))
        warnings = check_package_consistency(files, package)
        if warnings:
            for w in warnings:
                st.warning(w)
        else:
            st.success("✅ Toate verificările de consistență au trecut.")
        st.success(f"Dosar salvat: `dosare/{storage._safe_name(full_name)}/`")
        st.download_button(f"⬇️ Descarcă {zip_name}", data=zip_bytes,
                           file_name=zip_name, mime="application/zip",
                           use_container_width=True)


# ════════════════════════════════════════════════════════ 2. DOCUMENT SEPARAT

# ce secțiuni de formular cere fiecare document
DOC_FORMS = {
    "CIM (Contract Individual de Muncă)":
        {"PASS_MIN", "PASS_DATES", "PASS_FULL", "JOB", "JOB_EN", "CIM_META"},
    "DEMERS INVITATIE (scrisoare Direcția Regională)":
        {"PASS_MIN", "JOB", "DEMERS_META"},
    "INVITATIE (persoană juridică)":
        {"PASS_MIN", "PASS_DATES", "PASS_FULL", "BD2"},
    "CONFIRMARE": {"ADDR", "CONTRACT"},
    "ANEXA 1 (opțional)": {"PASS_MIN", "PASS_DATES", "ADDR"},
}
DOC_ICONS = {
    "CIM (Contract Individual de Muncă)": "📑",
    "DEMERS INVITATIE (scrisoare Direcția Regională)": "✉️",
    "INVITATIE (persoană juridică)": "🎫",
    "CONFIRMARE": "🏠",
    "ANEXA 1 (opțional)": "📋",
}


def page_document_separat():
    st.header("📝 Generează document separat")
    st.caption("Completați doar câmpurile necesare documentului ales — fără a crea un dosar.")

    ss.setdefault("doc_sep", None)
    cols = st.columns(len(DOC_FORMS))
    for col, doc in zip(cols, DOC_FORMS):
        short = doc.split(" (")[0]
        if col.button(f"{DOC_ICONS[doc]}\n\n**{short}**", key=f"pick_{doc}",
                      use_container_width=True,
                      type="primary" if ss["doc_sep"] == doc else "secondary"):
            ss["doc_sep"] = doc
            st.rerun()

    doc = ss["doc_sep"]
    if not doc:
        st.info("👆 Alegeți documentul pe care doriți să-l generați.")
        return
    S = DOC_FORMS[doc]
    st.divider()
    st.subheader(f"{DOC_ICONS[doc]} {doc}")

    c1, c2, c3 = st.columns([2, 2, 1.4])
    surname = c1.text_input("Numele *", placeholder="UDDIN", key="ds_sn").strip().upper()
    given_name = c2.text_input("Prenumele *", placeholder="MD MAIN", key="ds_gn").strip().upper()
    with c3:
        country = country_select(key="ds_country")
    if country is None:
        return
    is_bd = country == "BANGLADESH"

    pdata = passport_form(is_bd, key_prefix="ds_",
                          sections=S & {"PASS_MIN", "PASS_DATES", "PASS_FULL", "BD2"})

    address, ctype, cnr, cdate = "-", "locațiune", "F/N", None
    if "ADDR" in S:
        address = st.text_input("Adresa de cazare (exact ca în Contractul de Comodat) *",
                                placeholder="mun. Chișinău, str. București, nr. 83, ap. 9",
                                key="ds_addr").strip()
    if "CONTRACT" in S:
        k1, k2, k3 = st.columns(3)
        ctype = k1.selectbox("Tip contract", ["locațiune", "comodat"], key="ds_ct")
        cnr = k2.text_input("Nr. contract", value="F/N", key="ds_cn").strip()
        cdate = k3.date_input("Data contract *", value=None, format="DD.MM.YYYY", key="ds_cd")

    job_title = job_title_en = ""
    if "JOB" in S:
        j1, j2 = st.columns(2)
        job_title = j1.text_input("Funcția (RO) *", placeholder="Curier livrator",
                                  key="ds_job").strip()
        if "JOB_EN" in S:
            job_title_en = j2.text_input("Funcția (EN) *",
                                         value=config.JOB_TITLES_EN.get(job_title, ""),
                                         key="ds_job_en").strip()

    demers_number, demers_date = "-", None
    cim_number, cim_date = "-", None
    if "DEMERS_META" in S:
        m1, m2 = st.columns(2)
        demers_number = m1.text_input("Nr. demers *", placeholder="8B/25", key="ds_dn").strip()
        demers_date = m2.date_input("Data demers", value=date.today(),
                                    format="DD.MM.YYYY", key="ds_dd")
    if "CIM_META" in S:
        m1, m2 = st.columns(2)
        cim_number = m1.text_input("Nr. CIM *", placeholder="8B/26", key="ds_cimn").strip()
        cim_date = m2.date_input("Data CIM", value=date.today(),
                                 format="DD.MM.YYYY", key="ds_cimd")

    # câmpuri lipsă pentru documentul ales
    missing = []
    if not surname: missing.append("Numele")
    if not given_name: missing.append("Prenumele")
    if "PASS_MIN" in S and not pdata["passport_number"]: missing.append("Nr. pașaport")
    if "PASS_MIN" in S and not pdata["doe"]: missing.append("Valabil până la")
    if "PASS_DATES" in S and not pdata["dob"]: missing.append("Data nașterii")
    if "PASS_FULL" in S and not pdata["pob"]: missing.append("Locul nașterii")
    if "BD2" in S and is_bd and not pdata["father"]: missing.append("Prenume tată")
    if "ADDR" in S and not address: missing.append("Adresa de cazare")
    if "CONTRACT" in S and not cdate: missing.append("Data contractului")
    if "JOB" in S and not job_title: missing.append("Funcția")
    if "DEMERS_META" in S and not demers_number: missing.append("Nr. demers")
    if "CIM_META" in S and not cim_number: missing.append("Nr. CIM")

    if missing:
        st.info("Completați: " + ", ".join(missing))
        return

    try:
        package = build_package(country, surname, given_name, pdata,
                                address=address, contract_type=ctype,
                                contract_number=cnr, contract_date=cdate,
                                job_title=job_title, job_title_en=job_title_en,
                                demers_number=demers_number, demers_date=demers_date,
                                cim_number=cim_number, cim_date=cim_date)
        gen_fn, name_fn = AVAILABLE_DOCUMENTS[doc]
        fname = name_fn(package)
        if st.button(f"📄 Generează {doc.split(' (')[0]}", type="primary",
                     use_container_width=True, key="ds_gen"):
            import tempfile
            with tempfile.TemporaryDirectory() as tmp:
                path = gen_fn(package, Path(tmp) / fname)
                data = path.read_bytes()
            st.success(f"Generat: {fname}")
            st.download_button(f"⬇️ Descarcă {fname}", data=data, file_name=fname,
                               use_container_width=True, key="ds_dl",
                               mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    except Exception as e:
        st.error(f"Eroare: {e}")


# ════════════════════════════════════════════════════════ 3. IMPORT DIN EXCEL

def page_excel():
    from utils import excel_import
    st.header("📊 Import din Excel — creare automată în masă")
    st.caption("Pentru procesarea mai multor lucrători simultan: descărcați șablonul, "
               "completați câte un rând per lucrător, încărcați-l înapoi.")

    step(1, "Descărcați șablonul")
    st.download_button("⬇️ Descarcă șablonul Excel (cu foaia „Exemplu”)",
                       data=excel_import.build_template(),
                       file_name="SABLON_IMPORT_LUCRATORI.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    st.caption("Coloanele marcate cu * sunt obligatorii. Datele calendaristice: ZZ.LL.AAAA. "
               "Adresa de cazare se copiază EXACT din Contractul de Comodat.")

    step(2, "Încărcați fișierul completat")
    up = st.file_uploader("Fișierul Excel completat", type=["xlsx"], key="xl_up")
    if up is None:
        return

    rows, errors = excel_import.parse_workbook(up.getvalue())
    if errors:
        st.error(f"{len(errors)} rând(uri) cu probleme — corectați și reîncărcați:")
        for e in errors:
            st.markdown(f"- ⚠️ {e}")
    if not rows:
        if not errors:
            st.warning("Fișierul nu conține niciun rând completat în foaia „Lucrători”.")
        return

    st.success(f"✅ {len(rows)} lucrător(i) valid(izi) pregătiți de import:")
    st.table([{"Nume": f"{r['surname']} {r['given_name']}", "Țara": r["country"],
               "Pașaport": r["passport_number"], "Funcția": r["job_title"],
               "Adresa": r["address"][:50]} for r in rows])

    step(3, "Creați dosarele")
    if st.button(f"🚀 Crează {len(rows)} dosare + generează pachetele", type="primary",
                 use_container_width=True):
        with st.spinner(f"Se procesează {len(rows)} lucrători..."):
            results, big_zip = excel_import.process_bulk(rows)
        ok = sum(1 for r in results if r["status"] == "ok")
        warn = sum(1 for r in results if r["status"] == "avertisment")
        err = sum(1 for r in results if r["status"] == "eroare")
        c1, c2, c3 = st.columns(3)
        c1.metric("✅ Reușite", ok)
        c2.metric("⚠️ Cu avertismente", warn)
        c3.metric("❌ Erori", err)
        icons = {"ok": "✅", "avertisment": "⚠️", "eroare": "❌"}
        st.table([{"": icons[r["status"]], "Nume": r["nume"], "Detalii": r["detalii"][:100]}
                  for r in results])
        if ok or warn:
            st.download_button("⬇️ Descarcă TOATE pachetele (ZIP combinat)",
                               data=big_zip, file_name="PACHETE_IMPORT_EXCEL.zip",
                               mime="application/zip", use_container_width=True)
        st.caption("Dosarele au fost salvate și apar în „ACTE GATA PENTRU DEPUNERE”.")


# ════════════════════════════════════════════════════════ 4-6. restul paginilor

def page_exemple():
    st.header("📚 Exemple acte candidați")
    st.caption("Exemplele corect completate (Bangladesh și Nepal) — pentru referință rapidă.")
    exemple_dir = Path(__file__).parent / "exemple"
    files = sorted(exemple_dir.glob("*")) if exemple_dir.exists() else []
    if not files:
        st.info("Folderul `exemple/` este gol — puneți acolo exemplele corecte.")
    for f in files:
        col1, col2 = st.columns([4, 1])
        col1.write(f"📄 {f.name}")
        col2.download_button("⬇️ Descarcă", data=f.read_bytes(), file_name=f.name,
                             key=f"ex_{f.name}")


def page_acte_gata():
    st.header("📦 Acte gata pentru depunere")
    dosare = storage.list_dosare()
    if not dosare:
        st.info("Niciun dosar încă. Creați primul în „CREAZĂ DOSAR NOU” sau prin „IMPORT DIN EXCEL”.")
    for meta in dosare:
        with st.expander(f"📁 {meta['nume_complet']} — {meta.get('tara','?')} · "
                         f"status: {meta.get('status','?')} · creat {meta.get('creat_la','?')}"):
            st.write(f"**Adresa de cazare:** {meta.get('adresa_cazare') or '—'}")
            gen_files = storage.list_files(meta["nume_complet"], "acte_generate")
            zips = [f for f in gen_files if f.suffix == ".zip"]
            docs = [f for f in gen_files if f.suffix != ".zip"]
            if docs:
                st.write("**Documente generate:** " + " · ".join(f.name for f in docs))
            for z in zips:
                st.download_button(f"⬇️ Descarcă {z.name}", data=z.read_bytes(),
                                   file_name=z.name, key=f"zip_{meta['_folder']}_{z.name}")
            if not gen_files:
                st.caption("Nimic generat încă pentru acest dosar.")


def page_decizii():
    st.header("📩 Decizii și invitații obținute")
    dosare = storage.list_dosare()
    if not dosare:
        st.info("Niciun dosar încă. Creați primul în „CREAZĂ DOSAR NOU”.")
        return
    names = [m["nume_complet"] for m in dosare]
    sel = st.selectbox("Dosar (lucrător):", names)
    up = st.file_uploader("Încărcați decizia / invitația primită de la IGM (PDF sau imagine)",
                          type=["pdf", "jpg", "jpeg", "png"], key="dec_up")
    if up is not None and st.button("💾 Salvează în dosar", type="primary"):
        path = storage.save_decizie(sel, up.getvalue(), up.name)
        storage.update_meta(sel, status="decizie/invitație primită")
        st.success(f"Salvat: `{path.name}`")

    st.subheader("Documente primite pentru acest dosar")
    received = storage.list_files(sel, "decizii_invitatii")
    if not received:
        st.caption("Nimic încărcat încă.")
    for f in received:
        col1, col2 = st.columns([4, 1])
        col1.write(f"📩 {f.name}")
        col2.download_button("⬇️ Descarcă", data=f.read_bytes(), file_name=f.name,
                             key=f"dec_{f.name}")


# ════════════════════════════════════════════════════════ RUTARE

PAGES = {
    NAV[0]: page_dosar_nou,
    NAV[1]: page_document_separat,
    NAV[2]: page_excel,
    NAV[3]: page_exemple,
    NAV[4]: page_acte_gata,
    NAV[5]: page_decizii,
}
PAGES[page]()
