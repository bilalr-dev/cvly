# Cvly

**Language / Langue:** [English](#english) · [Français](#français)

AI-powered job application helper that runs on your computer.  
Assistant de candidature alimenté par l’IA, qui tourne sur votre ordinateur.

---

<a id="english"></a>

# English

**Index:** 
[1. Project context](#1-project-context) 
[2. Techniques & research](#2-techniques--research)
[3. Stack](#3-stack)
[4. Project structure](#4-project-structure)
[5. Environment setup](#5-environment-setup-env-file)
[6. How to run](#6-how-to-run)
[7. How to collaborate](#7-how-to-collaborate)

---

## 1. Project context

Cvly is a **local job-application agent**. You upload your résumé, set your search preferences, and Cvly:

1. Reads your CV (PDF or Word)
2. Searches several free job boards at once
3. Scores how well each offer matches you
4. Rewrites CV bullets and a cover letter for jobs you choose
5. Lets you review everything before saving
6. Optionally logs approved applications in a Google Sheet

It opens in your browser at `http://localhost:8000`. No cloud account for Cvly itself - only free API keys you put in a `.env` file.

**Design principles**

- Free-tier APIs only (personal use)
- One file = one responsibility
- Prefer maintained libraries over custom code
- Nothing is saved until you click Approve

---

## 2. Techniques & research

### Pipeline (what happens when you click Run)

```
Upload résumé (PDF/DOCX)
        │
        ▼
Resume parser ──► structured profile (Gemini, temperature 0.0)
        │
        ▼
Job discovery ──► France Travail + Adzuna + Arbeitnow + Remotive
                  + Jobicy + JSearch + La Bonne Alternance
        │
        ▼
Filters ──► dedup → seniority → contract type → title relevance → max 40 jobs
        │
        ▼
JD parser ──► structured requirements per offer (Gemini)
        │
        ▼
CV analyser ──► Pass 1: deterministic score │ Pass 2: qualitative ATF analysis
        │
        ▼
Tailoring ──► two-stage keyword rewrite + cover letter
        │
        ▼
Quality gates ──► deterministic checker + Gemini evaluator + Groq critic
                  + one-shot self-correction
        │
        ▼
Human review ──► Approve → Markdown files + Google Sheets tracking
```

### Anti-hallucination (why the AI does not invent skills)

LLMs often invent numbers, tools, or skills. Cvly stacks several defenses, inspired by [Grounded Optimization](https://arxiv.org/abs/2607.01457):

| Layer | What it does |
|---|---|
| 1. Prompt grounding | Prompts forbid fabrication; XML tags separate your real CV from the job ad |
| 2. Two-stage keywords | Inspired by [Chain-of-Verification](https://arxiv.org/abs/2309.11495): only keywords backed by your CV are rewritten |
| 3. Deterministic checker | Code (no LLM) flags new numbers / short tech names not in the original CV |
| 4. Evaluator agent | A second Gemini call reviews bullets as a critic |
| 5. Groq critic + self-correct | A **different** model (Groq) reviews Gemini’s work; Gemini then fixes flagged issues once |
| 6. Human approve | You see warnings in plain language; nothing is saved until you approve |

### Translation quality (French / English)

Informed by:

- [Google multi-stage translation](https://arxiv.org/abs/2409.06790) (Briakou et al., 2024) - translation brief (document type, audience, register)
- [Iterative translation refinement](https://arxiv.org/abs/2306.03856) (Chen et al., EAMT 2024)
- Target-language prompting (IJONIS, 2026) - French instructions written in French to avoid awkward “translationese”
- Concrete verb maps and anglicism blacklist for CVs

### Job discovery filters

```
Several APIs in parallel → remove duplicates → seniority filter
  → contract reclassification → contract filter → title relevance → cap at 40
```

France Travail uses INSEE city codes (not free-text city names). La Bonne Alternance is only called when you select **alternance** or **stage**, and uses ROME codes resolved from your job titles.

### Research references (summary)

| Source | Applied in Cvly |
|---|---|
| [Grounded Optimization](https://arxiv.org/abs/2607.01457) | Multi-layer anti-hallucination, evaluator |
| [Chain-of-Verification](https://arxiv.org/abs/2309.11495) | Two-stage keyword validation |
| [Google translation brief](https://arxiv.org/abs/2409.06790) | Cover letter / CV translation context |
| [Iterative refinement](https://arxiv.org/abs/2306.03856) | Native-quality translation |
| Target-language prompting (IJONIS, 2026) | French prompts in French |
| Harvard Career Services | STAR bullet formula |
| La Prompterie + HRLens | French cover-letter conventions |

---

## 3. Stack

| Piece | Version / choice | Role |
|---|---|---|
| Python | 3.12+ | Runtime |
| FastAPI | 0.115.12 | Local web API |
| Uvicorn | 0.34.3 | Server |
| Jinja2 | 3.1.6 | HTML pages |
| HTMX | 2.x (CDN) | Page updates without a heavy frontend |
| Tailwind CSS | v3 Play CDN | Styling (no build step) |
| Gemini | `gemini-3.1-flash-lite` | Parsing, scoring text, rewriting |
| Groq | `llama-3.1-8b-instant` (default) | Independent critic (optional but recommended) |
| aiohttp | 3.14.1 | Parallel job API calls |
| Pydantic / pydantic-settings | 2.x | Data models + `.env` loading |
| pdfplumber / python-docx | - | Read PDF / Word résumés |
| gspread / google-auth | - | Optional Google Sheets tracking |

**Job sources**

| Source | Key needed? | Notes |
|---|---|---|
| France Travail | Yes (recommended for France) | Largest French inventory |
| Adzuna | Yes (recommended) | Broader European listings |
| Arbeitnow | No | ATS boards (Greenhouse, Lever, …) |
| Remotive | No | Remote roles |
| Jobicy | No | Remote roles |
| JSearch (RapidAPI) | Optional | Extra coverage |
| La Bonne Alternance | Yes (for alternance/stage) | French apprenticeships / internships |

---

## 4. Project structure

Test folders and cache files are omitted on purpose.

```
cvly/
├── backend/
│   ├── main.py                     # App entry (FastAPI)
│   ├── config.py                   # Reads .env settings
│   ├── state.py                    # In-memory state + i18n strings
│   ├── prompts.py                  # All LLM prompts (research-referenced)
│   ├── models/                     # Frozen Pydantic models
│   │   ├── resume.py
│   │   ├── resume_profile.py
│   │   ├── job.py
│   │   ├── match.py
│   │   ├── tailoring.py
│   │   └── preferences.py
│   ├── modules/                    # One module per pipeline stage
│   │   ├── resume_parser.py
│   │   ├── job_discovery.py
│   │   ├── jd_parser.py
│   │   ├── cv_analyser.py
│   │   ├── atf_analyser.py
│   │   ├── tailoring.py
│   │   ├── cover_letter.py
│   │   ├── evaluator_agent.py
│   │   ├── critical_evaluator.py   # Groq critic
│   │   ├── self_corrector.py       # One-shot Gemini fix after Groq review
│   │   ├── hallucination_checker.py
│   │   ├── output_generator.py
│   │   └── sheets_tracker.py
│   ├── services/
│   │   ├── gemini_llm.py
│   │   ├── gemini_embeddings.py
│   │   ├── groq_llm.py
│   │   ├── rate_limiter.py
│   │   └── job_apis/
│   │       ├── base.py
│   │       ├── france_travail.py
│   │       ├── adzuna.py
│   │       ├── arbeitnow.py
│   │       ├── remotive.py
│   │       ├── jobicy.py
│   │       ├── jsearch.py
│   │       └── la_bonne_alternance.py
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── settings.py
│   │   ├── pipeline.py
│   │   ├── results.py
│   │   ├── preview.py
│   │   └── ws.py                   # Live progress (WebSocket)
│   └── utils/
│       ├── constants.py
│       ├── dedup.py
│       ├── cosine.py
│       └── location_filter.py
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   ├── results.html
│   │   ├── preview.html
│   │   ├── view_document.html
│   │   └── partials/               # HTMX fragments
│   └── static/
│       └── favicon.ico
├── config/                         # Place google_service_account.json here
├── cache/                          # Saved preferences / profile (local)
├── output/                         # Approved résumé & cover letters (.md)
├── start.sh / start.bat            # One-command start
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

**Pages**

| Page | URL | Purpose |
|---|---|---|
| Dashboard | `/` | Stats, start a run |
| Settings | `/settings` | Upload CV, search preferences |
| Results | `/results` | Scored matches, filters |
| Preview | `/preview/{job_id}` | Compare bullets, edit cover letter, approve |

---

## 5. Environment setup (`.env` file)

You only need to do this once.

### Step 0 - Create the file

```bash
cd cvly
cp .env.example .env
```

Open `.env` in any text editor. Leave unused optional keys empty.

---

### Step 1 - Google Gemini (REQUIRED)

1. Open **https://aistudio.google.com/apikey**
2. Sign in with your Google account
3. Click **Create API key**
4. Copy the key into `.env`:

```env
GEMINI_API_KEY=paste_your_key_here
```

Free tier is enough for personal use (rate limits apply).

---

### Step 2 - Groq (recommended - independent AI critic)

1. Open **https://console.groq.com**
2. Create an account / sign in
3. Open **https://console.groq.com/keys**
4. Create an API key and paste it:

```env
GROQ_API_KEY=paste_your_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

Keep `llama-3.1-8b-instant` unless you know you need a larger model (larger models hit free limits faster).

---

### Step 3 - France Travail (recommended for the French market)

1. Create an account at **https://francetravail.io**
2. Open the Offres d’emploi API page: **https://francetravail.io/data/api/offres-emploi**
3. Click **Utiliser l’API**
4. Create an application (example name: `cvly`, example URL: `https://example.com`)
5. **Subscribe the app to “Offres d’emploi v2”** (separate step from creating the app - do not skip)
6. In the application settings, copy:
   - **Identifiant client** (starts with `PAR_...`) → `FRANCE_TRAVAIL_CLIENT_ID`
   - **Clé secrète** → `FRANCE_TRAVAIL_CLIENT_SECRET`

```env
FRANCE_TRAVAIL_CLIENT_ID=PAR_...
FRANCE_TRAVAIL_CLIENT_SECRET=...
```

If you see `invalid_client`, the app is usually missing the **Offres d’emploi v2** subscription.

---

### Step 4 - Adzuna (recommended)

1. Open **https://developer.adzuna.com/**
2. Sign up (application type: **Personal or academic research**)
3. From the dashboard, copy App ID and App Key:

```env
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

---

### Step 5 - Arbeitnow, Remotive, Jobicy (automatic)

No keys. They start as soon as Cvly runs.

---

### Step 6 - JSearch / RapidAPI (optional)

1. Open **https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch**
2. Subscribe to the **BASIC** plan ($0.00/mo)
3. Copy `X-RapidAPI-Key`:

```env
JSEARCH_API_KEY=...
```

---

### Step 7 - La Bonne Alternance (recommended if you search alternance / stage)

1. Open **https://api.apprentissage.beta.gouv.fr/fr/compte/profil**
2. Register with your email (you receive a login link)
3. Complete your profile; the portal creates an **access token**
4. Copy the token:

```env
LA_BONNE_ALTERNANCE_API_KEY=...
```

API explorer (for reference): **https://api.apprentissage.beta.gouv.fr/fr/explorer/recherche-offre**  
Cvly only calls this API when **alternance** or **stage** is selected in Settings.

---

### Step 8 - Google Sheets tracking (optional)

**A. Service account**

1. Open **https://console.cloud.google.com/apis/credentials**
2. **+ CREATE CREDENTIALS** → **Service account** → name e.g. `cvly-sheets`
3. Open the service account → **Keys** → **Add key** → **JSON** → download the file
4. Move it into the project:

```bash
mkdir -p config
mv ~/Downloads/your-downloaded-file.json config/google_service_account.json
```

**B. Enable APIs**

1. Enable Sheets: **https://console.cloud.google.com/apis/library/sheets.googleapis.com**
2. Enable Drive: **https://console.cloud.google.com/apis/library/drive.googleapis.com**

**C. Create and share the sheet**

1. Create a Google Sheet named e.g. `Cvly Job Tracker`
2. Share it with the service account email (Editor). Find the email with:

```bash
grep client_email config/google_service_account.json
```

3. Copy the Sheet ID from the URL  
   (`https://docs.google.com/spreadsheets/d/THIS_PART/edit`) → `GOOGLE_SHEET_ID`

```env
GOOGLE_SERVICE_ACCOUNT_PATH=config/google_service_account.json
GOOGLE_SHEET_ID=...
```

---

### Step 9 - App defaults (already filled in `.env.example`)

```env
APP_PORT=8000
MATCH_THRESHOLD=50
DEFAULT_LANGUAGE=fr
DEFAULT_COUNTRY=FR
```

Change these only if you know why.

---

### Keys summary

| Service | Required? | Free tier (indicative) | Setup time |
|---|---|---|---|
| Gemini | Yes | ~15 RPM, ~1,500/day | ~1 min |
| Groq | Recommended | ~30 RPM | ~2 min |
| France Travail | Recommended (FR) | ~1,000/day | ~5 min |
| Adzuna | Recommended | ~250/day | ~3 min |
| Arbeitnow / Remotive / Jobicy | Automatic | - | 0 |
| JSearch | Optional | ~200/month | ~3 min |
| La Bonne Alternance | Recommended for alternance/stage | Free non-commercial | ~3 min |
| Google Sheets | Optional | - | ~10 min |

---

## 6. How to run

### Production release (recommended for most users)

Use a **tagged release**, not a random commit. Latest stable tag: **`v1.0.2`**.

All tags and release notes: [github.com/bilalr-dev/cvly/releases](https://github.com/bilalr-dev/cvly/releases)  
All tags list: [github.com/bilalr-dev/cvly/tags](https://github.com/bilalr-dev/cvly/tags)

| Tag | What it is |
|---|---|
| `v1.0.2` | Latest stable (docs + run guide with tags) - **use this** |
| `v1.0.1` | Tailwind CDN CORS fix |
| `v1.0.0` | First production release |

**New install**

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
git fetch --tags
git checkout v1.0.2
cp .env.example .env
# Fill .env (section 5)
./start.sh        # macOS / Linux
# or: start.bat   # Windows
```

**Already cloned - switch to / update the tag**

```bash
cd cvly
git fetch --tags
git checkout v1.0.2
./start.sh        # macOS / Linux
# or: start.bat   # Windows
```

Your browser should open at **http://localhost:8000**. If styles look broken, hard-refresh the page (`Cmd+Shift+R` / `Ctrl+Shift+R`).

### Local development (current branch)

Same as above, but stay on the branch you are working on (do not force a tag checkout):

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
cp .env.example .env
# Fill .env (section 5)
./start.sh        # macOS / Linux
start.bat         # Windows
```

`start.sh` / `start.bat` will:

1. Check Python 3
2. Create `.venv` if needed
3. Install `requirements.txt`
4. Refuse to start if `.env` is missing
5. Launch Uvicorn on port 8000

Stop the app with `Ctrl+C`.

---

## 7. How to collaborate

### Prerequisites for contributors

- Python 3.12+
- `.env` configured (at least `GEMINI_API_KEY`)
- Dev tools: `pip install -r requirements-dev.txt`

### Branch names

```
feat/short-name
fix/short-description
refactor/what-changed
```

### Pull request checklist

- [ ] `ruff check backend/` is clean
- [ ] New behavior has tests (RED → GREEN → REFACTOR)
- [ ] No broad `except Exception` - catch specific errors
- [ ] No hardcoded magic strings - use `backend/utils/constants.py` or translation keys
- [ ] No leftover `TODO` - implement or open an issue
- [ ] Prompts only in `backend/prompts.py` (never inlined in modules)

### Adding a job source

1. Add `backend/services/job_apis/your_source.py` with `async def search(...)`
2. Register keys in `config.py`, `.env.example`, and this README if needed
3. Extend the `source` Literal in `backend/models/job.py`
4. Wire the client in `_build_api_clients()` inside `backend/routes/pipeline.py`
5. Add tests under `tests/test_services/`

### Adding a prompt

1. Add a constant in `backend/prompts.py` (with a research comment when relevant)
2. Use `{placeholder}` syntax - never f-strings inside prompt constants
3. Cover anti-hallucination wording with tests when the prompt is safety-critical

### License

MIT

---

<a id="français"></a>

# Français

**Aller à :** 
[1. Contexte](#1-contexte-du-projet)
[2. Techniques & recherches](#2-techniques--recherches)
[3. Stack](#3-stack-utilisé)
[4. Structure](#4-structure-du-projet)
[5. Fichier .env](#5-configuration-du-fichier-env)
[6. Lancer le projet](#6-comment-lancer-le-projet)
[7. Collaborer](#7-comment-collaborer-correctement)

---

## 1. Contexte du projet

Cvly est un **assistant de candidature local**. Vous importez votre CV, définissez vos préférences de recherche, et Cvly :

1. Lit votre CV (PDF ou Word)
2. Interroge plusieurs sites d’offres gratuits en parallèle
3. Note la pertinence de chaque offre
4. Réécrit des puces de CV et une lettre de motivation pour les offres que vous choisissez
5. Vous laisse tout relire avant d’enregistrer
6. Peut journaliser les candidatures validées dans une Google Sheet

L’interface s’ouvre dans le navigateur sur `http://localhost:8000`. Cvly n’a pas de compte cloud propre - seulement des clés d’API gratuites dans un fichier `.env`.

**Principes**

- APIs gratuites uniquement (usage personnel)
- Un fichier = une responsabilité
- Préférer des bibliothèques maintenues au code maison
- Rien n’est enregistré tant que vous n’avez pas cliqué sur Approuver

---

## 2. Techniques & recherches

### Pipeline (quand vous lancez une recherche)

```
Import du CV (PDF/DOCX)
        │
        ▼
Parseur de CV ──► profil structuré (Gemini, température 0.0)
        │
        ▼
Découverte d’offres ──► France Travail + Adzuna + Arbeitnow + Remotive
                        + Jobicy + (optionnel) JSearch + La Bonne Alternance
        │
        ▼
Filtres ──► dédoublonnage → séniorité → type de contrat → pertinence du titre → max 40
        │
        ▼
Parseur d’annonce ──► exigences structurées (Gemini)
        │
        ▼
Analyse CV ──► Passe 1 : score déterministe │ Passe 2 : analyse qualitative ATF
        │
        ▼
Personnalisation ──► réécriture en 2 étapes + lettre de motivation
        │
        ▼
Contrôles qualité ──► vérificateur déterministe + évaluateur Gemini + critique Groq
                      + auto-correction en une passe
        │
        ▼
Relecture humaine ──► Approuver → fichiers Markdown (+ ligne Google Sheets optionnelle)
```

### Anti-hallucination (pourquoi l’IA n’invente pas de compétences)

Les LLM inventent souvent des chiffres, outils ou compétences. Cvly empile plusieurs défenses, inspirées de [Grounded Optimization](https://arxiv.org/abs/2607.01457) :

| Couche | Rôle |
|---|---|
| 1. Ancrage des prompts | Interdiction d’inventer ; balises XML qui séparent votre CV réel de l’annonce |
| 2. Mots-clés en 2 étapes | Inspiré de [Chain-of-Verification](https://arxiv.org/abs/2309.11495) : seuls les mots-clés prouvés dans votre CV sont réécrits |
| 3. Vérificateur déterministe | Du code (sans LLM) signale chiffres / noms techniques absents du CV d’origine |
| 4. Agent évaluateur | Un second appel Gemini critique les puces |
| 5. Critique Groq + auto-correction | Un **autre** modèle (Groq) relit Gemini ; Gemini corrige une fois les points signalés |
| 6. Approbation humaine | Avertissements en langage clair ; rien n’est sauvé sans votre OK |

### Qualité de traduction (FR / EN)

S’appuie sur :

- [Traduction multi-étapes Google](https://arxiv.org/abs/2409.06790) (Briakou et al., 2024) - brief de traduction
- [Raffinement itératif](https://arxiv.org/abs/2306.03856) (Chen et al., EAMT 2024)
- Prompting en langue cible (IJONIS, 2026) - consignes françaises rédigées en français
- Lexique de verbes et liste noire d’anglicismes pour les CV

### Filtres de découverte d’offres

```
Plusieurs APIs en parallèle → dédoublonnage → filtre de séniorité
  → reclassement de contrat → filtre de contrat → pertinence du titre → plafond 40
```

France Travail utilise les codes commune INSEE. La Bonne Alternance n’est appelée que si vous cochez **alternance** ou **stage**, avec des codes ROME dérivés de vos titres de poste.

### Références de recherche (résumé)

| Source | Utilisation dans Cvly |
|---|---|
| [Grounded Optimization](https://arxiv.org/abs/2607.01457) | Défense multi-couches, évaluateur |
| [Chain-of-Verification](https://arxiv.org/abs/2309.11495) | Validation des mots-clés en 2 étapes |
| [Brief de traduction Google](https://arxiv.org/abs/2409.06790) | Contexte CV / lettre |
| [Raffinement itératif](https://arxiv.org/abs/2306.03856) | Traduction de qualité native |
| Prompting langue cible (IJONIS, 2026) | Consignes FR en français |
| Harvard Career Services | Formule STAR |
| La Prompterie + HRLens | Conventions de lettres FR |

---

## 3. Stack utilisé

| Élément | Version / choix | Rôle |
|---|---|---|
| Python | 3.12+ | Exécution |
| FastAPI | 0.115.12 | API web locale |
| Uvicorn | 0.34.3 | Serveur |
| Jinja2 | 3.1.6 | Pages HTML |
| HTMX | 2.x (CDN) | Mises à jour de page sans gros frontend |
| Tailwind CSS | v3 Play CDN | Style (sans build) |
| Gemini | `gemini-3.1-flash-lite` | Parsing, texte, réécriture |
| Groq | `llama-3.1-8b-instant` (défaut) | Critique indépendante (recommandé) |
| aiohttp | 3.14.1 | Appels d’APIs d’offres en parallèle |
| Pydantic / pydantic-settings | 2.x | Modèles + lecture du `.env` |
| pdfplumber / python-docx | - | Lecture PDF / Word |
| gspread / google-auth | - | Suivi Google Sheets (optionnel) |

**Sources d’offres**

| Source | Clé ? | Notes |
|---|---|---|
| France Travail | Oui (recommandé en France) | Plus grand catalogue FR |
| Adzuna | Oui (recommandé) | Couverture européenne |
| Arbeitnow | Non | ATS (Greenhouse, Lever, …) |
| Remotive | Non | Remote |
| Jobicy | Non | Remote |
| JSearch (RapidAPI) | Optionnel | Couverture supplémentaire |
| La Bonne Alternance | Oui (alternance / stage) | Apprentissage / stages FR |

---

## 4. Structure du projet

Les dossiers de tests et fichiers de cache sont volontairement omis.

```
cvly/
├── backend/
│   ├── main.py                     # Point d’entrée FastAPI
│   ├── config.py                   # Lecture du .env
│   ├── state.py                    # État en mémoire + textes i18n
│   ├── prompts.py                  # Tous les prompts LLM
│   ├── models/                     # Modèles Pydantic figés
│   │   ├── resume.py
│   │   ├── resume_profile.py
│   │   ├── job.py
│   │   ├── match.py
│   │   ├── tailoring.py
│   │   └── preferences.py
│   ├── modules/                    # Une étape du pipeline = un module
│   │   ├── resume_parser.py
│   │   ├── job_discovery.py
│   │   ├── jd_parser.py
│   │   ├── cv_analyser.py
│   │   ├── atf_analyser.py
│   │   ├── tailoring.py
│   │   ├── cover_letter.py
│   │   ├── evaluator_agent.py
│   │   ├── critical_evaluator.py   # Critique Groq
│   │   ├── self_corrector.py       # Correction Gemini après Groq
│   │   ├── hallucination_checker.py
│   │   ├── output_generator.py
│   │   └── sheets_tracker.py
│   ├── services/
│   │   ├── gemini_llm.py
│   │   ├── gemini_embeddings.py
│   │   ├── groq_llm.py
│   │   ├── rate_limiter.py
│   │   └── job_apis/
│   │       ├── base.py
│   │       ├── france_travail.py
│   │       ├── adzuna.py
│   │       ├── arbeitnow.py
│   │       ├── remotive.py
│   │       ├── jobicy.py
│   │       ├── jsearch.py
│   │       └── la_bonne_alternance.py
│   ├── routes/
│   │   ├── dashboard.py
│   │   ├── settings.py
│   │   ├── pipeline.py
│   │   ├── results.py
│   │   ├── preview.py
│   │   └── ws.py                   # Progression live (WebSocket)
│   └── utils/
│       ├── constants.py
│       ├── dedup.py
│       ├── cosine.py
│       └── location_filter.py
├── frontend/
│   ├── templates/
│   │   ├── base.html
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   ├── results.html
│   │   ├── preview.html
│   │   ├── view_document.html
│   │   └── partials/
│   └── static/
│       └── favicon.ico
├── config/                         # Placer google_service_account.json ici
├── cache/                          # Préférences / profil locaux
├── output/                         # CV & lettres approuvés (.md)
├── start.sh / start.bat
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

**Pages**

| Page | URL | Rôle |
|---|---|---|
| Tableau de bord | `/` | Stats, lancer une recherche |
| Paramètres | `/settings` | Import CV, préférences |
| Résultats | `/results` | Offres scorées, filtres |
| Aperçu | `/preview/{job_id}` | Comparer puces, éditer lettre, approuver |

---

## 5. Configuration du fichier `.env`

À faire une seule fois.

### Étape 0 - Créer le fichier

```bash
cd cvly
cp .env.example .env
```

Ouvrez `.env` avec un éditeur de texte. Laissez vides les clés optionnelles non utilisées.

---

### Étape 1 - Google Gemini (OBLIGATOIRE)

1. Ouvrez **https://aistudio.google.com/apikey**
2. Connectez-vous avec Google
3. Cliquez sur **Create API key**
4. Collez la clé dans `.env` :

```env
GEMINI_API_KEY=collez_votre_cle_ici
```

---

### Étape 2 - Groq (recommandé - critique IA indépendante)

1. Ouvrez **https://console.groq.com**
2. Créez un compte / connectez-vous
3. Allez sur **https://console.groq.com/keys**
4. Créez une clé et collez-la :

```env
GROQ_API_KEY=collez_votre_cle_ici
GROQ_MODEL=llama-3.1-8b-instant
```

Gardez `llama-3.1-8b-instant` sauf besoin particulier (les modèles plus gros consomment le quota gratuit plus vite).

---

### Étape 3 - France Travail (recommandé pour le marché français)

1. Créez un compte sur **https://francetravail.io**
2. Page de l’API Offres d’emploi : **https://francetravail.io/data/api/offres-emploi**
3. Cliquez sur **Utiliser l’API**
4. Créez une application (ex. nom : `cvly`, URL : `https://example.com`)
5. **Abonnez l’application à « Offres d’emploi v2 »** (étape séparée - ne pas oublier)
6. Dans les paramètres de l’application, copiez :
   - **Identifiant client** (commence par `PAR_...`) → `FRANCE_TRAVAIL_CLIENT_ID`
   - **Clé secrète** → `FRANCE_TRAVAIL_CLIENT_SECRET`

```env
FRANCE_TRAVAIL_CLIENT_ID=PAR_...
FRANCE_TRAVAIL_CLIENT_SECRET=...
```

Si vous voyez `invalid_client`, l’abonnement **Offres d’emploi v2** manque souvent.

---

### Étape 4 - Adzuna (recommandé)

1. Ouvrez **https://developer.adzuna.com/**
2. Inscrivez-vous (type : **Personal or academic research**)
3. Copiez App ID et App Key depuis le tableau de bord :

```env
ADZUNA_APP_ID=...
ADZUNA_APP_KEY=...
```

---

### Étape 5 - Arbeitnow, Remotive, Jobicy (automatique)

Aucune clé. Elles démarrent dès que Cvly tourne.

---

### Étape 6 - JSearch / RapidAPI (optionnel)

1. Ouvrez **https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch**
2. Abonnez-vous au plan **BASIC** (0 € / mois)
3. Copiez `X-RapidAPI-Key` :

```env
JSEARCH_API_KEY=...
```

---

### Étape 7 - La Bonne Alternance (recommandé pour alternance / stage)

1. Ouvrez **https://api.apprentissage.beta.gouv.fr/fr/compte/profil**
2. Inscrivez-vous avec votre e-mail (lien de connexion reçu par mail)
3. Complétez le profil ; le portail crée un **jeton d’accès**
4. Copiez le jeton :

```env
LA_BONNE_ALTERNANCE_API_KEY=...
```

Explorateur d’API : **https://api.apprentissage.beta.gouv.fr/fr/explorer/recherche-offre**  
Cvly n’appelle cette API que si **alternance** ou **stage** est sélectionné dans Paramètres.

---

### Étape 8 - Suivi Google Sheets (optionnel)

**A. Compte de service**

1. Ouvrez **https://console.cloud.google.com/apis/credentials**
2. **+ CREATE CREDENTIALS** → **Service account** → nom ex. `cvly-sheets`
3. Onglet **Keys** → **Add key** → **JSON** → téléchargez le fichier
4. Déplacez-le dans le projet :

```bash
mkdir -p config
mv ~/Downloads/votre-fichier.json config/google_service_account.json
```

**B. Activer les APIs**

1. Sheets : **https://console.cloud.google.com/apis/library/sheets.googleapis.com**
2. Drive : **https://console.cloud.google.com/apis/library/drive.googleapis.com**

**C. Créer et partager la feuille**

1. Créez une Google Sheet (ex. `Cvly Job Tracker`)
2. Partagez-la avec l’e-mail du compte de service (droits **Éditeur**) :

```bash
grep client_email config/google_service_account.json
```

3. Copiez l’ID de la feuille depuis l’URL  
   (`https://docs.google.com/spreadsheets/d/CETTE_PARTIE/edit`) → `GOOGLE_SHEET_ID`

```env
GOOGLE_SERVICE_ACCOUNT_PATH=config/google_service_account.json
GOOGLE_SHEET_ID=...
```

---

### Étape 9 - Réglages de l’app (déjà présents dans `.env.example`)

```env
APP_PORT=8000
MATCH_THRESHOLD=50
DEFAULT_LANGUAGE=fr
DEFAULT_COUNTRY=FR
```

---

### Récapitulatif des clés

| Service | Obligatoire ? | Quota gratuit (indicatif) | Temps |
|---|---|---|---|
| Gemini | Oui | ~15 req/min, ~1 500/jour | ~1 min |
| Groq | Recommandé | ~30 req/min | ~2 min |
| France Travail | Recommandé (FR) | ~1 000/jour | ~5 min |
| Adzuna | Recommandé | ~250/jour | ~3 min |
| Arbeitnow / Remotive / Jobicy | Automatique | - | 0 |
| JSearch | Optionnel | ~200/mois | ~3 min |
| La Bonne Alternance | Recommandé pour alternance/stage | Gratuit non commercial | ~3 min |
| Google Sheets | Optionnel | - | ~10 min |

---

## 6. Comment lancer le projet

### Version production (recommandée pour la plupart des utilisateurs)

Utilisez un **tag de release**, pas un commit au hasard. Dernier tag stable : **`v1.0.2`**.

Toutes les releases : [github.com/bilalr-dev/cvly/releases](https://github.com/bilalr-dev/cvly/releases)  
Liste des tags : [github.com/bilalr-dev/cvly/tags](https://github.com/bilalr-dev/cvly/tags)

| Tag | Contenu |
|---|---|
| `v1.0.2` | Dernière version stable (docs + guide de lancement) - **à utiliser** |
| `v1.0.1` | Correctif CORS CDN Tailwind |
| `v1.0.0` | Première release production |

**Nouvelle installation**

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
git fetch --tags
git checkout v1.0.2
cp .env.example .env
# Remplir le .env (section 5)
./start.sh        # macOS / Linux
# ou : start.bat  # Windows
```

**Déjà cloné - passer au / mettre à jour le tag**

```bash
cd cvly
git fetch --tags
git checkout v1.0.2
./start.sh        # macOS / Linux
# ou : start.bat  # Windows
```

Le navigateur s’ouvre sur **http://localhost:8000**. Si le style est cassé, forcez le rechargement (`Cmd+Shift+R` / `Ctrl+Shift+R`).

### Développement local (branche courante)

Même procédure, sans forcer un checkout de tag :

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
cp .env.example .env
# Remplir le .env (section 5)
./start.sh        # macOS / Linux
start.bat         # Windows
```

`start.sh` / `start.bat` :

1. Vérifient Python 3
2. Créent `.venv` si besoin
3. Installent `requirements.txt`
4. Refusent de démarrer sans `.env`
5. Lancent Uvicorn sur le port 8000

Arrêt : `Ctrl+C`.

---

## 7. Comment collaborer correctement

### Prérequis contributeurs

- Python 3.12+
- `.env` configuré (au minimum `GEMINI_API_KEY`)
- Outils de dev : `pip install -r requirements-dev.txt`

### Démarche (TDD)

Toute modification suit **ROUGE → VERT → REFACTOR** :

1. **ROUGE** - Écrire d’abord un test qui échoue
2. **VERT** - Code minimal pour le faire passer ; lancer toute la suite
3. **REFACTOR** - Nettoyer ; relancer les tests

```bash
ruff check backend/
```

### Noms de branches

```
feat/nom-court
fix/description-courte
refactor/ce-qui-change
```

### Checklist de pull request

- [ ] `ruff check backend/` OK
- [ ] Nouveau comportement couvert par des tests (ROUGE → VERT → REFACTOR)
- [ ] Pas de `except Exception` trop large
- [ ] Pas de chaînes magiques - `constants.py` ou clés de traduction
- [ ] Pas de `TODO` orphelin
- [ ] Prompts uniquement dans `backend/prompts.py`

### Ajouter une source d’offres

1. Créer `backend/services/job_apis/votre_source.py` avec `async def search(...)`
2. Déclarer les clés dans `config.py`, `.env.example` et ce README si besoin
3. Étendre le Literal `source` dans `backend/models/job.py`
4. Brancher le client dans `_build_api_clients()` (`backend/routes/pipeline.py`)
5. Ajouter des tests sous `tests/test_services/`

### Ajouter un prompt

1. Constante dans `backend/prompts.py` (commentaire de recherche si utile)
2. Syntaxe `{placeholder}` - jamais de f-string dans la constante
3. Tests anti-hallucination si le prompt est critique pour la sécurité du contenu

### Licence

MIT
