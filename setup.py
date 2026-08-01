"""Cvly setup wizard - interactive .env configuration.

Launched automatically by start.sh / start.bat when .env is missing.
Works on macOS, Linux, and Windows.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

WIZARD_MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "\n  Cvly - Setup Wizard\n  -------------------\n",
        "choose_language": "Choose your language / Choisissez votre langue (EN/FR): ",
        "step_gemini": """
  Step {n}/{total} - Google Gemini (required)

  A page will open. Do this:
    1. Sign in with your Google account
    2. Click "Create API Key"
    3. Select an existing project (or create one).
    4. Copy the API key (it starts with AIza...).
    5. Come back here and paste it
""",
        "step_groq": """
  Step {n}/{total} - Groq (press Enter to skip)

  A page will open. Do this:
    1. Click "Sign Up" and create an account (no credit card needed)
    2. After login, click "Create API Key"
    3. Enter a name (e.g. cvly) and click "Submit"
    4. Copy the key that appears (it starts with gsk_...)
    5. Come back here and paste it
""",
        "step_france_travail": """
  Step {n}/{total} - France Travail (press Enter to skip)

  A page will open. Do this:
    1. Click "Se connecter" (top right) or create an account if needed
    2. Click the blue "Utiliser l'API" button
    3. Fill in the form:
       - Nom de l'application: Cvly
       - URL: https://example.com
       - Description: anything
    4. Click "Enregistrer"
    5. Click "Ajouter une API"
    6. Find "Offres d'emploi v2" and click "Ajouter"
    7. Scroll down, find "ROMEO v2" and click "Ajouter" too
    8. Go to your application settings
    9. Copy the "Identifiant client" (starts with PAR_...)
    10. Copy the "Cle secrete"
    11. Come back here and paste both
""",
        "step_adzuna": """
  Step {n}/{total} - Adzuna (press Enter to skip)

  A page will open. Do this:
    1. Click "Sign up" and create an account
    2. Select "Personal or academic research" when asked
    3. After signup, you are on the Dashboard
    4. Copy the "Application ID" (short number)
    5. Copy the "Application Key" (longer string)
    6. Come back here and paste both
""",
        "step_jsearch": """
  Step {n}/{total} - JSearch (press Enter to skip)

  A page will open. Do this:
    1. Create a RapidAPI account if you don't have one
    2. Click the "Pricing" tab
    3. Click "Subscribe" on the Basic plan (free)
    4. Go back to the "Endpoints" tab
    5. On the right side, find "X-RapidAPI-Key" and copy it
    6. Come back here and paste it
""",
        "step_lba": """
  Step {n}/{total} - La Bonne Alternance (press Enter to skip)

  Only needed if you search for alternance or internship contracts.
  A page will open. Do this:
    1. Click "Se connecter / S'inscrire"
    2. Enter your email
    3. Check your inbox and click the login link
    4. On your profile page, copy the "Jeton d'acces" / "Access token"
    5. Come back here and paste it
""",
        "step_google_sheets": """
  Step {n}/{total} - Google Sheets (press Enter to skip)

  This tracks your approved applications in a spreadsheet.
  It has 3 parts and takes about 10 minutes.

  PART A - Create a service account:
  A page will open. Do this:
    1. Create a project if asked (name it "cvly")
    2. Click "+ CREATE SERVICE ACCOUNT"
    3. Name: cvly-sheets
    4. Click "Create and Continue"
    5. Skip the optional steps
    6. Click on the email of the account you just created
    7. Click the "Keys" tab
    8. Click "Add Key" > "Create new key" > select "JSON" > click "Create"
    9. A file will be downloaded to your computer
    10. Come back here and paste the full path to that file
        Example Mac: /Users/you/Downloads/cvly-123456.json
        Example Windows: C:\\Users\\you\\Downloads\\cvly-123456.json
""",
        "step_google_sheets_apis": """
  PART B - Enable APIs:
  Two pages will open.
    1. On the first page, click "Enable"
    2. On the second page, click "Enable"
    3. Press Enter when done
