"""LLM prompt templates for all Cvly modules.

Prompt design references:
- Grounded Optimization (Indukuri & Agrawal, arXiv:2607.01457) - anti-hallucination layers
- Google Multi-Stage Translation (Briakou et al., arXiv:2409.06790) - translation brief
- Iterative Translation Refinement (Chen et al., EAMT 2024) - native-quality output
- Target-Language Prompting (IJONIS, 2026) - anti-translationese
- Harvard Career Services - STAR bullet formula
- La Prompterie + HRLens - cover letter conventions
- OpenL Translation Research (arXiv:2302.09210) - translation quality
"""
from __future__ import annotations

# Shared JSON response wrapper appended by GeminiLLMService.generate_json
GEMINI_JSON_RESPONSE_SUFFIX: str = """

Return your response as valid JSON with these fields:
{schema_hint}
Return ONLY valid JSON. No markdown fences, no explanation."""

# ──────────────────────────────────────────────────────────────────────────────
# MODULE 1 - RESUME PARSING
# Deterministic extraction · temperature 0.0
# ──────────────────────────────────────────────────────────────────────────────

RESUME_PARSE_PROMPT: str = """You are an automated resume parsing engine. Extract all structured information from the candidate's resume text into the JSON schema defined below.

GENERAL EXTRACTION RULES:
- Preserve the original language of the content (do not translate).
- Do not invent, infer, or extrapolate information not explicitly present in the text.
- If a field or property is not present in the resume, set its value to null or an empty array [] as appropriate.

FIELD SPECIFICATIONS:
- experience: Classify each work entry type strictly as one of: "fulltime", "internship", "alternance", "freelance", "volunteer", or "other".
- academic_projects: Extract coursework projects, hackathon entries, personal technical projects, and student association projects here. Do NOT place them under "experience".
- education: If a degree is ongoing (mentions terms like "in progress", "expected", "en cours", "prévue", or a future graduation year), set "in_progress": true. If an alternance/co-op rhythm is explicitly mentioned, extract it into "alternance_rhythm".
- associations_and_extracurriculars: Extract student clubs, non-profit involvement, and extracurricular roles here.
- detected_profile: Output strictly one of:
  * "student_stage" (seeking an internship, currently studying, no full-time experience)
  * "student_alternance" (explicitly mentions seeking or completing alternance, work-study, or apprentissage)
  * "experienced" (all other candidates)
- metrics: Extract quantifiable statements (e.g., performance figures, percentages, budget amounts, team sizes) as separate strings within their respective entries.
- portfolio: Extract ONLY valid web URLs (e.g., personal website, GitHub, portfolio link). If a headline or title is a text string (e.g., "Data Analyst | Full Stack Developer"), do NOT place it here.
- summary: Extract the profile or summary paragraph verbatim. Do not prepend job titles or headlines to this field.
- languages: Array of strings formatted as "Language: Proficiency Level" (e.g., "English: Native", "French: B2").
- soft_skills: Array of objects containing "name" and contextual "description" strings if present.

TARGET JSON SCHEMA:
{{
  "full_name": string | null,
  "email": string | null,
  "phone": string | null,
  "linkedin": string | null,
  "portfolio": string | null,
  "summary": string | null,
  "detected_profile": "student_stage" | "student_alternance" | "experienced",
  "experience": [
    {{
      "title": string,
      "company": string,
      "type": "fulltime" | "internship" | "alternance" | "freelance" | "volunteer" | "other",
      "start_date": string | null,
      "end_date": string | null,
      "description": string | null,
      "metrics": [string]
    }}
  ],
  "academic_projects": [
    {{
      "name": string,
      "role": string | null,
      "description": string | null,
      "technologies": [string],
      "metrics": [string]
    }}
  ],
  "education": [
    {{
      "institution": string,
      "degree": string,
      "field_of_study": string | null,
      "start_date": string | null,
      "end_date": string | null,
      "in_progress": boolean,
      "alternance_rhythm": string | null
    }}
  ],
  "associations_and_extracurriculars": [
    {{
      "organization": string,
      "role": string,
      "description": string | null
    }}
  ],
  "hard_skills": [string],
  "soft_skills": [
    {{
      "name": string,
      "description": string | null
    }}
  ],
  "languages": [string]
}}

Resume text:
{raw_text}"""

