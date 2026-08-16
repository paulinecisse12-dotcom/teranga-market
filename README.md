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
| `04_PRODUCTION/` | MLOps (MLflow), API (FastAPI + Docker), dashboard (Dash) | ✅ |
| `05_LIVRABLES/` | Business case, rapport final, présentation | ✅ |

---

## 📊 Jeu de données (synthétique, reproductible — graine = 42)

| Table | Volume | Description |
|---|---|---|
| `produits` | 500 | 7 catégories, marque, prix catalogue, coût, stock |
| `clients` | 10 000 | profils clients |
| `transactions` | 100 000 | ventes sur **12 mois** (juil. 2025 → juin 2026) — table de faits |
| `navigation` | 1 000 000 | événements web (vue, clic, ajout panier) |
| `promotions` | 10 | 9 campagnes datées (Black Friday, Tabaski, Korité…) + 1 ligne « Aucune promotion » |

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

## ⚙️ Mise en production (Partie 5) — ✅

- **MLOps** (`04_PRODUCTION/mlops/`) — suivi des expériences (MLflow), monitoring de dérive (PSI), CI/CD (GitHub Actions). → `GUIDE_MLOPS.md`
- **API FastAPI + Docker** (`04_PRODUCTION/api/`) — expose prix optimal, recommandations et produits similaires. → `GUIDE_API.md`
- **Dashboard Dash** (`04_PRODUCTION/dashboard/`) — **Cockpit Décisionnel** (11 sections) : KPI (CA, marge, conversion, rotation de stock, CLTV…), santé des modèles (PSI), opportunités de prix, simulateur interactif, remises par segment, chiffre d'affaires, prévision, **couverture de stock**, impact des promotions, carte du Sénégal, et reco en direct (branchée sur l'API). → `GUIDE_DASHBOARD.md`

---

## 🧰 Stack technique

**Données** : Python, PySpark (batch), Kafka (streaming), Airflow (orchestration), DuckDB (warehouse), Parquet (data lake).
**Data science** : pandas, scikit-learn, Prophet, LightGBM, statsmodels.
**MLOps / prod** : MLflow, FastAPI, Docker, Dash, Plotly, requests.

---

## 🚀 Installation & exécution

**Prérequis :** Python 3.11+ et Git installés.

```bash
# 1) Cloner le projet (code + données inclus)
git clone https://github.com/paulinecisse12-dotcom/teranga-market.git
cd teranga-market

# 2) Environnement virtuel
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # Mac / Linux

# 3) Dépendances (tout le projet)
pip install -r requirements.txt
```

### Lancer le Cockpit (dashboard + API)

Le dashboard a besoin de l'API pour la section « reco en direct » → **2 terminaux** :

```bash
# Terminal 1 — API (port 8000) · doc interactive (Swagger) : http://127.0.0.1:8000/docs
cd 04_PRODUCTION/api && uvicorn main:app --reload

# Terminal 2 — Dashboard (port 8050)
cd 04_PRODUCTION/dashboard && python app.py
```
→ ouvrir **http://127.0.0.1:8050** · guide détaillé : `04_PRODUCTION/dashboard/GUIDE_DASHBOARD.md`

> ✅ Les **données** (warehouse DuckDB) et les **prévisions** (`forecast.csv`) sont dans le dépôt : rien à régénérer.
> Les icônes et le fond de carte sont en local → le dashboard marche **hors-ligne**.

### Autres briques

```bash
# Notebooks des modèles (Partie 4) — JupyterLab (ou ouvrir 03_MODELES/**/*.ipynb dans VS Code, noyau = .venv)
jupyter lab                                                                  # http://localhost:8888/lab

# Suivi MLflow (Partie 5)
cd 04_PRODUCTION/mlops && mlflow ui --backend-store-uri sqlite:///mlflow.db   # http://127.0.0.1:5000

# Orchestration Airflow (Partie 3) — nécessite Docker Desktop lancé
cd 02_DONNEES/orchestration && docker compose up                             # http://localhost:8080  (admin / admin)
```

> ⚠️ **Spark** ne fonctionne que sous **WSL/Ubuntu** (Java 11 + PySpark 3.5.3), pas sous Windows.
> Il n'est nécessaire que pour **régénérer** les données ; le warehouse fourni suffit pour tout lancer.

---

## 📌 Statut du projet

- ✅ Parties 1 → 4 (cadrage, architecture, données, **3 modèles + synthèse**)
- ✅ Partie 5 (MLOps + **API FastAPI/Docker** + **Dashboard Cockpit Décisionnel**)
- ✅ Partie 6 (business case, rapport final, présentation)

---

*Projet académique — Master 2 Big Data, ISM. Données 100 % synthétiques.*
