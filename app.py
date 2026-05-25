import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

# Chargement d'un fichier .env si présent localement
load_dotenv()

# === CONFIGURATION & CHARGEMENT DES CLÉS API ===
def get_genai_client():
    keys = []
    # Parcourt l'environnement pour trouver des clés valides (Idéal pour Render)
    for name, value in os.environ.items():
        if name.startswith("GOOGLE_API_KEY") or name.startswith("GEMINI_API_KEY"):
            if value and value.strip() and value.strip() not in keys:
                keys.append(value.strip())
    
    if not keys:
        # Fallback si aucune variable système n'est définie (tente l'initialisation par défaut)
        print("⚠️ Aucune clé explicite trouvée dans l'environnement. Initialisation standard.")
        return genai.Client()
    
    print(f"✅ Client initialisé avec la clé active détectée dans l'environnement.")
    return genai.Client(api_key=keys[0])

# === INITIALISATION FASTAPI ===
app = FastAPI(title="Backend Simulateur Populaire - Alignement Complet")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permet les requêtes de votre fichier HTML en local ou hébergé
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODÈLE DE DONNÉES (Payload du Formulaire HTML) ===
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

# === ENDPOINT D'ANALYSE ===
@app.post("/api/analyse-budget")
async def analyser_budget(payload: SimulateurPayload):
    try:
        client = get_genai_client()
        
        # Construction de la fiche de situation textuelle lue par l'IA
        fiche_situation = f"""
        SITUATION RÉELLE DE L'UTILISATEUR :
        - Statut professionnel : {payload.statutPro}
        - Temps de travail hebdomadaire : {payload.tempsTravail}
        - Revenu individuel net mensuel : {payload.revenuIndiv} €
        - Composition du foyer : {payload.situationFoyer}
        - Revenu net du conjoint : {payload.revenuConjoint} €
        - Personnes / Enfants à charge fiscale : {payload.enfantsACharge}
        - Type de zone de vie : {payload.localisation}
        - Ville ou Département renseigné : {payload.ville}
        - Statut d'occupation du logement : {payload.statutLogement}
        - Mode de chauffage principal : {payload.modeChauffage}
        - Dépense d'énergie mensuelle actuelle : {payload.factureEnergie} €
        - Diagnostic d'isolation : {payload.isolation}
        - Moyen de transport principal : {payload.modeTransport}
        - Distance estimée : {payload.kmSemaine} km parcourus par semaine
        - Budget alimentation mensuel estimé : {payload.budgetAlimentation} €
        """

        prompt_systeme = """
        Tu es l'expert en économie, fiscalité et analyse budgétaire du programme l'Avenir en Commun.
        Ton rôle est de calculer précisément l'impact financier des mesures du programme sur la situation de l'utilisateur.

        CONSIGNES DE SÉCURITÉ ET DE RENDU :
        - Ne mets AUCUN émoji dans tes réponses. Garde un ton sobre, factuel et professionnel.
        - Rédige tes blocs thématiques au format Markdown standard (paragraphes courts ou listes à puces claires).

        Tu dois obligatoirement renvoyer un format JSON valide contenant exactement ces structures de clés :
        {
          "headline": "Titre global synthétique et percutant résumant le gain mensuel total estimé (ex: +240€/mois pour votre foyer)",
          "bloc_travail": "Analyse sur le salaire (SMIC revalorisé, semaine de 32h) et la fiscalité (impact du passage à l'impôt progressif à 14 tranches selon ses revenus).",
          "bloc_logement": "Analyse sur le logement et l'énergie (blocage des prix de l'électricité/gaz, gratuité des premiers kWh, encadrement des loyers).",
          "bloc_transports": "Analyse sur l'impact du carburant bloqué à 1,50€/L calculé selon ses kilomètres réels ou les alternatives de transports collectifs gratuits/développés.",
          "bloc_famille": "Analyse dédiée à l'impact sur les enfants et l'école s'il y en a (cantine gratuite et bio, fournitures scolaires gratuites, allocation d'autonomie)."
        }
        Rédige en français de manière claire, concise et directement exploitable.
        """

        # Appel de l'API Gemini avec contrainte de format JSON strict
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"{fiche_situation}\n\nGénère la réponse attendue au format JSON structure.",
            config=types.GenerateContentConfig(
                system_instruction=prompt_systeme,
                response_mime_type="application/json"
            )
        )

        # Extraction et conversion de la string JSON en dictionnaire Python pour FastAPI
        return json.loads(response.text)

    except Exception as e:
        print(f"Erreur d'analyse : {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erreur interne lors de la simulation : {str(e)}")
