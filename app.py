import os
import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import google.generativeai as genai

# === CHARGEMENT DES CLÉS API ===
def load_api_keys():
    keys = []
    # Vérification des variables d'environnement
    for name, value in os.environ.items():
        if name.startswith("GOOGLE_API_KEY") or name.startswith("GEMINI_API_KEY"):
            if value and value.strip() and value not in keys:
                keys.append(value.strip())
    
    if not keys:
        # Fallback pour le développement local si aucune variable d'env
        print("⚠️ Aucune clé API trouvée dans l'environnement.")
        return []
    
    print(f"✅ {len(keys)} clé(s) API chargée(s)")
    return keys

API_KEYS = load_api_keys()

# === CONFIGURATION FASTAPI ===
app = FastAPI(title="Backend Simulateur Populaire - Mélenchon 2027")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === SCHÉMA DE DONNÉES (Aligné sur les IDs de simulateur.html) ===
class BudgetRequest(BaseModel):
    sexe: str
    trancheAge: str
    statutPro: str
    tempsTravail: str = "35"
    revenuIndiv: float
    situationFoyer: str
    revenuConjoint: float = 0.0
    enfantsACharge: int = 0
    localisation: str
    ville: str = ""
    statutLogement: str
    montantLoyer: float = 0.0
    modeChauffage: str
    factureEnergie: float = 0.0
    isolation: str
    modeTransport: str
    kmSemaine: float = 0.0
    essenceHebdo: float = 0.0
    abonnementTransport: float = 0.0
    budgetAlimentation: float = 0.0

# === APPEL SÉCURISÉ À L'IA GEMINI ===
def appeler_gemini_ia(prompt_text: str) -> Dict[str, Any]:
    if not API_KEYS:
        raise HTTPException(status_code=500, detail="Clés API non configurées.")
        
    for attempt in range(len(API_KEYS)):
        try:
            genai.configure(api_key=API_KEYS[attempt])
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            response = model.generate_content(
                prompt_text,
                generation_config={"response_mime_type": "application/json"}
            )
            return json.loads(response.text)
            
        except Exception as e:
            print(f"⚠️ Échec avec la clé {attempt + 1}: {str(e)}")
            continue
            
    raise HTTPException(status_code=500, detail="Toutes les clés de l'API Gemini ont échoué.")

# === ENDPOINT PRINCIPAL ===
@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    # Le prompt reste identique comme demandé
    prompt = f"""
    Tu es l'assistant de calcul officiel du simulateur de programme "L'Avenir en Commun" pour Jean-Luc Mélenchon 2027.
    Analyse la situation de ce citoyen et explique avec précision et pédagogie comment les mesures phares du programme vont impacter son reste à vivre et sa vie quotidienne.

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
        "headline": "Une seule phrase d'accroche marquante résumant le gain financier global estimé",
        "bloc_travail": "Texte explicatif court en Markdown sur l'augmentation du SMIC, baisse fiscale et les 32h.",
        "bloc_logement": "Texte explicatif court en Markdown sur le blocage des prix énergie et encadrement loyers.",
        "bloc_transports": "Texte explicatif court en Markdown sur le blocage des carburants et gratuité transports.",
        "bloc_famille": "Texte explicatif court en Markdown sur la gratuité cantines et minima sociaux."
    }}

    Consignes de rédaction :
    - Reste rigoureux, factuel, et ultra-pédagogique.
    - Utilise des listes à puces Markdown (*) et du texte en gras (**mot**).
    - Ne fais aucune référence à la structure interne du code HTML ou JSON.
    """

    return appeler_gemini_ia(prompt)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
