"""
============================================================================
 5.2 MLOps — Suivi MLflow des modeles PRICING et RECOMMANDATION
============================================================================
Complete le suivi MLflow (apres le forecasting) : on enregistre aussi le
modele de prix et le modele de reco, chacun dans sa propre "experience".

  - Experience "teranga-pricing"        : 1 run (elasticite -> marge)
  - Experience "teranga-recommandation" : 5 runs (hasard/populaire/content/
                                          collaboratif/hybride) pour comparer.

Lancer :
    python 04_PRODUCTION/mlops/02_mlflow_pricing_reco.py
    puis (depuis 04_PRODUCTION/mlops) :  mlflow ui --backend-store-uri sqlite:///mlflow.db
============================================================================
"""
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import duckdb
import mlflow
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import MinMaxScaler
warnings.simplefilter("ignore")

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
DB = RACINE / "02_DONNEES" / "warehouse" / "teranga.duckdb"
mlflow.set_tracking_uri(f"sqlite:///{(ICI / 'mlflow.db').as_posix()}")
K = 5

# ============================================================================
#  1) PRICING
# ============================================================================
def suivi_pricing():
    con = duckdb.connect(str(DB), read_only=True)
    src = con.execute("""
        SELECT p.categorie, (t.id_promo!=0) a_promo, SUM(t.quantite) qte,
               COUNT(DISTINCT CAST(t.date_vente AS DATE)) njours,
               SUM(t.quantite*t.prix_unitaire)*1.0/SUM(t.quantite) prix,
               SUM(t.quantite*p.cout_unitaire)*1.0/SUM(t.quantite) cout
        FROM transactions t JOIN produits p ON t.id_produit=p.id_produit
        GROUP BY 1,2
    """).fetchdf()
    con.close()
    elas, var, gain = [], [], []
    for cat, sub in src.groupby("categorie"):
        n = sub[~sub["a_promo"]].iloc[0]; pr = sub[sub["a_promo"]].iloc[0]
        Q0, Q1 = n["qte"]/n["njours"], pr["qte"]/pr["njours"]
        E = np.log(Q1/Q0)/np.log(pr["prix"]/n["prix"])
        c, P0 = n["cout"], n["prix"]
        Pstar = c*E/(E+1)
        M0 = (P0-c); Mstar = (Pstar-c)*(Pstar/P0)**E
        elas.append(E); var.append(Pstar/P0-1); gain.append(Mstar/M0-1)

    mlflow.set_experiment("teranga-pricing")
    with mlflow.start_run(run_name="elasticite_marge"):
        mlflow.log_param("methode", "elasticite log-log (via promotions)")
        mlflow.log_param("objectif", "maximisation de la marge")
        mlflow.log_param("formule_prix", "cout * E/(E+1)")
        mlflow.log_metric("elasticite_moyenne", round(float(np.mean(elas)), 3))
        mlflow.log_metric("variation_prix_moy_pct", round(float(np.mean(var))*100, 1))
        mlflow.log_metric("gain_marge_moy_pct", round(float(np.mean(gain))*100, 2))
    print(f"  [pricing] E={np.mean(elas):.2f}  prix +{np.mean(var)*100:.0f}%  "
          f"marge +{np.mean(gain)*100:.1f}%  -> logge")

# ============================================================================
#  2) RECOMMANDATION
# ============================================================================
def suivi_reco():
    con = duckdb.connect(str(DB), read_only=True)
    achats = con.execute("SELECT id_client,id_produit,CAST(date_vente AS DATE) date FROM transactions").fetchdf()
    produits = con.execute("SELECT id_produit,categorie,marque,prix_catalogue FROM produits ORDER BY id_produit").fetchdf()
    con.close()
    achats["date"] = pd.to_datetime(achats["date"]); achats = achats.sort_values(["id_client","date"])
    dernier = achats.groupby("id_client").tail(1); train = achats.drop(dernier.index)
    clients_eval = sorted(set(train.id_client) & set(dernier.id_client))
    test = dernier.set_index("id_client")["id_produit"].to_dict()

    ids = produits["id_produit"].values; pos = {p:i for i,p in enumerate(ids)}
    # content
    fc = pd.get_dummies(produits["categorie"]); fm = pd.get_dummies(produits["marque"])
    fp = pd.DataFrame(MinMaxScaler().fit_transform(produits[["prix_catalogue"]]), columns=["p"])
    sim_content = cosine_similarity(pd.concat([fc,fm,fp],axis=1).values)
    # collaboratif
    clients = sorted(train.id_client.unique()); cp = {c:i for i,c in enumerate(clients)}
    M = np.zeros((len(clients), len(ids)))
    for c,p in zip(train.id_client, train.id_produit): M[cp[c],pos[p]] = 1.0
    sim_cf = cosine_similarity(M.T)
    pop = train["id_produit"].value_counts(); top_pop = pop.index.tolist()
    hist = {c: train[train.id_client==c]["id_produit"].tolist() for c in clients_eval}

    def norm(x):
        f = np.isfinite(x)
        if f.sum()==0: return x
        mn,mx = x[f].min(), x[f].max()
        if mx==mn: return np.where(f,0.0,-np.inf)
        o = (x-mn)/(mx-mn); o[~f]=-np.inf; return o
    def scores(h, sim):
        idx=[pos[p] for p in h if p in pos]
        if not idx: return np.zeros(len(ids))
        s=sim[idx].sum(0); s[idx]=-np.inf; return s
    def reco_pop(h): s=set(h); return [p for p in top_pop if p not in s][:K]
    def reco_hyb(h, alpha):
        sc = alpha*norm(scores(h,sim_cf)) + (1-alpha)*norm(scores(h,sim_content))
        return [ids[i] for i in np.argsort(-sc)[:K]]
    def evaluer(fn):
        hits=sum(1 for c in clients_eval if test[c] in fn(hist[c]))
        r=hits/len(clients_eval); return round(r*100,1), round(r/K*100,1)

    modeles = {
        "hasard":       (lambda h: list(ids[:K]), K/len(ids)*100, 1/len(ids)*100),  # ref analytique
        "populaire":    (lambda h: reco_pop(h), None, None),
        "content":      (lambda h: reco_hyb(h, 0.0), None, None),
        "collaboratif": (lambda h: reco_hyb(h, 1.0), None, None),
        "hybride":      (lambda h: reco_hyb(h, 0.5), None, None),
    }
    mlflow.set_experiment("teranga-recommandation")
    for nom, (fn, rec_fix, prec_fix) in modeles.items():
        rec, prec = (round(rec_fix,1), round(prec_fix,1)) if rec_fix is not None else evaluer(fn)
        with mlflow.start_run(run_name=nom):
            mlflow.log_param("approche", nom)
            mlflow.log_param("K", K)
            mlflow.log_param("catalogue_produits", len(ids))
            mlflow.log_metric("Recall_at_5_pct", rec)
            mlflow.log_metric("Precision_at_5_pct", prec)
        print(f"  [reco:{nom:12s}] Recall@5={rec:4.1f}%  -> logge")

def main():
    print("Suivi MLflow — pricing & recommandation :\n")
    suivi_pricing()
    suivi_reco()
    print("\nTermine ! 3 experiences dans MLflow : teranga-forecasting / -pricing / -recommandation")
    print("  cd 04_PRODUCTION/mlops && mlflow ui --backend-store-uri sqlite:///mlflow.db")

if __name__ == "__main__":
    main()
