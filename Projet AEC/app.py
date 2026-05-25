import os
import json
import re
import random
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# ==========================================================================
# 1. CONFIGURATION ET CHARGEMENT DES CLÉS API
# ==========================================================================

chemin_env = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=chemin_env, override=True)

# Charge GEMINI_API_KEY_1 à _20
API_KEYS = [
    os.getenv(f"GEMINI_API_KEY_{i}")
    for i in range(1, 21)
    if os.getenv(f"GEMINI_API_KEY_{i}")
]

# Fallback si tu n'as qu'une seule clé nommée GEMINI_API_KEY
if not API_KEYS and os.getenv("GEMINI_API_KEY"):
    API_KEYS = [os.getenv("GEMINI_API_KEY")]

if not API_KEYS:
    raise ValueError("Aucune clé API trouvée dans .env (ajoute GEMINI_API_KEY_1, _2...)")

print("\n" + "="*60)
print(f"✅ {len(API_KEYS)} clé(s) API détectée(s)")
for i, k in enumerate(API_KEYS, 1):
    print(f"   {i}. {k[:8]}...{k[-4:]}")
print("="*60 + "\n")

# Crée un client pour chaque clé
CLIENTS = [(key, genai.Client(api_key=key)) for key in API_KEYS]

def is_quota_error(e: Exception) -> bool:
    """Détecte les erreurs 429/quota sans module supplémentaire"""
    msg = str(e).lower()
    return any(x in msg for x in ["429", "resource_exhausted", "quota", "rate limit", "exceeded", "permission_denied"])

def generate_with_failover(**kwargs):
    """Essaie les clés dans un ordre aléatoire, bascule si quota"""
    failed_keys = []
    shuffled = CLIENTS.copy()
    random.shuffle(shuffled)
    
    for api_key, client in shuffled:
        try:
            print(f"→ Tentative avec clé {api_key[:8]}...")
            return client.models.generate_content(**kwargs)
        except Exception as e:
            if is_quota_error(e):
                print(f"⚠️  Quota atteint sur {api_key[:8]}... → bascule")
                failed_keys.append(api_key)
                continue
            else:
                print(f"❌ Erreur critique: {e}")
                raise
    
    raise HTTPException(status_code=429, detail=f"Toutes les {len(API_KEYS)} clés ont atteint leur quota")

# ==========================================================================
# 2. FASTAPI
# ==========================================================================

app = FastAPI(title="Backend Simulateur Populaire IA")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Chargement du contexte programme
MESURES_PATH = Path(__file__).resolve().parent / "mesures.json"
if not MESURES_PATH.exists():
    MESURES_PATH = Path(__file__).resolve().parent / "mersures.json"

PROGRAMME_CONTEXTE = MESURES_PATH.read_text(encoding="utf-8") if MESURES_PATH.exists() else "[]"
print(f"📄 Contexte chargé: {MESURES_PATH.name if MESURES_PATH.exists() else 'aucun'}")

# ==========================================================================
# 3. MODÈLE DE DONNÉES
# ==========================================================================

class SimulateurPayload(BaseModel):
    statutPro: str
    tempsTravail: str
    revenuIndiv: float
    situationFoyer: str
    revenuConjoint: float
    enfantsACharge: int
    localisation: str
    ville: str
    statutLogement: str
    modeChauffage: str
    factureEnergie: float
    isolation: str
    modeTransport: str
    kmSemaine: float
    budgetAlimentation: float

# ==========================================================================
# 4. ENDPOINT D'ANALYSE
# ==========================================================================

@app.post("/api/analyse-budget")
async def analyser_budget(payload: SimulateurPayload):
    try:
        fiche_situation = f"""
        FICHE DE SITUATION DE L'UTILISATEUR :
        - Profil professionnel : {payload.statutPro}
        - Temps de travail : {payload.tempsTravail}h
        - Revenu individuel net : {payload.revenuIndiv} €
        - Situation foyer : {payload.situationFoyer}
        - Revenu conjoint : {payload.revenuConjoint} €
        - Enfants à charge : {payload.enfantsACharge}
        - Zone : {payload.localisation} - {payload.ville}
        - Logement : {payload.statutLogement}
        - Chauffage : {payload.modeChauffage}, facture {payload.factureEnergie}€
        - Isolation : {payload.isolation}
        - Transport : {payload.modeTransport}, {payload.kmSemaine} km/sem
        - Alimentation : {payload.budgetAlimentation}€/mois
        """

        prompt_systeme = """
        Tu es l'expert budgétaire du programme l'Avenir en Commun.
        1. Fais une recherche web pour trouver le barème IR 2025 actuel en France.
        2. Compare avec la réforme LFI à 14 tranches (gain sous 4000€/mois).
        3. Applique les mesures du JSON fourni (SMIC 1600€, blocage énergie, etc.).
        4. Réponds UNIQUEMENT avec un objet JSON valide, sans markdown, sans texte autour.
        Structure obligatoire :
        {
          "headline": "Titre percutant avec gain mensuel",
          "bloc_travail": "Analyse salaire et impôt",
          "bloc_logement": "Analyse énergie et loyer",
          "bloc_transports": "Analyse carburant/transports",
          "bloc_famille": "Analyse aides enfants"
        }
        """

        prompt_final = f"{fiche_situation}\n\nDONNÉES PROGRAMME:\n{PROGRAMME_CONTEXTE}"

        # Appel avec rotation aléatoire
        response = generate_with_failover(
            model='gemini-2.5-flash',
            contents=prompt_final,
            config=types.GenerateContentConfig(
                system_instruction=prompt_systeme,
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )

        # Nettoyage de la réponse pour extraire le JSON
        text = response.text.strip()
        text = re.sub(r'^```json\s*|\s*```$', '', text, flags=re.MULTILINE)
        match = re.search(r'\{.*\}', text, re.DOTALL)
        
        if not match:
            raise ValueError(f"Réponse non-JSON reçue: {text[:300]}")
        
        return json.loads(match.group(0))

    except HTTPException:
        raise
    except Exception as e:
        print(f"Erreur d'analyse : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")