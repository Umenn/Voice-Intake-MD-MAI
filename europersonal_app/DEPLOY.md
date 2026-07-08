# Publicare pe Streamlit Community Cloud — ghid pas cu pas

## ⚠️ Citiți întâi — date personale

Aplicația procesează date personale (pașapoarte, nume, adrese). Pe Streamlit
Community Cloud (gratuit) aplicația este **accesibilă public** — oricine are
link-ul vede pagina de login. Protecții incluse:

- login obligatoriu (utilizator + parolă din Secrets)
- `.gitignore` exclude TOATE datele personale de pe GitHub
  (`dosare/`, `exemple/`, `test_output/`, `users.db`)
- ⚠️ dar datele încărcate în aplicație tranzitează serverele Streamlit.
  Pentru date reale, varianta locală (`python launcher.py`) rămâne cea sigură.
  Versiunea cloud e potrivită pentru acces de pe orice dispozitiv + testare.

## Pasul 1 — Creați repository-ul pe GitHub (o singură dată)

1. Cont pe https://github.com (gratuit) dacă nu aveți
2. https://github.com/new →
   - Repository name: `europersonal-app`
   - **Private** ✅ (important!)
   - NU bifați "Add README" (avem deja)
   - Create repository

## Pasul 2 — Urcați codul (o singură dată)

În Command Prompt, în folderul `europersonal_app`:

```
git remote add origin https://github.com/NUMELE_VOSTRU/europersonal-app.git
git branch -M main
git push -u origin main
```

(La prima comandă `push`, Windows deschide fereastra de autentificare GitHub —
conectați-vă în browser.)

Repository-ul local e deja pregătit (git init + commit făcute de Claude);
`.gitignore` garantează că dosarele și exemplele cu date reale NU se urcă.

## Pasul 3 — Conectați Streamlit Cloud (o singură dată)

1. https://share.streamlit.io → Sign in with GitHub
2. **New app** →
   - Repository: `NUMELE_VOSTRU/europersonal-app`
   - Branch: `main`
   - Main file path: `app.py`
3. **Advanced settings → Secrets** — lipiți (cu valorile voastre!):
   ```toml
   admin_user = "admin"
   admin_password = "1337"
   deployment = "cloud"
   ```
4. **Deploy** — în 2-3 minute primiți link-ul public
   (ex. `https://europersonal-app.streamlit.app`)

Link-ul funcționează de pe orice dispozitiv: PC, telefon, tabletă.

## Cum se fac actualizările pe viitor (workflow cu Claude)

1. Îi cereți lui Claude o modificare (ex. „adaugă generatorul Model M”)
2. Claude modifică codul local, testează, apoi rulează:
   ```
   git add -A && git commit -m "descrierea modificării" && git push
   ```
3. Streamlit Cloud detectează push-ul și **redeployează automat** în 1-2 minute
4. Reîncărcați pagina — versiunea nouă e live (verificați nr. versiunii din sidebar)

Pentru ca Claude să poată face push direct, îi dați o singură dată un
**Personal Access Token** GitHub:
GitHub → Settings → Developer settings → Personal access tokens →
Fine-grained tokens → Generate: acces doar la repo `europersonal-app`,
permisiune „Contents: Read and write”. Trimiteți token-ul lui Claude în chat
când cereți prima actualizare (poate fi revocat oricând).

## Limitări cunoscute pe cloud (v1.2.0)

| Ce | Local | Cloud |
|---|---|---|
| Dosarele (`dosare/`) | persistă pe disc | ❌ se pierd la repornire — descărcați ZIP-urile imediat |
| Utilizatorii adăugați în aplicație | persistă | ❌ se pierd la repornire (admin-ul din Secrets rămâne) |
| Folderul `exemple/` | plin | gol (exclus de pe GitHub — conține date reale) |
| Iconița din tray (`launcher.py`) | ✅ | nu se aplică (serverul e la Streamlit) |
