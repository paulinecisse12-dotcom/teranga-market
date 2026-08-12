"""
============================================================================
 5.1 API — Export des modeles entraines (artefacts pour l'API)
============================================================================
L'API ne doit PAS ré-entraîner a chaque requete. On calcule ici, une fois,
les artefacts dont l'API a besoin, et on les sauvegarde dans "artefacts/".

Produit :
  - pricing.csv        : par produit -> prix_actuel, cout, elasticite, prix_optimal
  - reco.npz           : matrices de similarite (collaboratif + content) + ids
  - reco_meta.joblib   : infos produits, historique d'achat par client, top populaires
============================================================================
"""
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb
import joblib
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler

ICI = Path(__file__).resolve().parent                 # .../04_PRODUCTION/api
RACINE = ICI.parents[1]
DB = RACINE / "02_DONNEES" / "warehouse" / "teranga.duckdb"
ART = ICI / "artefacts"; ART.mkdir(exist_ok=True)

def charger():
    con = duckdb.connect(str(DB), read_only=True)
    produits = con.execute("""
        SELECT id_produit, nom, categorie, marque, prix_catalogue, cout_unitaire
        FROM produits ORDER BY id_produit
    """).fetchdf()
    achats = con.execute("SELECT id_client, id_produit FROM transactions").fetchdf()
    # prix moyen paye par categorie, en promo vs hors promo (pour l'elasticite)
    elas_src = con.execute("""
        SELECT p.categorie, (t.id_promo!=0) a_promo,
               SUM(t.quantite) qte,
               COUNT(DISTINCT CAST(t.date_vente AS DATE)) njours,
               SUM(t.quantite*t.prix_unitaire)*1.0/SUM(t.quantite) prix
        FROM transactions t JOIN produits p ON t.id_produit=p.id_produit
        GROUP BY 1,2
    """).fetchdf()
    con.close()
    return produits, achats, elas_src

# --- 1) PRICING : elasticite par categorie -> prix optimal par produit -------
def exporter_pricing(produits, elas_src):
    elas = {}
    for cat, sub in elas_src.groupby("categorie"):
        n  = sub[~sub["a_promo"]].iloc[0]; pr = sub[sub["a_promo"]].iloc[0]
        Q0, Q1 = n["qte"]/n["njours"], pr["qte"]/pr["njours"]
        E = np.log(Q1/Q0) / np.log(pr["prix"]/n["prix"])
        elas[cat] = E
    df = produits.copy()
    df["elasticite"] = df["categorie"].map(elas).round(3)
    # prix optimal de marge = cout * E/(E+1)  (valide si E < -1)
    df["prix_optimal"] = (df["cout_unitaire"] * df["elasticite"] /
                          (df["elasticite"] + 1)).round(0)
    df = df.rename(columns={"prix_catalogue": "prix_actuel", "cout_unitaire": "cout"})
    df[["id_produit","nom","categorie","prix_actuel","cout","elasticite","prix_optimal"]] \
        .to_csv(ART / "pricing.csv", index=False)
    print(f"  pricing.csv : {len(df)} produits")

# --- 2) RECO : matrices de similarite collaboratif + content -----------------
def exporter_reco(produits, achats):
    ids = produits["id_produit"].values
    pos = {p:i for i,p in enumerate(ids)}

    # content : categorie + marque + prix (normalise)
    fc = pd.get_dummies(produits["categorie"]); fm = pd.get_dummies(produits["marque"])
    fp = pd.DataFrame(MinMaxScaler().fit_transform(produits[["prix_catalogue"]]), columns=["p"])
    sim_content = cosine_similarity(pd.concat([fc,fm,fp],axis=1).values).astype(np.float32)

    # collaboratif : matrice clients x produits (achats)
    clients = sorted(achats["id_client"].unique()); cp = {c:i for i,c in enumerate(clients)}
    M = np.zeros((len(clients), len(ids)), dtype=np.float32)
    for c,p in zip(achats["id_client"], achats["id_produit"]):
        M[cp[c], pos[p]] = 1.0
    sim_cf = cosine_similarity(M.T).astype(np.float32)

    np.savez_compressed(ART / "reco.npz", ids=ids, sim_cf=sim_cf, sim_content=sim_content)

    # meta : infos produits, historique par client, top populaires (fallback)
    hist = achats.groupby("id_client")["id_produit"].apply(list).to_dict()
    top_pop = achats["id_produit"].value_counts().index.tolist()
    meta = {
        "ids": ids,
        "pos": pos,
        "nom": produits.set_index("id_produit")["nom"].to_dict(),
        "categorie": produits.set_index("id_produit")["categorie"].to_dict(),
        "historique": hist,
        "top_pop": top_pop,
    }
    joblib.dump(meta, ART / "reco_meta.joblib")
    print(f"  reco.npz : matrices {sim_cf.shape} | reco_meta.joblib : {len(hist)} clients")

def main():
    produits, achats, elas_src = charger()
    print("Export des artefacts pour l'API :")
    exporter_pricing(produits, elas_src)
    exporter_reco(produits, achats)
    print(f"\nArtefacts ecrits dans : {ART}")

if __name__ == "__main__":
    main()