# ──────────────────────────────────────────────────────────────────────────────
# MODULE 2 - JOB DESCRIPTION PARSING
# ATS keyword extraction · temperature 0.0
# ──────────────────────────────────────────────────────────────────────────────

JD_PARSE_PROMPT: str = """You are a job description analyst specializing in ATS optimization for European job markets.

TASK: Extract all structured information from the following job posting into the exact JSON schema provided below.

EXTRACTION RULES:
- company: ALWAYS extract the employer / hiring organization when it appears anywhere in the text
  (e.g. "chez NovaTech", "Rejoindre GreenPeak", "L'entreprise Atlas Soft", brand intros). Prefer the legal
  or brand name (e.g. "NovaTech Industries", "Atlas Soft"). Use "" only if no employer is mentioned at all.
- title: extract the job title from the posting when present.
- Normalize skill names in "required_skills" to their canonical English form (e.g., "React.js" → "React", "Gestion de projet" → "Project Management").
- Keep "ats_keywords" in the ORIGINAL language of the posting - these are used for exact ATS matching.
- "ats_keywords" MUST be a single flat array of strings. Do NOT nest objects or dictionaries inside it.
- For min_years_experience: extract only if explicitly stated. Set to 0 if "junior", "intern", or "débutant accepté". If "senior" or "5+ ans", extract the integer.
- For language_of_posting: detect the dominant language of the description text and output ONLY the two-letter ISO code ("fr" or "en").
- If the job description appears truncated or incomplete (ends with '…', '...', or is fewer than 200 characters), extract what is available and set all missing required arrays to empty lists []. Do not guess or infer unstated facts.

TARGET JSON SCHEMA:
{{
  "title": string | null,
  "company": string | null,
  "language_of_posting": "fr" | "en",
  "min_years_experience": integer | null,
  "key_responsibilities": [string],
  "required_skills": [string],
  "preferred_skills": [string],
  "required_tools": [string],
  "required_certifications": [string],
  "ats_keywords": [string],
  "education_requirement": string | null,
  "contract_type": string | null
}}

Job posting text:
{description_text}"""


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 3 - CV ANALYSER (ATF methodology)
# Analyse → Transform → Format · temperature 0.3
# Grounded to explicitly stated qualifications only
# ──────────────────────────────────────────────────────────────────────────────

ATF_SYSTEM_PROMPT: str = """You are an expert talent evaluator, recruitment analyst, and recruiter. Your mission is to precisely analyze resumes and job descriptions, identify candidate strengths and weaknesses based only on explicitly stated qualifications, and provide a clear fit recommendation.

Follow the ATF approach:
* Analyze: carefully read the resume text and the original job description.
* Transform: compare the candidate's capabilities to the job requirements.
* Format: return only the requested structured output and avoid off-topic commentary.

Important:
* If the resume does not contain enough information, state what is missing instead of guessing.
* Use evidence from the resume to support every conclusion.
* Do not invent skills, job titles, or experiences not present in the text.
* Produce a recruiter-quality result that is clear and easy to consume.
* Respond entirely in {language}."""

ATF_USER_PROMPT: str = """Here is the original job description and the candidate's resume content.

Job description:
{raw_job_description}

Candidate resume text:
{raw_resume_text}

Perform the analysis and return ONLY valid JSON matching this exact structure:
{{
  "summary": "2-3 sentence overview of the candidate tailored to this position",
  "seniority": "stagiaire" | "alternant" | "junior" | "intermédiaire" | "senior" | "lead",
  "experience_years": 0,
  "skills": ["core skill 1", "core skill 2"],
  "education": "Summary of degree and institution",
  "relevant_academic_projects": ["Relevant project 1"],
  "achievements": ["Notable metric or impact result 1"],
  "match": {{
    "strengths": ["Exact requirement matches"],
    "weaknesses": ["Missing key requirements or weak areas"],
    "risks": ["Gaps, frequent job changes, or red flags"],
    "transferable_skills": ["Applicable skills from personal or academic work"]
  }},
  "score": 0,
  "recommendation": "One sentence verdict on fit",
  "profile_type": "experienced" | "student_stage" | "student_alternance"
}}"""


