# -*- coding: utf-8 -*-
"""
Etape 5 — Generation de la table NAVIGATION (logs web / evenements).
~400 000 evenements : vues, clics, ajouts panier (entonnoir realiste).
Sert a la recommandation et au calcul du taux de conversion.
"""
import os
import numpy as np
import pandas as pd

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

# ~1 000 000 evenements : l'entonnoir doit rester coherent avec les 100 000 achats
# (ajouts panier > achats, car certains paniers sont abandonnes).
N_NAV = 1_000_000
BASE = os.path.dirname(os.path.dirname(__file__))
BRUT = os.path.join(BASE, "brut")

clients = pd.read_csv(os.path.join(BRUT, "clients.csv"))
produits = pd.read_csv(os.path.join(BRUT, "produits.csv"))

DEBUT = pd.Timestamp("2025-07-01")
FIN = pd.Timestamp("2026-06-30")
n_jours = (FIN - DEBUT).days

# --- Clients : les plus actifs (Premium/Regulier) naviguent plus ---
poids_segment = {"Premium": 4.0, "Regulier": 2.5, "Occasionnel": 1.2, "Nouveau": 0.7}
w_cli = clients["segment"].map(poids_segment).to_numpy(); w_cli /= w_cli.sum()
idx_cli = rng.choice(len(clients), size=N_NAV, p=w_cli)
id_client = clients["id_client"].to_numpy()[idx_cli]

# --- Produits : popularite inegale (correlee aux ventes) ---
boost_cat = {"Accessoires": 2.2, "Smartphones & tablettes": 1.8, "Audio": 1.4,
             "Objets connectes": 1.0, "Gaming": 0.9, "TV & image": 0.6, "Ordinateurs": 0.5}
pop = rng.gamma(shape=1.3, size=len(produits)) * produits["categorie"].map(boost_cat).to_numpy()
pop /= pop.sum()
idx_prod = rng.choice(len(produits), size=N_NAV, p=pop)
id_produit = produits["id_produit"].to_numpy()[idx_prod]

# --- Action : entonnoir (beaucoup de vues, peu d'ajouts panier) ---
action = rng.choice(["vue", "clic", "ajout_panier"], size=N_NAV, p=[0.70, 0.18, 0.12])

# --- Horodatage : date dans la fenetre + heure (pic le soir) ---
jours = rng.integers(0, n_jours + 1, size=N_NAV)
# poids par heure (0..23) : creux la nuit, pic 12-14h et surtout 18-23h
poids_h = np.array([0.5,0.3,0.2,0.2,0.2,0.3,0.6,1.0,1.5,1.8,2.0,2.2,
                    2.6,2.4,1.9,1.8,2.0,2.6,3.4,3.8,3.6,3.0,2.2,1.2])
poids_h /= poids_h.sum()
heures = rng.choice(24, size=N_NAV, p=poids_h)
minutes = rng.integers(0, 60, size=N_NAV)
secondes = rng.integers(0, 60, size=N_NAV)
horodatage = (DEBUT + pd.to_timedelta(jours, unit="D")
              + pd.to_timedelta(heures, unit="h")
              + pd.to_timedelta(minutes, unit="m")
              + pd.to_timedelta(secondes, unit="s"))

navigation = pd.DataFrame({
    "id_navigation": np.arange(1, N_NAV + 1),
    "id_client": id_client,
    "id_produit": id_produit,
    "horodatage": horodatage.strftime("%Y-%m-%d %H:%M:%S"),
    "action": action,
}).sort_values("horodatage").reset_index(drop=True)
navigation["id_navigation"] = np.arange(1, N_NAV + 1)

navigation.to_csv(os.path.join(BRUT, "navigation.csv"), index=False, encoding="utf-8-sig")

# --- Verification ---
print(f"Total evenements de navigation : {len(navigation):,}")
print(f"Periode : {navigation['horodatage'].min()} -> {navigation['horodatage'].max()}")
print("\nRepartition par action (entonnoir) :")
va = navigation["action"].value_counts()
for a, n in va.items():
    print(f"  {a:14s} : {n:7,}  ({n/len(navigation)*100:.1f} %)")
print(f"\nClients actifs (navigation) : {navigation['id_client'].nunique():,} / {len(clients):,}")
print(f"Produits consultes          : {navigation['id_produit'].nunique():,} / {len(produits):,}")
print("\nApercu (8 evenements) :")
print(navigation.head(8).to_string(index=False))
# taux de conversion indicatif : ajouts panier -> achats
n_panier = int((navigation['action'] == 'ajout_panier').sum())
print(f"\nAjouts au panier : {n_panier:,}  (les achats reels = 100 000 dans transactions.csv)")
