# -*- coding: utf-8 -*-
"""
Etape 4 — Generation de la table TRANSACTIONS (table de faits, 100 000 ventes).
Relie clients + produits + promotions, avec une logique realiste.
"""
import os
import numpy as np
import pandas as pd

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

N_TRANSACTIONS = 100_000
BASE = os.path.dirname(os.path.dirname(__file__))
BRUT = os.path.join(BASE, "brut")

# --- Chargement des tables deja generees ---
clients = pd.read_csv(os.path.join(BRUT, "clients.csv"))
produits = pd.read_csv(os.path.join(BRUT, "produits.csv"))
promotions = pd.read_csv(os.path.join(BRUT, "promotions.csv"))

# --- Fenetre temporelle : 12 mois ---
DEBUT = pd.Timestamp("2025-07-01")
FIN = pd.Timestamp("2026-06-30")
n_jours = (FIN - DEBUT).days

# ============================================================
# 1. CHOIX DES CLIENTS (pondere par segment : Premium achete +)
# ============================================================
poids_segment = {"Premium": 4.0, "Regulier": 2.5, "Occasionnel": 1.2, "Nouveau": 0.7}
w_clients = clients["segment"].map(poids_segment).to_numpy()
w_clients = w_clients / w_clients.sum()
idx_clients = rng.choice(len(clients), size=N_TRANSACTIONS, p=w_clients)
id_client = clients["id_client"].to_numpy()[idx_clients]
inscription = pd.to_datetime(clients["date_inscription"]).to_numpy()[idx_clients]

# ============================================================
# 2. CHOIX DES PRODUITS (popularite inegale : best-sellers)
#    boost pour Accessoires et Smartphones (plus vendus)
# ============================================================
boost_cat = {"Accessoires": 2.2, "Smartphones & tablettes": 1.8, "Audio": 1.4,
             "Objets connectes": 1.0, "Gaming": 0.9, "TV & image": 0.6, "Ordinateurs": 0.5}
pop = rng.gamma(shape=1.3, size=len(produits)) * produits["categorie"].map(boost_cat).to_numpy()
pop = pop / pop.sum()
idx_prod = rng.choice(len(produits), size=N_TRANSACTIONS, p=pop)
id_produit = produits["id_produit"].to_numpy()[idx_prod]
prix_cat = produits["prix_catalogue"].to_numpy()[idx_prod]

# ============================================================
# 3. DATES DE VENTE (mixture : 30% pendant les promos = pics)
# ============================================================
promo_reelles = promotions[promotions["id_promo"] != 0].copy()
promo_reelles["date_debut"] = pd.to_datetime(promo_reelles["date_debut"])
promo_reelles["date_fin"] = pd.to_datetime(promo_reelles["date_fin"])

dates = np.empty(N_TRANSACTIONS, dtype="datetime64[ns]")
pendant_promo = rng.random(N_TRANSACTIONS) < 0.30
# ventes hors promo : uniforme sur l'annee
n_hors = (~pendant_promo).sum()
offs = rng.integers(0, n_jours + 1, size=n_hors)
dates[~pendant_promo] = (DEBUT + pd.to_timedelta(offs, unit="D")).to_numpy()
# ventes pendant promo : on tire une campagne puis une date dans sa periode
idx_campagne = rng.integers(0, len(promo_reelles), size=pendant_promo.sum())
deb = promo_reelles["date_debut"].to_numpy()[idx_campagne]
fin = promo_reelles["date_fin"].to_numpy()[idx_campagne]
span = ((fin - deb) / np.timedelta64(1, "D")).astype(int)
rand_off = (rng.random(len(span)) * (span + 1)).astype(int)
dates[pendant_promo] = deb + rand_off.astype("timedelta64[D]")

# ============================================================
# 4. COHERENCE : pas d'achat avant l'inscription du client
# ============================================================
avant = dates < inscription
n_avant = int(avant.sum())
if n_avant:
    # re-tire une date entre l'inscription et la fin de fenetre
    insc_a = inscription[avant]
    marge = ((np.datetime64(FIN) - insc_a) / np.timedelta64(1, "D")).astype(int)
    marge = np.clip(marge, 1, None)
    rand2 = (rng.random(n_avant) * marge).astype(int)
    dates[avant] = insc_a + rand2.astype("timedelta64[D]")

dates = pd.to_datetime(dates)

# ============================================================
# 5. AFFECTATION DES PROMOTIONS selon la date
# ============================================================
id_promo = np.zeros(N_TRANSACTIONS, dtype=int)
taux = np.zeros(N_TRANSACTIONS)
for _, p in promo_reelles.iterrows():
    dans = (dates >= p["date_debut"]) & (dates <= p["date_fin"])
    # 75% des ventes dans la periode profitent de la promo
    applique = dans & (rng.random(N_TRANSACTIONS) < 0.75)
    id_promo[applique] = p["id_promo"]
    taux[applique] = p["taux_reduction"]

# ============================================================
# 6. QUANTITE, PRIX, MONTANT
# ============================================================
quantite = rng.choice([1, 2, 3, 4], size=N_TRANSACTIONS, p=[0.72, 0.18, 0.07, 0.03])
prix_unitaire = (prix_cat * (1 - taux)).round(-2).astype(int)   # arrondi a 100 FCFA
montant_total = prix_unitaire * quantite

transactions = pd.DataFrame({
    "id_transaction": np.arange(1, N_TRANSACTIONS + 1),
    "id_client": id_client,
    "id_produit": id_produit,
    "id_promo": id_promo,
    "date_vente": dates.strftime("%Y-%m-%d"),
    "quantite": quantite,
    "prix_unitaire": prix_unitaire,
    "montant_total": montant_total,
}).sort_values("date_vente").reset_index(drop=True)
transactions["id_transaction"] = np.arange(1, N_TRANSACTIONS + 1)

# --- Sauvegarde ---
transactions.to_csv(os.path.join(BRUT, "transactions.csv"), index=False, encoding="utf-8-sig")

# --- Verification ---
print(f"Total transactions : {len(transactions):,}")
print(f"Periode : {transactions['date_vente'].min()} -> {transactions['date_vente'].max()}")
print(f"Chiffre d'affaires total : {transactions['montant_total'].sum():,} FCFA")
print(f"Panier moyen : {int(transactions['montant_total'].mean()):,} FCFA")
part_promo = (transactions['id_promo'] != 0).mean() * 100
print(f"Ventes avec promotion : {part_promo:.1f} %")
print(f"Clients distincts ayant achete : {transactions['id_client'].nunique():,} / {len(clients):,}")
print(f"Produits distincts vendus : {transactions['id_produit'].nunique():,} / {len(produits):,}")
print("\nApercu (8 transactions) :")
print(transactions.head(8).to_string(index=False))
print("\nVentes par mois :")
vm = transactions.copy(); vm["mois"] = pd.to_datetime(vm["date_vente"]).dt.to_period("M")
print(vm.groupby("mois").size().to_string())
