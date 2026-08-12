# -*- coding: utf-8 -*-
"""
Etape 2 — Generation de la table CLIENTS.
Teranga Market : 10 000 clients (noms senegalais, villes du Senegal).
"""
import numpy as np
import pandas as pd

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

N_CLIENTS = 10_000

# --- Noms senegalais ---
PRENOMS = [
    "Aminata", "Fatou", "Mariama", "Awa", "Aissatou", "Khadija", "Astou", "Ndeye",
    "Fatoumata", "Sokhna", "Adama", "Bineta", "Rokhaya", "Coumba", "Dieynaba",
    "Ousmane", "Moussa", "Ibrahima", "Cheikh", "Modou", "Abdoulaye", "Mamadou",
    "Seydou", "Babacar", "Pape", "Assane", "Alioune", "Serigne", "Malick", "Idrissa",
]
NOMS = [
    "Diop", "Ndiaye", "Fall", "Sow", "Ba", "Diallo", "Gueye", "Sarr", "Faye", "Sy",
    "Cisse", "Mbaye", "Sene", "Kane", "Diouf", "Thiam", "Camara", "Toure", "Niang", "Wade",
]

# --- Villes du Senegal (avec poids realistes) ---
VILLES = ["Dakar", "Thies", "Touba", "Rufisque", "Saint-Louis", "Kaolack", "Mbour",
          "Ziguinchor", "Diourbel", "Louga", "Tambacounda", "Kolda"]
POIDS_VILLES = [0.40, 0.11, 0.10, 0.07, 0.06, 0.05, 0.05, 0.04, 0.03, 0.03, 0.03, 0.03]

# --- Segments et canaux ---
SEGMENTS = ["Nouveau", "Occasionnel", "Regulier", "Premium"]
POIDS_SEGMENTS = [0.30, 0.38, 0.24, 0.08]

CANAUX = ["Recherche Google (SEO)", "Publicite (Ads)", "Reseaux sociaux",
          "Parrainage", "Acces direct"]
POIDS_CANAUX = [0.28, 0.25, 0.22, 0.13, 0.12]

# --- Dates d'inscription ---
# Une boutique etablie : la plupart des clients existent AVANT la periode analysee
# (fenetre des ventes = juillet 2025 -> juin 2026).
#  - 70% inscrits AVANT la fenetre : entre 2023-07-01 et 2025-06-30 (base existante)
#  - 30% inscrits PENDANT la fenetre : entre 2025-07-01 et 2026-06-30 (nouveaux clients)
avant_deb, avant_fin = pd.Timestamp("2023-07-01"), pd.Timestamp("2025-06-30")
pdt_deb,   pdt_fin   = pd.Timestamp("2025-07-01"), pd.Timestamp("2026-06-30")
n_avant = (avant_fin - avant_deb).days
n_pdt = (pdt_fin - pdt_deb).days

est_ancien = rng.random(N_CLIENTS) < 0.70
dates_inscription = []
for anc in est_ancien:
    if anc:  # base existante : uniforme avant la fenetre
        o = int(rng.integers(0, n_avant + 1))
        dates_inscription.append(avant_deb + pd.Timedelta(days=o))
    else:    # nouveau client : pendant la fenetre, reparti uniformement
        o = int(rng.integers(0, n_pdt + 1))
        dates_inscription.append(pdt_deb + pd.Timedelta(days=o))

clients = pd.DataFrame({
    "id_client": np.arange(1, N_CLIENTS + 1),
    "nom": [f"{rng.choice(PRENOMS)} {rng.choice(NOMS)}" for _ in range(N_CLIENTS)],
    "ville": rng.choice(VILLES, size=N_CLIENTS, p=POIDS_VILLES),
    "date_inscription": [d.strftime("%Y-%m-%d") for d in dates_inscription],
    "segment": rng.choice(SEGMENTS, size=N_CLIENTS, p=POIDS_SEGMENTS),
    "canal_acquisition": rng.choice(CANAUX, size=N_CLIENTS, p=POIDS_CANAUX),
})

# --- Age du client ---
# Tire EN DERNIER pour ne pas decaler les tirages precedents (les autres
# colonnes restent identiques -> transactions/navigation restent coherents).
# Distribution realiste : clientele e-commerce plutot jeune (moyenne ~33 ans),
# bornee entre 18 et 75 ans.
age = np.clip(rng.normal(33, 11, N_CLIENTS), 18, 75).round().astype(int)
clients.insert(2, "age", age)   # colonne placee juste apres 'nom'

# --- Sauvegarde ---
import os
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "brut")
os.makedirs(OUT_DIR, exist_ok=True)
clients.to_csv(os.path.join(OUT_DIR, "clients.csv"), index=False, encoding="utf-8-sig")

# --- Verification ---
print(f"Total clients : {len(clients)}")
print("\nApercu (10 clients) :")
print(clients.head(10).to_string(index=False))
print("\nRepartition par ville :")
print(clients["ville"].value_counts().to_string())
print("\nRepartition par segment :")
print(clients["segment"].value_counts().to_string())
print("\nRepartition par canal d'acquisition :")
print(clients["canal_acquisition"].value_counts().to_string())
print(f"\nDates d'inscription : de {clients['date_inscription'].min()} a {clients['date_inscription'].max()}")
print(f"\nAge : min {clients['age'].min()} | moyen {clients['age'].mean():.1f} | max {clients['age'].max()}")
print("Tranches d'age :")
tranches = pd.cut(clients['age'], bins=[17,25,35,45,55,75],
                  labels=["18-25","26-35","36-45","46-55","56-75"])
print(tranches.value_counts().sort_index().to_string())
