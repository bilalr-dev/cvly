# PRD: AI Job Application Agent
 
**Version:** 1.0
**Last updated:** 2026-07-25
**Status:** Draft
**Target market:** France (primary), with multilingual support
 
---
 
## Overview
 
A lightweight, API-driven personal tool that automates the job search pipeline — from parsing your resume to discovering matching jobs, scoring fit, tailoring your CV per posting, and tracking applications in Google Sheets. Runs as a local FastAPI web app with zero heavy local dependencies.
 
---
 
## Problem
 
Applying to jobs manually is repetitive and slow. Each posting requires reading the JD, mentally mapping your experience to their requirements, rewriting bullet points to match ATS keywords, drafting a cover letter, and tracking where you applied. This agent automates every step except clicking "Apply."
 
---
 
## User Profiles
 
Single user (you). The system is general-purpose by design — any field, any location, any career stage — but configured per session via preferences. Primary target is the French job market, but the tool supports English output as well.
 
### Supported career stages
 
The tool must handle three distinct user profiles, each with different CV conventions, scoring logic, and output expectations:
 
| Profile | Contract types | Typical CV content | Scoring adjustments |
|---|---|---|---|
| **Experienced professional** | CDI, CDD, freelance | Work history with metrics, certifications | Standard scoring — experience alignment matters most |
| **Student seeking internship (stage)** | Stage (3–6 months) | Academic projects, coursework, associations, limited or no work experience | Experience weight reduced to 5%. Education and skills weight increased. Academic projects treated as equivalent to work bullets. |
| **Student seeking alternance** | Contrat d'apprentissage, contrat de professionnalisation | Mix of academic + part-time work, some projects | Experience weight reduced to 10%. Education match is critical (degree level, field). Availability rhythm matters (e.g., 3 weeks company / 1 week school). |
 
The profile is **auto-detected** from the parsed resume (Module 1) based on:
- If `experience` array is empty or all entries are < 6 months → likely student.
- If `education` contains an in-progress degree (`year` is null or in the future) → likely student.
- If the user selects `stage` or `alternance` in contract type filters → confirmed student profile.
The detected profile is stored in the session and affects Modules 4 and 5 behavior.
 
---
 
## Interaction Model
 
Local web UI served by FastAPI at `localhost:8000`. The user opens a browser, uploads their base resume once, sets search preferences (including output language), and triggers pipeline runs. Results appear in-browser with download links for `.md` files and a live link to the Google Sheets tracker.
 
---
 
## Language & Localization
 
### Output Language Selection
 
The user selects their preferred output language in the preferences page. This setting controls:
 
- The language of tailored resume bullets (Module 5).
- The language of the generated cover letter (Module 5).
- The language of the gap analysis summary in match results (Module 4).
- The language of the Google Sheets tracker headers and status labels (Module 6).
It does NOT affect:
 
- The internal JSON schemas (always English keys for code consistency).
- The web UI chrome (labels, buttons, navigation — always English in v1).
- The matching/scoring logic (language-agnostic, operates on structured data).
### Supported languages (v1)
 
| Code | Language | Notes |
|---|---|---|
| `fr` | French | Default. Primary market. CV and lettre de motivation output. |
| `en` | English | Full support. Resume and cover letter output. |
 
### Implementation
 
The selected language is passed to every Gemini prompt that produces user-facing text. Example instruction suffix:
 
```
Respond entirely in {language}. All bullet points, summaries, and the cover letter must be written in {language}. Use professional vocabulary appropriate for the {country} job market.
```
 
For French output, the prompt also includes:
 
```
Utilisez le vouvoiement dans la lettre de motivation. Respectez les conventions françaises de CV : pas de photo requise, pas de mention de l'âge, structure anti-chronologique.
```
 
For French student profiles (stage/alternance), additional conventions apply:
 
```
Pour un CV étudiant français :
- La section "Formation" apparaît AVANT la section "Expérience professionnelle".
- Inclure une section "Projets académiques" après la formation si pertinent.
- Inclure une section "Associations et activités extra-scolaires" si des rôles existent.
- Pour l'alternance : mentionner le rythme d'alternance (ex : "3 semaines en entreprise / 1 semaine en école") et la date de disponibilité.
- Pour le stage : mentionner la durée souhaitée et les dates de disponibilité.
- Les compétences techniques acquises en cours ou en projet personnel sont valides et doivent être mises en avant.
```
 
### Schema addition
 
The `SearchPreferences` schema gains a `language` field:
 
```json
{
  "titles": ["string"],
  "location": "string",
  "radius_km": "integer",
  "remote_ok": "boolean",
  "seniority": ["stagiaire", "alternant", "junior", "mid", "senior", "lead"],
  "exclude_keywords": ["string"],
  "max_results_per_source": "integer (default: 20)",
  "language": "fr | en (default: fr)",
  "country": "FR | GB | US | other (default: FR)"
}
```
 
---
 
## Tech Stack — Pinned Versions
 
### Runtime
 
| Component | Version | Notes |
|---|---|---|
| Python | 3.12.x | Minimum 3.11. Use latest 3.12 patch. |
| pip | latest | Package manager. No conda, no poetry for simplicity. |
| OS | Any (Windows/macOS/Linux) | No OS-specific dependencies. |
 
### Python Dependencies (`requirements.txt`)
 
```
# Web framework
fastapi==0.115.12
uvicorn[standard]==0.34.3
jinja2==3.1.6
python-multipart==0.0.20
 
# HTTP client
aiohttp==3.12.6
 
# Document parsing
pdfplumber==0.11.6
python-docx==1.1.2
 
# Google AI
google-generativeai==0.8.5
 
# Google Sheets
gspread==6.2.1
google-auth==2.40.1
 
# Config
python-dotenv==1.1.0
 
# Data validation
pydantic==2.11.4
```
 
### Gemini API
 
