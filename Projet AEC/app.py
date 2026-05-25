import os
import random
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
import google.generativeai as genai

# === CHARGEMENT DES CLÉS ===
def load_api_keys():
    keys = []
    for name, value in os.environ.items():
        if name.startswith("GOOGLE_API_KEY") or name.startswith("GEMINI_API_KEY"):
            if value and value.strip() and value not in keys:
                keys.append(value.strip())
    
    if not keys:
        raise ValueError("❌ Aucune clé API trouvée. Ajoute GOOGLE_API_KEY_1 ou GEMINI_API_KEY_1 sur Render")
    
    print(f"✅ {len(keys)} clés API chargées")
    return keys

API_KEYS = load_api_keys()

# === APP FASTAPI ===
app = FastAPI(title="Simulateur Mélenchon 2027")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tu pourras restreindre à https://melenchon2027.netlify.app plus tard
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === MODÈLE DE DONNÉES ===
class BudgetRequest(BaseModel):
    revenus: float
    loyer: float
    charges: float
    situation: str = "célibataire"
    enfants: int = 0
    data: Dict[str, Any] = {}

# === FONCTION GEMINI ===
def analyse_avec_gemini(prompt: str) -> str:
    # rotation des clés pour éviter les quotas
    for attempt in range(len(API_KEYS)):
        api_key = random.choice(API_KEYS)
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Clé échouée, tentative {attempt+1}/{len(API_KEYS)}: {e}")
            continue
    raise HTTPException(status_code=500, detail="Toutes les clés API ont échoué")

# === ENDPOINT PRINCIPAL ===
@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    try:
        prompt = f"""
Tu es l'assistant du simulateur "L'Avenir en Commun" de Jean-Luc Mélenchon 2027.
Analyse ce budget et explique concrètement ce que le programme change pour cette personne.

Données :
- Revenus mensuels : {req.revenus}€
- Loyer : {req.loyer}€
- Charges : {req.charges}€
- Situation : {req.situation}
- Enfants : {req.enfants}

Réponds en 3 parties courtes :
1. Situation actuelle (reste à vivre)
2. Gains avec le programme (SMIC à 1600€ net, blocage loyers, cantine gratuite, etc.)
3. 3 mesures concrètes qui l'impactent

Ton ton : pédagogique, factuel, sans slogan.
"""
        resultat = analyse_avec_gemini(prompt)
        
        reste_actuel = req.revenus - req.loyer - req.charges
        
        return {
            "success": True,
            "reste_a_vivre_actuel": round(reste_actuel, 2),
            "analyse": resultat,
            "cles_utilisees": len(API_KEYS)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
async def root():
    return {"status": "ok", "keys_loaded": len(API_KEYS)}

@app.get("/health")
async def health():
    return {"status": "healthy"}