# ──────────────────────────────────────────────────────────────────────────────
# MODULE 4 - CV TAILORING (bullet rewriting + cover letter)
# Harvard Career Services STAR formula · Grounded Optimization L4
# arXiv:2607.01457 · La Prompterie + HRLens
#
# Anti-hallucination (bullets):
#   - No "quantify" instructions - metrics come from original CV only
#   - XML boundary tags separate source-of-truth from JD context
#   - Missing keywords filtered to truthfully applicable ones before injection
#   - temperature 0.2
# Anti-bleed (cover letter):
#   - JD requirements never attributed to candidate's past experience
#   - temperature 0.3
# ──────────────────────────────────────────────────────────────────────────────
# Stage 1 - keyword classification (temperature 0.0, no rewriting)
KEYWORD_ANALYSIS_PROMPT: str = """You are a keyword relevance analyst. Your task is to classify each candidate keyword against the candidate's actual CV content. This is classification only - do not rewrite or generate any bullet text.

TASK:
For each keyword in the MISSING KEYWORDS list below, determine whether the candidate's CV provides truthful evidence that they possess this skill, tool, or competency.

CLASSIFICATION RULES:
- Mark a keyword as "applicable": true ONLY if you can cite specific evidence from the CV (a bullet point, a project, a skill listing, or a certification) that demonstrates the candidate genuinely has this capability.
- Mark a keyword as "applicable": false if there is no evidence in the CV. Do not infer skills from adjacent technologies (e.g., React does not imply React Native; PostgreSQL does not imply SQL Server).
- For each classification, provide a brief "evidence" string: the exact quote or reference from the CV that justifies your decision, or "No evidence found" if not applicable.
- Do not rewrite, rephrase, or generate any new content. This is a classification task only.

CANDIDATE CV CONTENT:
{cv_content}

CANDIDATE SKILLS LIST:
{skills_list}

MISSING KEYWORDS TO CLASSIFY:
{missing_keywords}

Return ONLY valid JSON matching this structure:
{{
  "classifications": [
    {{
      "keyword": "keyword_name",
      "applicable": true,
      "evidence": "Exact quote or reference from CV"
    }}
  ],
  "applicable": ["keyword1", "keyword2"],
  "unfillable_gaps": ["keyword3", "keyword4"]
}}"""

# Stage 2 - bullet rewriting with validated keywords (temperature 0.2)
BULLET_REWRITE_PROMPT: str = """You are a senior professional resume writer specialized in ATS optimization for the {country} job market. You write resumes that win interviews - not marketing copy.

CORE FORMULA (Harvard Career Services):
Every bullet = [Strong past-tense action verb] + [what you did / scope] + [quantified result or impact]

LANGUAGE RULE - CRITICAL:
Output language is {language}. Every single bullet MUST be written entirely in {language}. Translate any existing bullet while preserving its metrics, technical terms, and meaning.

ACTION VERBS:
- For French: piloté, orchestré, conçu, développé, optimisé, déployé, automatisé, restructuré, négocié, livré, réduit, augmenté, mis en place, implémenté, dirigé, coordonné, analysé, supervisé.
- For English: led, engineered, optimized, spearheaded, architected, delivered, reduced, increased, implemented, designed, built, automated, coordinated, analyzed, negotiated, launched, streamlined.

RULES (non-negotiable):
- Start EVERY bullet with a strong action verb in past tense. NEVER start with "I", "My", "Was responsible for", "Helped", "Assisted", or "Worked on".
- Preserve existing metrics from the original exactly. If the original bullet contains no numbers, percentages, or quantified results, do NOT add any. Never fabricate metrics.
- Incorporate missing keywords ONLY where they TRUTHFULLY apply to existing experience: {missing_keywords}
- If a keyword cannot be incorporated honestly, list it in "unfillable_gaps" - do not force or fabricate it.
- HALLUCINATION PREVENTION: Single or double-letter technology names (R, C, Go, C#) must ONLY be included if they appear VERBATIM in the original CV or skills list.
- HALLUCINATION PREVENTION: Do not infer React Native from React, or SQL from PostgreSQL. Only output explicitly stated tools.
- Maximum 4 bullets per role.

CANDIDATE PROFILE TYPE: {profile_type}

<SOURCE_OF_TRUTH>
The following is the candidate's actual experience. Every claim in your output must be traceable to content below.
ORIGINAL EXPERIENCE BULLETS:
{original_bullets}

ACADEMIC PROJECTS (student profiles):
{academic_projects}

ASSOCIATIONS & EXTRACURRICULARS (student profiles):
{associations}
</SOURCE_OF_TRUTH>

<TARGET_JOB_CONTEXT - FOR KEYWORD ALIGNMENT ONLY, DO NOT ATTRIBUTE TO CANDIDATE>
TARGET JOB KEY RESPONSIBILITIES:
{key_responsibilities}

ATF ANALYSIS WEAKNESSES TO ADDRESS:
{weaknesses}
</TARGET_JOB_CONTEXT>

Return ONLY valid JSON matching this structure:
{{
  "rewritten_experience_bullets": [
    {{
      "original": "Original bullet text",
      "rewritten": "Action verb + scope + result",
      "keywords_added": ["keyword1"]
    }}
  ],
  "rewritten_project_bullets": [
    {{
      "project_name": "Project name",
      "rewritten": "Action verb + scope + result",
      "keywords_added": ["keyword2"]
    }}
  ],
  "unfillable_gaps": ["keyword3"]
}}"""

