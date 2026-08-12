"""
============================================================================
 5.2 MLOps — Suivi d'experiences avec MLflow (modele de prevision)
============================================================================
But : demontrer le "MLOps leger" demande par le sujet. On ré-entraine les
3 approches de prevision (baseline / Prophet / Prophet+promo) et on
enregistre CHAQUE run dans MLflow : parametres + metriques + artefact.

Ensuite, dans l'interface MLflow (`mlflow ui`), on compare visuellement les
runs -> on VOIT que Prophet+promo est le meilleur. C'est le suivi de modeles.

Comment lancer :
    1) python 04_PRODUCTION/mlops/01_mlflow_forecasting.py     (cree les runs)
    2) depuis 04_PRODUCTION/mlops :  mlflow ui                 (ouvre l'UI)
       puis http://127.0.0.1:5000 dans le navigateur.
============================================================================
"""
from pathlib import Path
import logging, warnings
import numpy as np
import pandas as pd
import duckdb
import mlflow

from prophet import Prophet
logging.getLogger("prophet").setLevel(logging.ERROR)
logging.getLogger("cmdstanpy").setLevel(logging.ERROR)
warnings.simplefilter("ignore")

# --- Chemins -----------------------------------------------------------------
ICI = Path(__file__).resolve().parent                  # .../04_PRODUCTION/mlops
RACINE = ICI.parents[1]                                 # .../PROJET_FINAL
DB = RACINE / "02_DONNEES" / "warehouse" / "teranga.duckdb"
HORIZON_TEST = 30

# MLflow : backend SQLite (recommande depuis MLflow 3). La base "mlflow.db"
# est creee a cote de ce script ; les artefacts vont dans "mlartifacts".
DB_MLFLOW = (ICI / "mlflow.db").as_posix()
mlflow.set_tracking_uri(f"sqlite:///{DB_MLFLOW}")
mlflow.set_experiment("teranga-forecasting")

# --- Metriques ---------------------------------------------------------------
def mae(y, yhat):  return float(np.mean(np.abs(y - yhat)))
def rmse(y, yhat): return float(np.sqrt(np.mean((y - yhat) ** 2)))
def mape(y, yhat):
    m = y != 0
    return float(np.mean(np.abs((y[m]-yhat[m])/y[m]))*100) if m.any() else np.nan

# --- Donnees : demande quotidienne par categorie + calendrier promo ----------
def charger():
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute("""
        SELECT CAST(t.date_vente AS DATE) date, p.categorie, SUM(t.quantite) quantite
        FROM transactions t JOIN produits p ON t.id_produit=p.id_produit
        GROUP BY 1,2 ORDER BY 2,1
    """).fetchdf()
    promos = con.execute("""
        SELECT taux_reduction, CAST(date_debut AS DATE) d1, CAST(date_fin AS DATE) d2
        FROM promotions WHERE id_promo != 0
    """).fetchdf()
    con.close()
    df["date"] = pd.to_datetime(df["date"])
    cats = df["categorie"].unique()
    plage = pd.date_range(df["date"].min(), df["date"].max(), freq="D")
    grille = pd.MultiIndex.from_product([cats, plage], names=["categorie","date"])
    df = df.set_index(["categorie","date"]).reindex(grille, fill_value=0).reset_index()
    # calendrier promo quotidien
    taux = pd.Series(0.0, index=plage)
    for _, r in promos.iterrows():
        actif = (plage >= pd.Timestamp(r.d1)) & (plage <= pd.Timestamp(r.d2))
        taux[actif] = np.maximum(taux[actif], r.taux_reduction)
    promo_cal = pd.DataFrame({"ds": plage, "taux_promo": taux.values})
    return df, promo_cal

# --- 3 approches de prevision ------------------------------------------------
def prev_baseline(train, test):
    s = pd.concat([train, test]).set_index("ds")["y"]
    return s.shift(7).loc[test["ds"]].values

def prev_prophet(train, test, promo_cal=None):
    m = Prophet(growth="linear", weekly_seasonality=True, yearly_seasonality=False,
                daily_seasonality=False, seasonality_mode="multiplicative")
    m.add_seasonality(name="mensuelle", period=30.5, fourier_order=5)
    if promo_cal is not None:
        m.add_regressor("taux_promo")
        train = train.merge(promo_cal, on="ds", how="left")
    m.fit(train)
    fut = m.make_future_dataframe(periods=HORIZON_TEST, freq="D")
    if promo_cal is not None:
        fut = fut.merge(promo_cal, on="ds", how="left").fillna({"taux_promo": 0})
    prev = m.predict(fut).set_index("ds").loc[test["ds"], "yhat"].values
    return np.clip(prev, 0, None)

# --- Evaluation moyenne sur les 7 categories ---------------------------------
def evaluer(df, methode, promo_cal=None):
    maes, rmses, mapes = [], [], []
    for cat in sorted(df["categorie"].unique()):
        g = (df[df["categorie"]==cat].rename(columns={"date":"ds","quantite":"y"})
             [["ds","y"]].sort_values("ds").reset_index(drop=True))
        train, test = g.iloc[:-HORIZON_TEST].copy(), g.iloc[-HORIZON_TEST:].copy()
        y = test["y"].values
        if methode == "baseline":       yhat = prev_baseline(train, test)
        elif methode == "prophet":      yhat = prev_prophet(train, test)
        else:                           yhat = prev_prophet(train, test, promo_cal)
        maes.append(mae(y, yhat)); rmses.append(rmse(y, yhat)); mapes.append(mape(y, yhat))
    return np.mean(maes), np.mean(rmses), np.nanmean(mapes)

def main():
    df, promo_cal = charger()
    experiences = [
        ("baseline",       {"modele": "naive_saisonnier", "lag_jours": 7}),
        ("prophet",        {"modele": "Prophet", "saison_hebdo": True, "saison_mensuelle": True}),
        ("prophet_promo",  {"modele": "Prophet", "saison_hebdo": True, "saison_mensuelle": True,
                             "regresseur_promo": True}),
    ]
    print("Entrainement + suivi MLflow des 3 approches...\n")
    for nom, params in experiences:
        with mlflow.start_run(run_name=nom):
            promo = promo_cal if nom == "prophet_promo" else None
            m, r, p = evaluer(df, "prophet_promo" if nom=="prophet_promo" else nom, promo)
            mlflow.log_param("approche", nom)
            for k, v in params.items():
                mlflow.log_param(k, v)
            mlflow.log_param("horizon_test_jours", HORIZON_TEST)
            mlflow.log_param("granularite", "categorie (7 series)")
            mlflow.log_metric("MAE", round(m, 2))
            mlflow.log_metric("RMSE", round(r, 2))
            mlflow.log_metric("MAPE", round(p, 2))
            print(f"  [{nom:14s}] MAE={m:6.1f}  RMSE={r:6.1f}  MAPE={p:5.1f}%  -> logge dans MLflow")

    print("\nTermine ! Pour voir les resultats dans l'interface MLflow :")
    print("  cd 04_PRODUCTION/mlops")
    print("  mlflow ui --backend-store-uri sqlite:///mlflow.db")
    print("  puis ouvrir http://127.0.0.1:5000")

if __name__ == "__main__":
    main()
