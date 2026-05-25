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
    for name, value in os.environ.items():
        if name.startswith("GOOGLE_API_KEY") or name.startswith("GEMINI_API_KEY"):
            if value and value.strip() and value not in keys:
                keys.append(value.strip())
    
    if not keys:
        raise ValueError("❌ Aucune clé API trouvée. Ajoutez GOOGLE_API_KEY_1 ou GEMINI_API_KEY_1.")
    
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

# === SCHÉMA DE DONNÉES PREDICATIF (Parfaitement aligné sur le Payload HTML/JS) ===
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

# === APPEL SÉCURISÉ À L'IA GEMINI (Rotation de clés et format JSON forcé) ===
def appeler_gemini_ia(prompt_text: str) -> Dict[str, Any]:
    for attempt in range(len(API_KEYS)):
        try:
            genai.configure(api_key=API_KEYS[attempt])
            
            # Utilisation de gemini-1.5-flash pour un excellent ratio vitesse/pertinence
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Forçage du type de réponse en JSON structuré officiel
            response = model.generate_content(
                prompt_text,
                generation_config={"response_mime_type": "application/json"}
            )
            
            # Parsing et validation du JSON retourné par l'IA
            return json.loads(response.text)
            
        except Exception as e:
            print(f"⚠️ Échec avec la clé {attempt + 1}/{len(API_KEYS)}: {str(e)}")
            continue
            
    raise HTTPException(status_code=500, detail="Toutes les clés de l'API Gemini ont échoué.")

# === ENDPOINT PRINCIPAL D'ANALYSE BUDGETAIRE ===
@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    
    # Construction du prompt contextualisé basé sur le programme "L'Avenir en Commun"
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

    Tu dois obligatoirement générer et renvoyer un objet JSON valide contenant exactement ces 5 clés (sans dévier de ces structures de clés pour être compris par l'application front-end) :
    {{
        "headline": "Une seule phrase d'accroche marquante résumant le gain financier global estimé (ex: '+240 € / mois de pouvoir d'achat retrouvé')",
        "bloc_travail": "Texte explicatif court en Markdown sur l'augmentation du SMIC à 1600€ net, la baisse fiscale des classes populaires et moyennes via la réforme de l'impôt à 14 tranches, ou l'impact des 32h.",
        "bloc_logement": "Texte explicatif court en Markdown sur le blocage des prix de l'énergie, la gratuité des premiers kWh essentiels, et l'encadrement des loyers.",
        "bloc_transports": "Texte explicatif court en Markdown sur le blocage des carburants à 1,50 € le litre, ou la gratuité/baisse drastique ciblée des transports en commun.",
        "bloc_famille": "Texte explicatif court en Markdown sur la gratuité intégrale de l'école républicaine (cantines gratuites, fournitures), ou les minima sociaux/retraites selon le profil."
    }}

    Consignes de rédaction :
    - Reste rigoureux, factuel, et ultra-pédagogique. Évite les slogans vides, appuie-toi sur les données fournies.
    - Utilise des listes à puces Markdown (`*`) et du texte en gras (`**mot**`) à l'intérieur de tes chaînes de blocs pour un affichage élégant.
    - Ne fais aucune référence à la structure interne du code HTML ou JSON dans ton texte.
    """

    try:
        resultat_ia = appeler_gemini_ia(prompt)
        return resultat_ia
    except json.JSONDecodeError:
        # Fallback de secours si l'IA produit un JSON mal formé malgré la configuration
        raise HTTPException(status_code=502, detail="La réponse générée par l'IA n'est pas au format JSON attendu.")
