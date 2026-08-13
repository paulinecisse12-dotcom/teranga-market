"""
============================================================================
 5.1 API — Microservice FastAPI (recommandations + prix dynamique)
============================================================================
Charge les artefacts pre-calcules (voir export_modeles.py) et expose :
  GET /                              -> etat de l'API
  GET /prix/{id_produit}            -> prix actuel + prix optimal + elasticite
  GET /recommander/{id_client}      -> top-K produits recommandes (hybride)
  GET /produit/{id_produit}/similaires -> produits similaires ("vous aimerez aussi")

Lancer (depuis 04_PRODUCTION/api) :
    uvicorn main:app --reload
Puis ouvrir la doc interactive :  http://127.0.0.1:8000/docs
============================================================================
"""
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from fastapi import FastAPI, HTTPException, Query

# --- Chargement des artefacts (une seule fois, au demarrage) -----------------
ICI = Path(__file__).resolve().parent
ART = ICI / "artefacts"

pricing = pd.read_csv(ART / "pricing.csv").set_index("id_produit")
_reco = np.load(ART / "reco.npz", allow_pickle=True)
sim_cf, sim_content = _reco["sim_cf"], _reco["sim_content"]
ids = _reco["ids"]
pos = {int(p): i for i, p in enumerate(ids)}
_meta = joblib.load(ART / "reco_meta.joblib")
historique = {int(c): v for c, v in _meta["historique"].items()}
top_pop = [int(p) for p in _meta["top_pop"]]
NOM = {int(k): v for k, v in _meta["nom"].items()}
CAT = {int(k): v for k, v in _meta["categorie"].items()}

app = FastAPI(
    title="Teranga Market API",
    description="Recommandations produits + prix dynamique (projet M2 Data & E-Business).",
    version="1.0",
)

# --- Fonctions de scoring reco (identiques au notebook 4.3) ------------------
def _norm(x):
    f = np.isfinite(x)
    if f.sum() == 0:
        return x
    mn, mx = x[f].min(), x[f].max()
    if mx == mn:
        return np.where(f, 0.0, -np.inf)
    o = (x - mn) / (mx - mn)
    o[~f] = -np.inf
    return o

def _scores(hist, sim):
    idx = [pos[p] for p in hist if p in pos]
    if not idx:
        return np.zeros(len(ids))
    s = sim[idx].sum(axis=0)
    s[idx] = -np.inf          # on exclut les produits deja achetes
    return s

def _produit(p):
    return {"id_produit": int(p), "nom": NOM.get(int(p)), "categorie": CAT.get(int(p))}

# ============================================================================
#  ENDPOINTS
# ============================================================================
@app.get("/")
def accueil():
    return {
        "service": "Teranga Market API",
        "statut": "ok",
        "produits": len(ids),
        "clients_connus": len(historique),
        "endpoints": ["/prix/{id_produit}", "/recommander/{id_client}",
                      "/client/{id_client}/historique",
                      "/produit/{id_produit}/similaires", "/docs"],
    }

@app.get("/prix/{id_produit}")
def prix(id_produit: int):
    """Prix actuel et prix optimal (maximisation de la marge)."""
    if id_produit not in pricing.index:
        raise HTTPException(404, f"Produit {id_produit} introuvable")
    r = pricing.loc[id_produit]
    return {
        "id_produit": id_produit,
        "nom": r["nom"],
        "categorie": r["categorie"],
        "prix_actuel": int(r["prix_actuel"]),
        "prix_optimal": int(r["prix_optimal"]),
        "elasticite": float(r["elasticite"]),
        "variation_pct": round((r["prix_optimal"] / r["prix_actuel"] - 1) * 100, 1),
    }

@app.get("/recommander/{id_client}")
def recommander(id_client: int, k: int = Query(5, ge=1, le=20)):
    """Top-K produits recommandes pour un client (reco hybride)."""
    hist = historique.get(id_client, [])
    if not hist:
        # client inconnu (cold start) -> on renvoie les best-sellers
        recs = top_pop[:k]
        source = "populaire (client inconnu)"
    else:
        sc = 0.5 * _norm(_scores(hist, sim_cf)) + 0.5 * _norm(_scores(hist, sim_content))
        recs = [int(ids[i]) for i in np.argsort(-sc)[:k]]
        source = "hybride (content + collaboratif)"
    return {
        "id_client": id_client,
        "source": source,
        "nb_achats_connus": len(hist),
        "recommandations": [_produit(p) for p in recs],
    }

@app.get("/client/{id_client}/historique")
def historique_client(id_client: int):
    """Produits deja achetes par un client (ce que la reco utilise en entree)."""
    hist = historique.get(id_client)
    if hist is None:
        raise HTTPException(404, f"Client {id_client} inconnu")
    return {
        "id_client": id_client,
        "nb_achats": len(hist),
        "achats": [_produit(p) for p in hist],
    }

@app.get("/produit/{id_produit}/similaires")
def similaires(id_produit: int, k: int = Query(5, ge=1, le=20)):
    """Produits similaires par attributs (content-based) : 'vous aimerez aussi'."""
    if id_produit not in pos:
        raise HTTPException(404, f"Produit {id_produit} introuvable")
    i = pos[id_produit]
    voisins = np.argsort(-sim_content[i])
    voisins = [int(ids[j]) for j in voisins if int(ids[j]) != id_produit][:k]
    return {"id_produit": id_produit, "nom": NOM.get(id_produit),
            "similaires": [_produit(p) for p in voisins]}
