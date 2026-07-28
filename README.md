# Cvly

AI-powered job application agent — matches, scores, and tailors your CV for every posting.

### Quick Start (3 steps)
```bash
git clone https://github.com/bilalr-dev/cvly.git
cd cvly
cp .env.example .env
# Fill in your API keys (see setup guide below)
./start.sh        # macOS/Linux
start.bat          # Windows
```
The browser opens automatically to `http://localhost:8000`.

### What It Does
Upload Resume → Discover Jobs → Score Matches → Tailor CV → Track in Google Sheets

### API Keys Setup (detailed, step-by-step)

#### 1. Google Gemini API (REQUIRED)
- Go to https://aistudio.google.com/apikey
- Click "Create API Key"
- Copy the key → paste as `GEMINI_API_KEY` in `.env`
- Free tier: 15 requests/min, 1,500/day

#### 2. France Travail API (recommended — French job market)
- Go to https://francetravail.io and create an account
- Go to https://francetravail.io/data/api/offres-emploi
- Click "Utiliser l'API"
- Create an application:
  - Name: `Cvly`
  - URL: `https://example.com` (placeholder — not actually used)
- Subscribe to "Offres d'emploi v2"
- Go to your application settings to find:
  - `Identifiant client` (starts with `PAR_...`) → `FRANCE_TRAVAIL_CLIENT_ID`
  - `Clé secrète` → `FRANCE_TRAVAIL_CLIENT_SECRET`
- Free tier: 1,000 calls/day

#### 3. Adzuna API (recommended)
- Go to https://developer.adzuna.com/ and sign up:
  - Organisation: your name or "Cvly"
  - Website: `https://example.com`
  - Application: "Personal or academic research"
  - Monthly visitors: "N/A"
  - Market: "Europe"
  - Industry: "Career Services"
- After registration, find your credentials on the dashboard
- Copy → `ADZUNA_APP_ID` and `ADZUNA_APP_KEY`
- Free tier: 250 calls/day

#### 4. JSearch / RapidAPI (optional)
- Go to https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch
- Sign up or log in to RapidAPI
- Subscribe to the **BASIC** plan ($0.00/mo, no credit card)
- On any endpoint page, copy the `X-RapidAPI-Key` from the right panel
- Paste as `JSEARCH_API_KEY`
- Free tier: 200 calls/month

#### 5. Google Custom Search Engine (optional)

**Step A — Create the search engine:**
- Go to https://programmablesearchengine.google.com/
- Click "Add" to create a new search engine
- Name: `Cvly Job Search`
- Add these sites (one per line):
```
  welcometothejungle.com/*
  indeed.fr/*
  apec.fr/*
  linkedin.com/jobs/*
  jobteaser.com/*
  alternance.emploi.gouv.fr/*
```
- Click Create
- Copy the **Search engine ID** → `GOOGLE_CSE_ID`

**Step B — Get the API key:**
- Go to https://console.cloud.google.com/apis/library/customsearch.googleapis.com
- Enable the **Custom Search API**
- Go to Credentials → "+ CREATE CREDENTIALS" → "API key"
- Select "Custom Search API" in the API restrictions dropdown
- Copy the key → `GOOGLE_CSE_API_KEY`

#### 6. Google Sheets Tracking (optional)

**Step A — Create a service account:**
- Go to https://console.cloud.google.com/apis/credentials
- Click "+ CREATE CREDENTIALS" → "Service account"
- Name: `cvly-sheets` → Create and Continue → skip optional steps → Done
- Click on the created service account
- Go to "Keys" tab → "Add Key" → "Create new key" → JSON → Create
- A `.json` file downloads — move it:
```bash
  mv ~/Downloads/your-file.json config/google_service_account.json
```

**Step B — Enable APIs:**
- Go to https://console.cloud.google.com/apis/library/sheets.googleapis.com → Enable
- Go to https://console.cloud.google.com/apis/library/drive.googleapis.com → Enable

**Step C — Create and share the Sheet:**
- Go to https://sheets.google.com → create a blank sheet → name it "Cvly Job Tracker"
- Find your service account email:
```bash
  grep client_email config/google_service_account.json
```
- Share the sheet with that email address → give **Editor** access
- Copy the Sheet ID from the URL (between `/d/` and `/edit`)
- Paste as `GOOGLE_SHEET_ID`

### API Keys Summary Table

| Service | Required? | Free tier | `.env` variable(s) |
|---|---|---|---|
| Google Gemini | ✅ Yes | 15 RPM, 1,500/day | `GEMINI_API_KEY` |
| France Travail | Recommended | 1,000/day | `FRANCE_TRAVAIL_CLIENT_ID`, `FRANCE_TRAVAIL_CLIENT_SECRET` |
| Adzuna | Recommended | 250/day | `ADZUNA_APP_ID`, `ADZUNA_APP_KEY` |
| JSearch | Optional | 200/month | `JSEARCH_API_KEY` |
| Google CSE | Optional | 100/day | `GOOGLE_CSE_API_KEY`, `GOOGLE_CSE_ID` |
| Google Sheets | Optional | Unlimited | `GOOGLE_SERVICE_ACCOUNT_PATH`, `GOOGLE_SHEET_ID` |

### Pages Overview
- **Dashboard** (`/`): pipeline stats and run trigger
- **Settings** (`/settings`): upload resume, set search preferences and language
- **Results** (`/results`): scored job matches with expandable ATF analysis
- **Preview** (`/preview/{job_id}`): side-by-side bullet comparison, cover letter, approve/edit/regenerate

### Tech Stack
Python 3.12 · FastAPI · Gemini API · Tailwind CSS v3 · HTMX

### Development
```bash
pip install -r requirements-dev.txt
ruff check .
pytest
```

### Project Structure (condensed)
```
cvly/
├── backend/
│   ├── main.py
│   ├── state.py
│   ├── config.py
│   ├── prompts.py
│   ├── models/
│   ├── modules/
│   ├── services/
│   ├── routes/
│   └── utils/
├── frontend/
│   ├── templates/
│   └── static/
├── config/
├── output/
├── tests/
├── start.sh
├── start.bat
├── requirements.txt
└── .env.example
```
