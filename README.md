# Cvly

AI-powered job application agent that automates the full pipeline - from parsing your resume to discovering matching jobs, scoring fit, tailoring your CV per posting, and tracking applications. Runs locally at `localhost:8000`. Zero heavy dependencies.

## Quick Start

```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
cp .env.example .env
# Fill in your API keys (see setup guide below)
./start.sh        # macOS/Linux
start.bat         # Windows
```

The browser opens automatically to `http://localhost:8000`.

## What It Does

```
Upload Resume (PDF/DOCX)
       │
       ▼
Module 1: Resume Parser ──► Structured JSON profile (Gemini, temp 0.0)
       │
       ▼
Module 2: Job Discovery ──► France Travail + Adzuna + Arbeitnow + Remotive (parallel)
       │
       ▼
Module 3: JD Parser ──► Structured job requirements per posting (Gemini, temp 0.0)
       │
       ▼
Module 4: CV Analyser ──► Pass 1: Deterministic scoring │ Pass 2: ATF qualitative analysis
       │
       ▼
Module 5: Tailoring ──► Two-stage bullet rewriting + Cover letter + Evaluator QA gate
       │
       ▼
Module 6: Tracker ──► Google Sheets row per approved application
```

## How It Was Built

### Architecture Decisions

Every design choice follows three principles: **free-tier APIs only**, **strict SRP** (one file = one responsibility), and **library-first** (don't build what a maintained package already does).

**Why FastAPI + HTMX instead of React?** A local single-user tool doesn't need a JavaScript SPA. HTMX gives partial page updates with zero build tooling. Tailwind v3 Play CDN means no npm, no PostCSS, no config files.

**Why Gemini instead of OpenAI?** Free tier. `gemini-3.1-flash-lite` gives 1,500 requests/day at zero cost - enough for ~20 full pipeline runs.

**Why 4 job sources instead of 1?** No single free API covers the French market well. France Travail has the largest French job inventory but misses international postings. Adzuna covers broader European listings. Arbeitnow pulls from ATS systems (Greenhouse, Lever, Workday). Remotive covers remote roles. Together they produce 50-80 results per run.

### Anti-Hallucination System (5 Layers)

LLMs fabricate skills, inflate metrics, and attribute JD requirements to the candidate. This is the highest-risk area in any CV tailoring tool. Cvly implements five defense layers, informed by the [Grounded Optimization framework](https://arxiv.org/abs/2607.01457):

**Layer 1 : Prompt grounding:** Every prompt explicitly forbids fabrication. No "quantify every achievement" instructions (these force the LLM to invent numbers). XML boundary tags (`<SOURCE_OF_TRUTH>` / `<TARGET_JOB_CONTEXT>`) separate the candidate's real experience from JD requirements, preventing cross-contamination.

**Layer 2 : Two-stage keyword rewriting (CoVe-inspired):** Missing ATS keywords are classified before rewriting. Stage 1 (temperature 0.0) evaluates each keyword against the CV and requires evidence. Only validated keywords reach Stage 2 (temperature 0.2), which performs the actual rewrite. The LLM never sees unfillable keywords.

**Layer 3 : Deterministic post-generation checker:** Compares rewritten output against the original CV using set-difference logic. Catches fabricated metrics (numbers not in original), invented short tech names (Go, R, C#), and new tool names. No LLM involved.

**Layer 4 : Evaluator agent (generator-critic):** An independent LLM call acts as an adversarial reviewer. Receives original + rewritten bullets and flags four violation types: fabricated metrics, invented skills, JD attribution, and scope inflation. Operates at temperature 0.0.

**Layer 5 : Human review:** Nothing is saved until the user clicks "Approve." Warnings are displayed in plain language (not developer jargon) with actionable guidance like "A number seems to have been added - check it matches your real experience."

### Translation Quality

Standard LLM translation produces "translationese" grammatically correct but unnatural output instantly spotted by native speakers. Cvly's translation system is informed by three research sources:

- **Target-language prompting** ([IJONIS 2026](https://doi.org/10.xxx)): French translation instructions are written IN French to activate the model's native register
- **Translation brief** ([Briakou et al. 2024, Google](https://arxiv.org/abs/2409.06790)): The prompt specifies document type (CV), audience (recruiters), and register (factual, concise)
- **Anti-translationese rules**: Concrete verb mappings ("Managed" → "Piloté", never "Managé"), job title conventions ("Software Engineer" → "Ingénieur logiciel"), and an anglicism blacklist

### Job Discovery Pipeline

```
4 API sources (parallel) → dedup → seniority filter (word-boundary regex)
    → contract reclassification → contract type filter (title-aware)
    → title relevance pre-filter → cap at 40 → JD parsing
```

Each filter stage is a separate function. The title pre-filter saves ~50% of Gemini API calls by skipping obviously irrelevant postings before JD parsing.

France Travail uses INSEE commune codes for geographic filtering (not free-text city names). A mapping of major French cities is built into `constants.py`.

## Pages

| Page | URL | What It Does |
|---|---|---|
| Dashboard | `/` | Pipeline stats, run trigger, last run timestamp |
| Settings | `/settings` | Upload resume, set search preferences (titles, location, radius, seniority, contract types, language) |
| Results | `/results` | Scored job matches with pill filters (score threshold, status), expandable ATF analysis |
| Preview | `/preview/{job_id}` | Side-by-side bullet comparison, cover letter with inline edit, hallucination warnings, approve/regenerate |

## API Keys Setup

### 1. Google Gemini API (REQUIRED)

1. Go to https://aistudio.google.com/apikey
2. Click "Create API Key"
3. Copy the key → paste as `GEMINI_API_KEY` in `.env`
4. Free tier: 15 requests/min, 1,500/day

### 2. France Travail API (recommended - French job market)

1. Go to https://francetravail.io and create an account
2. Go to https://francetravail.io/data/api/offres-emploi
3. Click "Utiliser l'API"
4. Create an application (e.g. name: `myApp`, URL: `https://example.com`)
5. **Subscribe to "Offres d'emploi v2"** - this is a separate step from creating the app
6. Go to your application settings to find:
   - `Identifiant client` (starts with `PAR_...`) → `FRANCE_TRAVAIL_CLIENT_ID`
   - `Clé secrète` → `FRANCE_TRAVAIL_CLIENT_SECRET`
7. Free tier: 1,000 calls/day, 10 requests/second

**Troubleshooting:** If authentication fails with `invalid_client`, verify that your app is subscribed to the API (step 5) and that the scope includes `application_{client_id} api_offresdemploiv2 o2dsoffre`.

### 3. Adzuna API (recommended)

1. Go to https://developer.adzuna.com/ and sign up
2. Application type: "Personal or academic research"
3. Copy credentials from the dashboard → `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
4. Free tier: 250 calls/day

### 4. Arbeitnow + Remotive (automatic - no setup needed)

These two free job APIs are always active. No API keys required. Arbeitnow pulls from ATS systems (Greenhouse, Lever, Workday). Remotive covers remote positions.

### 5. JSearch / RapidAPI (optional)

1. Go to https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
2. Subscribe to the **BASIC** plan ($0.00/mo)
3. Copy the `X-RapidAPI-Key` → `JSEARCH_API_KEY`
4. Free tier: 200 calls/month

### 6. Google Sheets Tracking (optional)

**Step A - Create a service account:**
1. Go to https://console.cloud.google.com/apis/credentials
2. "+ CREATE CREDENTIALS" → "Service account" → name: `cvly-sheets`
3. Go to "Keys" tab → "Add Key" → JSON → download the file
4. Move it: `mv ~/Downloads/your-file.json config/google_service_account.json`

**Step B - Enable APIs:**
1. Enable [Sheets API](https://console.cloud.google.com/apis/library/sheets.googleapis.com)
2. Enable [Drive API](https://console.cloud.google.com/apis/library/drive.googleapis.com)

**Step C - Create and share the Sheet:**
1. Create a blank Google Sheet named "Cvly Job Tracker"
2. Share it with the service account email (find it with `grep client_email config/google_service_account.json`)
3. Give **Editor** access
4. Copy the Sheet ID from the URL → `GOOGLE_SHEET_ID`

### API Keys Summary

| Service | Required? | Free tier | Setup time |
|---|---|---|---|
| Google Gemini | Yes | 15 RPM, 1,500/day | 1 min |
| France Travail | Recommended | 1,000/day | 5 min |
| Adzuna | Recommended | 250/day | 3 min |
| Arbeitnow | Automatic | Unlimited | 0 min |
| Remotive | Automatic | Unlimited | 0 min |
| JSearch | Optional | 200/month | 3 min |
| Google Sheets | Optional | Unlimited | 10 min |

## Tech Stack

| Component | Version | Why |
|---|---|---|
| Python | 3.12 | Runtime |
| FastAPI | 0.115.12 | Async backend, no boilerplate |
| Gemini API | `gemini-3.1-flash-lite` | Free tier, structured JSON output |
| HTMX | 2.0.4 | Partial updates without a JS framework |
| Tailwind CSS | v3 Play CDN | Utility styling, zero build step |
| Jinja2 | 3.1.6 | Server-side templates |
| aiohttp | 3.12.6 | Async HTTP for parallel API calls |
| Pydantic | 2.11.4 | Frozen models, schema validation |

## Project Structure

```
cvly/
├── backend/
│   ├── main.py                  # FastAPI app entry point
│   ├── state.py                 # In-memory app state + translations
│   ├── config.py                # Pydantic Settings + get_settings()
│   ├── prompts.py               # All LLM prompts (7 constants, research-referenced)
│   ├── models/                  # Frozen Pydantic models per domain
│   │   ├── resume.py            # ResumeProfile, ExperienceEntry, etc.
│   │   ├── job.py               # RawJobPosting, ParsedJobDescription
│   │   ├── match.py             # MatchResult, ATFAnalysis
│   │   ├── tailoring.py         # TailoredOutput, KeywordAnalysisResult, EvaluatorVerdict
│   │   └── preferences.py       # SearchPreferences
│   ├── modules/                 # One module per pipeline stage
│   │   ├── resume_parser.py     # PDF/DOCX → ResumeProfile
│   │   ├── job_discovery.py     # Parallel multi-API fetch
│   │   ├── jd_parser.py         # JD text → ParsedJobDescription
│   │   ├── cv_analyser.py       # Deterministic scoring (Pass 1)
│   │   ├── atf_analyser.py      # LLM qualitative analysis (Pass 2)
│   │   ├── tailoring.py         # Two-stage keyword validation + bullet rewriting
│   │   ├── cover_letter.py      # Cover letter generation
│   │   ├── evaluator_agent.py   # Generator-critic QA gate
│   │   ├── hallucination_checker.py  # Deterministic output validation
│   │   ├── output_generator.py  # Markdown rendering + language translation
│   │   └── sheets_tracker.py    # Google Sheets integration
│   ├── services/
│   │   ├── gemini_llm.py        # LLM completions wrapper
│   │   ├── gemini_embeddings.py # Embedding wrapper
│   │   ├── rate_limiter.py      # Async token-bucket (10 RPM)
│   │   └── job_apis/            # One client per job source
│   │       ├── france_travail.py
│   │       ├── adzuna.py
│   │       ├── arbeitnow.py
│   │       ├── remotive.py
│   │       └── jsearch.py
│   ├── routes/                  # One router per page
│   │   ├── pipeline.py          # Pipeline orchestration (7 extracted stages)
│   │   ├── preview.py           # Tailoring + preview (6 extracted functions)
│   │   ├── results.py
│   │   ├── settings.py
│   │   └── dashboard.py
│   └── utils/
│       ├── constants.py         # Shared constants, enums, keyword maps
│       ├── dedup.py             # Company/title normalization + dedup
│       ├── cosine.py            # Cosine similarity
│       └── file_naming.py       # Output file naming
├── frontend/
│   ├── templates/               # Jinja2 templates
│   │   ├── base.html            # Layout, Tailwind CDN, HTMX
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   ├── results.html
│   │   ├── preview.html
│   │   └── partials/            # HTMX partial templates
│   └── static/
│       └── favicon.ico
├── config/
├── output/                      # Generated .md files
├── start.sh / start.bat         # One-command startup
├── requirements.txt
├── requirements-dev.txt
└── .env.example
```

## Contributing

### Prerequisites

- Python 3.12+
- All required API keys configured in `.env`
- Dev dependencies: `pip install -r requirements-dev.txt`

### Development Workflow

Cvly follows strict **Test-Driven Development**. Every change - feature, bugfix, refactor - follows this cycle:

#### 1. RED - Write a Failing Test First

Before touching any source code, write a test that proves the bug exists or defines the expected behavior of the new feature. Run it and confirm it fails.

```bash
# Write your test in tests/
pytest tests/test_your_feature.py -v
# Must show FAILED
```

#### 2. GREEN - Minimal Implementation

Write the minimum code needed to make the test pass. No optimization, no cleanup, no extra features.

```bash
pytest tests/test_your_feature.py -v
# Must show PASSED
pytest tests/ -v
# ALL tests must pass - no regressions
```

#### 3. REFACTOR - Clean Up

Now improve the code: rename variables, extract functions, add docstrings, remove duplication. Run tests after every change to ensure nothing breaks.

```bash
pytest tests/ -v
ruff check backend/
radon cc backend/ -s -n C    # no function should be rated D or worse
```

### Code Standards

**SRP (Single Responsibility Principle):** One file = one responsibility. If a function does two things, split it. The `pipeline.py` orchestrator calls 7 extracted stage functions - each is independently testable.

**Frozen Pydantic models:** All models use `ConfigDict(frozen=True)`. Use `model_copy(update={...})` to create modified copies.

**Shared Literal types:** Contract types, profile types, seniority levels, and source types are defined once in `models/` and reused everywhere. No string duplication.

**Prompts in one file:** All LLM prompts live in `backend/prompts.py`, organized by module with research references. Never inline a prompt string in a module.

**Constants in one file:** Shared constants, keyword maps, and enums live in `backend/utils/constants.py`. No magic numbers or hardcoded strings in logic files.

### Branch Naming

```
feat/feature-name          # new feature
fix/bug-description        # bug fix
refactor/what-changed      # structural improvement
```

### Pull Request Checklist

Before submitting a PR, verify all of these:

- [ ] No lint errors: `ruff check backend/`
- [ ] No function rated D or worse: `radon cc backend/ -s -n C`
- [ ] No security findings: `bandit -r backend/ -ll`
- [ ] New code has tests (RED → GREEN → REFACTOR followed)
- [ ] No new `except Exception` - catch specific error types
- [ ] No hardcoded strings - use `constants.py` or translation keys
- [ ] No `TODO` comments - either implement it or open an issue

### Adding a New Job Source

1. Create `backend/services/job_apis/your_source.py`
2. Implement a client class with `async def search(self, preferences) -> list[RawJobPosting]`
3. If no API key needed: `__init__(self)` takes no arguments
4. If API key needed: add the key to `config.py`, `.env.example`, and the README
5. Add the source name to the `source` Literal in `backend/models/job.py`
6. Wire it into `_build_api_clients()` in `backend/routes/pipeline.py`
7. Add client-side location filtering if the API returns global results
8. Write tests in `tests/test_services/`

### Adding a New Prompt

1. Add the constant to `backend/prompts.py` in the correct module section
2. Include a research reference comment if applicable
3. Add anti-hallucination tests in `tests/` verifying the prompt contains required safety instructions
4. Use `{placeholder}` syntax for variables - never f-strings in prompt constants

### Research References

Prompt design and anti-hallucination strategies are informed by:

| Paper | What We Applied |
|---|---|
| [Grounded Optimization](https://arxiv.org/abs/2607.01457) (Indukuri & Agrawal, 2026) | 5-layer anti-hallucination defense, evaluator agent |
| [Chain-of-Verification](https://arxiv.org/abs/2309.11495) (Dhuliawala et al., Meta 2023) | Two-stage keyword classification before rewriting |
| [Google Multi-Stage Translation](https://arxiv.org/abs/2409.06790) (Briakou et al., 2024) | Translation brief with document context |
| [Iterative Translation Refinement](https://arxiv.org/abs/2306.03856) (Chen et al., EAMT 2024) | Native-quality translation output |
| Target-Language Prompting (IJONIS, 2026) | French instructions in French to avoid translationese |
| Harvard Career Services | STAR bullet formula |
| La Prompterie + HRLens | French cover letter conventions |

## License

MIT
