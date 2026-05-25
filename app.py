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
    ]
    return list(dict.fromkeys([k for k in keys if k]))

API_KEYS = load_api_keys()

class BudgetRequest(BaseModel):
    revenus: float
    loyer: float
    charges: float
    situation: str = "célibataire"
    enfants: int = 0
    data: Dict[str, Any] = {}

def analyse_avec_gemini(prompt: str) -> str:
    for api_key in API_KEYS:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel("gemini-2.5-flash-preview-04-17")
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Clé {api_key[:8]}... erreur: {e}")
            continue
    raise HTTPException(status_code=500, detail="Toutes les clés API ont échoué")

@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    reste_actuel = req.revenus - req.loyer - req.charges
    
    prompt = f"""Tu es l'assistant du simulateur "L'Avenir en Commun" Mélenchon 2027.
Analyse ce budget.

Données: Revenus {req.revenus}€, Loyer {req.loyer}€, Charges {req.charges}€, {req.situation}, {req.enfants} enfants.

Réponds en 3 parties courtes:
1. Situation actuelle
2. Gains avec le programme (SMIC 1600€ net, blocage loyers)
3. 3 mesures concrètes
"""
    resultat = analyse_avec_gemini(prompt)
    
    return {
        "success": True,
        "reste_a_vivre_actuel": round(reste_actuel, 2),
        "analyse": resultat
    }

@app.get("/")
async def root():
    return {"status": "ok", "keys_loaded": len(API_KEYS)}