| Setting | Value |
|---|---|
| LLM model | `gemini-2.0-flash` |
| Embedding model | `text-embedding-004` |
| Temperature (parsing) | `0.0` (deterministic extraction) |
| Temperature (tailoring) | `0.3` (slight creativity for rewrites) |
| Temperature (cover letter) | `0.5` (more natural writing) |
| Response format | `response_mime_type="application/json"` + `response_schema` |
| Safety settings | All categories set to `BLOCK_NONE` (resume content may trigger false positives) |
 
### Job APIs
 
| API | Version / Plan | Base URL | Auth |
|---|---|---|---|
| Adzuna | Free (5 calls/sec, 250/day) | `https://api.adzuna.com/v1/api/jobs/fr/search/` | App ID + App Key (query params) |
| JSearch (RapidAPI) | Basic (free, 200 req/month) | `https://jsearch.p.rapidapi.com/search` | RapidAPI key (header) |
| Google CSE | Free (100 queries/day) | `https://www.googleapis.com/customsearch/v1` | API key (query param) + CSE ID |
| France Travail (Pôle Emploi) | Free (public API) | `https://api.francetravail.io/partenaire/offresdemploi/v2/offres/search` | OAuth2 client credentials |
 
#### France Travail API (added for French market)
 
Since the primary target is France, we add the France Travail (ex-Pôle Emploi) public API as a fourth job source. This is the official French government job board with the largest inventory of French postings.
 
- Auth: OAuth2 client credentials flow → `https://entreprise.francetravail.fr/connexion/oauth2/access_token`
- Free tier: 1,000 calls/day (generous for personal use).
- Returns structured JSON with `intitule`, `description`, `lieuTravail`, `entreprise`, `competences[]`.
- Filters: `motsCles`, `commune`, `distance`, `typeContrat`, `experience`.
- Key `typeContrat` values for students: `CDD` (often used for stages), `MIS` (mission/intérim), `SAI` (saisonnier). For alternance, filter via `motsCles=alternance` or `motsCles=apprentissage` since France Travail does not have a dedicated alternance contract type filter.
- Additional source for alternance: Google CSE can be configured to search `https://www.alternance.emploi.gouv.fr` (official French alternance portal) as a supplementary site.
### Google Sheets
 
| Setting | Value |
|---|---|
| Library | `gspread` 6.2.1 |
| Auth method | Service Account JSON key |
| Scopes | `https://www.googleapis.com/auth/spreadsheets`, `https://www.googleapis.com/auth/drive.file` |
 
---
 
## System Architecture
 
### Module 1: Resume Parser
 
**Input:** PDF or DOCX file uploaded via the web UI.
 
**Process:**
 
- Extract raw text using `pdfplumber` (PDF) or `python-docx` (DOCX).
- Send extracted text to Gemini 2.0 Flash with `response_schema` set to `ResumeProfile`.
- Gemini returns a JSON profile conforming to the schema.
- The extraction prompt is language-agnostic — it reads the CV regardless of what language it's written in and outputs English-keyed JSON with values preserved in the original language.
**Output:** `ResumeProfile` JSON stored in memory for the session.
 
**Gemini prompt (Module 1):**
 
```
You are a resume parsing engine. Extract all information from the following resume text into the exact JSON schema provided. Preserve the original language of the content (do not translate). If a field is not present in the resume, use null.
 
Special instructions:
- For experience entries, classify each as "fulltime", "internship", "alternance", "freelance", "volunteer", or "other" based on context clues (e.g., "stage", "stagiaire", "alternance", "apprenti", "intern", "working student").
- Extract academic projects separately from work experience. These include: coursework projects, hackathon entries, personal technical projects, and student association projects. They belong in "academic_projects", not "experience".
- If the candidate has an in-progress degree (mentions "en cours", "expected", "prévue", or a future graduation year), set "in_progress": true and extract the alternance rhythm if mentioned (e.g., "3 semaines entreprise / 1 semaine école").
- Extract associations, clubs, student organizations, and extracurricular roles into "associations_and_extracurriculars".
- For "detected_profile": set to "student_stage" if the candidate appears to be seeking an internship (no full-time experience, in-progress degree), "student_alternance" if they mention alternance or apprentissage, "experienced" otherwise.
- For metrics, extract any quantifiable achievements (percentages, amounts, team sizes, etc.) as separate strings.
 
Resume text:
{raw_text}
```
 
**Schema (`ResumeProfile`):**
 
```json
{
  "name": "string",
  "email": "string",
  "phone": "string | null",
  "location": "string | null",
  "summary": "string | null",
  "detected_profile": "experienced | student_stage | student_alternance (inferred by parser)",
  "skills": {
    "technical": ["string"],
    "soft": ["string"],
    "tools": ["string"],
    "certifications": ["string"]
  },
  "experience": [
    {
      "company": "string",
      "title": "string",
      "type": "fulltime | internship | alternance | freelance | volunteer | other",
      "start_date": "string (YYYY-MM or YYYY)",
      "end_date": "string | null (YYYY-MM or YYYY or 'Present')",
      "bullets": ["string"],
      "metrics": ["string"]
    }
  ],
  "academic_projects": [
    {
      "name": "string",
      "context": "string (course name, hackathon, personal project, association)",
      "description": "string",
      "technologies": ["string"],
      "metrics": ["string | null"]
    }
  ],
  "education": [
    {
      "institution": "string",
      "degree": "string",
      "field": "string",
      "year": "integer | null",
      "in_progress": "boolean",
      "alternance_rhythm": "string | null (e.g., '3 semaines entreprise / 1 semaine école', '3 jours / 2 jours')"
    }
  ],
  "associations_and_extracurriculars": [
    {
      "name": "string",
      "role": "string",
      "description": "string | null"
    }
  ],
  "languages": ["string"]
}
```
 
**Why this matters:** Every downstream module operates on this JSON — not raw text. This ensures consistency and makes comparisons deterministic.
 
---
 
### Module 2: Job Discovery
 
**Input:** User-defined search preferences (see schema in Language & Localization section).
 
**Process:**
 
