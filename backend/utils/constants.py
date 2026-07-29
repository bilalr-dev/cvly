SENIORITY_KEYWORDS = {
    "stagiaire": ["stagiaire", "intern", "stage"],
    "alternant": ["alternant", "alternance", "apprenti"],
    "junior": ["junior", "jr"],
    "mid": ["mid", "intermédiaire", "confirmé"],
    "senior": ["senior", "sr", "expérimenté", "experienced"],
    "lead": ["lead", "principal", "staff", "head"],
}

CONTRACT_KEYWORDS = {
    "CDI": ["cdi", "permanent", "full-time", "full time", "unbefristet"],
    "CDD": ["cdd", "fixed-term", "fixed term", "contract", "temporary"],
    "stage": ["stage", "internship", "intern", "stagiaire"],
    "alternance_apprentissage": ["alternance", "apprentissage", "apprenti", "work-study"],
    "alternance_professionnalisation": ["alternance", "professionnalisation"],
    "freelance": ["freelance", "contractor", "independent", "indépendant"],
}

# Keywords that indicate a CDD is actually an apprenticeship contract.
# France Travail encodes these as "CDD - Contrat apprentissage".
ALTERNANCE_KEYWORDS: list[str] = [
    "apprentissage", "apprenti", "alternance", "contrat pro",
    "professionnalisation", "work-study",
]

# Bare-keyword signals for detecting contract type from a job title.
# Used when the API provides no explicit contract_type field.
# Keys match the contract_type values in CONTRACT_KEYWORDS.
TITLE_CONTRACT_SIGNALS: dict[str, list[str]] = {
    "stage": ["internship", "stage", "intern", "stagiaire"],
    "freelance": ["freelance", "contractor", "indépendant", "freelancer"],
    "alternance_apprentissage": ["alternance", "apprenti", "apprentissage", "work-study"],
}

# INSEE commune codes for major French cities.
# France Travail's `distance` parameter requires a `commune` code, not free-text.
CITY_INSEE_CODES: dict[str, str] = {
    "paris": "75056",
    "lyon": "69123",
    "marseille": "13055",
    "toulouse": "31555",
    "nice": "06088",
    "nantes": "44109",
    "strasbourg": "67482",
    "montpellier": "34172",
    "bordeaux": "33063",
    "lille": "59350",
    "rennes": "35238",
    "grenoble": "38185",
    "metz": "57463",
    "nancy": "54395",
    "rouen": "76540",
    "tours": "37261",
    "dijon": "21231",
    "angers": "49007",
    "clermont-ferrand": "63113",
    "reims": "51454",
    "aix-en-provence": "13001",
    "brest": "29019",
    "le havre": "76351",
    "limoges": "87085",
    "toulon": "83137",
}
