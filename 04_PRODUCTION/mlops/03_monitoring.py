"""
============================================================================
 5.2 MLOps — Monitoring des modeles (detection de derive / "data drift")
============================================================================
Un modele entraine sur des donnees passees se degrade si les donnees
CHANGENT dans le temps (nouveaux comportements, inflation, tendance...).
Le monitoring compare une periode de REFERENCE (donnees d'entrainement) aux
donnees RECENTES et alerte si la distribution a trop bouge.

Indicateur standard : le PSI (Population Stability Index)
    PSI < 0.10  -> stable (OK)
    0.10-0.25   -> derive moderee (a surveiller)
    PSI > 0.25  -> derive importante (re-entrainer le modele !)

Ici : reference = 9 premiers mois, recent = 3 derniers mois.
Sortie : un rapport console + un CSV dans "monitoring_rapport.csv".
============================================================================
"""
from pathlib import Path
import numpy as np
import pandas as pd
import duckdb

ICI = Path(__file__).resolve().parent
RACINE = ICI.parents[1]
DB = RACINE / "02_DONNEES" / "warehouse" / "teranga.duckdb"

# --- PSI (Population Stability Index) ----------------------------------------
def psi(reference, recent, n_bins=10):
    """Mesure de combien la distribution 'recent' s'ecarte de 'reference'."""
    # bornes de bins definies sur la reference (quantiles)
    bornes = np.quantile(reference, np.linspace(0, 1, n_bins + 1))
    bornes[0], bornes[-1] = -np.inf, np.inf
    ref_pct = np.histogram(reference, bins=bornes)[0] / len(reference)
    rec_pct = np.histogram(recent, bins=bornes)[0] / len(recent)
    # on evite les zeros (log)
    ref_pct = np.clip(ref_pct, 1e-4, None)
    rec_pct = np.clip(rec_pct, 1e-4, None)
    return float(np.sum((rec_pct - ref_pct) * np.log(rec_pct / ref_pct)))

def verdict(p):
    if p < 0.10:  return "OK (stable)"
    if p < 0.25:  return "DERIVE MODEREE (surveiller)"
    return "DERIVE IMPORTANTE (re-entrainer !)"

def main():
    con = duckdb.connect(str(DB), read_only=True)
    tx = con.execute("""
        SELECT CAST(t.date_vente AS DATE) date, t.quantite, t.prix_unitaire,
               p.categorie
        FROM transactions t JOIN produits p ON t.id_produit=p.id_produit
    """).fetchdf()
    con.close()
    tx["date"] = pd.to_datetime(tx["date"])

    # --- Coupure reference / recent -----------------------------------------
    coupure = tx["date"].max() - pd.DateOffset(months=3)
    ref = tx[tx["date"] <  coupure]
    rec = tx[tx["date"] >= coupure]
    print(f"Reference : {ref['date'].min().date()} -> {coupure.date()}  ({len(ref):,} ventes)")
    print(f"Recent    : {coupure.date()} -> {tx['date'].max().date()}  ({len(rec):,} ventes)\n")

    # --- Demande quotidienne (agregee) --------------------------------------
    ref_dem = ref.groupby("date")["quantite"].sum().values
    rec_dem = rec.groupby("date")["quantite"].sum().values

    rapport = []
    # 1) derive de la DEMANDE quotidienne (PSI)
    rapport.append(("demande_quotidienne", "PSI",
                    round(psi(ref_dem, rec_dem), 3),
                    f"{ref_dem.mean():.0f} -> {rec_dem.mean():.0f} u/j"))
    # 2) derive du PRIX moyen paye (PSI)
    rapport.append(("prix_unitaire", "PSI",
                    round(psi(ref["prix_unitaire"].values, rec["prix_unitaire"].values), 3),
                    f"{ref['prix_unitaire'].mean():.0f} -> {rec['prix_unitaire'].mean():.0f} FCFA"))
    # 3) derive du MIX CATEGORIES (part de marche)
    ref_mix = ref["categorie"].value_counts(normalize=True).sort_index()
    rec_mix = rec["categorie"].value_counts(normalize=True).sort_index().reindex(ref_mix.index, fill_value=0)
    psi_mix = float(np.sum((rec_mix - ref_mix) * np.log(np.clip(rec_mix,1e-4,None)/np.clip(ref_mix,1e-4,None))))
    rapport.append(("mix_categories", "PSI", round(psi_mix, 3), "repartition des ventes"))

    df = pd.DataFrame(rapport, columns=["indicateur", "metrique", "PSI", "detail"])
    df["verdict"] = df["PSI"].apply(verdict)

    pd.set_option("display.width", 200)
    print("=== RAPPORT DE MONITORING (derive reference -> recent) ===")
    print(df.to_string(index=False))
    df.to_csv(ICI / "monitoring_rapport.csv", index=False)
    print(f"\nRapport ecrit : {ICI / 'monitoring_rapport.csv'}")

    # --- Conclusion automatique ---------------------------------------------
    if (df["PSI"] > 0.25).any():
        print("\n[ALERTE] Derive importante detectee -> il faut RE-ENTRAINER les modeles.")
    elif (df["PSI"] > 0.10).any():
        print("\n[INFO] Derive moderee -> a surveiller au prochain cycle.")
    else:
        print("\n[OK] Donnees stables -> modeles encore valides.")

if __name__ == "__main__":
    main()