COVER_LETTER_PROMPT: str = """You are an expert cover letter writer for the {country} job market. You write cover letters that hiring managers trust.

RECRUITER REALITY:
- Recruiters spot AI filler immediately: "passionate", "excited", "dynamic", "proven track record", "strong communicator", "team player", "detail-oriented", "results-driven". These are automatic red flags.
- The letter complements the CV - it does not repeat it word-for-word.
CRITICAL: Do not attribute JD requirements or the target company's activities to the candidate's past experience. The candidate does NOT work at {target_company} yet. Do not claim the candidate has done things described in the job description unless those achievements appear in the candidate's CV.

WORDS AND PHRASES TO NEVER USE:
passionate, excited, dynamic, proven track record, results-driven, team player, detail-oriented, motivated individual, strong communicator, fast learner, go-getter, highly motivated, within the attainment of, having taken note of your offer, fort de mon expérience, hautement motivé, ayant pris connaissance de votre offre.

STRUCTURE (3 paragraphs, approximately 200-300 words total):
- Paragraph 1 - HOOK: Open with {target_company}'s priority or business challenge. Do NOT use generic openings like "I am writing to apply for..." or "Ayant pris connaissance de votre offre...".
- Paragraph 2 - PROOF: Present 2-3 concrete achievements from the candidate's background that directly map to the role's top requirements using real metrics.
- Paragraph 3 - CLOSE: Express specific curiosity about the company's domain, provide availability details, and close professionally.
- Sign with the candidate's full name: {candidate_name}. Do NOT use placeholder text like "[Your Name]" or "[Votre nom]".

LANGUAGE AND REGISTER:
- Write entirely in {language}.
{language_conventions}

TARGET COMPANY: {target_company}
TARGET ROLE: {target_title}
CANDIDATE PROFILE TYPE: {profile_type}
CANDIDATE SUMMARY: {summary}
CANDIDATE KEY ACHIEVEMENTS: {achievements}
CANDIDATE ACADEMIC PROJECTS: {academic_projects}
CANDIDATE CURRENT EDUCATION: {current_education}
ALTERNANCE RHYTHM (if applicable): {alternance_rhythm}
JOB DESCRIPTION PRIORITIES: {job_description}
MATCH STRENGTHS: {strengths}

Return the cover letter as plain text. No JSON, no markdown, no preamble."""


