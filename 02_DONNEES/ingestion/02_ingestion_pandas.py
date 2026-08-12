# -*- coding: utf-8 -*-
"""
DONNEES — 3.2 (variante) INGESTION LEGERE avec pandas + pyarrow.
Meme role que l'ingestion Spark (CSV -> Parquet), mais SANS Spark/Java.
Utilisee par l'orchestration Airflow (qui tourne dans un conteneur sans Spark).
    CSV bruts  ->  [pandas + pyarrow]  ->  Parquet (Data Lake)

Lancement :
    python 02_DONNEES/ingestion/02_ingestion_pandas.py
"""
import os
import shutil
import pandas as pd

DONNEES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUT = os.path.join(DONNEES, "brut")
LAKE = os.path.join(DONNEES, "lake")

TABLES = ["produits", "clients", "promotions", "transactions", "navigation"]

# Colonnes de date a typer (comme le fait Spark) -> sinon elles restent en texte
DATE_COLS = {
    "clients":      ["date_inscription"],
    "promotions":   ["date_debut", "date_fin"],
    "transactions": ["date_vente"],
    "navigation":   ["horodatage"],
}

print("=== Ingestion pandas -> Parquet ===")
for t in TABLES:
    df = pd.read_csv(os.path.join(BRUT, f"{t}.csv"))
    # typage des dates (VARCHAR -> datetime) pour coherence avec l'ingestion Spark
    for col in DATE_COLS.get(t, []):
        df[col] = pd.to_datetime(df[col], errors="coerce")
    # nettoyage minimal : retrait des doublons sur la 1re colonne (la cle) et des cles nulles
    cle = df.columns[0]
    n_avant = len(df)
    df = df.drop_duplicates(subset=[cle]).dropna(subset=[cle])
    # ecriture Parquet dans lake/<table>/data.parquet
    # on VIDE d'abord le dossier (comme Spark en mode overwrite) pour eviter
    # que d'anciens fichiers Parquet ne se cumulent -> doublons.
    dossier = os.path.join(LAKE, t)
    if os.path.exists(dossier):
        shutil.rmtree(dossier)
    os.makedirs(dossier, exist_ok=True)
    df.to_parquet(os.path.join(dossier, "data.parquet"), index=False)
    print(f"  {t:14s} : {len(df):>9,} lignes  ({n_avant - len(df)} retiree(s)) -> {dossier}")

print("Ingestion terminee (Parquet dans 02_DONNEES/lake/).")
