# EUROPERSONAL — Generator documente IGM · Versiunea 1.2.0 (untested)

Aplicație locală (Windows) pentru pregătirea dosarelor lucrătorilor migranți
din Bangladesh și Nepal (decizie + invitație).

## Instalare pe un calculator nou (3 pași)

1. **Instalați Python** de pe https://www.python.org/downloads/
   ⚠️ La instalare bifați obligatoriu **"Add Python to PATH"**
2. **Copiați folderul** `europersonal_app` pe noul calculator (oriunde, ex. Desktop)
3. **Deschideți Command Prompt în folder** (în Explorer: click în bara de
   adresă, scrieți `cmd`, Enter) și rulați:
   ```
   pip install -r requirements.txt
   ```

## Pornire

```
python launcher.py
```

Apare o **iconiță albastră „E" în tray** (lângă ceas; poate fi ascunsă sub
săgeata ^). Click dreapta pe iconiță:

| Opțiune | Ce face |
|---|---|
| Status: Pornit ✅ / Oprit ⛔ | starea serverului |
| ▶ Start App | pornește aplicația în fundal |
| ⏹ Stop App | oprește aplicația |
| 🌐 Deschide în browser | deschide http://localhost:8501 (pornește serverul dacă e oprit) |
| ℹ Info | versiune, status, adresă |
| ✖ Ieșire | oprește tot și închide iconița |

Dublu-click pe iconiță = deschide direct în browser.

Alternativ (fără tray): `streamlit run app.py`

**☁️ Publicare online (Streamlit Cloud):** vedeți ghidul complet în
[DEPLOY.md](DEPLOY.md) — aplicația devine accesibilă de pe orice dispozitiv,
iar actualizările făcute de Claude se publică automat prin GitHub.

**Autentificare (cont implicit de testare):**

| Utilizator | Parola |
|---|---|
| `admin` | `1337` |

## Utilizatori și parole

Conturile sunt stocate local în `users.db` (parolele ca hash SHA-256 cu salt,
niciodată în clar). Sesiunea rămâne activă cât timp tabul de browser e deschis.

- **Utilizator nou:** conectați-vă ca admin → sidebar → „➕ Utilizator nou”
- **Resetare completă:** ștergeți fișierul `users.db` — la următoarea pornire
  se recreează contul implicit admin / 1337
- ⚠️ Schimbați parola admin înainte de utilizarea reală

## Cum adăugați/modificați șabloane

Șabloanele sunt în `templates/` — documente .docx normale în care valorile
variabile sunt scrise ca `{{PLACEHOLDER}}` (ex. `{{NUME_COMPLET}}`,
`{{ADRESA_CAZARE}}`). Pentru a modifica un șablon:

1. Deschideți fișierul .docx din `templates/` în Word
2. Modificați textul fix cum doriți — NU ștergeți placeholder-ele `{{...}}`
3. Salvați. Gata — următoarea generare folosește noul șablon.

Șabloane existente: `CIM.docx`, `DEMERS_INVITATIE.docx`, `INVITATIE_PJ.docx`,
`CONFIRMARE.docx`, `ANEXA_1.docx`

## Secțiunile aplicației

| Secțiune | Ce face |
|---|---|
| **➕ CREAZĂ DOSAR NOU** | fluxul complet în 5 pași numerotați: lucrător (țara cu ★ Nepal/Bangladesh favorite) → 4 acte → adresa din Comodat → pașaport + funcția → generare pachet |
| **📝 GENEREAZĂ DOCUMENT SEPARAT** | butoane vizuale pentru fiecare document; formular doar cu câmpurile necesare documentului ales; descărcare directă, fără dosar |
| **📊 IMPORT DIN EXCEL** | descărcați șablonul → completați câte un rând per lucrător → încărcați → dosarele + pachetele se creează automat pentru toți, cu raport pe fiecare rând și ZIP combinat |
| **📚 EXEMPLE ACTE CANDIDAȚI** | exemplele corect completate, pentru referință |
| **📦 ACTE GATA PENTRU DEPUNERE** | dosarele create, cu status și ZIP descărcabil |
| **📩 DECIZII ȘI INVITAȚII OBȚINUTE** | încărcați ce primiți de la IGM, per dosar |

## Pachetul-țintă (5 documente)

1. ✅ CIM — Contract Individual de Muncă (bilingv RO/EN)
2. ⬜ DEMERS (Model M, formularul lung) — urmează
3. ✅ DEMERS INVITATIE (scrisoarea către Direcția Regională)
4. ✅ INVITATIE (persoană juridică)
5. ✅ CONFIRMARE

ANEXA 1 disponibilă ca opțiune suplimentară.

## Structura folderului

```
europersonal_app/
├── launcher.py      ← porniți de aici (iconiță tray)
├── app.py           ← aplicația propriu-zisă
├── config.py        ← setări + traduceri funcții (EN) pt. CIM
├── users.db         ← utilizatorii (se creează automat; admin/1337)
├── models.py        ← modelele de date + reguli
├── requirements.txt
├── generators/      ← generarea documentelor din șabloane
├── utils/           ← storage (dosare), validators, contract_parser
├── templates/       ← șabloanele .docx cu {{placeholder-e}}
├── exemple/         ← exemplele corecte (secțiunea 2)
├── dosare/          ← dosarele create (se creează automat)
└── test_output/     ← pachete de test
```

Folderele lipsă se creează automat la prima pornire.

## Verificări automate de consistență

- adresa din Contractul de Comodat identică în toate documentele care o conțin
- avertisment dacă adresa editată diferă de cea extrasă din contract
- numele (complet sau despărțit Numele/Prenumele) + nr. pașaport prezente unde e obligatoriu
- coerența țării (un dosar Nepal nu poate conține „BANGLA" etc.)

## Limitări curente (v1.2.0 untested)

- versiune NETESTATĂ în producție — verificați fiecare document generat
- OCR pașapoarte nu există încă — datele se introduc manual
- PDF-urile scanate fără strat de text nu pot fi citite automat
- DEMERS Model M (formularul lung) nu este încă generat automat
- login-ul protejează accesul în aplicație; fișierele de pe disc nu sunt criptate
- la Import Excel, Contractul de Comodat NU se poate atașa per rând — adresa se
  copiază manual în coloana „Adresa cazare” (extragerea automată rămâne în fluxul individual)
- alte țări decât Nepal/Bangladesh apar în listă ca „în curând” — se activează la cerere