""",
        "step_google_sheets_share": """
  PART C - Share the spreadsheet:
    1. Open sheets.google.com in your browser
    2. Create a new blank spreadsheet
    3. Click "Share" (top right)
    4. Paste this email: {service_account_email}
    5. Set access to "Editor"
    6. Uncheck "Notify people"
    7. Click "Share"
    8. Look at the URL bar. Copy the long ID between /d/ and /edit
       Example: https://docs.google.com/spreadsheets/d/THIS_PART/edit
    9. Come back here and paste that ID
""",
        "key_valid": "  * Valid - connected successfully",
        "key_invalid": "  * Invalid - {error}",
        "skip_prompt": "  Paste your key (or press Enter to skip): ",
        "paste_key": "  Paste your key: ",
        "paste_client_id": "  Paste your Client ID (starts with PAR_...), or press Enter to skip: ",
        "paste_client_secret": "  Paste your Client Secret: ",
        "paste_app_id": "  Paste your App ID (or press Enter to skip): ",
        "paste_app_key": "  Paste your App Key: ",
        "paste_sheet_id": "  Paste your Google Sheet ID (or press Enter to skip): ",
        "open_url": "  Opening {url} in your browser...",
        "open_url_manual": "  If it did not open, go to: {url}",
        "setup_complete": "\n  * Setup complete - {count} APIs configured\n  Run ./start.sh (or start.bat) to launch Cvly\n",
        "env_exists": "\n  .env already exists. Overwrite? (y/N): ",
        "service_account_prompt": "  Paste the FULL path to your JSON file (or press Enter to skip): ",
        "service_account_copied": "  * Service account copied to config/google_service_account.json",
        "required_note": "  (This key is required for Cvly to function.)",
        "press_enter_when_done": "  Press Enter to continue...",
        "validating": "  Validating...",
        "skipped": "  - Skipped",
        "step_app_settings": """
  Step {n}/{total} - App settings
""",
        "choose_default_language": "  Default UI language (fr/en) [fr]: ",
        "choose_default_country": "  Default country (FR/GB/US) [FR]: ",
    },
    "fr": {
        "welcome": "\n  Cvly - Assistant de configuration\n  ----------------------------------\n",
        "choose_language": "Choose your language / Choisissez votre langue (EN/FR): ",
        "step_gemini": """
  Etape {n}/{total} - Google Gemini (obligatoire)

  Une page va s'ouvrir. Faites ceci :
    1. Connectez-vous avec votre compte Google
    2. Cliquez sur "Create API Key"
    3. Sélectionnez un projet (ou créez-en un si demandé)
    4. Copiez la cle qui apparait (commence par AIza...)
    5. Revenez ici et collez-la
""",
        "step_groq": """
  Etape {n}/{total} - Groq (Entree pour passer)

  Une page va s'ouvrir. Faites ceci :
    1. Cliquez sur "Sign Up" et créez un compte (pas de carte bancaire)
    2. Apres connexion, cliquez sur "Create API Key"
    3. Entrez un nom (par ex. : cvly) et cliquez "Submit"
    4. Copiez la cle qui apparait (commence par gsk_...)
    5. Revenez ici et collez-la
""",
        "step_france_travail": """
  Etape {n}/{total} - France Travail (Entree pour passer)

  Une page va s'ouvrir. Faites ceci :
    1. Cliquez sur "Se connecter" (en haut a droite) ou créez un compte si besoin
    2. Cliquez sur le bouton bleu "Utiliser l'API"
    3. Remplissez le formulaire :
       - Nom de l'application : Cvly
       - URL : https://example.com
       - Description : ce que vous voulez
    4. Cliquez sur "Enregistrer"
    5. Cliquez sur "Ajouter une API"
    6. Trouvez "Offres d'emploi v2" et cliquez "Ajouter"
    7. Descendez, trouvez "ROMEO v2" et cliquez "Ajouter" aussi
    8. Allez dans les parametres de votre application
    9. Copiez l'"Identifiant client" (commence par PAR_...)
    10. Copiez la "Cle secrete"
    11. Revenez ici et collez les deux
