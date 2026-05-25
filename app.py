import os
import random
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import google.generativeai as genai

app = FastAPI(title="Simulateur Mélenchon 2027")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def load_api_keys():
    keys = [
        v.strip()
        for k, v in os.environ.items()
        if k.startswith("GOOGLE_API_KEY") or k.startswith("GEMINI_API_KEY")
        if v and v.strip()
    ]
    keys = list(dict.fromkeys(keys))
    if not keys:
        raise ValueError("Aucune clé API trouvée. Ajoute GOOGLE_API_KEY_1 sur Render")
    print(f"{len(keys)} clés API chargées")
    return keys

API_KEYS = load_api_keys()

class BudgetRequest(BaseModel):
    revenus: float
    loyer: float
    charges: float
    situation: str = "célibataire"
    enfants: int = 0
    data: Dict[str, Any] = {}

def analyse_avec_gemini(prompt: str) -> str:
    for _ in range(len(API_KEYS)):
        api_key = random.choice(API_KEYS)
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Clé échouée: {e}")
            continue
    raise HTTPException(status_code=500, detail="Toutes les clés API ont échoué")

@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    reste_actuel = req.revenus - req.loyer - req.charges
    
    prompt = f"""
Tu es l'assistant du simulateur "L'Avenir en Commun" Mélenchon 2027.
Analyse ce budget et explique ce que le programme change.

Données:
- Revenus: {req.revenus}€
- Loyer: {req.loyer}€
- Charges: {req.charges}€
- Situation: {req.situation}
- Enfants: {req.enfants}

Réponds en 3 parties:
1. Situation actuelle (reste à vivre)
2. Gains avec le programme (SMIC 1600€ net, blocage loyers, etc.)
3. 3 mesures concrètes

Ton: pédagogique, factuel.
"""
    resultat = analyse_avec_gemini(prompt)
    
    return {
        "success": True,
        "reste_a_vivre_actuel": round(reste_actuel, 2),
        "analyse": resultat,
        "cles_utilisees": len(API_KEYS)
    }

@app.get("/")
async def root():
    return {"status": "ok", "keys_loaded": len(API_KEYS)}

@app.get("/health")
async def health():
    return {"status": "healthy"}
