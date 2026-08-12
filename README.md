# 🛒 Teranga Market — Plateforme Data-Driven Pricing & Recommandation

> Projet final du module **Gestion de Projet Data & E-Business** — Master 2 Big Data, ISM.
> Plateforme *data-driven* pour un e-commerce local d'électronique (contexte Sénégal, FCFA) :
> **prévision de la demande**, **optimisation des prix** et **recommandation** de produits.

---

## 🎯 Contexte & objectif

Une entreprise e-commerce locale souhaite **maximiser sa marge et fidéliser** ses clients grâce à :
- une **prévision de la demande** (gestion du stock),
- un **pricing** optimisé (élasticité prix / marge),
- des **recommandations** personnalisées (cross-sell / up-sell).

Le projet couvre toute la chaîne : cadrage → architecture → pipeline de données → modèles → mise en production.

---

## 🗂️ Structure du dépôt

| Dossier | Contenu | Statut |
|---|---|---|
| `00_CADRAGE/` | Cahier des charges, charte, RACI, WBS, Gantt, risques, RGPD | ✅ |
| `01_ARCHITECTURE/` | Schéma d'architecture technique + schéma de données | ✅ |
| `02_DONNEES/` | Génération du dataset, ingestion Spark, warehouse DuckDB, qualité, streaming Kafka, orchestration Airflow | ✅ |
| `03_MODELES/` | Les 3 modèles (notebooks) + évaluation | ✅ |
| `04_PRODUCTION/` | MLOps (MLflow), API (FastAPI + Docker), dashboard (Dash) | 🔶 en cours |
| `05_LIVRABLES/` | Business case, rapport final, présentation | ⬜ à venir |

---

## 📊 Jeu de données (synthétique, reproductible — graine = 42)

| Table | Volume | Description |
|---|---|---|
| `produits` | 500 | 7 catégories, marque, prix catalogue, coût, stock |
| `clients` | 10 000 | profils clients |
| `transactions` | 100 000 | ventes sur **12 mois** (juil. 2025 → juin 2026) — table de faits |
| `navigation` | 1 000 000 | événements web (vue, clic, ajout panier) |
| `promotions` | 10 | campagnes datées (Black Friday, Tabaski, Korité…) |

Modèle en **étoile** ; entrepôt final : **DuckDB** (`02_DONNEES/warehouse/teranga.duckdb`).

---

## 🤖 Les 3 modèles (Partie 4)

Chaque modèle est un **notebook reproductible**, évalué contre une **baseline**.

| # | Modèle | Métrique | Baseline | Notre modèle | Résultat |
|---|---|---|---|---|---|
| 4.1 | **Prévision demande** (Prophet + promos) | MAE | 66 (naïf) | 37 (Prophet+promo) | **−43 % d'erreur** |
| 4.2 | **Optimisation prix** (élasticité → marge) | Marge | prix actuels | +14 % de prix | **+3,8 % de marge** |
| 4.3 | **Recommandation** (hybride content + collaboratif) | Recall@5 | 1 % (hasard) | 6,8 % (collaboratif) | **~7× le hasard** |

- **4.1** `03_MODELES/forecasting/4.1_prevision_demande.ipynb` — séries temporelles par catégorie, régresseur promotions.
- **4.2** `03_MODELES/pricing/4.2_optimisation_prix.ipynb` — élasticité (~ −2,5) estimée via les promos, prix optimal = `coût × E/(E+1)`.
- **4.3** `03_MODELES/recommandation/4.3_recommandation.ipynb` — similarité cosinus (produits similaires + achetés ensemble).
- **4.4** `03_MODELES/evaluation/4.4_synthese_evaluation.ipynb` — synthèse / scorecard.

> 📝 *Résultat reco assumé* : sur ce jeu synthétique, la popularité est une baseline très forte ;
> le modèle personnalisé la rejoint. La valeur réelle (personnalisation, diversité) se valide par **A/B test** en production.

---

## ⚙️ MLOps & mise en production (Partie 5)

- **MLflow** — suivi des expériences (`04_PRODUCTION/mlops/`). Les 3 approches de prévision sont enregistrées et comparables dans l'UI MLflow.
- **API FastAPI + Docker** *(à venir)* — expose recommandations & prix dynamique.
- **Dashboard Dash** *(à venir)* — KPI décisionnels (marge, rotation stock, conversion, CLTV).

---

## 🧰 Stack technique

**Données** : Python, PySpark (batch), Kafka (streaming), Airflow (orchestration), DuckDB (warehouse), Parquet (data lake).
**Data science** : pandas, scikit-learn, Prophet, LightGBM, statsmodels.
**MLOps / prod** : MLflow, FastAPI, Docker *(à venir)*, Dash *(à venir)*.

---

## 🚀 Installation & exécution

```bash
# 1) Environnement virtuel (déjà présent : .venv)
python -m venv .venv
.venv\Scripts\activate            # Windows

# 2) Dépendances
pip install pandas numpy duckdb pyarrow scikit-learn matplotlib statsmodels lightgbm prophet mlflow jupyterlab

# 3) Notebooks des modèles (Partie 4)
#    Ouvrir 03_MODELES/**/*.ipynb dans VS Code / JupyterLab (noyau = .venv)

# 4) Suivi MLflow (Partie 5)
python 04_PRODUCTION/mlops/01_mlflow_forecasting.py
cd 04_PRODUCTION/mlops
mlflow ui --backend-store-uri sqlite:///mlflow.db     # http://127.0.0.1:5000
```

> ⚠️ **Spark** ne fonctionne que sous **WSL/Ubuntu** (Java 11 + PySpark 3.5.3), pas sous Windows.
> Lancer via `wsl` puis `spark-submit /mnt/d/PROJET_FINAL/...`.

---

## 📌 Statut du projet

- ✅ Parties 1 → 4 (cadrage, architecture, données, **3 modèles + synthèse**)
- 🔶 Partie 5 (MLOps MLflow ✅ ; API + dashboard à venir)
- ⬜ Partie 6 (business case, rapport, présentation)

---

*Projet académique — Master 2 Big Data, ISM. Données 100 % synthétiques.*
