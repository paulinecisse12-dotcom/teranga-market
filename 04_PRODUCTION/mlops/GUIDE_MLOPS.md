# 📘 Guide — MLOps & CI/CD

> Guide d'équipe pour la partie **MLOps léger** du projet **Teranga Market**.
> Répond à l'objectif du sujet : *« Déploiement et MLOps léger (CI/CD, monitoring modèles) »*.
> Fait partie du critère **« Intégration & déploiement » (15 %)**.

---

## 1. Ce qu'on a mis en place (3 briques)

| Brique | Outil | À quoi ça sert |
|---|---|---|
| **Suivi des modèles** | MLflow | Logger les paramètres/métriques de chaque modèle, comparer les versions |
| **Monitoring** | script + PSI | Détecter si les nouvelles données s'éloignent des données d'entraînement (*data drift*) |
| **CI/CD** | GitHub Actions + pytest | Lancer automatiquement lint + tests à chaque `push` |

---

## 2. Où sont les fichiers

```
04_PRODUCTION/mlops/
├── 01_mlflow_forecasting.py     Suivi MLflow du modèle de prévision (3 runs comparés)
├── 02_mlflow_pricing_reco.py    Suivi MLflow des modèles prix + reco
├── 03_monitoring.py             Détection de dérive (PSI) + rapport
├── mlflow.db                    Base de suivi MLflow (SQLite)  [ignoré par Git]
└── monitoring_rapport.csv       Dernier rapport de monitoring

tests/test_fonctions.py          7 tests unitaires (métriques, prix, PSI)
.github/workflows/ci.yml         Le workflow CI (GitHub Actions)
requirements.txt                 Dépendances du projet
```

---

## 3. MLflow — suivi des modèles 🎛️

**Lancer les runs** (crée/complète le suivi) :
```bash
python 04_PRODUCTION/mlops/01_mlflow_forecasting.py
python 04_PRODUCTION/mlops/02_mlflow_pricing_reco.py
```

**Ouvrir l'interface** :
```bash
cd 04_PRODUCTION/mlops
mlflow ui --backend-store-uri sqlite:///mlflow.db
```
→ ouvrir **http://127.0.0.1:5000** (l'arrêter avec `Ctrl+C`).

**3 expériences** visibles : `teranga-forecasting`, `teranga-pricing`, `teranga-recommandation`.
En soutenance : sélectionner « Model training » → une expérience → cocher les runs → **Compare** (graphe des métriques).

> ⚠️ MLflow 3 : le stockage fichier est déprécié → on utilise **sqlite** (`sqlite:///mlflow.db`).
> Les noms de métriques ne peuvent pas contenir `%` → on écrit `_pct`.

---

## 4. Monitoring — dérive des données 📉

**Lancer** :
```bash
python 04_PRODUCTION/mlops/03_monitoring.py
```

**Ce qu'il fait** : compare une période de **référence** (9 premiers mois) aux **3 derniers mois** et calcule le
**PSI** (Population Stability Index) sur 3 indicateurs.

| PSI | Interprétation |
|---|---|
| < 0,10 | stable (OK) |
| 0,10 – 0,25 | dérive modérée (surveiller) |
| > 0,25 | dérive importante (**ré-entraîner**) |

**Résultat obtenu** : la **demande** a fortement dérivé (PSI ≈ 4,5 → *ré-entraîner*), car le business grandit ;
le **prix** et le **mix catégories** sont stables. → Message : *le modèle de prévision doit être ré-entraîné périodiquement*.

---

## 5. CI/CD — GitHub Actions ⚙️

**Principe** : à chaque `push` sur `main`, GitHub exécute automatiquement le workflow `.github/workflows/ci.yml` :
1. installe Python + les dépendances de test,
2. lance un **lint** (ruff, informatif),
3. lance les **tests** (`pytest tests/`).

**Où le voir** : onglet **Actions** du dépôt GitHub → workflow **« CI »** (pastille verte = tout passe ✅).

**Dépôt** : https://github.com/paulinecisse12-dotcom/teranga-market

**Relancer les tests en local** :
```bash
pytest tests/ -q
```

---

## 6. 🎤 Comment le présenter au jury

- **MLflow** : « On trace chaque modèle (params + métriques) dans MLflow. On compare les versions d'un coup d'œil — ex. Prophet+promo bat la baseline. »
- **Monitoring** : « On surveille la dérive des données avec le PSI. Ici, la demande dérive → le système alerte qu'il faut ré-entraîner. »
- **CI/CD** : « Le projet est sous Git ; à chaque push, GitHub lance nos tests automatiquement (onglet Actions). »

---

## 7. Cheat sheet des commandes

```bash
# MLflow : créer les runs puis ouvrir l'UI
python 04_PRODUCTION/mlops/01_mlflow_forecasting.py
python 04_PRODUCTION/mlops/02_mlflow_pricing_reco.py
cd 04_PRODUCTION/mlops && mlflow ui --backend-store-uri sqlite:///mlflow.db   # Ctrl+C pour arrêter

# Monitoring
python 04_PRODUCTION/mlops/03_monitoring.py

# Tests (comme le CI)
pytest tests/ -q
```

---

*Guide MLOps — Teranga Market. Voir aussi les guides Données (`02_DONNEES`) et Modèles (`03_MODELES`).*
