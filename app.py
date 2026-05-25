import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import google.generativeai as genai

# === CLÉS API ===
API_KEYS = [v.strip() for k, v in os.environ.items()
            if (k.startswith("GOOGLE_API_KEY") or k.startswith("GEMINI_API_KEY")) and v.strip()]

print(f"✅ {len(API_KEYS)} clé(s) API détectée(s)")

# === FASTAPI ===
app = FastAPI(title="Simulateur Avenir en Commun 2027")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SCHÉMA ===
class BudgetRequest(BaseModel):
    sexe: str = ""
    trancheAge: str = ""
    statutPro: str = ""
    tempsTravail: str = "35"
    revenuIndiv: float = 0
    situationFoyer: str = ""
    revenuConjoint: float = 0
    enfantsACharge: int = 0
    localisation: str = ""
    ville: str = ""
    statutLogement: str = ""
    montantLoyer: float = 0
    modeChauffage: str = ""
    factureEnergie: float = 0
    isolation: str = ""
    modeTransport: str = ""
    kmSemaine: float = 0
    essenceHebdo: float = 0
    abonnementTransport: float = 0
    budgetAlimentation: float = 0

# === GEMINI ===
def interroger_gemini(prompt: str):
    if not API_KEYS:
        raise HTTPException(500, "Aucune clé API configurée sur Render")
    
    last_error = None
    for i, key in enumerate(API_KEYS):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            
            # Nettoie le markdown si Gemini en met
            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            return json.loads(text.strip())
            
        except Exception as e:
            last_error = str(e)
            print(f"⚠️ Clé {i+1} échouée: {last_error}")
            continue
    
    raise HTTPException(500, f"Toutes les clés ont échoué. Dernière erreur: {last_error}")

# === ROUTES ===
@app.get("/")
def root():
    return {"status": "ok", "keys_loaded": len(API_KEYS)}

@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    prompt = f"""
Tu es l'assistant de calcul officiel du simulateur de programme "L'Avenir en Commun" pour Jean-Luc Mélenchon 2027.
Analyse la situation de ce citoyen et explique avec précision et pédagogie comment les mesures phares du programme vont impacter son reste à vivre et sa vie quotidienne.

Tu dois utiliser mesures.json et Google Search pour faire une réponse personalisée et vérifier les informations

Profil de l'utilisateur :
- Sexe : {req.sexe}
- Âge : Tranche {req.trancheAge}
- Professionnel : {req.statutPro} ({req.tempsTravail}h/semaine) - Revenu : {req.revenuIndiv} €/mois.
- Foyer : {req.situationFoyer} - Revenu Conjoint : {req.revenuConjoint} €/mois - {req.enfantsACharge} enfant(s) à charge.
- Géographie : Zone {req.localisation} ({req.ville}).
- Logement : {req.statutLogement} (Frais : {req.montantLoyer} €/mois), Chauffage {req.modeChauffage}, Facture énergie : {req.factureEnergie} €/mois, Isolation : {req.isolation}.
- Déplacements : Transports via {req.modeTransport} ({req.kmSemaine} km/sem), Carburant : {req.essenceHebdo} €/sem, Abonnements : {req.abonnementTransport} €/mois.
- Alimentation : Budget moyen de {req.budgetAlimentation} €/mois.

Tu dois obligatoirement générer et renvoyer un objet JSON valide contenant exactement ces 5 clés :
{{
    "headline": "Une seule phrase d'accroche marquante résumant les mesures phares qui profiteront à l'utilisateur",
    "bloc_travail": "Texte explicatif court contextualisé sur la situation de l'utilisateur, en Markdown, sur l'augmentation du SMIC, baisse fiscale et les 32h.",
    "bloc_logement": "Texte explicatif court en Markdown les mesures du programme LFI applicables au profil de l'utilisateur en matière de logement",
    "bloc_transports": "Texte explicatif court en Markdown les mesures du programme LFI applicables au profil de l'utilisateur en matière de transport et mesures écologiques",
    "bloc_famille": "Texte explicatif court en Markdown les mesures du programme LFI applicables au profil de l'utilisateur sur les questions de la famille, des enfants, de l'école etc"
}}

Consignes de rédaction :
- Reste rigoureux, factuel, et ultra-pédagogique.
- Utilise des listes à puces Markdown (*) et du texte en gras (**mot**).
- Ne fais aucune référence à la structure interne du code HTML ou JSON.
- Réponds UNIQUEMENT avec le JSON, sans texte avant ou après.
"""
    
    return interroger_gemini(prompt)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
