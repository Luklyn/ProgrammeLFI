import os
import json
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI(title="Simulateur Avenir en Commun 2027")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Configuration des Clés API (Idéal pour Render) ---
API_KEYS = [v.strip() for k, v in os.environ.items() 
            if k.startswith("GOOGLE_API_KEY") or k.startswith("GEMINI_API_KEY")]

# --- Chargement sécurisé du programme local ---
try:
    with open("mesures.json", "r", encoding="utf-8") as f:
        PROGRAMME_DATA = json.load(f)
    PROGRAMME_CONTEXTE = json.dumps(PROGRAMME_DATA, ensure_ascii=False, indent=2)
except Exception as e:
    print(f"Erreur chargement mesures.json: {e}")
    PROGRAMME_DATA = {}
    PROGRAMME_CONTEXTE = "{}"

# --- Modèle de données (Payload du formulaire HTML) ---
class Payload(BaseModel):
    statutPro: str = ""
    tempsTravail: str = "35"
    revenuIndiv: float = 0
    situationFoyer: str = "celibataire"
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

# --- Fonction d'interrogation avec votre logique de fallback ---
def interroger_gemini(prompt: str) -> dict:
    if not API_KEYS:
        raise HTTPException(status_code=500, detail="Aucune clé API configurée dans les variables d'environnement.")
        
    for key in random.sample(API_KEYS, len(API_KEYS)):
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            resp = model.generate_content(prompt)
            
            # Nettoyage des balises de code Markdown pour isoler le JSON pur
            text = resp.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            return json.loads(text)
        except Exception as e:
            print(f"Clé {key[:8]}... échec: {e}")
            continue
    raise HTTPException(status_code=500, detail="Toutes les clés IA ont échoué")

@app.post("/api/analyse-budget")
async def analyse_budget(payload: Payload):
    fiche_situation = f"""
FICHE DE SITUATION DE L'UTILISATEUR :
- Profil professionnel : {payload.statutPro}
- Temps de travail hebdomadaire : {payload.tempsTravail}h
- Revenu individuel net mensuel : {payload.revenuIndiv} €
- Situation du foyer : {payload.situationFoyer}
- Revenu du/de la conjoint(e) : {payload.revenuConjoint} €
- Nombre d'enfants à charge : {payload.enfantsACharge}
- Type de zone géographique : {payload.localisation}
- Ville/Département de résidence : {payload.ville}
- Statut du logement : {payload.statutLogement}
- Mode de chauffage : {payload.modeChauffage}
- Facture d'énergie mensuelle actuelle : {payload.factureEnergie} €
- Performance de l'isolation : {payload.isolation}
- Moyen de transport principal : {payload.modeTransport}
- Distance parcourue : {payload.kmSemaine} km par semaine
- Budget alimentation mensuel actuel : {payload.budgetAlimentation} €
"""

    prompt_systeme = """
Tu es l'expert en économie et en analyse budgétaire du programme l'Avenir en Commun pour l'élection présidentielle de 2027.
Ton rôle est de calculer de manière réaliste et personnalisée l'impact des mesures du programme sur le "reste à vivre" mensuel de l'utilisateur.

Tu as deux sources d'informations obligatoires :
1. Le fichier JSON du programme fourni dans le prompt. Tu dois appliquer ses réformes phares (ex: SMIC à 1600€ net, semaine de 32h, blocage des prix de l'énergie et des carburants à 1,50€/L, suppression de la TVA sur les produits de première nécessité, gratuité ou gel des transports, encadrement des loyers...).
2. Une simulation des réalités économiques actuelles pour calculer précisément l'écart (ex: prix moyen actuel du carburant en France ~1,85€, tarifs réglementés actuels de l'électricité ~0,25€/kWh).

CONSIGNES DE RÉDACTION :
- Ne mets AUCUN émoji dans tes réponses. Garde un ton sobre, factuel et professionnel.
- Rédige tes blocs thématiques au format Markdown standard (paragraphes courts ou listes à puces claires).
- Tu dois OBLIGATOIREMENT répondre sous la forme d'un objet JSON unique contenant exactement ces clés :

{
  "headline": "Un titre global synthétique résumant le gain mensuel total estimé (ex: +240€/mois pour votre foyer)",
  "bloc_travail": "Analyse sur le salaire (SMIC, semaine de 32h) et la fiscalité (impôt progressif à 14 tranches selon ses revenus).",
  "bloc_logement": "Analyse sur le logement et l'énergie (blocage des prix du gaz/électricité, gratuité des premiers kWh, encadrement des loyers).",
  "bloc_transports": "Analyse sur le carburant bloqué à 1,50€/L selon ses kilomètres réels ou les alternatives de transports collectifs.",
  "bloc_famille": "Analyse dédiée à l'impact sur les enfants et l'école (cantine gratuite, fournitures gratuites, allocation d'autonomie)."
}
"""

    prompt_final = f"{fiche_situation}\n{prompt_systeme}\n\nDONNÉES OFFICIELLES DU PROGRAMME (CONTEXTE JSON) :\n{PROGRAMME_CONTEXTE}\n\nCalcule les impacts et génère la réponse attendue au format JSON strict."

    # Interrogation et répartition des données lues
    resultat = interroger_gemini(prompt_final)
    
    return {
        "headline": resultat.get("headline", "Analyse de votre pouvoir d'achat"),
        "bloc_travail": resultat.get("bloc_travail", "Non applicable à votre situation."),
        "bloc_logement": resultat.get("bloc_logement", "Non applicable à votre situation."),
        "bloc_transports": resultat.get("bloc_transports", "Non applicable à votre situation."),
        "bloc_famille": resultat.get("bloc_famille", "Non applicable à votre situation.")
    }

@app.get("/")
def root():
    return {"status": "ok", "mesures_loaded": bool(PROGRAMME_DATA), "keys_detected": len(API_KEYS)}