- Query multiple free job APIs in parallel using `asyncio` + `aiohttp`:
  - **France Travail API** — primary source for French market, 1,000 calls/day.
  - **Adzuna API** — broad coverage, configured for `fr` country code by default.
  - **JSearch (RapidAPI)** — aggregates LinkedIn/Indeed/Glassdoor.
  - **Google Programmable Search Engine** — configured to search French job boards (Welcome to the Jungle, Indeed.fr, Apec.fr, LinkedIn, JobTeaser.com, alternance.emploi.gouv.fr).
- Deduplicate results by normalizing company name + job title + location.
- Store raw results in a local `cache/jobs_cache.json` to avoid re-fetching.
- Cache TTL: 24 hours. After that, re-fetch.
**Output:** List of `RawJobPosting` objects.
 
**Schema (`RawJobPosting`):**
 
```json
{
  "id": "string (SHA-256 hash of title+company+location)",
  "title": "string",
  "company": "string",
  "location": "string",
  "url": "string",
  "description_text": "string",
  "date_posted": "string (ISO 8601)",
  "source": "france_travail | adzuna | jsearch | google_cse",
  "salary_range": "string | null",
  "contract_type": "string | null (CDI, CDD, freelance, stage, alternance_apprentissage, alternance_professionnalisation)"
}
```
 
**Deduplication logic:**
 
1. Normalize company name: lowercase, strip legal suffixes (SAS, SARL, SA, Ltd, Inc, GmbH), strip whitespace.
2. Normalize title: lowercase, strip seniority prefixes (senior, junior, lead, staff).
3. Two postings match if `normalized_company == normalized_company AND normalized_title == normalized_title AND city_from_location == city_from_location`.
4. On match, keep the posting with the most complete `description_text`.
**Rate limiting strategy:**
 
- France Travail: 1,000 calls/day → primary source, no throttling needed.
- Adzuna: 250 calls/day → secondary source.
- JSearch: 200 calls/month → use as tertiary, cache aggressively.
- Google CSE: 100/day → supplementary, budget ~30 queries per run.
---
 
### Module 3: Job Description Parser
 
**Input:** `RawJobPosting.description_text` for each discovered job.
 
**Process:**
 
- Send each JD to Gemini 2.0 Flash with `response_schema` set to `ParsedJobDescription`.
- The prompt handles JDs in any language (French or English) and outputs English-keyed JSON.
**Gemini prompt (Module 3):**
 
```
You are a job description parser. Extract all requirements and details from the following job posting into the exact JSON schema provided. Normalize skill names to their canonical English form (e.g., "React.js" → "React", "Gestion de projet" → "Project Management"). Keep the ats_keywords in the original language of the posting (these will be used for ATS matching). If a field is not present, use null or an empty array.
 
Job posting text:
{description_text}
```
 
**Output:** `ParsedJobDescription` JSON.
 
**Schema (`ParsedJobDescription`):**
 
```json
{
  "job_id": "string",
  "title": "string",
  "company": "string",
  "required_skills": ["string"],
  "preferred_skills": ["string"],
  "required_tools": ["string"],
  "required_certifications": ["string"],
  "min_years_experience": "integer | null",
  "education_requirement": "string | null",
  "key_responsibilities": ["string"],
  "ats_keywords": ["string"],
  "contract_type": "string | null",
  "language_of_posting": "fr | en"
}
```
 
**Why this module exists:** Comparing structured JSON to structured JSON is far more reliable than comparing structured JSON to raw text. This step extracts what the job actually requires so the scorer can do a field-by-field comparison.
 
**Rate limiting:** At 15 RPM (Gemini free tier), parsing 20 JDs takes ~1.5 minutes. The pipeline batches in groups of 12 with a 60-second cooldown between batches.
 
---
 
### Module 4: CV Analyser Agent (Match & ATS Scorer)
 
**Input:** `ResumeProfile` + `ParsedJobDescription` + raw JD text for each job.
 
This module uses a two-pass approach: first a deterministic scoring pass (no LLM), then an LLM-powered qualitative analysis using the ATF methodology.
 
#### Pass 1: Deterministic Scoring (no API calls)
 
1. **Hard keyword match (40% of score)**
   - Direct string comparison: resume skills/tools/certs vs. JD required_skills/required_tools/required_certifications.
   - Case-insensitive, alias-aware. Alias map stored in `config/skill_aliases.json`:
     ```json
     {
       "javascript": ["js", "ecmascript", "es6", "es2015"],
       "kubernetes": ["k8s", "kube"],
       "project management": ["gestion de projet", "chef de projet"],
       "python": ["python3", "python 3"]
     }
     ```
   - Produces: `matched_keywords[]`, `missing_keywords[]`, `keyword_match_pct`.
2. **Semantic similarity (40% of score)**
   - Embed `ResumeProfile.summary` + all `experience.bullets` as a single vector using Gemini `text-embedding-004`.
   - Embed `ParsedJobDescription.key_responsibilities` + `required_skills` as a single vector.
   - Compute cosine similarity using `numpy` (the only numeric dependency, already installed with most setups).
   - Produces: `semantic_score` (0.0–1.0).
3. **Experience alignment (variable weight — see below)**
   - Compare `min_years_experience` vs. calculated years from resume work history.
   - Check education requirement match (degree level, field).
   - For alternance postings: check if the candidate's `alternance_rhythm` is compatible with the posting's schedule if specified.
   - Produces: `experience_fit_score` (0.0–1.0).
**Score weight adjustment by profile:**
 
The three scoring weights shift depending on the detected user profile and the contract type of the job posting:
 
| Scoring layer | Experienced (CDI/CDD) | Student → Stage | Student → Alternance |
|---|---|---|---|
| Hard keyword match | 40% | 35% | 35% |
| Semantic similarity | 40% | 40% | 40% |
| Experience alignment | 20% | 5% | 10% |
| Education match bonus | — | +20% | +15% |
 