""",
        "step_adzuna": """
  Etape {n}/{total} - Adzuna (Entree pour passer)

  Une page va s'ouvrir. Faites ceci :
    1. Cliquez sur "Sign up" et créez un compte
    2. Sélectionnez "Personal or academic research" lorsque cela vous est demandé
    3. Apres inscription, vous êtes sur le Dashboard
    4. Copiez l'"Application ID" (numero court)
    5. Copiez l'"Application Key" (chaine plus longue)
    6. Revenez ici et collez les deux
""",
        "step_jsearch": """
  Etape {n}/{total} - JSearch (Entree pour passer)

  Une page va s'ouvrir. Faites ceci :
    1. Créez un compte RapidAPI si vous n'en avez pas
    2. Cliquez sur l'onglet "Pricing"
    3. Cliquez "Subscribe" sur le plan Basic (gratuit)
    4. Retournez a l'onglet "Endpoints"
    5. A droite, trouvez "X-RapidAPI-Key" et copiez la valeur
    6. Revenez ici et collez-la
""",
        "step_lba": """
  Etape {n}/{total} - La Bonne Alternance (Entree pour passer)

  Utile uniquement si vous cherchez une alternance ou un stage.
  Une page va s'ouvrir. Faites ceci :
    1. Cliquez sur "Se connecter / S'inscrire"
    2. Entrez votre email
    3. Vérifiez votre boîte mail et cliquez sur le lien de connexion
    4. Sur votre page de profil, copiez le "Jeton d'acces"
    5. Revenez ici et collez-le
""",
        "step_google_sheets": """
  Etape {n}/{total} - Google Sheets (Entree pour passer)

  Pour suivre vos candidatures dans un tableur Google.
  Il y a 3 parties, comptez environ 10 minutes.

  PARTIE A - Creer un compte de service :
  Une page va s'ouvrir. Faites ceci :
    1. Créez un projet (nommez-le "cvly")
    2. Cliquez sur "+ CREATE SERVICE ACCOUNT"
    3. Nom : cvly-sheets
    4. Cliquez "Create and Continue"
    5. Passez les etapes optionnelles
    6. Cliquez sur l'email du compte que vous venez de creer
    7. Cliquez sur l'onglet "Keys"
    8. Cliquez "Add Key" > "Create new key" > Sélectionnez "JSON" > cliquez "Create"
    9. Un fichier se telecharge sur votre ordinateur
    10. Revenez ici et collez le chemin complet vers ce fichier
        Exemple Mac : /Users/vous/Downloads/cvly-123456.json
        Exemple Windows : C:\\Users\\vous\\Downloads\\cvly-123456.json
""",
        "step_google_sheets_apis": """
  PARTIE B - Activer les APIs :
  Deux pages vont s'ouvrir.
    1. Sur la premiere page, cliquez sur "Enable"
    2. Sur la deuxieme page, cliquez sur "Enable"
    3. Appuyez sur Entree quand c'est fait
""",
        "step_google_sheets_share": """
  PARTIE C - Partager le tableur :
    1. Ouvrez sheets.google.com dans votre navigateur
    2. Créez un nouveau tableur vierge
    3. Cliquez sur "Partager" (en haut a droite)
    4. Collez cet email : {service_account_email}
    5. Mettez l'acces sur "Editeur"
    6. Decochez "Prevenir les personnes"
    7. Cliquez "Partager"
    8. Regardez la barre d'URL. Copiez le long ID entre /d/ et /edit
       Exemple : https://docs.google.com/spreadsheets/d/CETTE_PARTIE/edit
    9. Revenez ici et collez cet ID
