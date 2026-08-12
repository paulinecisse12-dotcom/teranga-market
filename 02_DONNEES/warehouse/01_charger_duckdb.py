# -*- coding: utf-8 -*-
"""
DONNEES — 3.3 DATA WAREHOUSE (DuckDB).
Charge les 5 tables Parquet (Data Lake) dans une base DuckDB requetable en SQL.
    Parquet (lake/)  ->  [DuckDB]  ->  base teranga.duckdb (requetes SQL)

Lancement (venv Windows avec duckdb installe) :
    python 02_DONNEES/warehouse/01_charger_duckdb.py
"""
import os
import duckdb

# ------------------------------------------------------------------
# 0. Chemins
# ------------------------------------------------------------------
DONNEES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LAKE = os.path.join(DONNEES, "lake")
WAREHOUSE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(WAREHOUSE, "teranga.duckdb")

def glob_parquet(table):
    # DuckDB accepte les / meme sous Windows
    return os.path.join(LAKE, table, "*.parquet").replace("\\", "/")

# ------------------------------------------------------------------
# 1. Connexion a la base (creee si elle n'existe pas)
# ------------------------------------------------------------------
con = duckdb.connect(DB)

# ------------------------------------------------------------------
# 2. Charger chaque table Parquet dans le Warehouse
# ------------------------------------------------------------------
TABLES = ["produits", "clients", "promotions", "transactions", "navigation"]
print("=== Chargement des tables dans DuckDB ===")
for t in TABLES:
    con.execute(f"CREATE OR REPLACE TABLE {t} AS SELECT * FROM read_parquet('{glob_parquet(t)}')")
    n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    print(f"  {t:14s} : {n:>9,} lignes")

# ------------------------------------------------------------------
# 3. Quelques requetes SQL de demonstration (l'interet du Warehouse !)
# ------------------------------------------------------------------
print("\n=== Demo 1 : Chiffre d'affaires par categorie ===")
q1 = con.execute("""
    SELECT p.categorie,
           COUNT(*)                        AS nb_ventes,
           SUM(t.montant_total)            AS ca_total,
           CAST(AVG(t.montant_total) AS INT) AS panier_moyen
    FROM transactions t
    JOIN produits p ON t.id_produit = p.id_produit
    GROUP BY p.categorie
    ORDER BY ca_total DESC
""").fetchall()
print(f"{'Categorie':<26}{'Nb ventes':>10}{'CA total (FCFA)':>20}{'Panier moyen':>15}")
for cat, nb, ca, pm in q1:
    print(f"{cat:<26}{nb:>10,}{ca:>20,}{pm:>15,}")

print("\n=== Demo 2 : Top 5 des produits les plus vendus ===")
q2 = con.execute("""
    SELECT p.nom, p.categorie, COUNT(*) AS nb_ventes
    FROM transactions t
    JOIN produits p ON t.id_produit = p.id_produit
    GROUP BY p.nom, p.categorie
    ORDER BY nb_ventes DESC
    LIMIT 5
""").fetchall()
for nom, cat, nb in q2:
    print(f"  {nb:>5,} ventes  -  {nom}  ({cat})")

print("\n=== Demo 3 : Part des ventes avec promotion ===")
q3 = con.execute("""
    SELECT ROUND(100.0 * COUNT(*) FILTER (WHERE id_promo <> 0) / COUNT(*), 1)
    FROM transactions
""").fetchone()[0]
print(f"  {q3} % des ventes ont beneficie d'une promotion")

con.close()
print(f"\nWarehouse pret : {DB}")
print("Tu peux maintenant interroger ces 5 tables en SQL.")