For student profiles, the experience alignment weight drops sharply because requiring years of experience against a student CV would produce artificially low scores. The freed weight goes to an **education match bonus** that evaluates: degree level match (Bac+3, Bac+5, Master, etc.), field alignment (informatique vs. the JD's domain), and for alternance, rhythm compatibility.
 
When a student profile is matched against a CDI/CDD posting (mismatch), the score is calculated normally but a `profile_mismatch_warning` flag is set in the output. The UI displays this as a yellow notice: "This is a full-time position — your profile suggests you may be looking for a stage/alternance."
 
#### Pass 2: LLM Qualitative Analysis (ATF Methodology)
 
For jobs scoring above the threshold (default: 50) in Pass 1, the module runs a second pass using the CV Analyser Agent prompt. This provides recruiter-grade qualitative analysis.
 
**System prompt (CV Analyser Agent):**
 
```
Vous êtes un expert évaluateur de talents, analyste de recrutement et recruteur. Votre mission est d'analyser avec précision les CV et les descriptions de poste, d'identifier les points forts et les faiblesses du candidat, d'inférer les compétences implicites et de fournir une recommandation claire d'adéquation.
Suivez l'approche ATF :
 
* Analyser : lisez attentivement le texte du CV et la description de poste originale.
* Transformer : comparez les capacités du candidat aux exigences du poste.
* Formater : ne renvoyez que la sortie structurée demandée et évitez les commentaires hors sujet.
 
Important :
 
* Si le CV ne contient pas suffisamment d'informations, indiquez ce qui manque au lieu de deviner.
* Utilisez des preuves issues du CV pour étayer chaque conclusion.
* N'inventez pas de compétences, de titres de poste ou d'expériences qui ne sont pas présentes dans le texte.
* Produisez un résultat de qualité recruteur, clair et facile à consommer.
* Répondez en {language}.
```
 
**User prompt (CV Analyser Agent):**
 
```
Voici la description de poste originale et le contenu du CV du candidat.
 
Description de poste :
{raw_job_description}
 
Texte du CV du candidat :
{raw_resume_text}
 
Veuillez effectuer l'analyse suivante :
 
1. Résumé du candidat :
   - Résumez le candidat en 2-3 phrases.
   - Identifiez le niveau de séniorité probable (stagiaire/alternant/junior/intermédiaire/senior/lead).
 
2. Détails clés du candidat :
   - Compétences principales
   - Années d'expérience
   - Technologies et outils principaux
   - Formation / certifications
   - Réalisations marquantes ou résultats d'impact
 
3. Analyse de correspondance avec le poste :
   - Listez les correspondances exactes avec les exigences de la description de poste.
   - Listez les exigences importantes manquantes ou les points faibles.
   - Identifiez les risques, signaux d'alerte ou lacunes.
 
4. Évaluation de l'adéquation :
   - Fournissez un score d'adéquation de 0 à 10.
   - Donnez une recommandation en une phrase.
 
5. Format de sortie :
Renvoyez uniquement du JSON valide avec cette structure exacte :
{
  "summary": "...",
  "seniority": "stagiaire | alternant | junior | intermédiaire | senior | lead",
  "experience_years": ...,
  "skills": [...],
  "education": "...",
  "relevant_academic_projects": ["... (only for student profiles)"],
  "achievements": [...],
  "match": {
    "strengths": [...],
    "weaknesses": [...],
    "risks": [...],
    "transferable_skills": ["... (skills from academic/personal projects applicable to the role)"]
  },
  "score": ...,
  "recommendation": "...",
  "profile_type": "experienced | student_stage | student_alternance"
}
```
 
**Note on language:** When the user has selected English as their output language, the system prompt and user prompt are sent in English instead. The prompt templates are stored in `config/prompts/{lang}/cv_analyser.txt` so they can be edited without touching code.
 
#### Combined Output
 
**Schema (`MatchResult`):**
 
```json
{
  "job_id": "string",
  "overall_score": "float (0-100, from Pass 1)",
  "keyword_match_pct": "float",
  "semantic_score": "float",
  "experience_fit_score": "float",
  "matched_keywords": ["string"],
  "missing_keywords": ["string"],
  "gap_analysis": "string (natural language, from Pass 2)",
  "atf_analysis": {
    "summary": "string",
    "seniority": "string",
    "experience_years": "integer",
    "skills": ["string"],
    "education": "string",
    "achievements": ["string"],
    "match": {
      "strengths": ["string"],
      "weaknesses": ["string"],
      "risks": ["string"]
    },
    "recruiter_score": "float (0-10, from Pass 2)",
    "recommendation": "string"
  }
}
```
 
**Score reconciliation:** The UI displays both scores — the algorithmic score (0–100) and the recruiter score (0–10). They serve different purposes: the algorithmic score is for sorting and filtering; the recruiter score is for qualitative assessment. No attempt is made to merge them into one number.
 
**Filtering:** Jobs scoring below the configurable threshold (default: 50 algorithmic) skip Pass 2 entirely to save API calls. The user can manually trigger Pass 2 for any job via the UI.
 
---
 
### Module 5: CV Tailoring Engine
 
**Input:** `ResumeProfile` + `ParsedJobDescription` + `MatchResult` (with ATF analysis) for jobs above threshold.
 
**Process:**
 
1. **Bullet rewriting**
   - Prompt Gemini with: original bullets, missing keywords, the job's key responsibilities, and the ATF analysis strengths/weaknesses.
   - Instruction: rewrite using STAR method (Situation, Task, Action, Result), incorporating missing keywords only where truthful.
   - Language: output in the user's selected language (`fr` or `en`).
   **Gemini prompt (bullet rewriting):**
   ```
   You are a professional CV writer specializing in ATS optimization for the {country} job market.
 
   TASK: Rewrite the candidate's experience bullet points to better match the target job description.
 
   RULES:
   - Use the STAR method (Situation, Task, Action, Result) for each bullet.
   - Incorporate the following missing keywords ONLY where they truthfully apply to existing experience: {missing_keywords}
   - NEVER invent experience, tools, metrics, or achievements not present in the original CV.
   - If a missing keyword cannot be truthfully incorporated, skip it and list it in the "unfillable_gaps" field.
   - Preserve all quantifiable metrics from the original bullets.
   - Write in {language}.
   - For French output: use active verbs (piloté, développé, optimisé, mis en place, conçu).
   - For English output: use active verbs (led, developed, optimized, implemented, designed).
 
   CANDIDATE PROFILE TYPE: {profile_type}
 
   PROFILE-SPECIFIC RULES:
   - If profile is "student_stage" or "student_alternance":
     - Academic projects and coursework are valid experience. Rewrite them with the same STAR rigor as work bullets.
     - Highlight transferable skills (teamwork, methodology, tools used in projects).
     - For alternance candidates: mention the alternance rhythm ({alternance_rhythm}) in the availability section if provided.
     - Do NOT fabricate professional experience to compensate for a thin work history. Lean on projects, coursework, and associations instead.
     - Use verbs appropriate for student context: "réalisé dans le cadre de", "contribué à", "participé à", "développé lors de" (FR) / "completed as part of", "contributed to", "developed during" (EN).
   - If profile is "experienced": standard professional rewriting.
 
   ORIGINAL EXPERIENCE BULLETS:
   {original_bullets}
 
   ACADEMIC PROJECTS (if student profile):
   {academic_projects}
 
   ASSOCIATIONS & EXTRACURRICULARS (if student profile):
   {associations}
 
   TARGET JOB KEY RESPONSIBILITIES:
   {key_responsibilities}
 
   ATF ANALYSIS WEAKNESSES TO ADDRESS:
   {weaknesses}
 
   Return JSON:
   {
     "rewritten_experience_bullets": [{"original": "...", "rewritten": "...", "keywords_added": [...]}],
     "rewritten_project_bullets": [{"project_name": "...", "rewritten": "...", "keywords_added": [...]}],
     "unfillable_gaps": ["keyword1", "keyword2"]
   }
   ```
 
2. **Cover letter generation**
   - Prompt Gemini with: resume summary, job description, match result, ATF strengths.
   - Language: output in the user's selected language.
   **Gemini prompt (cover letter):**
   ```
   You are an expert cover letter writer for the {country} job market.
 
   TASK: Write a cover letter for the following job application.
 
   CANDIDATE PROFILE TYPE: {profile_type}
 
   RULES:
   - 3 paragraphs maximum.
   - Write in {language}.
   - NEVER mention skills or experience not present in the CV.
 
   RULES FOR EXPERIENCED PROFILES:
   - Paragraph 1: Hook — why this company and role specifically interest the candidate. Reference something specific about the company.
   - Paragraph 2: Value — map 2-3 specific achievements from the CV to specific requirements from the JD. Use concrete numbers.
   - Paragraph 3: Close — express enthusiasm and availability.
   - For French: use vouvoiement. Open with "Madame, Monsieur," and close with "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées."
   - For English: professional but not stiff. Open with "Dear Hiring Manager," and close with "Sincerely,".
 
   RULES FOR STUDENT PROFILES (stage/alternance):
   - Paragraph 1: Context — state the degree being pursued, the institution, and why this specific company/role aligns with the academic path. For alternance: explicitly state the rhythm (e.g., "dans le cadre de mon alternance en rythme 3 semaines / 1 semaine").
   - Paragraph 2: Value — highlight 2-3 relevant academic projects, coursework, or association experiences that demonstrate applicable skills. Link them to the JD requirements. Numbers from projects count (e.g., "application utilisée par 200 étudiants").
   - Paragraph 3: Motivation and availability — express genuine curiosity about the company's domain, mention availability dates and duration.
   - Tone: enthusiastic but not naive. Show awareness of the professional context.
   - For French: use vouvoiement. Open with "Madame, Monsieur," and close with "Je vous prie d'agréer, Madame, Monsieur, l'expression de mes salutations distinguées."
   - For English: open with "Dear Hiring Manager," and close with "Sincerely,".
   - For alternance: include the alternance rhythm and start date in paragraph 1 if available.
 
   CANDIDATE SUMMARY: {summary}
   CANDIDATE KEY ACHIEVEMENTS: {achievements}
   CANDIDATE ACADEMIC PROJECTS: {academic_projects}
   CANDIDATE EDUCATION (current): {current_education}
   ALTERNANCE RHYTHM (if applicable): {alternance_rhythm}
   JOB DESCRIPTION: {job_description}
   MATCH STRENGTHS: {strengths}
 
   Return the cover letter as plain text (not JSON).
   ```
 
3. **Output generation**
   - Render tailored resume as a clean markdown file.
   - Render cover letter as a separate markdown file.
   - File naming: `{date}_{company}_{title}_resume_{lang}.md` and `{date}_{company}_{title}_cover_{lang}.md`.
   - Date format: `YYYYMMDD`.
**Output:** Two `.md` files per job, saved to `output/` and downloadable from the UI.
 
**Hallucination guardrails:**
 
1. **Prompt-level:** Every prompt includes explicit anti-hallucination instructions (see above).
2. **Post-generation validation:** After Gemini returns tailored bullets, a validation function:
   - Extracts all proper nouns, tool names, and numeric claims from the output.
   - Checks each against the original `ResumeProfile.skills`, `experience.bullets`, and `experience.metrics`.
   - Any unmatched term is flagged as `WARNING: "{term}" not found in original CV` in the UI.
   - Implementation: simple set difference — `terms_in_output - terms_in_original = flagged_terms`.
3. **Human review:** Nothing goes to Google Sheets or gets saved until the user explicitly approves in the preview screen. The diff view makes additions and changes visually obvious.
---
 
### Module 6: Google Sheets Tracker
 
**Input:** Job metadata + match scores + tailoring status.
 
**Process:**
 
- On first run, create a new Google Sheet (or connect to an existing one via `GOOGLE_SHEET_ID` in `.env`).
- Use `gspread` + Google Service Account credentials to write rows.
- Each approved job appends a row.
**Sheet columns:**
 
| Column | Content | Type |
|---|---|---|
| Date | Date the job was processed | `YYYY-MM-DD` |
| Entreprise / Company | Company name | string |
| Poste / Title | Job title | string |
| Localisation / Location | Job location | string |
| Type contrat | CDI, CDD, stage, alternance, etc. | string |
| Score algo (0-100) | Algorithmic match score | integer |
| Score recruteur (0-10) | ATF recruiter score | float |
| Mots-clés manquants | Comma-separated missing keywords | string |
| Statut / Status | "À postuler" / "To apply" (default) | string |
| URL | Link to original posting | URL |
| CV fichier | Path to tailored `.md` | string |
| LM fichier | Path to cover letter `.md` | string |
| Recommandation | ATF recommendation string | string |
| Notes | Empty — for user's manual notes | string |
 
**Status values (French / English):**
 
- `À postuler` / `To apply` (default)
- `Postulé` / `Applied`
- `Entretien` / `Interview`
- `Refusé` / `Rejected`
- `Offre` / `Offer`
Column headers and status labels are set based on the user's selected language.
 
**Auth:** Google Service Account JSON key stored at `config/google_service_account.json` (path configured in `.env`, gitignored). The sheet must be shared with the service account email address.
 
---
 
## Web UI (FastAPI + Jinja2 + HTMX)
 
### Tech
 
| Component | Version | Notes |
|---|---|---|
| FastAPI | 0.115.12 | Async backend |
| Jinja2 | 3.1.6 | Server-side templates |
| HTMX | 2.0.4 (CDN) | Partial page updates without full JS framework |
| Tailwind CSS | 3.4.17 (CDN Play) | Utility-first styling, no build step |
| WebSocket | FastAPI built-in | Progress updates during pipeline runs |
 
**Why Tailwind via CDN:** Tailwind v3 offers a Play CDN script (`https://cdn.tailwindcss.com/3.4.17`) that works without any build step — no npm, no PostCSS, no `tailwind.config.js` required. The script processes utility classes at runtime in the browser. This is intended for development and small projects, which fits a single-user local tool perfectly. A single `<script src="https://cdn.tailwindcss.com/3.4.17"></script>` in `base.html` is all that's needed. Custom theme overrides (colors, fonts) can be inlined via `tailwind.config` in a `<script>` block in the template head.
 
**Why not Tailwind v4:** v4 drops the Play CDN and requires a build step or Vite plugin. Since the goal is zero build tooling, v3 is the right choice.
 
**Custom config (inline in `base.html`):**
 
```html
<script src="https://cdn.tailwindcss.com/3.4.17"></script>
<script>
  tailwind.config = {
    theme: {
      extend: {
        colors: {
          score: {
            high: '#16a34a',    // green-600 — score 80-100
            medium: '#d97706',  // amber-600 — score 60-79
            low: '#ea580c',     // orange-600 — score 40-59
            poor: '#dc2626',    // red-600 — score 0-39
          }
        }
      }
    }
  }
</script>
```
 
**No separate `style.css`:** All styling is done via Tailwind utility classes directly in the Jinja2 templates. The only custom CSS needed is for HTMX transition states (e.g., `.htmx-swapping { opacity: 0; transition: opacity 0.2s; }`), which goes in a small `<style>` block in `base.html`.
 
### Pages
 
**1. Home / Dashboard (`/`)**
 
- Summary stats: total jobs found, average match score, jobs above threshold.
- Quick link to Google Sheet (opens in new tab).
- Button to trigger a new pipeline run.
- Last run timestamp and status.
**2. Upload & Preferences (`/settings`)**
 
- File upload for resume (PDF/DOCX). Shows current parsed resume summary after upload.
- Form fields for search preferences:
  - Target titles (comma-separated text input)
  - Location (text input, e.g., "Paris", "Lyon", "Remote")
  - Radius in km (number input, default: 30)
  - Remote toggle (checkbox)
  - Seniority checkboxes (stagiaire, alternant, junior, mid, senior, lead)
  - Contract type checkboxes (CDI, CDD, freelance, stage, alternance (apprentissage), alternance (professionnalisation))
  - Exclude keywords (comma-separated text input)
  - **Language selector** (dropdown: Français / English)
- "Save preferences" persists to `config/preferences.json`.
**3. Results (`/results`)**
 
- Table of matched jobs, sorted by algorithmic score descending.
- Each row: company, title, algo score (color-coded badge), recruiter score, location, contract type, date posted, source.
- Score color coding: 80–100 green, 60–79 amber, 40–59 orange, 0–39 red.
- HTMX expandable row detail: ATF analysis, gap analysis, matched/missing keywords, strengths, weaknesses, risks.
- Action buttons per row: "Tailor CV" (POST via HTMX), "Skip", "View JD" (modal).
- "Tailor CV" triggers Module 5 for that specific job and shows inline preview.
**4. Preview & Download (`/preview/{job_id}`)**
 
- Side-by-side view: original bullets (left) vs. tailored bullets (right), diff-highlighted.
- Hallucination warnings shown as yellow banners above flagged terms.
- Cover letter preview below.
- "Approve & save" → writes to `output/`, adds row to Google Sheet, returns to results.
- "Edit" → inline textarea for manual markdown edits before saving.
- "Regenerate" → re-runs Module 5 with temperature += 0.1 for variety.
---
 
## Project Structure
 
```
job-agent/
├── backend/
│   ├── main.py                      # FastAPI app entry point, route registration
│   ├── config.py                    # Pydantic Settings, env var loading
│   ├── models/
│   │   ├── __init__.py
│   │   ├── resume.py                # ResumeProfile, ResumeSkills schemas
│   │   ├── job.py                   # RawJobPosting, ParsedJobDescription schemas
│   │   ├── match.py                 # MatchResult, ATFAnalysis schemas
│   │   ├── tailoring.py             # TailoredOutput, HallucinationWarning schemas
│   │   └── preferences.py          # SearchPreferences, AppSettings schemas
│   ├── modules/
│   │   ├── __init__.py
│   │   ├── resume_parser.py         # Module 1: PDF/DOCX → ResumeProfile JSON
│   │   ├── job_discovery.py         # Module 2: Multi-API job fetching + dedup
│   │   ├── jd_parser.py             # Module 3: JD text → ParsedJobDescription JSON
│   │   ├── cv_analyser.py           # Module 4: Deterministic scoring (Pass 1)
│   │   ├── atf_analyser.py          # Module 4: LLM qualitative analysis (Pass 2)
│   │   ├── tailoring.py             # Module 5: Bullet rewriting only
│   │   ├── cover_letter.py          # Module 5: Cover letter generation only
│   │   ├── output_generator.py      # Module 5: Render .md files from tailored data
│   │   ├── hallucination_checker.py # Post-generation validation
│   │   └── sheets_tracker.py        # Module 6: Google Sheets integration
│   ├── services/
│   │   ├── __init__.py
│   │   ├── gemini_llm.py            # Gemini LLM completions wrapper
│   │   ├── gemini_embeddings.py     # Gemini embeddings wrapper
│   │   ├── rate_limiter.py          # Generic async token-bucket rate limiter
│   │   └── job_apis/
│   │       ├── __init__.py
│   │       ├── base.py              # Abstract base class for job API clients
│   │       ├── france_travail.py
│   │       ├── adzuna.py
│   │       ├── jsearch.py
│   │       └── google_cse.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py             # GET / — dashboard page
│   │   ├── settings.py              # GET/POST /settings — upload & preferences
│   │   ├── pipeline.py              # POST /pipeline/run — trigger pipeline
│   │   ├── results.py               # GET /results — results page + HTMX partials
│   │   ├── preview.py               # GET/POST /preview/{job_id} — preview & approve
│   │   └── ws.py                    # WebSocket /ws/progress — pipeline progress
│   └── utils/
│       ├── __init__.py
│       ├── dedup.py                 # Company/title normalization + dedup logic
│       ├── cosine.py                # Cosine similarity (thin wrapper around numpy)
│       └── file_naming.py           # Output file naming conventions
├── frontend/
│   ├── templates/
│   │   ├── base.html                # Layout: nav, Tailwind CDN, HTMX script
│   │   ├── dashboard.html
│   │   ├── settings.html
│   │   ├── results.html
│   │   ├── preview.html
│   │   └── partials/
│   │       ├── job_row.html         # HTMX partial: single job row
│   │       ├── job_detail.html      # HTMX partial: expanded row detail
│   │       ├── progress.html        # HTMX partial: pipeline progress bar
│   │       └── score_badge.html     # HTMX partial: color-coded score badge
│   └── static/
│       └── favicon.ico
├── config/
│   ├── preferences.json             # User search preferences (gitignored)
│   ├── skill_aliases.json           # Skill name alias mappings
│   ├── prompts/
│   │   ├── fr/
│   │   │   ├── cv_analyser_system.txt
│   │   │   ├── cv_analyser_user.txt
│   │   │   ├── bullet_rewrite.txt
│   │   │   └── cover_letter.txt
│   │   └── en/
│   │       ├── cv_analyser_system.txt
│   │       ├── cv_analyser_user.txt
│   │       ├── bullet_rewrite.txt
│   │       └── cover_letter.txt
│   └── google_service_account.json  # Google SA key (gitignored)
├── output/                          # Generated .md files
├── cache/                           # jobs_cache.json (gitignored)
├── .env                             # API keys (gitignored)
├── .env.example                     # Template with required env var names
├── .gitignore
├── requirements.txt
└── README.md
```
 
---
 
## Coding Principles
 
### Single Responsibility Principle (SRP) — strictly enforced
 
Every file, class, and function does exactly one thing. When in doubt, split. Examples of how SRP is applied in this project:
 
- `gemini_llm.py` handles LLM completions. `gemini_embeddings.py` handles embeddings. They share nothing — no god `gemini.py` that does both.
- `cv_analyser.py` runs deterministic scoring (Pass 1). `atf_analyser.py` runs LLM qualitative analysis (Pass 2). They are separate modules, not two methods in one class.
- `tailoring.py` rewrites bullets. `cover_letter.py` generates cover letters. `output_generator.py` renders markdown files. Three files, three responsibilities.
- `hallucination_checker.py` validates output. It does not also generate output.
- Each route file in `routes/` handles one page or one endpoint group. No 500-line `main.py` with all routes inlined.
- Each Pydantic model file in `models/` groups schemas by domain (resume, job, match, tailoring, preferences). No single `models.py` with every schema.
### No over-engineering
 
- No abstractions until the second use case proves the need. One job API client does not justify a plugin system.
- No custom implementations when a library exists. If `numpy` does cosine similarity, use `numpy`. If `gspread` handles Google Sheets, use `gspread`. If `aiohttp` does HTTP, use `aiohttp`.
- No ORMs, no dependency injection frameworks, no event buses. Plain Python functions, Pydantic models, and `asyncio`.
- No premature generalization. The tool serves one user running one resume. Build for that.
### Library-first policy
 
Before writing any utility function, check if a maintained library already does it:
 
| Need | Use | Don't build |
|---|---|---|
| PDF text extraction | `pdfplumber` | Custom PDF parser |
| DOCX text extraction | `python-docx` | Custom XML walker |
| JSON validation | `pydantic` | Manual dict checking |
| HTTP requests | `aiohttp` | Custom HTTP client |
| Google Sheets | `gspread` | Raw Google API calls |
| Cosine similarity | `numpy.dot` | Manual vector math |
| Rate limiting | `asyncio.Semaphore` + `deque` | Custom thread pool |
| Environment config | `python-dotenv` + `pydantic.Settings` | Manual `os.environ` parsing |
 
---
 
## Environment Variables (`.env`)
 
```bash
# Gemini
GEMINI_API_KEY=your_key_here
 
# France Travail (Pôle Emploi)
FRANCE_TRAVAIL_CLIENT_ID=your_client_id
FRANCE_TRAVAIL_CLIENT_SECRET=your_client_secret
 
# Adzuna
ADZUNA_APP_ID=your_app_id
ADZUNA_APP_KEY=your_app_key
 
# JSearch (RapidAPI)
JSEARCH_API_KEY=your_rapidapi_key
 
# Google Custom Search Engine
GOOGLE_CSE_API_KEY=your_key
GOOGLE_CSE_ID=your_cse_id
 
# Google Sheets
GOOGLE_SERVICE_ACCOUNT_PATH=config/google_service_account.json
GOOGLE_SHEET_ID=optional_existing_sheet_id
 
# App config
APP_PORT=8000
MATCH_THRESHOLD=50
DEFAULT_LANGUAGE=fr
DEFAULT_COUNTRY=FR
```
 
---
 
## API Keys Required (All Free Tier)
 
| Service | Free tier limit | Sign-up URL | Purpose |
|---|---|---|---|
| Google Gemini API | 15 RPM, 1,500 req/day | `https://aistudio.google.com/apikey` | LLM + embeddings |
| France Travail API | 1,000 calls/day | `https://francetravail.io/data/api` | French job listings |
| Adzuna API | 250 calls/day | `https://developer.adzuna.com/` | International job listings |
| JSearch (RapidAPI) | 200 calls/month | `https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch` | Aggregated job listings |
| Google CSE | 100 queries/day | `https://programmablesearchengine.google.com/` | Custom job board search |
| Google Service Account | Unlimited | `https://console.cloud.google.com/iam-admin/serviceaccounts` | Google Sheets read/write |
 
---
 
## Rate Limiting Strategy
 
All Gemini calls go through a centralized async token-bucket rate limiter (`services/rate_limiter.py`):
 
- Bucket size: 12 tokens.
- Refill rate: 12 tokens per 60 seconds (leaving headroom below the 15 RPM cap).
- Automatic retry with exponential backoff (base 2s, max 32s, 3 retries) on HTTP 429 responses.
- Pipeline progress reported to the UI via WebSocket.
**Implementation:**
 
```python
class AsyncRateLimiter:
    def __init__(self, max_calls: int = 12, period_seconds: float = 60.0):
        self.max_calls = max_calls
        self.period = period_seconds
        self.semaphore = asyncio.Semaphore(max_calls)
        self.timestamps: deque = deque()
 
    async def acquire(self):
        # Wait if bucket is empty, release oldest token after period
        ...
```
 
**Typical pipeline run (20 jobs):**
 
| Step | Gemini calls | Time estimate |
|---|---|---|
| Resume parsing | 1 | ~2s |
| JD parsing (20 jobs) | 20 | ~2 min |
| Embedding generation | 21 (1 resume + 20 JDs) | ~2 min |
| ATF analysis (top 10 by score) | 10 | ~1 min |
| Tailoring (top 5 matches) | 10 (2 per job: bullets + cover) | ~1 min |
| **Total** | **62 calls** | **~6 min** |
 
---
 
## Hallucination Prevention
 
This is the highest-risk area. Three layers of defense:
 
1. **Prompt-level:** Every LLM prompt includes explicit anti-hallucination rules:
   - "N'inventez pas de compétences, de titres de poste ou d'expériences qui ne sont pas présentes dans le texte."
   - "NEVER invent experience, tools, metrics, or achievements not present in the original CV."
   - "If a missing keyword cannot be truthfully incorporated, skip it and list it in unfillable_gaps."
2. **Post-generation validation (`validate_output()`):**
   - Extract all proper nouns and tool names from tailored output using simple regex + the skill alias map.
   - Compute `flagged = terms_in_output - terms_in_original_resume`.
   - Each flagged term produces a `HallucinationWarning(term, context_sentence, severity)`.
   - Severity: `HIGH` if the term looks like a tool/technology name, `MEDIUM` if it's a proper noun, `LOW` otherwise.
   - Warnings displayed as yellow banners in the preview UI.
3. **Human review:** Nothing is saved or tracked until the user explicitly clicks "Approve" in the preview screen.
---
 
## Out of Scope (v1)
 
- Auto-applying to jobs (too risky, each platform is different).
- Scheduled/cron runs (v2 — `APScheduler` or system cron).
- Push notifications (v2 — Ntfy.sh or Telegram bot).
- Multiple resume versions (v1 uses one base resume).
- PDF output (v2 — `weasyprint` or LaTeX via Tectonic).
- User authentication (single-user local tool).
- UI internationalization (UI chrome is English-only in v1; only LLM output respects language selection).
- Salary analysis or negotiation features.
- Interview preparation features.
---
 
## Success Criteria
 
- Parses a resume (FR or EN) into clean JSON in under 5 seconds.
- Correctly detects student vs. experienced profile from resume content in 95%+ of cases.
- Returns 15+ relevant job matches per run from combined sources (France Travail + Adzuna + JSearch + Google CSE).
- For student profiles searching stage/alternance: returns 10+ relevant matches (smaller posting pool than CDI).
- Match scores correlate with manual assessment (spot-check 10 jobs, scores should feel right ±10%).
- Student profiles are NOT penalized for lack of professional experience when matching against stage/alternance postings.
- Tailored bullets contain zero hallucinated skills or experience (validated by post-generation check).
- Student CV output correctly places Formation before Expérience and includes Projets académiques section.
- Cover letters for alternance explicitly mention the rhythm and availability dates.
- Full pipeline completes in under 7 minutes for 20 jobs.
- Google Sheet updates reliably after each approved application.
- French and English outputs are both grammatically correct and professionally appropriate for their respective markets.
- ATF recruiter analysis provides actionable strengths/weaknesses, not generic platitudes.
 