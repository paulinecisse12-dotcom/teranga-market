"""
============================================================================
 5.2 DASHBOARD — Export des prévisions de demande (Prophet)  [brique B]
============================================================================
On n'entraîne PAS Prophet à chaque ouverture du dashboard (trop lent).
Ce script calcule UNE fois la prévision à 30 jours par catégorie, et la
sauvegarde dans "forecast.csv" que le dashboard lira instantanément.

Lancer (depuis 04_PRODUCTION/dashboard), une seule fois :
    python export_forecast.py
============================================================================
"""
import logging
from pathlib import Path
import pandas as pd
import duckdb

# Prophet est bavard -> on coupe ses logs
logging.getLogger("prophet").setLevel(logging.CRITICAL)
logging.getLogger("cmdstanpy").setLevel(logging.CRITICAL)
from prophet import Prophet

ICI = Path(__file__).resolve().parent
DB = ICI.parents[1] / "02_DONNEES" / "warehouse" / "teranga.duckdb"
HORIZON = 30   # jours à prévoir

def series_par_categorie():
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute("""
        SELECT p.categorie, CAST(t.date_vente AS DATE) ds, SUM(t.quantite) y
        FROM transactions t JOIN produits p ON t.id_produit = p.id_produit
        GROUP BY 1, 2 ORDER BY 1, 2
    """).fetchdf()
    con.close()
    df["ds"] = pd.to_datetime(df["ds"])
    return df

def main():
    data = series_par_categorie()
    resultats = []
    for cat, sub in data.groupby("categorie"):
        print(f"  Prophet : {cat} ...")
        serie = sub[["ds", "y"]].sort_values("ds")
        m = Prophet(weekly_seasonality=True, yearly_seasonality=False, daily_seasonality=False,
                    interval_width=0.80)
        m.fit(serie)
        futur = m.make_future_dataframe(periods=HORIZON)
        prev = m.predict(futur)[["ds", "yhat", "yhat_lower", "yhat_upper"]]
        # on rattache la vraie demande observée (vide pour les jours futurs)
        prev = prev.merge(serie, on="ds", how="left")
        prev["categorie"] = cat
        prev["type"] = prev["y"].isna().map({True: "prevision", False: "historique"})
        resultats.append(prev)

    out = pd.concat(resultats, ignore_index=True)
    out[["yhat", "yhat_lower", "yhat_upper"]] = out[["yhat", "yhat_lower", "yhat_upper"]].round(1)
    out.to_csv(ICI / "forecast.csv", index=False)
    print(f"\nOK -> {ICI / 'forecast.csv'}  ({len(out):,} lignes, {out['categorie'].nunique()} catégories)")

if __name__ == "__main__":
    main()