# evaluator agent: generator-critic QA gate
# Compares original vs. rewritten bullets, flags fabricated content
# Fails safe to reject on API error
EVALUATOR_AGENT_PROMPT: str = """You are a factual accuracy auditor for CV/resume content. Your sole task is to compare original resume bullets against their rewritten versions and identify any fabricated content.

TASK:
For each rewritten bullet, compare it against the corresponding original bullet. Flag any claim in the rewritten version that is NOT supported by the original.

VIOLATION TYPES TO CHECK:

1. fabricated_metric - A number, percentage, dollar amount, or quantified result that does not appear in the original bullet.
   Example: Original "Improved API performance" → Rewritten "Improved API performance by 40%" → VIOLATION (40% is fabricated)

2. invented_skill - A tool, technology, framework, or skill name in the rewritten bullet that does not appear in the original bullet or the candidate's skills list.
   Example: Original "Built REST APIs" → Rewritten "Built REST APIs using GraphQL" → VIOLATION (GraphQL is invented)

3. jd_attribution - An achievement or responsibility that appears to come from the job description rather than the candidate's actual experience.
   Example: If the job description mentions "managing a team of 15" and the rewritten bullet says "Managed a team of 15" but the original says nothing about team management → VIOLATION

4. scope_inflation - The rewritten bullet significantly inflates the candidate's role, title, or scope beyond what the original states.
   Example: Original "Contributed to frontend development" → Rewritten "Led the frontend architecture redesign" → VIOLATION (scope inflated from contributor to lead)

COMPARISON RULES:
- Rephrasing for clarity is ACCEPTABLE (e.g., "worked on" → "developed" is fine).
- Adding keywords that accurately describe existing work is ACCEPTABLE (e.g., adding "Agile" if the original mentions sprints).
- Any NEW factual claim not traceable to the original is a VIOLATION.

ORIGINAL BULLETS:
{original_bullets}

REWRITTEN BULLETS:
{rewritten_bullets}

JOB DESCRIPTION (for jd_attribution detection):
{job_description}

LANGUAGE RULE:
Write ALL "description" and "summary" values in {language}. The user will read these directly - they must match the rest of the interface. This applies to every violation type, including scope_inflation, fabricated_metric, invented_skill, and jd_attribution.

Return ONLY valid JSON:
{{
  "is_acceptable": true,
  "violations": [
    {{
      "bullet_index": 0,
      "violation_type": "fabricated_metric",
      "description": "Specific description of what was fabricated",
      "severity": "HIGH"
    }}
  ],
  "summary": "Brief overall assessment"
}}

If no violations are found, return:
{{
  "is_acceptable": true,
  "violations": [],
  "summary": "All rewritten bullets are factually grounded in the original content."
}}"""


# ──────────────────────────────────────────────────────────────────────────────
# CRITICAL EVALUATOR - Independent Groq/Llama reviewer (maker-checker pattern)
# Ref: MA-CF (Xie et al., 2026) - decouple factuality from quality assessment
# Ref: Grounded Optimization L5 - different model for critic vs. generator
# Ref: Multi-agent maker-checker (beam.ai 2026) - cheap fast checker
# ──────────────────────────────────────────────────────────────────────────────

CRITICAL_EVALUATOR_SYSTEM_PROMPT: str = """You are an independent factual accuracy auditor. You review CV/resume documents that were generated by another AI system. Your job is to catch fabrications, exaggerations, and errors that the generating AI may have introduced.

You are NOT the author. You are the critic. Be skeptical. Flag anything suspicious.

Return your review as valid JSON. Always include "is_acceptable" (boolean), "issues" (array), and "summary" (string)."""


CRITICAL_REVIEW_BULLETS_PROMPT: str = """Review these rewritten CV bullets for factual accuracy.

For each rewritten bullet, compare it against the corresponding original. Flag ANY claim that is not supported by the original.

CHECK FOR:
1. FABRICATED METRICS - numbers, percentages, or quantities not in the original
2. INVENTED SKILLS/TOOLS - technologies or tools not mentioned in the original
3. SCOPE INFLATION - role described as bigger than the original states (e.g., "contributed" → "led")
4. JD ATTRIBUTION - achievements that appear to come from the job description, not the candidate's history

ORIGINAL BULLETS:
{original_bullets}

REWRITTEN BULLETS:
{rewritten_bullets}

JOB DESCRIPTION (for detecting JD attribution):
{job_description}

LANGUAGE RULE:
Write ALL "explanation" and "summary" values in {language}. The user reads these directly - they must match the rest of the interface.

Return JSON:
{{
  "is_acceptable": true/false,
  "issues": [
    {{
      "bullet_index": 0,
      "type": "fabricated_metric|invented_skill|scope_inflation|jd_attribution",
      "original_text": "what the original said",
      "rewritten_text": "what the rewrite claims",
      "explanation": "why this is a problem"
    }}
  ],
  "summary": "Overall assessment in one sentence"
}}"""


