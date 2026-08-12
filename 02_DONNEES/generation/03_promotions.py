# -*- coding: utf-8 -*-
"""
Etape 3 — Generation de la table PROMOTIONS.
Teranga Market : campagnes promotionnelles calees sur des periodes reelles.
La ligne id_promo=0 = "Aucune promotion" (pour les ventes sans promo).
"""
import pandas as pd

# id_promo, nom_campagne, type, taux_reduction (fraction), date_debut, date_fin
PROMOTIONS = [
    (0,  "Aucune promotion",        "Aucune",        0.00, None,          None),
    (1,  "Rentree scolaire",        "Remise",        0.15, "2025-09-01", "2025-09-30"),
    (2,  "Destockage electro",      "Liquidation",   0.40, "2025-10-10", "2025-10-20"),
    (3,  "Black Friday",            "Vente flash",   0.30, "2025-11-24", "2025-11-30"),
    (4,  "Fetes de fin d'annee",    "Soldes",        0.20, "2025-12-15", "2025-12-31"),
    (5,  "Saint-Valentin",          "Code promo",    0.10, "2026-02-10", "2026-02-16"),
    (6,  "Korite (Aid el-Fitr)",    "Remise",        0.25, "2026-03-18", "2026-03-25"),
    (7,  "Fete de l'Independance",     "Soldes",        0.15, "2026-04-01", "2026-04-07"),
    (8,  "Tabaski",                 "Remise",        0.25, "2026-05-25", "2026-06-05"),
    (9,  "Vente flash mobile",      "Vente flash",   0.35, "2026-06-20", "2026-06-22"),
]

promotions = pd.DataFrame(
    PROMOTIONS,
    columns=["id_promo", "nom_campagne", "type", "taux_reduction", "date_debut", "date_fin"]
)

# --- Sauvegarde ---
import os
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "brut")
os.makedirs(OUT_DIR, exist_ok=True)
promotions.to_csv(os.path.join(OUT_DIR, "promotions.csv"), index=False, encoding="utf-8-sig")

# --- Verification ---
print(f"Total promotions : {len(promotions)} (dont 1 ligne 'Aucune promotion')")
print("\nTable PROMOTIONS :")
aff = promotions.copy()
aff["taux_reduction"] = (aff["taux_reduction"] * 100).astype(int).astype(str) + " %"
print(aff.to_string(index=False))
