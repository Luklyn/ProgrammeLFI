import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def get_genai_client():
    keys = [v.strip() for k, v in os.environ.items()
            if (k.startswith("GOOGLE_API_KEY") or k.startswith("GEMINI_API_KEY")) and v.strip()]
    if not keys:
        print("⚠️ Aucune clé API trouvée")
        return genai.Client()
    return genai.Client(api_key=keys[0])

app = FastAPI(title="Simulateur Avenir en Commun")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class SimulateurPayload(BaseModel):
    statutPro: str = ""
    tempsTravail: str = "35"
    revenuIndiv: float = 0
    situationFoyer: str = ""
    revenuConjoint: float = 0
    enfantsACharge: int = 0
    localisation: str = ""
    ville: str = ""
    statutLogement: str = ""
    modeChauffage: str = ""
    factureEnergie: float = 0
    isolation: str = ""
    modeTransport: str = ""
    kmSemaine: float = 0
    budgetAlimentation: float = 0

@app.post("/api/analyse-budget")
async def analyser_budget(payload: SimulateurPayload):
    try:
        client = get_genai_client()

        fiche = f"""
SITUATION: {payload.statutPro}, {payload.tempsTravail}h/semaine, {payload.revenuIndiv}€/mois
FOYER: {payload.situationFoyer}, conjoint {payload.revenuConjoint}€, {payload.enfantsACharge} enfants
LOGEMENT: {payload.ville} ({payload.localisation}), {payload.statutLogement}, chauffage {payload.modeChauffage}, facture {payload.factureEnergie}€, isolation {payload.isolation}
TRANSPORT: {payload.modeTransport}, {payload.kmSemaine} km/sem
ALIMENTATION: {payload.budgetAlimentation}€/mois
"""

        system = """
Tu es l'expert du programme l'Avenir en Commun 2027. Calcule l'impact réel.
Applique : SMIC 1600€ net, semaine 32h, carburant 1,50€/L, TVA 0% produits première nécessité, loyers -10%, cantine gratuite, allocation autonomie 1063€.

Réponds UNIQUEMENT en JSON valide :
{
  "headline": "titre avec gain",
  "bloc_travail": "texte clair sans markdown",
  "bloc_logement": "texte clair",
  "bloc_transports": "texte clair",
  "bloc_famille": "texte clair"
}
"""

        resp = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=fiche,
            config=types.GenerateContentConfig(
                system_instruction=system,
                response_mime_type="application/json"
            )
        )
        return json.loads(resp.text)
    except Exception as e:
        raise HTTPException(500, str(e))

@app.get("/")
def root(): return {"ok": True}
