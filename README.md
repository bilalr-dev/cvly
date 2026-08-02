# Cvly

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/) [![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/) [![Gemini](https://img.shields.io/badge/AI-Gemini-4285F4?logo=google)](https://ai.google.dev/) [![Groq](https://img.shields.io/badge/AI-Groq-black)](https://groq.com/) [![HTMX](https://img.shields.io/badge/HTMX-2.x-3366CC?logo=htmx&logoColor=white)](https://htmx.org/) [![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-v3-06B6D4?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/) [![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](#license) [![GitHub Release](https://img.shields.io/github/v/release/bilalr-dev/cvly)](https://github.com/bilalr-dev/cvly/releases) [![GitHub Stars](https://img.shields.io/github/stars/bilalr-dev/cvly)](https://github.com/bilalr-dev/cvly/stargazers)

**Language / Langue:** [English](#english) · [Français](#french)

AI-powered job application helper that runs on your computer.  
Assistant de candidature alimenté par l’IA, qui tourne sur votre ordinateur.

---

# English

**Index:**

- [1. Project context](#1-project-context)
- [2. Techniques & research](#2-techniques--research)
- [3. Stack](#3-stack)
- [4. Project structure](#4-project-structure)
- [5. Configuration (setup wizard)](#5-configuration-setup-wizard)
- [6. How to run](#6-how-to-run)
- [7. How to collaborate](#7-how-to-collaborate)
---

## 1. Project context

Cvly is a **local job-application agent**. You upload your résumé, set your search preferences, and Cvly:

1. Reads your CV (PDF or Word)
2. Searches several free job boards at once
3. Scores how well each offer matches you
4. Rewrites CV bullets and a cover letter for jobs you choose
5. Lets you review everything before saving
6. Optionally logs approved applications in a Google Sheet

It opens in your browser at `http://localhost:8000`. No Cvly account or hosted backend is required. On first launch, the **setup wizard** walks you through API keys (EN/FR) and writes `.env` for you - you do not need to edit config files by hand.

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
├── setup.py                        # Interactive setup wizard (EN/FR)
├── start.sh / start.bat            # One-command start (launches wizard if needed)
├── requirements.txt
├── requirements-dev.txt
└── .env.example                    # Reference only - wizard creates .env
```

**Pages**

| Page | URL | Purpose |
|---|---|---|
| Dashboard | `/` | Stats, start a run |
| Settings | `/settings` | Upload CV, search preferences |
| Results | `/results` | Scored matches, filters |
| Preview | `/preview/{job_id}` | Compare bullets, edit cover letter, approve |

---

## 5. Configuration (setup wizard)

**Important:** you do **not** need to create or edit `.env` by hand. Cvly includes an interactive setup wizard (`setup.py`) that is the recommended way for every new user.

### Recommended - use the setup wizard

The wizard:

- Starts automatically the first time you run `./start.sh` or `start.bat` when `.env` is missing
- Asks for language first (**EN** or **FR**)
- Opens each API signup page in your browser
- Shows click-by-click steps (Create key, copy, paste)
- Lets you skip optional services with Enter
- Writes a valid `.env` for you
- Then continues and starts the app

**First launch**

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
./start.sh        # macOS / Linux - wizard opens if .env is missing
# or: start.bat   # Windows
```

**Run the wizard again later** (to change keys or redo setup):

```bash
python3 setup.py
# or delete .env and run ./start.sh again
```

Only **Google Gemini** is required. Everything else can be skipped; you can add keys later by re-running the wizard.

### What the wizard configures

| Service | Required? | Notes |
|---|---|---|
| Gemini | Yes | Main AI |
| Groq | Recommended | Second AI that checks Gemini output |
| France Travail | Recommended (France) | Includes Offres d'emploi v2 + ROMEO v2 in the guided steps |
| Adzuna | Recommended | European job listings |
| Arbeitnow / Remotive / Jobicy | Automatic | No keys |
| JSearch | Optional | Extra coverage via RapidAPI |
| La Bonne Alternance | Optional | Alternance / stage |
| Google Sheets | Optional | Track approved applications |

### Manual `.env` editing (optional - not required)

Manual setup is **not required** for normal use. Prefer the wizard above.

If you really want to edit files yourself: copy `.env.example` to `.env` and fill the keys. `.env.example` is a reference template only; `start.sh` / `start.bat` will still launch the wizard when `.env` is missing.

---

## 6. How to run

### Production release (recommended for most users)

Use a **tagged release**, not a random commit. Latest stable tag: **`v1.0.7`**.

All tags and release notes: [github.com/bilalr-dev/cvly/releases](https://github.com/bilalr-dev/cvly/releases)  
All tags list: [github.com/bilalr-dev/cvly/tags](https://github.com/bilalr-dev/cvly/tags)

| Tag | What it is |
|---|---|
| `v1.0.7` | Stage / internship API fixes, company name extraction from JD |
| `v1.0.6` | Interactive setup wizard |
| `v1.0.5` | ROMEO v2 docs, fork contributor guide, CDN CORS fix (view page) |
| `v1.0.4` | Auto-install Python 3.12 in start scripts |
| `v1.0.3` | README Markdown / anchor / badge fixes |
| `v1.0.2` | Docs + run guide with tags |
| `v1.0.1` | Tailwind CDN CORS fix |
| `v1.0.0` | First production release |

**New install**

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
git fetch --tags
git checkout v1.0.7
./start.sh        # macOS / Linux - launches setup wizard if .env is missing
# or: start.bat   # Windows
```

No `cp .env.example .env` step. Follow the wizard, then the server starts.

**Already cloned - switch to / update the tag**

```bash
cd cvly
git fetch --tags
git checkout v1.0.7
./start.sh        # macOS / Linux
# or: start.bat   # Windows
```

Your browser should open at **http://localhost:8000**. If styles look broken, hard-refresh the page (`Cmd+Shift+R` / `Ctrl+Shift+R`).

### Local development (current branch)

Same as above, but stay on the branch you are working on (do not force a tag checkout):

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
./start.sh        # macOS / Linux - wizard on first run
start.bat         # Windows
```

`start.sh` / `start.bat` will:

1. Check Python 3.10-3.12
2. Create `.venv` if needed
3. Install `requirements.txt`
4. Launch the **setup wizard** if `.env` is missing
5. Launch Uvicorn on port 8000

Stop the app with `Ctrl+C`. If you see `Address already in use`, another Cvly instance is still running on port 8000 - stop it first.

---

## 7. How to collaborate

### Reporting issues

If you found a bug or have a feature request:

1. Go to [Issues](https://github.com/bilalr-dev/cvly/issues)
2. Click **"New Issue"**
3. Describe: what you expected, what happened, how to reproduce
4. Include your Python version (`python3 --version`) and OS

### Contributing code (fork workflow)

Cvly uses a **fork-based workflow**. You do not need write access to the main repository.

**Step 1 : Fork the repository:**

1. Go to [github.com/bilalr-dev/cvly](https://github.com/bilalr-dev/cvly)
2. Click the **"Fork"** button (top-right)
3. This creates your own copy at `github.com/YOUR_USERNAME/cvly`

**Step 2 : Clone your fork:**

```bash
git clone https://github.com/YOUR_USERNAME/cvly.git
cd cvly
```

**Step 3 : Set up the upstream remote:**

```bash
git remote add upstream https://github.com/bilalr-dev/cvly.git

# Verify
git remote -v
# origin    https://github.com/YOUR_USERNAME/cvly.git (fetch/push)
# upstream  https://github.com/bilalr-dev/cvly.git (fetch/push)
```

**Step 4 : Install dependencies and configure:**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
./start.sh        # launches the setup wizard if .env is missing
# or: python3 setup.py
```
**Step 5 : Create a branch from the latest main:**

```bash
git fetch upstream
git checkout main
git merge upstream/main
git checkout -b feat/your-feature-name
```

**Step 6 : Code using TDD (RED → GREEN → REFACTOR):**

1. **RED:** Write a failing test first
```bash
pytest tests/test_your_feature.py -v   # Must FAIL
```

2. **GREEN:** Minimum code to pass
```bash
pytest tests/test_your_feature.py -v   # Must PASS
pytest                                  # No regressions
```

3. **REFACTOR:** Clean up, then verify
```bash
pytest                            # All pass
ruff check backend/               # No lint errors
radon cc backend/ -s -n C         # No D-rated functions
bandit -r backend/ -ll            # No security issues
```

**Step 7 : Commit with clear messages:**

```bash
git add .
git commit -m "feat: add location filter for remote jobs

- Created location_filter.py for client-side geo matching
- Updated arbeitnow and remotive to use shared filter
- Added 5 tests"
```

Format: `type: short description` : types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Step 8 : Push and open a Pull Request:**

```bash
git push origin feat/your-feature-name
```

Then on GitHub: click **"Compare & pull request"** → verify base is `bilalr-dev/cvly:main` → fill in the description → submit.

**Step 9 : Address review feedback:**

```bash
# Make changes, then:
git add .
git commit -m "fix: address review feedback"
git push origin feat/your-feature-name
# PR updates automatically
```

**Keeping your fork up to date:**

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Branch names

```
feat/short-name
fix/short-description
refactor/what-changed
docs/what-updated
```

### Pull request checklist

- [ ] `pytest` : all tests pass
- [ ] `ruff check backend/` : no lint errors
- [ ] `radon cc backend/ -s -n C` : no D-rated functions
- [ ] `bandit -r backend/ -ll` : no security issues
- [ ] New behavior has tests (RED → GREEN → REFACTOR)
- [ ] No broad `except Exception` : catch specific errors
- [ ] No hardcoded magic strings : use `backend/utils/constants.py` or translation keys
- [ ] No leftover `TODO` : implement or open an issue
- [ ] Prompts only in `backend/prompts.py` (never inlined in modules)

### Adding a job source

1. Add `backend/services/job_apis/your_source.py` with `async def search(...)`
2. If API key needed: register in `config.py`, `.env.example`, and this README (both EN and FR)
3. Extend the `source` Literal in `backend/models/job.py`
4. Wire the client in `_build_api_clients()` inside `backend/routes/pipeline.py`
5. Add location filtering if the API returns global results
6. Add tests under `tests/test_services/`

### Adding a prompt

1. Add a constant in `backend/prompts.py` (with a research comment when relevant)
2. Use `{placeholder}` syntax : never f-strings inside prompt constants
3. If the prompt needs `{language}`, add it
4. Cover anti-hallucination wording with tests when the prompt is safety-critical

---

<a id="french"></a>

# Francais

**Index :**

- [1. Contexte](#1-contexte-du-projet)
- [2. Techniques & recherches](#2-techniques--recherches)
- [3. Stack](#3-stack-utilise)
- [4. Structure](#4-structure-du-projet)
- [5. Configuration (assistant de setup)](#5-configuration-assistant-de-setup)
- [6. Lancer le projet](#6-comment-lancer-le-projet)
- [7. Collaborer](#7-comment-collaborer-correctement)
---

## 1. Contexte du projet

Cvly est un **assistant de candidature local**. Vous importez votre CV, définissez vos préférences de recherche, et Cvly :

1. Lit votre CV (PDF ou Word)
2. Interroge plusieurs sites d’offres gratuits en parallèle
3. Note la pertinence de chaque offre
4. Réécrit des puces de CV et une lettre de motivation pour les offres que vous choisissez
5. Vous laisse tout relire avant d’enregistrer
6. Peut journaliser les candidatures validées dans une Google Sheet

L’interface s’ouvre dans le navigateur sur `http://localhost:8000`. Aucun compte Cvly ni backend hébergé n’est requis. Au premier lancement, l’**assistant de configuration** vous guide pour les clés d’API (EN/FR) et écrit le fichier `.env` - vous n’avez pas besoin d’éditer la config à la main.

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

## 3. Stack utilise

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
├── setup.py                        # Assistant de configuration interactif (EN/FR)
├── start.sh / start.bat            # Lancement en une commande (lance l'assistant si besoin)
├── requirements.txt
├── requirements-dev.txt
└── .env.example                    # Référence seulement - l'assistant crée .env
```

**Pages**

| Page | URL | Rôle |
|---|---|---|
| Tableau de bord | `/` | Stats, lancer une recherche |
| Paramètres | `/settings` | Import CV, préférences |
| Résultats | `/results` | Offres scorées, filtres |
| Aperçu | `/preview/{job_id}` | Comparer puces, éditer lettre, approuver |

---

## 5. Configuration (assistant de setup)

**Important :** vous n’avez **pas** besoin de créer ni d’éditer `.env` à la main. Cvly inclut un assistant de configuration interactif (`setup.py`) - c’est la méthode recommandée pour tous les nouveaux utilisateurs.

### Recommandé - utiliser l’assistant de setup

L’assistant :

- Se lance automatiquement au premier `./start.sh` ou `start.bat` si `.env` est absent
- Demande d’abord la langue (**EN** ou **FR**)
- Ouvre chaque page d’inscription API dans le navigateur
- Affiche des étapes clic par clic (créer la clé, copier, coller)
- Permet de passer les services optionnels avec Entrée
- Écrit un `.env` valide pour vous
- Puis continue et démarre l’application

**Premier lancement**

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
./start.sh        # macOS / Linux - l'assistant s'ouvre si .env est absent
# ou : start.bat  # Windows
```

**Relancer l’assistant plus tard** (changer des clés ou refaire la config) :

```bash
python3 setup.py
# ou supprimer .env puis relancer ./start.sh
```

Seul **Google Gemini** est obligatoire. Tout le reste peut être ignoré ; vous pourrez ajouter des clés plus tard en relançant l’assistant.

### Ce que l’assistant configure

| Service | Obligatoire ? | Notes |
|---|---|---|
| Gemini | Oui | IA principale |
| Groq | Recommandé | Seconde IA qui vérifie la sortie de Gemini |
| France Travail | Recommandé (France) | Inclut Offres d'emploi v2 + ROMEO v2 dans les étapes guidées |
| Adzuna | Recommandé | Offres européennes |
| Arbeitnow / Remotive / Jobicy | Automatique | Aucune clé |
| JSearch | Optionnel | Couverture supplémentaire via RapidAPI |
| La Bonne Alternance | Optionnel | Alternance / stage |
| Google Sheets | Optionnel | Suivi des candidatures approuvées |

### Édition manuelle de `.env` (optionnel - non requis)

La configuration manuelle **n’est pas requise** pour un usage normal. Préférez l’assistant ci-dessus.

Si vous tenez vraiment à éditer les fichiers vous-même : copiez `.env.example` vers `.env` et remplissez les clés. `.env.example` n’est qu’un modèle de référence ; `start.sh` / `start.bat` lanceront toujours l’assistant si `.env` est absent.

---

## 6. Comment lancer le projet

### Version production (recommandée pour la plupart des utilisateurs)

Utilisez un **tag de release**, pas un commit au hasard. Dernier tag stable : **`v1.0.7`**.

Toutes les releases : [github.com/bilalr-dev/cvly/releases](https://github.com/bilalr-dev/cvly/releases)  
Liste des tags : [github.com/bilalr-dev/cvly/tags](https://github.com/bilalr-dev/cvly/tags)

| Tag | Contenu |
|---|---|
| `v1.0.7` | Correctifs API stage / internship, extraction du nom d'entreprise depuis la JD |
| `v1.0.6` | Assistant de configuration interactif |
| `v1.0.5` | Docs ROMEO v2, guide contributeur fork, fix CORS CDN (page view) |
| `v1.0.4` | Auto-install Python 3.12 dans les scripts de démarrage |
| `v1.0.3` | Correctifs Markdown / ancres / badges du README |
| `v1.0.2` | Docs + guide de lancement avec tags |
| `v1.0.1` | Fix CORS Tailwind CDN |
| `v1.0.0` | Première release production |

**Nouvelle installation**

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
git fetch --tags
git checkout v1.0.7
./start.sh        # macOS / Linux - lance l'assistant si .env est absent
# ou : start.bat  # Windows
```

Pas d’étape `cp .env.example .env`. Suivez l’assistant, puis le serveur démarre.

**Déjà cloné - passer au / mettre à jour le tag**

```bash
cd cvly
git fetch --tags
git checkout v1.0.7
./start.sh        # macOS / Linux
# ou : start.bat  # Windows
```

Le navigateur s’ouvre sur **http://localhost:8000**. Si le style est cassé, forcez le rechargement (`Cmd+Shift+R` / `Ctrl+Shift+R`).

### Développement local (branche courante)

Même procédure, sans forcer un checkout de tag :

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
./start.sh        # macOS / Linux - assistant au premier lancement
start.bat         # Windows
```

`start.sh` / `start.bat` :

1. Vérifient Python 3.10-3.12
2. Créent `.venv` si besoin
3. Installent `requirements.txt`
4. Lancent l’**assistant de setup** si `.env` est absent
5. Lancent Uvicorn sur le port 8000

Arrêt : `Ctrl+C`. Si vous voyez `Address already in use`, une autre instance Cvly tourne encore sur le port 8000 - arrêtez-la d’abord.

---

## 7. Comment collaborer correctement

### Signaler un problème

Si vous avez trouvé un bug ou souhaitez proposer une fonctionnalité :

1. Allez dans [Issues](https://github.com/bilalr-dev/cvly/issues)
2. Cliquez sur **"New Issue"**
3. Décrivez : ce que vous attendiez, ce qui s'est passé, comment reproduire
4. Incluez votre version de Python (`python3 --version`) et votre OS

### Contribuer au code (workflow fork)

Cvly utilise un **workflow basé sur le fork**. Vous n'avez pas besoin d'accès en écriture au dépôt principal.

**Étape 1 : Forker le dépôt :**

1. Allez sur [github.com/bilalr-dev/cvly](https://github.com/bilalr-dev/cvly)
2. Cliquez sur le bouton **"Fork"** (en haut à droite)
3. Cela crée votre propre copie à `github.com/VOTRE_NOM/cvly`

**Étape 2 : Cloner votre fork :**

```bash
git clone https://github.com/VOTRE_NOM/cvly.git
cd cvly
```

**Étape 3 : Configurer le remote upstream :**

```bash
git remote add upstream https://github.com/bilalr-dev/cvly.git

# Vérifier
git remote -v
# origin    https://github.com/VOTRE_NOM/cvly.git (fetch/push)
# upstream  https://github.com/bilalr-dev/cvly.git (fetch/push)
```

**Étape 4 : Installer les dépendances et configurer :**

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
./start.sh        # lance l'assistant de setup si .env est absent
# ou : python3 setup.py
```

**Étape 5 : Créer une branche depuis le dernier main :**

```bash
git fetch upstream
git checkout main
git merge upstream/main
git checkout -b feat/nom-de-votre-fonctionnalité
```

**Étape 6 : Coder en TDD (ROUGE → VERT → REFACTOR) :**

1. **ROUGE :** Écrire d'abord un test qui échoue
```bash
pytest tests/test_votre_fonctionnalité.py -v   # Doit ÉCHOUER
```

2. **VERT :** Code minimal pour le faire passer
```bash
pytest tests/test_votre_fonctionnalité.py -v   # Doit PASSER
pytest                                          # Pas de régressions
```

3. **REFACTOR :** Nettoyer, puis vérifier
```bash
pytest                            # Tous passent
ruff check backend/               # Pas d'erreurs de lint
radon cc backend/ -s -n C         # Pas de fonctions notées D
bandit -r backend/ -ll            # Pas de problèmes de sécurité
```

**Étape 7 : Commitez avec des messages clairs :**

```bash
git add .
git commit -m "feat: ajout du filtre géographique pour les offres distantes

- Création de location_filter.py pour le filtrage géo côté client
- Mise à jour de arbeitnow et remotive pour utiliser le filtre partagé
- Ajout de 5 tests"
```

Format : `type: description courte` : types : `feat`, `fix`, `refactor`, `docs`, `test`, `chore`

**Étape 8 : Poussez et ouvrez une Pull Request :**

```bash
git push origin feat/nom-de-votre-fonctionnalité
```

Sur GitHub : cliquez sur **"Compare & pull request"** → vérifiez que la base est `bilalr-dev/cvly:main` → remplissez la description → envoyez.

**Étape 9 : Répondre aux retours de review :**

```bash
# Faites les modifications, puis :
git add .
git commit -m "fix: prise en compte du retour review"
git push origin feat/nom-de-votre-fonctionnalité
# La PR se met à jour automatiquement
```

**Garder votre fork à jour :**

```bash
git fetch upstream
git checkout main
git merge upstream/main
git push origin main
```

### Noms de branches

```
feat/nom-court
fix/description-courte
refactor/ce-qui-change
docs/mise-à-jour
```

### Checklist de pull request

- [ ] `pytest` : tous les tests passent
- [ ] `ruff check backend/` : pas d'erreurs de lint
- [ ] `radon cc backend/ -s -n C` : pas de fonctions notées D ou pire
- [ ] `bandit -r backend/ -ll` : pas de problèmes de sécurité
- [ ] Le nouveau code a des tests (ROUGE → VERT → REFACTOR respecté)
- [ ] Pas de `except Exception` trop large : erreurs spécifiques
- [ ] Pas de chaînes magiques : `backend/utils/constants.py` ou clés de traduction
- [ ] Pas de `TODO` orphelin : implémenter ou ouvrir une issue
- [ ] Prompts uniquement dans `backend/prompts.py`

### Ajouter une source d'offres

1. Créez `backend/services/job_apis/votre_source.py` avec `async def search(...)`
2. Si clé API requise : déclarez dans `config.py`, `.env.example`, et ce README (EN et FR)
3. Étendez le Literal `source` dans `backend/models/job.py`
4. Branchez le client dans `_build_api_clients()` de `backend/routes/pipeline.py`
5. Ajoutez un filtre géographique si l'API renvoie des résultats mondiaux
6. Ajoutez des tests sous `tests/test_services/`

### Ajouter un prompt

1. Constante dans `backend/prompts.py` (commentaire de recherche si pertinent)
2. Syntaxe `{placeholder}` : jamais de f-string dans la constante
3. Si le prompt a besoin de `{language}`, ajoutez-le
4. Tests anti-hallucination si le prompt est critique pour la sécurité du contenu

### Licence

This project is licensed under the MIT License.