""",
        "key_valid": "  * Valide - connexion reussie",
        "key_invalid": "  * Invalide - {error}",
        "skip_prompt": "  Collez votre cle (ou Appuyez sur Entree pour passer) : ",
        "paste_key": "  Collez votre cle : ",
        "paste_client_id": "  Collez votre Identifiant client (PAR_...), ou Entree pour passer : ",
        "paste_client_secret": "  Collez votre Cle secrete : ",
        "paste_app_id": "  Collez votre App ID (ou Entree pour passer) : ",
        "paste_app_key": "  Collez votre App Key : ",
        "paste_sheet_id": "  Collez l'ID de votre Google Sheet (ou Entree pour passer) : ",
        "open_url": "  Ouverture de {url} dans votre navigateur...",
        "open_url_manual": "  Si ca ne s'est pas ouvert : {url}",
        "setup_complete": "\n  * Configuration terminee - {count} APIs configurees\n  Lancez ./start.sh (ou start.bat) pour demarrer Cvly\n",
        "env_exists": "\n  .env existe deja. Ecraser ? (o/N) : ",
        "service_account_prompt": "  Collez le chemin COMPLET du fichier JSON (ou Entree pour passer) : ",
        "service_account_copied": "  * Compte de service copie dans config/google_service_account.json",
        "required_note": "  (Cette cle est indispensable au fonctionnement de Cvly)",
        "press_enter_when_done": "  Appuyez sur Entree pour continuer...",
        "validating": "  Validation...",
        "skipped": "  - Passe",
        "step_app_settings": """
  Etape {n}/{total} - Reglages de l'application
