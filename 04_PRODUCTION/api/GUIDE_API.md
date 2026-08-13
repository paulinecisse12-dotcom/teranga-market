# 📗 Guide — API & Docker

> Guide d'équipe pour la partie **5.1 Mise en production — API** du projet **Teranga Market**.
> Répond à l'objectif du sujet : *« exposer les modèles via un microservice déployable »*.
> Fait partie du critère **« Intégration & déploiement » (15 %)**.

---

## 1. À quoi ça sert (en une image 🍽️)

Nos 3 modèles (prix, reco, produits similaires) vivaient dans des **notebooks** — donc inutilisables par une appli.
L'**API** est un **serveur** qui rend ces modèles interrogeables par n'importe qui (site web, dashboard, mobile) :
on pose une question → l'API répond en JSON, en **~3 millisecondes**.

> Principe clé : on **entraîne les modèles une seule fois** (notebooks Partie 4), on **sauvegarde les résultats**
> (les *artefacts*), et l'API ne fait que **servir** ces résultats — vite, sans jamais réapprendre.

---

## 2. Où sont les fichiers

```
04_PRODUCTION/api/
├── export_modeles.py     Génère les artefacts depuis le warehouse DuckDB (à lancer 1 fois)
├── main.py               L'API FastAPI (5 endpoints)
├── requirements.txt      Dépendances légères (fastapi, uvicorn, pandas, numpy, joblib)
├── Dockerfile            Recette de l'image Docker
├── docker-compose.yml    Lancement en 1 commande
├── .dockerignore         Fichiers exclus de l'image
└── artefacts/            Résultats pré-calculés chargés au démarrage
    ├── pricing.csv        prix_actuel, coût, élasticité, prix_optimal (par produit)
    ├── reco.npz           matrices de similarité (collaboratif + content) + ids
    └── reco_meta.joblib   noms produits, historique d'achat par client, top populaires
```

---

## 3. Ce que l'API expose (5 endpoints)

| Endpoint | Question posée | Modèle derrière |
|---|---|---|
| `GET /` | « L'API va bien ? » (état + nb produits/clients) | — |
| `GET /prix/{id_produit}` | « Prix optimal de ce produit ? » (+ élasticité) | Pricing (4.2) |
| `GET /recommander/{id_client}` | « Quels produits recommander à ce client ? » | Reco hybride (4.3) |
| `GET /client/{id_client}/historique` | « Qu'a acheté ce client ? » | — (données) |
| `GET /produit/{id_produit}/similaires` | « Produits qui ressemblent à celui-ci ? » (*vous aimerez aussi*) | Reco content (4.3) |

**Exemple de réponse** (`/prix/1`) :
```json
{ "id_produit": 1, "nom": "Samsung Galaxy Tab A9 128 Go",
  "prix_actuel": 373500, "prix_optimal": 461843,
  "elasticite": -2.619, "variation_pct": 23.7 }
```

> Client inconnu (sans achat) → l'endpoint reco bascule automatiquement sur les **best-sellers** (*cold start*).

---

## 4. Lancer l'API en local (sans Docker) 🖥️

```bash
cd 04_PRODUCTION/api
python export_modeles.py          # 1 fois : (re)génère artefacts/  (a besoin du warehouse DuckDB)
uvicorn main:app --reload         # démarre l'API  (Ctrl+C pour arrêter)
```
→ ouvrir la **doc interactive** : **http://127.0.0.1:8000/docs**
Chaque endpoint se teste au clic : `Try it out` → saisir un id → `Execute` → réponse sous *Server response*.

> `--reload` = l'API se recharge toute seule à chaque modification de `main.py`.

---

## 5. Lancer l'API avec Docker 🐳

Docker emballe l'API **+ toutes ses dépendances** dans un conteneur qui tourne **à l'identique sur n'importe quelle
machine** — fini le *« ça marche chez moi mais pas chez toi »*. C'est ce que demande le critère déploiement.

**Prérequis** : Docker Desktop installé + le dossier `artefacts/` présent.

```bash
cd 04_PRODUCTION/api
docker compose up --build         # construit l'image puis démarre  (Ctrl+C pour arrêter)
```
→ même adresse : **http://127.0.0.1:8000/docs** (identique à la version locale — c'est normal !).

| Commande | Effet |
|---|---|
| `docker compose up --build` | Construit l'image et lance le conteneur |
| `docker compose up -d` | Idem, mais en arrière-plan |
| `docker compose down` | Arrête et supprime le conteneur |

---

## 6. 🎤 Comment le présenter au jury

- **API** : « Nos 3 modèles sont exposés via un microservice **FastAPI**. On teste chaque endpoint en direct dans la
  doc Swagger (`/docs`). L'API ne réentraîne rien : elle sert des **artefacts pré-calculés**, d'où une réponse en ~3 ms. »
- **Docker** : « L'API est **conteneurisée** : `docker compose up` la lance à l'identique sur n'importe quelle machine.
  Ça garantit la reproductibilité du déploiement. »
- **Cold start** : « Pour un client inconnu, l'API bascule sur les best-sellers — un vrai système gère ce cas. »

---

## 7. Cheat sheet des commandes

```bash
# Générer les artefacts (1 fois, ou après ré-entraînement des modèles)
cd 04_PRODUCTION/api && python export_modeles.py

# Lancer en local
uvicorn main:app --reload            # http://127.0.0.1:8000/docs

# Lancer avec Docker
docker compose up --build            # http://127.0.0.1:8000/docs
docker compose down                  # arrêter
```

---

*Guide API — Teranga Market. Voir aussi le guide MLOps (`04_PRODUCTION/mlops/GUIDE_MLOPS.md`), Données (`02_DONNEES`) et Modèles (`03_MODELES`).*
