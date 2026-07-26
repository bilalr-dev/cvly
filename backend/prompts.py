"""LLM prompt templates for all Cvly modules."""
from __future__ import annotations

RESUME_PARSE_PROMPT: str = """You are a resume parsing engine. Extract all information from the following resume text into the exact JSON schema provided. Preserve the original language of the content (do not translate). If a field is not present in the resume, use null.

Special instructions:
- For experience entries, classify each as "fulltime", "internship", "alternance", "freelance", "volunteer", or "other" based on context clues (e.g., "stage", "stagiaire", "alternance", "apprenti", "intern", "working student").
- Extract academic projects separately from work experience. These include: coursework projects, hackathon entries, personal technical projects, and student association projects. They belong in "academic_projects", not "experience".
- If the candidate has an in-progress degree (mentions "en cours", "expected", "prévue", or a future graduation year), set "in_progress": true and extract the alternance rhythm if mentioned (e.g., "3 semaines entreprise / 1 semaine école").
- Extract associations, clubs, student organizations, and extracurricular roles into "associations_and_extracurriculars".
- For "detected_profile": set to "student_stage" if the candidate appears to be seeking an internship (no full-time experience, in-progress degree), "student_alternance" if they mention alternance or apprentissage, "experienced" otherwise.
- For metrics, extract any quantifiable achievements (percentages, amounts, team sizes, etc.) as separate strings.

Resume text:
{raw_text}"""

JD_PARSE_PROMPT: str = """You are a job description parser. Extract all requirements and details from the following job posting into the exact JSON schema provided. Normalize skill names to their canonical English form (e.g., "React.js" → "React", "Gestion de projet" → "Project Management"). Keep the ats_keywords in the original language of the posting (these will be used for ATS matching). If a field is not present, use null or an empty array.

Job posting text:
{description_text}"""

ATF_SYSTEM_PROMPT_FR: str = """Vous êtes un expert évaluateur de talents, analyste de recrutement et recruteur. Votre mission est d'analyser avec précision les CV et les descriptions de poste, d'identifier les points forts et les faiblesses du candidat, d'inférer les compétences implicites et de fournir une recommandation claire d'adéquation.
Suivez l'approche ATF :

* Analyser : lisez attentivement le texte du CV et la description de poste originale.
* Transformer : comparez les capacités du candidat aux exigences du poste.
* Formater : ne renvoyez que la sortie structurée demandée et évitez les commentaires hors sujet.

Important :

* Si le CV ne contient pas suffisamment d'informations, indiquez ce qui manque au lieu de deviner.
* Utilisez des preuves issues du CV pour étayer chaque conclusion.
* N'inventez pas de compétences, de titres de poste ou d'expériences qui ne sont pas présentes dans le texte.
* Produisez un résultat de qualité recruteur, clair et facile à consommer.
* Répondez en {language}."""

ATF_USER_PROMPT_FR: str = """Voici la description de poste originale et le contenu du CV du candidat.

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
}"""

ATF_SYSTEM_PROMPT_EN: str = """You are an expert talent evaluator, recruitment analyst, and recruiter. Your mission is to precisely analyze resumes and job descriptions, identify the candidate's strengths and weaknesses, infer implicit skills, and provide a clear fit recommendation.
Follow the ATF approach:

* Analyze: carefully read the resume text and the original job description.
* Transform: compare the candidate's capabilities to the job requirements.
* Format: return only the requested structured output and avoid off-topic commentary.

Important:

* If the resume does not contain enough information, state what is missing instead of guessing.
* Use evidence from the resume to support every conclusion.
* Do not invent skills, job titles, or experiences that are not present in the text.
* Produce a recruiter-quality result that is clear and easy to consume.
* Respond in {language}."""

ATF_USER_PROMPT_EN: str = """Here is the original job description and the candidate's resume content.

Job description:
{raw_job_description}

Candidate resume text:
{raw_resume_text}

Please perform the following analysis:

1. Candidate summary:
   - Summarize the candidate in 2-3 sentences.
   - Identify the likely seniority level (intern/apprentice/junior/mid-level/senior/lead).

2. Key candidate details:
   - Core skills
   - Years of experience
   - Main technologies and tools
   - Education / certifications
   - Notable achievements or impact results

3. Job match analysis:
   - List exact matches with the job description requirements.
   - List important missing requirements or weaknesses.
   - Identify risks, red flags, or gaps.

4. Fit evaluation:
   - Provide a fit score from 0 to 10.
   - Give a one-sentence recommendation.

5. Output format:
Return only valid JSON with this exact structure:
{
  "summary": "...",
  "seniority": "intern | apprentice | junior | mid-level | senior | lead",
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
}"""
