# 📘 GUIDE — Partie Données (Partie 3)
**Projet Teranga Market — Gestion de Projet Data & E-Business (M2 Big Data, ISM)**

Ce guide explique, étape par étape, comment faire tourner **toute la partie données** du projet :
génération → ingestion → stockage → qualité → streaming → orchestration.

> ⚠️ **Règle d'or : lancez les scripts DANS L'ORDRE.** Chaque étape a besoin des fichiers produits par la précédente.

---

## 0. Prérequis (à installer une fois)

| Outil | Pourquoi | Vérifier avec |
|-------|----------|---------------|
| **Python 3.11+** | Générer les données, DuckDB, Kafka | `python --version` |
| **Docker Desktop** | Kafka (3.5) et Airflow (3.6) | `docker --version` |
| **WSL2 + Ubuntu** | Faire tourner **Spark** (voir §3) | `wsl -l -v` |
| **Java 11 (dans WSL)** | Requis par Spark | `wsl -- bash -lc "java -version"` |

> 🚨 **IMPORTANT — le chemin du projet ne doit contenir NI espaces NI caractères spéciaux** (`&`, accents…).
> Spark et Docker plantent sinon. Le projet doit être dans un chemin propre, ex : `D:\PROJET_FINAL`.
> ❌ `D:\MASTER BD-DS\...\Data & E-Business\...`  →  ✅ `D:\PROJET_FINAL`

---

## 1. Installer l'environnement Python (une fois)

Ouvrir **PowerShell** à la racine du projet :

```powershell
cd D:\PROJET_FINAL
python -m venv .venv
.venv\Scripts\Activate.ps1
```

> Si erreur « l'exécution de scripts est désactivée » :
> ```powershell
> Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
> ```

Installer les bibliothèques (dans le venv, sur Windows) :

```powershell
pip install pandas numpy duckdb pyarrow kafka-python-ng
```

> **Spark ne s'installe PAS ici** — il tourne dans WSL/Ubuntu (voir §3).

---

## 2. Génération des données (3.1)

Génère les 5 tables synthétiques (graine fixe = 42, donc tout le monde obtient les mêmes données).

```powershell
cd D:\PROJET_FINAL\02_DONNEES\generation
python 01_produits.py
python 02_clients.py
python 03_promotions.py
python 04_transactions.py
python 05_navigation.py
```