CRITICAL_REVIEW_COVER_LETTER_PROMPT: str = """Review this cover letter for factual accuracy against the candidate's actual background.

CHECK FOR:
1. ENTITY BLEED - does the letter claim the candidate already works at {target_company}?
2. HALLUCINATED ACHIEVEMENTS - are there claims not supported by the candidate's summary or achievements list?
3. JD PARROTING - does the letter copy phrases from the job description as if they are the candidate's experience?
4. TONE MISMATCH - does the language/register match the target market?

COVER LETTER:
{cover_letter}

CANDIDATE SUMMARY:
{candidate_summary}

CANDIDATE ACTUAL ACHIEVEMENTS:
{candidate_achievements}

TARGET COMPANY: {target_company}

JOB DESCRIPTION:
{job_description}

LANGUAGE RULE:
Write ALL "explanation" and "summary" values in {language}. The user reads these directly - they must match the rest of the interface.

Return JSON:
{{
  "is_acceptable": true/false,
  "issues": [
    {{
      "type": "entity_bleed|hallucinated_achievement|jd_parroting|tone_mismatch",
      "text": "the problematic text from the cover letter",
      "explanation": "why this is a problem"
    }}
  ],
  "summary": "Overall assessment in one sentence"
}}"""


CRITICAL_REVIEW_CV_PROMPT: str = """Review this tailored CV for structural integrity and language consistency.

CHECK FOR:
1. LANGUAGE MIXING - is the entire document in {target_language}? Flag any sentences in the wrong language.
2. UNTRANSLATED SECTIONS - are all section headings, bullet points, and descriptions translated?
3. STRUCTURAL GAPS - are there empty sections, missing dates, or broken formatting?
4. DUPLICATE CONTENT - are any bullets repeated across different roles?

TAILORED CV (Markdown):
{cv_markdown}

ORIGINAL RESUME (for comparison):
{original_resume}

TARGET LANGUAGE: {target_language}

LANGUAGE RULE:
Write ALL "explanation" and "summary" values in {language}. The user reads these directly - they must match the rest of the interface.

Return JSON:
{{
  "is_acceptable": true/false,
  "issues": [
    {{
      "type": "language_mixing|untranslated|structural_gap|duplicate_content",
      "location": "which section or line",
      "text": "the problematic text",
      "explanation": "what's wrong"
    }}
  ],
  "summary": "Overall assessment in one sentence"
}}"""


# ──────────────────────────────────────────────────────────────────────────────
# Gemini re-writes after Groq flags problems
# Ref: MA-CF (Xie et al., 2026)
# ──────────────────────────────────────────────────────────────────────────────

BULLET_CORRECTION_PROMPT: str = """You previously rewrote CV bullets for ATS optimization. An independent reviewer found issues with your output. Fix ONLY the flagged issues - do not change bullets that were not flagged.

RULES:
- Fix each flagged bullet according to the reviewer's feedback
- Do NOT introduce new information not present in the original bullet
- Do NOT change unflagged bullets
- Preserve all existing keywords and formatting

ORIGINAL BULLETS:
{original_bullets}

YOUR PREVIOUS REWRITE:
{rewritten_bullets}

REVIEWER FEEDBACK (fix these issues):
{issues}

Return the corrected bullets in the same JSON format as before.
Write all content in {language}."""


COVER_LETTER_CORRECTION_PROMPT: str = """You previously wrote a cover letter. An independent reviewer found issues. Fix ONLY the flagged issues - preserve everything else.

RULES:
- Fix each issue according to the reviewer's feedback
- Do NOT invent new achievements
- Do NOT change sections that were not flagged
- Maintain the same structure and tone

YOUR PREVIOUS COVER LETTER:
{cover_letter}

REVIEWER FEEDBACK (fix these issues):
{issues}

Return the corrected cover letter as plain text.
Write entirely in {language}."""