""",
        "choose_default_language": "  Langue par defaut de l'interface (fr/en) [fr] : ",
        "choose_default_country": "  Code pays par defaut (FR/GB/US) [FR] : ",
    },
}


# -- Validation functions ------------------------------------------

_HTTP_USER_AGENT = "Cvly-Setup/1.0"


def _http_error_message(error: urllib.error.HTTPError) -> str:
    """Build a short error string including response body when useful."""
    body = ""
    try:
        body = error.read().decode("utf-8", errors="replace").strip()
    except Exception:
        body = ""
    if body and len(body) < 200:
        return f"HTTP Error {error.code}: {body}"
    return str(error)


def validate_gemini_key(key: str) -> tuple[bool, str]:
    """Test a Gemini API key by listing models."""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={key}"
        req = urllib.request.Request(
            url,
            method="GET",
            headers={"User-Agent": _HTTP_USER_AGENT},
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200, ""
    except urllib.error.HTTPError as e:
        return False, _http_error_message(e)
    except Exception as e:
        return False, str(e)


def validate_groq_key(key: str) -> tuple[bool, str]:
    """Test a Groq API key by listing models."""
    try:
        url = "https://api.groq.com/openai/v1/models"
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {key}",
                "User-Agent": _HTTP_USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200, ""
    except urllib.error.HTTPError as e:
        return False, _http_error_message(e)
    except Exception as e:
        return False, str(e)


def validate_france_travail(client_id: str, client_secret: str) -> tuple[bool, str]:
    """Test France Travail OAuth credentials."""
    try:
        url = "https://entreprise.francetravail.fr/connexion/oauth2/access_token?realm=/partenaire"
        data = urllib.parse.urlencode({
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
            "scope": f"application_{client_id} api_offresdemploiv2 o2dsoffre",
        }).encode()
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": _HTTP_USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            if result.get("access_token"):
                return True, ""
            return False, result.get("error_description", "Unknown error")
    except urllib.error.HTTPError as e:
        return False, _http_error_message(e)
    except Exception as e:
        return False, str(e)


def validate_adzuna(app_id: str, app_key: str) -> tuple[bool, str]:
    """Test Adzuna credentials with a minimal search."""
    try:
        url = (
            f"https://api.adzuna.com/v1/api/jobs/fr/search/1"
            f"?app_id={app_id}&app_key={app_key}&what=test&results_per_page=1"
        )
        req = urllib.request.Request(url, headers={"User-Agent": _HTTP_USER_AGENT})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200, ""
    except urllib.error.HTTPError as e:
        return False, _http_error_message(e)
    except Exception as e:
        return False, str(e)


def write_env_file(config: dict[str, str], path: Path | None = None) -> None:
    """Write the .env file from a config dict."""
    env_path = path or Path(".env")
    lines = [
        "# Cvly configuration - generated by setup wizard",
        "",
    ]
    for key, value in config.items():
        lines.append(f"{key}={value}")
    lines.append("")
    env_path.write_text("\n".join(lines), encoding="utf-8")


def setup_google_service_account(source_path: str) -> bool:
    """Copy a Google service account JSON to config/."""
    import shutil

    src = Path(source_path.strip().strip('"').strip("'"))
    if not src.exists():
        return False
    dest = Path("config/google_service_account.json")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)
    return True


# -- Wizard helpers ------------------------------------------------

def _open_url(url: str, msg: dict[str, str]) -> None:
    """Open a URL in the default browser and print guidance."""
    print(msg["open_url"].format(url=url))
    print(msg["open_url_manual"].format(url=url))
    try:
        webbrowser.open(url)
    except Exception:
        pass


def _ask(prompt: str, required: bool = False) -> str:
    """Prompt the user for input. Loop until non-empty if required."""
    while True:
        value = input(prompt).strip()
        if value or not required:
            return value
        print("  This field is required.")


def _wait_for_enter(msg: dict[str, str]) -> None:
    """Block until the user presses Enter before asking for credentials."""
    input(msg["press_enter_when_done"])


# -- Main wizard ---------------------------------------------------

def run_wizard() -> None:
    """Run the interactive setup wizard."""
    print("\n  Cvly - Setup\n")
    lang_choice = input(
        "  Choose your language / Choisissez votre langue (EN/FR): "
    ).strip().lower()
    lang = "fr" if lang_choice.startswith("f") else "en"
    msg = WIZARD_MESSAGES[lang]

    print(msg["welcome"])

    env_path = Path(".env")
    if env_path.exists():
        overwrite = input(msg["env_exists"]).strip().lower()
        if overwrite not in ("y", "o", "yes", "oui"):
            print("  Aborted.")
            return

    config: dict[str, str] = {}
    api_count = 0
    total_steps = 8

    # Step 1 - Gemini (required)
    print(msg["step_gemini"].format(n=1, total=total_steps))
    print(msg["required_note"])
    _open_url("https://aistudio.google.com/apikey", msg)
    _wait_for_enter(msg)
    key = _ask(msg["paste_key"], required=True)
    print(msg["validating"])
    valid, err = validate_gemini_key(key)
    if valid:
        print(msg["key_valid"])
        config["GEMINI_API_KEY"] = key
        api_count += 1
    else:
        print(msg["key_invalid"].format(error=err))
        config["GEMINI_API_KEY"] = key

    # Step 2 - Groq (recommended)
    print(msg["step_groq"].format(n=2, total=total_steps))
    _open_url("https://console.groq.com/keys", msg)
    _wait_for_enter(msg)
    key = _ask(msg["skip_prompt"])
    if key:
        print(msg["validating"])
        valid, err = validate_groq_key(key)
        if valid:
            print(msg["key_valid"])
            api_count += 1
        else:
            print(msg["key_invalid"].format(error=err))
        config["GROQ_API_KEY"] = key
        config["GROQ_MODEL"] = "llama-3.1-8b-instant"
    else:
        print(msg["skipped"])
        config["GROQ_API_KEY"] = ""

    # Step 3 - France Travail (recommended)
    print(msg["step_france_travail"].format(n=3, total=total_steps))
    _open_url("https://francetravail.io/data/api/offres-emploi", msg)
    _wait_for_enter(msg)
    client_id = _ask(msg["paste_client_id"])
    if client_id:
        client_secret = _ask(msg["paste_client_secret"], required=True)
        print(msg["validating"])
        valid, err = validate_france_travail(client_id, client_secret)
        if valid:
            print(msg["key_valid"])
            api_count += 1
        else:
            print(msg["key_invalid"].format(error=err))
        config["FRANCE_TRAVAIL_CLIENT_ID"] = client_id
        config["FRANCE_TRAVAIL_CLIENT_SECRET"] = client_secret
    else:
        print(msg["skipped"])
        config["FRANCE_TRAVAIL_CLIENT_ID"] = ""
        config["FRANCE_TRAVAIL_CLIENT_SECRET"] = ""

    # Step 4 - Adzuna (recommended)
    print(msg["step_adzuna"].format(n=4, total=total_steps))
    _open_url("https://developer.adzuna.com/", msg)
    _wait_for_enter(msg)
    app_id = _ask(msg["paste_app_id"])
    if app_id:
        app_key = _ask(msg["paste_app_key"], required=True)
        print(msg["validating"])
        valid, err = validate_adzuna(app_id, app_key)
        if valid:
            print(msg["key_valid"])
            api_count += 1
        else:
            print(msg["key_invalid"].format(error=err))
        config["ADZUNA_APP_ID"] = app_id
        config["ADZUNA_APP_KEY"] = app_key
    else:
        print(msg["skipped"])
        config["ADZUNA_APP_ID"] = ""
        config["ADZUNA_APP_KEY"] = ""

    # Step 5 - JSearch (optional but recommended)
    print(msg["step_jsearch"].format(n=5, total=total_steps))
    _open_url("https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch", msg)
    _wait_for_enter(msg)
    key = _ask(msg["skip_prompt"])
    if key:
        config["JSEARCH_API_KEY"] = key
        api_count += 1
        print(msg["key_valid"])
    else:
        print(msg["skipped"])
        config["JSEARCH_API_KEY"] = ""

    # Step 6 - La Bonne Alternance (optional but recommended)
    print(msg["step_lba"].format(n=6, total=total_steps))
    _open_url("https://api.apprentissage.beta.gouv.fr/fr/compte/profil", msg)
    _wait_for_enter(msg)
    key = _ask(msg["skip_prompt"])
    if key:
        config["LA_BONNE_ALTERNANCE_API_KEY"] = key
        api_count += 1
        print(msg["key_valid"])
    else:
        print(msg["skipped"])
        config["LA_BONNE_ALTERNANCE_API_KEY"] = ""

    # Step 7 - Google Sheets (optional but recommended)
    print(msg["step_google_sheets"].format(n=7, total=total_steps))
    _open_url("https://console.cloud.google.com/iam-admin/serviceaccounts", msg)
    _wait_for_enter(msg)
    sa_path = _ask(msg["service_account_prompt"])
    if sa_path:
        if setup_google_service_account(sa_path):
            print(msg["service_account_copied"])
            config["GOOGLE_SERVICE_ACCOUNT_PATH"] = "config/google_service_account.json"

            print(msg["step_google_sheets_apis"])
            _open_url(
                "https://console.cloud.google.com/apis/library/sheets.googleapis.com",
                msg,
            )
            _open_url(
                "https://console.cloud.google.com/apis/library/drive.googleapis.com",
                msg,
            )
            _wait_for_enter(msg)

            sa_email = ""
            sa_file = Path("config/google_service_account.json")
            if sa_file.exists():
                try:
                    sa_email = json.loads(sa_file.read_text(encoding="utf-8")).get(
                        "client_email", ""
                    )
                except (json.JSONDecodeError, OSError):
                    sa_email = ""
            print(
                msg["step_google_sheets_share"].format(
                    service_account_email=sa_email or "(see client_email in the JSON file)"
                )
            )
            _wait_for_enter(msg)
            sheet_id = _ask(msg["paste_sheet_id"])
            if sheet_id:
                config["GOOGLE_SHEET_ID"] = sheet_id
                api_count += 1
            else:
                config["GOOGLE_SHEET_ID"] = ""
        else:
            print(msg["key_invalid"].format(error="File not found"))
            config["GOOGLE_SERVICE_ACCOUNT_PATH"] = ""
            config["GOOGLE_SHEET_ID"] = ""
    else:
        print(msg["skipped"])
        config["GOOGLE_SERVICE_ACCOUNT_PATH"] = ""
        config["GOOGLE_SHEET_ID"] = ""

    # Step 8 - App settings
    print(msg["step_app_settings"].format(n=8, total=total_steps))
    config["APP_PORT"] = "8000"
    config["MATCH_THRESHOLD"] = "50"
    default_lang = _ask(msg["choose_default_language"]) or "fr"
    config["DEFAULT_LANGUAGE"] = default_lang
    default_country = _ask(msg["choose_default_country"]) or "FR"
    config["DEFAULT_COUNTRY"] = default_country.upper()

    write_env_file(config, env_path)
    print(msg["setup_complete"].format(count=api_count))


if __name__ == "__main__":
    run_wizard()
