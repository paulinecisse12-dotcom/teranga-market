# -*- coding: utf-8 -*-
"""
DONNEES — 3.4 CONTROLES QUALITE.
Lance une batterie de tests automatiques sur le Warehouse DuckDB.
Chaque test compte les lignes en anomalie : 0 = PASS, sinon = FAIL.

Lancement (venv avec duckdb) :
    python 02_DONNEES/qualite/01_controles_qualite.py
"""
import os
import duckdb

DONNEES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB = os.path.join(DONNEES, "warehouse", "teranga.duckdb")

con = duckdb.connect(DB, read_only=True)

# Chaque test : (categorie, description, requete SQL qui compte les ANOMALIES)
CHECKS = [
    # --- Unicite des cles primaires ---
    ("Unicite PK", "produits.id_produit unique",
     "SELECT COUNT(*)-COUNT(DISTINCT id_produit) FROM produits"),
    ("Unicite PK", "clients.id_client unique",
     "SELECT COUNT(*)-COUNT(DISTINCT id_client) FROM clients"),
    ("Unicite PK", "transactions.id_transaction unique",
     "SELECT COUNT(*)-COUNT(DISTINCT id_transaction) FROM transactions"),
    ("Unicite PK", "navigation.id_navigation unique",
     "SELECT COUNT(*)-COUNT(DISTINCT id_navigation) FROM navigation"),

    # --- Cles primaires non nulles ---
    ("Non nul", "aucun id_client nul",
     "SELECT COUNT(*) FROM clients WHERE id_client IS NULL"),
    ("Non nul", "aucun id_transaction nul",
     "SELECT COUNT(*) FROM transactions WHERE id_transaction IS NULL"),

    # --- Integrite referentielle (cles etrangeres) ---
    ("Integrite FK", "transactions.id_client existe dans clients",
     "SELECT COUNT(*) FROM transactions t LEFT JOIN clients c ON t.id_client=c.id_client WHERE c.id_client IS NULL"),
    ("Integrite FK", "transactions.id_produit existe dans produits",
     "SELECT COUNT(*) FROM transactions t LEFT JOIN produits p ON t.id_produit=p.id_produit WHERE p.id_produit IS NULL"),
    ("Integrite FK", "transactions.id_promo existe dans promotions",
     "SELECT COUNT(*) FROM transactions t LEFT JOIN promotions pr ON t.id_promo=pr.id_promo WHERE pr.id_promo IS NULL"),
    ("Integrite FK", "navigation.id_client existe dans clients",
     "SELECT COUNT(*) FROM navigation n LEFT JOIN clients c ON n.id_client=c.id_client WHERE c.id_client IS NULL"),
    ("Integrite FK", "navigation.id_produit existe dans produits",
     "SELECT COUNT(*) FROM navigation n LEFT JOIN produits p ON n.id_produit=p.id_produit WHERE p.id_produit IS NULL"),

    # --- Coherence des valeurs numeriques ---
    ("Valeurs", "quantite > 0",
     "SELECT COUNT(*) FROM transactions WHERE quantite <= 0"),
    ("Valeurs", "prix_unitaire > 0",
     "SELECT COUNT(*) FROM transactions WHERE prix_unitaire <= 0"),
    ("Valeurs", "montant_total = prix_unitaire x quantite",
     "SELECT COUNT(*) FROM transactions WHERE montant_total <> prix_unitaire * quantite"),
    ("Valeurs", "prix_unitaire <= prix_catalogue (remise seulement)",
     "SELECT COUNT(*) FROM transactions t JOIN produits p ON t.id_produit=p.id_produit WHERE t.prix_unitaire > p.prix_catalogue"),
    ("Valeurs", "age client entre 18 et 75",
     "SELECT COUNT(*) FROM clients WHERE age < 18 OR age > 75"),
    ("Valeurs", "taux_reduction entre 0 et 1",
     "SELECT COUNT(*) FROM promotions WHERE taux_reduction < 0 OR taux_reduction > 1"),
    ("Valeurs", "action valide (vue/clic/ajout_panier)",
     "SELECT COUNT(*) FROM navigation WHERE action NOT IN ('vue','clic','ajout_panier')"),

    # --- Coherence temporelle ---
    ("Dates", "date_vente dans la fenetre [2025-07-01, 2026-06-30]",
     "SELECT COUNT(*) FROM transactions WHERE date_vente < DATE '2025-07-01' OR date_vente > DATE '2026-06-30'"),
    ("Dates", "aucun achat avant l'inscription du client",
     "SELECT COUNT(*) FROM transactions t JOIN clients c ON t.id_client=c.id_client WHERE t.date_vente < c.date_inscription"),

    # --- Coherence de l'entonnoir ---
    ("Entonnoir", "ajouts panier > nombre d'achats",
     "SELECT CASE WHEN (SELECT COUNT(*) FROM navigation WHERE action='ajout_panier') > (SELECT COUNT(*) FROM transactions) THEN 0 ELSE 1 END"),
]

print("=" * 78)
print(" CONTROLES QUALITE — Teranga Market")
print("=" * 78)

n_pass = 0
n_fail = 0
cat_courante = None
for cat, desc, sql in CHECKS:
    if cat != cat_courante:
        print(f"\n[{cat}]")
        cat_courante = cat
    anomalies = con.execute(sql).fetchone()[0]
    if anomalies == 0:
        print(f"  PASS  | {desc}")
        n_pass += 1
    else:
        print(f"  FAIL  | {desc}  -> {anomalies:,} anomalie(s)")
        n_fail += 1

con.close()

print("\n" + "=" * 78)
total = n_pass + n_fail
print(f" RESULTAT : {n_pass}/{total} tests reussis", end="")
if n_fail == 0:
    print("   --  JEU DE DONNEES 100% VALIDE")
else:
    print(f"   --  {n_fail} test(s) en echec a corriger")
print("=" * 78)
