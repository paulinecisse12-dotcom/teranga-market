# -*- coding: utf-8 -*-
"""
Genere le schema d'architecture technique de Teranga Market.
Source reutilisable (matplotlib) -> 01_ARCHITECTURE/archi_technique.png (1794x2014).

Chaine de la donnee en 6 couches (Sources -> Restitution) + 3 composants
transversaux a droite : ORCHESTRATION (Airflow), MLOPS (MLflow/monitoring/CI-CD),
GOUVERNANCE (qualite/RGPD/securite).

Lancer :  python 01_ARCHITECTURE/generer_schema_archi.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

# ---------------------------------------------------------------- Palette
NAVY = "#1B2A3A"   # titre / fleches
GREY = "#6B7887"   # sous-titre / bas de page

COUCHES = {
    # nom        : (couleur boite,  couleur bande claire)
    "SOURCES"    : ("#127A8A", "#E2EEF0"),
    "INGESTION"  : ("#E67E22", "#FBEFE4"),
    "STOCKAGE"   : ("#0F2A43", "#E1E5E8"),
    "MODÈLES"    : ("#8E44AD", "#F1E8F5"),
    "EXPOSITION" : ("#27AE60", "#E4F5EB"),
    "RESTITUTION": ("#2C7BE5", "#E5EEFB"),
}
SLATE = "#34495E"   # panneau Orchestration
TEAL  = "#2D6E75"   # panneau MLOps (nouveau)
GRIS  = "#7F8C8D"   # panneau Gouvernance

# ---------------------------------------------------------------- Geometrie
CENTRE = 50.5          # centre horizontal de la composition
BX = [15.5, 35.5, 55.5]   # centres des 3 colonnes de boites
BW = 18                    # largeur d'une boite standard
FLUX_X = 35.5             # axe des fleches de flux
PAN_L, PAN_R = 69, 96     # colonne des panneaux transversaux
PAN_CX = (PAN_L + PAN_R) / 2

# ---------------------------------------------------------------- Figure
fig, ax = plt.subplots(figsize=(8.97, 10.07), dpi=200)
ax.set_xlim(0, 100)
ax.set_ylim(0, 112)
ax.axis("off")
fig.subplots_adjust(left=0, right=1, top=1, bottom=0)


def carte(cx, cy, w, h, face, txt, tc="white", fs=9, bold=True):
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=1.1",
        facecolor=face, edgecolor=face, linewidth=1.2, zorder=3))
    ax.text(cx, cy, txt, ha="center", va="center", color=tc,
            fontsize=fs, fontweight="bold" if bold else "normal",
            zorder=4, linespacing=1.25)


def bande(cy, face):
    ax.add_patch(FancyBboxPatch(
        (5, cy - 5), 61, 10, boxstyle="round,pad=0.02,rounding_size=1.4",
        facecolor=face, edgecolor="none", zorder=1))


def label(cy, txt, color):
    ax.text(2.6, cy, txt, ha="center", va="center", rotation=90,
            color=color, fontsize=11.5, fontweight="bold")


def fleche(x, y1, y2):
    ax.annotate("", xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.6,
                                mutation_scale=22), zorder=2)


# ------------------------------------------------------ Titre / sous-titre
ax.text(CENTRE, 108.2, "Architecture technique — Plateforme Data-Driven",
        ha="center", va="center", fontsize=17.5, fontweight="bold", color=NAVY)
ax.text(CENTRE, 104, "Teranga Market  ·  chaîne de la donnée de bout en bout",
        ha="center", va="center", fontsize=11.5, style="italic", color=GREY)

# ------------------------------------------------------ Bandes + labels
CY = {"SOURCES": 94, "INGESTION": 80, "STOCKAGE": 66,
      "MODÈLES": 52, "EXPOSITION": 38, "RESTITUTION": 24}
for nom, cy in CY.items():
    bande(cy, COUCHES[nom][1])
    label(cy, nom, COUCHES[nom][0])

# ------------------------------------------------------ Fleches de flux
for y1, y2 in [(89, 85), (75, 71), (61, 57), (47, 43), (33, 29)]:
    fleche(FLUX_X, y1, y2)

# ------------------------------------------------------ Couche SOURCES
teal = COUCHES["SOURCES"][0]
carte(BX[0], 94, BW, 7, teal, "Applications\nMobile / Web")
carte(BX[1], 94, BW, 7, teal, "Site e-commerce\n(transactions)")
carte(BX[2], 94, BW, 7, teal, "Logs de navigation\n& événements")

# ------------------------------------------------------ Couche INGESTION
orange = COUCHES["INGESTION"][0]
carte(BX[0], 80, BW, 7, orange, "Kafka\n(streaming temps réel)")
carte(BX[1], 80, BW, 7, orange, "Spark\n(traitement batch)")
carte(BX[2], 80, BW, 7, orange, "APIs /\nConnecteurs")

# ------------------------------------------------------ Couche STOCKAGE
navy = COUCHES["STOCKAGE"][0]
carte(20, 66, 19, 7.5, navy, "Data Lake\n(Parquet)", fs=10.5)
carte(51, 66, 19, 7.5, navy, "Data Warehouse\n(DuckDB)", fs=10.5)
ax.annotate("", xy=(41, 66), xytext=(29.6, 66),
            arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=2.6, mutation_scale=20), zorder=2)

# ------------------------------------------------------ Couche MODÈLES
purple = COUCHES["MODÈLES"][0]
carte(BX[0], 52, BW, 7, purple, "Prévision\nde la demande")
carte(BX[1], 52, BW, 7, purple, "Optimisation\ndes prix")
carte(BX[2], 52, BW, 7, purple, "Recommandation\nde produits")

# ------------------------------------------------------ Couche EXPOSITION
carte(FLUX_X, 38, 43, 7, COUCHES["EXPOSITION"][0], "API REST — FastAPI (Docker)", fs=11.5)

# ------------------------------------------------------ Couche RESTITUTION
carte(FLUX_X, 24, 43, 7, COUCHES["RESTITUTION"][0], "Dashboard décisionnel — Dash (KPIs)", fs=11.5)

# ------------------------------------------------------ Panneaux transversaux
def panneau(y0, y1, face, titre, corps):
    ax.add_patch(FancyBboxPatch(
        (PAN_L, y0), PAN_R - PAN_L, y1 - y0,
        boxstyle="round,pad=0.02,rounding_size=1.1",
        facecolor=face, edgecolor="none", zorder=3))
    ax.text(PAN_CX, y1 - 3.0, titre, ha="center", va="center",
            color="white", fontsize=11.5, fontweight="bold", zorder=4)
    ax.text(PAN_CX, (y0 + y1) / 2 - 2.0, corps, ha="center", va="center",
            color="#E8ECEF", fontsize=9, zorder=4, linespacing=1.5)

panneau(60, 88, SLATE, "ORCHESTRATION",
        "Airflow\n\nEnchaîne\ningestion →\nqualité →\ntransform →\nentraînement")
panneau(45, 57.5, TEAL, "MLOPS",
        "MLflow ·\nmonitoring\ndérive (PSI) ·\nCI/CD")
panneau(19, 42.5, GRIS, "GOUVERNANCE",
        "Qualité des\ndonnées ·\nRGPD ·\nsécurité\n(chiffrement)")

# fleche pointillee Orchestration -> Warehouse
ax.annotate("", xy=(60.6, 66), xytext=(PAN_L, 66),
            arrowprops=dict(arrowstyle="-|>", color=SLATE, lw=2.0,
                            linestyle=(0, (4, 3)), mutation_scale=18), zorder=2)

# ------------------------------------------------------ Bas de page
ax.text(CENTRE, 11,
        "Flux principal : Sources → Ingestion → Stockage → Modèles → API → Dashboard",
        ha="center", va="center", fontsize=11.5, fontweight="bold", color=NAVY)
ax.text(CENTRE, 6.2,
        "Airflow orchestre le pipeline · MLOps opère les modèles · "
        "La gouvernance (qualité, RGPD, sécurité) s'applique à toutes les couches",
        ha="center", va="center", fontsize=8.8, style="italic", color=GREY)

# ------------------------------------------------------ Sauvegarde
OUT = os.path.join(os.path.dirname(__file__), "archi_technique.png")
fig.savefig(OUT, dpi=200)
print("Schema enregistre :", OUT)