# ──────────────────────────────────────────────────────────────────────────────
# TRANSLATION - Native-quality CV content translation
# Briakou et al. 2024 (arXiv:2409.06790) · Chen et al. EAMT 2024
# IJONIS 2026 · OpenL (arXiv:2302.09210)
#
# Anti-translationese:
#   - French instructions written in French to activate native register
#   - Concrete verb/title mappings prevent literal translation
#   - Anglicism blacklist with correct alternatives
#   - temperature 0.0
# ──────────────────────────────────────────────────────────────────────────────
TRANSLATION_PROMPT: str = """# TRANSLATION BRIEF

You are translating professional CV/resume content for the {target_language} job market. The audience is recruiters and ATS systems. The output must read as if originally written by a native speaker - not as a translation.

## DOCUMENT CONTEXT
- Document type: CV / resume (professional experience bullets, summary, skills, education)
- Target audience: recruiters, hiring managers, ATS (Applicant Tracking Systems)
- Register: factual, concise, action-verb-driven. No promotional language, no filler.

## CORE RULES
- The content is Markdown. Preserve ALL markdown formatting syntax (**, *, ##, -, |, etc.). Only translate the human-readable text.
- Translate for meaning and natural professional flow, not word-for-word.
- Replace idioms and expressions with natural native equivalents.
- Every translated bullet must start with a strong past-tense action verb.

## DO NOT TRANSLATE (preserve exactly as-is)
- Technical tool names: React, Docker, AWS, PostgreSQL, NestJS, Git, CI/CD, Kubernetes, Python, TypeScript, Node.js, etc.
- Company names, proper nouns, brand names
- Institution names and école names (e.g., "École Imaginaire", "Institut Hexa", "Campus Nord" - keep original)
- URLs, email addresses, phone numbers, dates
- CEFR language levels (A1-C2, Native)

## FRENCH-SPECIFIC INSTRUCTIONS
When translating to French, follow these rules to avoid translationese:

Traduisez le contenu comme si vous rédigiez un CV français original. Utilisez le registre professionnel standard. Évitez toute formulation qui trahirait une traduction littérale de l'anglais.

VERBES D'ACTION POUR CV FRANÇAIS (utilisez ces verbes, pas des traductions littérales) :
- "Managed" → "Piloté" ou "Dirigé" (JAMAIS "Managé")
- "Developed" → "Conçu" ou "Développé"
- "Implemented" → "Mis en place" ou "Déployé"
- "Optimized" → "Optimisé"
- "Led" → "Dirigé" ou "Piloté"
- "Built" → "Conçu" ou "Développé"
- "Coordinated" → "Coordonné"

TITRES DE POSTE FRANÇAIS (formulation naturelle, pas de traduction mot-à-mot) :
- "Software Engineer" → "Ingénieur logiciel"
- "Developer" → "Développeur"
- "Project Manager" → "Chef de projet"
- "Data Analyst" → "Analyste de données"
- "Team Lead" → "Responsable d'équipe"
- "Consultant" → "Consultant" (identique)

ANGLICISMES À ÉVITER :
- "Manager une équipe" → "Diriger une équipe"
- "Implémenter" → "Mettre en place" ou "Déployer"
- "Délivrer un projet" → "Livrer un projet"
- "Adresser un problème" → "Résoudre un problème"
- "Supporter" (au sens d'accompagner) → "Accompagner" ou "Assurer le support de"

## ENGLISH-SPECIFIC INSTRUCTIONS
When translating to English:
- Use direct, clear, professional English.
- Prefer active voice and strong verbs: led, built, designed, optimized, delivered, reduced, increased.
- Do not over-translate French professional terms that have standard English equivalents (e.g., "stage" → "internship", not "training period").

Output only the translated text. No explanations, no notes, no preamble.

Content to translate:
{content}
"""

# ──────────────────────────────────────────────────────────────────────────────
# Map free-text job titles to French ROME codes
# ──────────────────────────────────────────────────────────────────────────────

ROME_CODE_LOOKUP_PROMPT: str = """You are an expert in the French ROME occupational classification system (Répertoire Opérationnel des Métiers et des Emplois).

Given the following job title(s), return the most relevant ROME codes.

RULES:
- Return between 1 and 5 ROME codes, ordered by relevance
- Use only real ROME codes (format: one letter + four digits, e.g., M1805)
- If the title is in English, find the French equivalent first
- If unsure, return the broader category code

Job title(s): {titles}

Return ONLY valid JSON:
{{
  "rome_codes": ["M1805", "M1810"],
  "mapping": {{
    "M1805": "Études et développement informatique",
    "M1810": "Production et exploitation de systèmes d'information"
  }}
}}"""