**Résultat** : 5 fichiers CSV dans `02_DONNEES\brut\` :
- `produits.csv` (500), `clients.csv` (10 000), `promotions.csv` (10),
- `transactions.csv` (100 000), `navigation.csv` (1 000 000)

---

## 3. Ingestion Spark (3.2) — ⚠️ sous WSL/Ubuntu

**Pourquoi WSL ?** Spark ne fonctionne pas bien sous Windows (Java 21, chemins, winutils…).
Il tourne parfaitement dans **Ubuntu/WSL** (Java 11 + pyspark 3.5.3).

### Préparer WSL (une fois)
```powershell
wsl -- bash -lc "java -version"     # doit afficher Java 11
wsl -- bash -lc "pip show pyspark"  # doit afficher pyspark 3.5.3
```
> Si pyspark absent dans WSL : `wsl` puis `pip install pyspark==3.5.3`

### Lancer l'ingestion Spark
```powershell
wsl
cd /mnt/d/PROJET_FINAL
spark-submit 02_DONNEES/ingestion/01_ingestion_spark.py
exit
```

**Résultat** : les données propres en **Parquet** dans `02_DONNEES\lake\` (5 dossiers).

> 💡 Sans Spark, une version légère existe : `python 02_DONNEES\ingestion\02_ingestion_pandas.py`
> (utilisée par Airflow — voir §7).

---

## 4. Data Warehouse DuckDB (3.3)

Charge le Parquet dans une base SQL requêtable (retour sous **Windows**, venv actif).

```powershell
cd D:\PROJET_FINAL
python 02_DONNEES\warehouse\01_charger_duckdb.py
```

**Résultat** : base `02_DONNEES\warehouse\teranga.duckdb` + affichage de requêtes de démo
(CA par catégorie, top produits, % de promos).

---

## 5. Contrôles qualité (3.4)

Lance 21 tests automatiques sur les données (clés, FK, valeurs, dates, entonnoir).

```powershell
python 02_DONNEES\qualite\01_controles_qualite.py
```

**Résultat attendu** : `RESULTAT : 21/21 tests reussis -- JEU DE DONNEES 100% VALIDE`

---

## 6. Streaming Kafka (3.5) — Docker

Simule un flux de ventes en temps réel (producteur → Kafka → consommateur).

### a) Démarrer Kafka
```powershell
cd D:\PROJET_FINAL\02_DONNEES\streaming
docker compose up -d
docker ps                # doit montrer "teranga-kafka" en Up
```

### b) Lancer le flux (⚠️ DEUX terminaux, venv actif dans les deux)

**Terminal 1 — le consommateur (écoute) :**
```powershell
cd D:\PROJET_FINAL\02_DONNEES\streaming
python consumer_transactions.py
```

**Terminal 2 — le producteur (envoie) :**
```powershell
cd D:\PROJET_FINAL\02_DONNEES\streaming
python producer_transactions.py
```

→ Dans le Terminal 1, les ventes défilent en direct avec le **CA cumulé**.

### c) Arrêter Kafka (quand fini)
```powershell
cd D:\PROJET_FINAL\02_DONNEES\streaming
docker compose down
```

---

## 7. Orchestration Airflow (3.6) — Docker

Airflow enchaîne tout le pipeline automatiquement, avec une interface web.

> 💡 Arrêtez Kafka avant (pour libérer de la RAM).

### a) Démarrer Airflow
```powershell
cd D:\PROJET_FINAL\02_DONNEES\orchestration
docker compose up -d
```
> ⏳ **1re fois = 3 à 6 min** (téléchargement des images + installation des libs dans le conteneur).

```powershell
docker ps    # doit montrer : teranga-airflow-web, -scheduler, -db en Up
```

### b) Ouvrir l'interface
- Navigateur : **http://localhost:8080**
- Identifiants : **admin** / **admin**
- (Si la page ne charge pas : attendre 1-2 min de plus.)

### c) Lancer le pipeline
1. Trouver le DAG **`pipeline_teranga`**
2. L'activer avec l'interrupteur (toggle **ON**)
3. Cliquer sur son nom → bouton **▶ (Trigger DAG)**
4. Onglet **Graph** → les 4 tâches passent au vert :
   `1_generation → 2_ingestion_parquet → 3_warehouse_duckdb → 4_controle_qualite`
5. Cliquer une tâche → **Logs** pour voir le détail (ex. « 21/21 tests réussis »)

### d) Arrêter Airflow (quand fini)
```powershell
cd D:\PROJET_FINAL\02_DONNEES\orchestration
docker compose down
```

---

## 8. 🛠️ Dépannage (problèmes rencontrés)

| Problème | Cause | Solution |
|----------|-------|----------|
| `'D:\MASTER' n'est pas reconnu` (Spark) | Espaces / `&` dans le chemin | Mettre le projet dans `D:\PROJET_FINAL` |
| `JAVA_GATEWAY_EXITED` / `loopback connection` (Spark) | Java 21 sous Windows | Lancer Spark **dans WSL** (Java 11) |
| `No such file` en lançant un script | Mauvais ordre / fichier manquant | Relancer depuis l'étape 2, dans l'ordre |
| `ModuleNotFoundError: pandas` | venv non activé | `.venv\Scripts\Activate.ps1` |
| Page Airflow ne charge pas | Libs encore en installation | Attendre 2-4 min et rafraîchir |
| Docker : « daemon not running » | Docker Desktop éteint | Lancer Docker Desktop, attendre la baleine 🐳 |

---

## 9. 🔁 Récapitulatif — l'ordre complet

```
1. (une fois)  venv + pip install
2. generation/     01 → 02 → 03 → 04 → 05        (Windows)
3. ingestion/      spark-submit 01_ingestion...  (WSL)
4. warehouse/      01_charger_duckdb.py          (Windows)
5. qualite/        01_controles_qualite.py       (Windows)
6. streaming/      docker compose up + producer/consumer
7. orchestration/  docker compose up + interface web
```

> Pour tout relancer proprement : suivre l'ordre ci-dessus. Grâce à la graine fixe (42),
> les données seront **identiques** pour tous les membres de l'équipe.

---

## 📂 Structure du dossier `02_DONNEES`

```
02_DONNEES/
├── generation/     Scripts qui génèrent les données (5 fichiers)
├── brut/           CSV bruts (générés)
├── ingestion/      01 = Spark (WSL) · 02 = pandas (léger)
├── lake/           Parquet (Data Lake)
├── warehouse/      Chargement DuckDB + base teranga.duckdb
├── qualite/        Contrôles qualité
├── streaming/      Kafka (docker-compose + producer + consumer)
├── orchestration/  Airflow (docker-compose + dags/)
├── Dictionnaire_des_donnees.docx
└── GUIDE_PARTIE_DONNEES.md   ← ce fichier
```
