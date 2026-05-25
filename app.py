import os
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

API_KEYS = [v.strip() for k,v in os.environ.items() if k.startswith("GOOGLE_API_KEY") or k.startswith("GEMINI_API_KEY")]

class BudgetRequest(BaseModel):
    revenus: float
    loyer: float
    charges: float
    situation: str = "célibataire"
    enfants: int = 0

def analyse_avec_gemini(prompt: str) -> str:
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-2.5-flash")  # ← LE BON NOM
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            print(f"Erreur clé {key[:8]}: {e}")
            continue
    raise HTTPException(500, "Toutes les clés ont échoué")

@app.post("/api/analyse-budget")
async def analyse_budget(req: BudgetRequest):
    reste = req.revenus - req.loyer - req.charges
    prompt = f"Analyse budget: {req.revenus}€ revenus, {req.loyer}€ loyer, {req.charges}€ charges, {req.situation}, {req.enfants} enfants. Donne 3 points sur le programme Mélenchon 2027."
    analyse = analyse_avec_gemini(prompt)
    return {"success": True, "reste_a_vivre_actuel": round(reste,2), "analyse": analyse}

@app.get("/")
def root():
    return {"status": "ok", "keys_loaded": len(API_KEYS)}
