# 📊 Guide — Dashboard (Cockpit Décisionnel)

> Guide d'équipe pour la partie **5.2 Mise en production — Dashboard** du projet **Teranga Market**.
> Répond à l'objectif du sujet : *« restituer les modèles et les KPI dans un tableau de bord décisionnel »*.
> Contribue aux critères **Business case / KPI (15 %)** et **Intégration & déploiement (15 %)**.

---

## 1. À quoi ça sert (l'angle « cockpit »)

La plupart des dashboards se contentent de **montrer le passé** (« voici le CA »). Le nôtre est un **cockpit
décisionnel** : il montre **quelles décisions prendre et combien ça rapporte**, en branchant directement nos
**3 modèles** (prix, prévision, reco), notre **API** et notre **MLOps**.

**L'analogie 🚗 :** le tableau de bord d'une voiture — on ne regarde pas le moteur, on lit les cadrans et les alertes.

---

## 2. Où sont les fichiers

```
04_PRODUCTION/dashboard/
├── app.py                 L'application Dash (layout + callbacks)
├── export_forecast.py     Génère les prévisions Prophet (à lancer 1 fois -> forecast.csv)
├── forecast.csv           Prévisions pré-calculées (lues par le dashboard)
└── assets/                Chargé automatiquement par Dash
    ├── custom.css          Thème Teranga (curseur, menu, sidebar)
    ├── logo.png            Logo Teranga Market (sidebar)
    ├── fa/                 Icônes Font Awesome (en local -> marche hors-ligne)
    └── topojson/           Fond de carte Afrique (en local -> carte hors-ligne)
```

---

## 3. Ce que le dashboard affiche (11 sections)

| # | Section | Ce qu'elle montre | Source |
|---|---|---|---|
| 1 | **Indicateurs (KPI)** | 7 cadrans : CA, marge, clients actifs, panier moyen, taux de conversion, rotation de stock, CLTV | Warehouse DuckDB |
| 2 | **Santé des modèles** | Voyants de dérive (PSI) — alerte de ré-entraînement | Monitoring MLOps |
| 3 | **Opportunités de prix** | Top produits à re-tarifer + gain de marge (+629 M/an) | Modèle pricing (4.2) |
| 4 | **Simulateur « et si… »** | Curseur de prix → marge recalculée en direct | Élasticité (4.2) |
| 5 | **Remise par segment** | Remise conseillée par type de client (règle métier CRM) | Segments + valeur client |
| 6 | **Chiffre d'affaires** | CA par mois + par catégorie | Warehouse DuckDB |
| 7 | **Prévision de la demande** | Demande réelle + prévision 30 j par catégorie | Modèle Prophet (4.1) |
| 8 | **Couverture de stock** | Jours de couverture par catégorie → rupture / sain / surstock | Prophet (4.1) + stock |
| 9 | **Impact des promotions** | CA/jour ×1,9 les jours de promo | Warehouse DuckDB |
| 10 | **Carte du Sénégal** | CA par ville (bulles) | Warehouse DuckDB |
| 11 | **Reco en direct** | Recommandations d'un client via l'**API** | API FastAPI (port 8000) |

> Le **menu latéral** (sidebar) permet de sauter directement à une section d'un clic.

### Les 7 indicateurs du bandeau

Les 4 premiers sont directs (CA, marge, clients actifs, panier moyen). Les **3 derniers** reprennent les KPI
attendus par le sujet (*rotation stock, taux de conversion, CLTV*) et sont chacun branchés sur un objectif SMART :

| KPI | Formule | Valeur | Objectif servi |
|---|---|---|---|
| **Taux de conversion** | achats ÷ vues produit | 14,3 % (vue → achat) | O3 — +15 % de conversion |
| **Rotation de stock** | unités vendues ÷ stock total | 1,9× / 12 mois | O2 — −20 % de ruptures |
| **CLTV** (marge nette / client) | marge totale ÷ clients actifs | 899 792 FCFA | O4 — −10 % de churn |

> *Nuance assumée : la CLTV est une version simplifiée (marge moyenne sur 12 mois, pas une projection) ;
> la conversion est calculée au niveau « vue produit » car le dataset trace les vues de produits.*

---

## 4. Lancer le dashboard

**Prérequis (une fois) :**
```bash
pip install dash plotly
cd 04_PRODUCTION/dashboard
python export_forecast.py          # génère forecast.csv (Prophet, ~1 min)
```

**Lancer (à chaque session) :** le dashboard a besoin de l'**API en parallèle** pour la section reco.
Il faut donc **2 terminaux** :

```bash
# Terminal 1 — l'API (port 8000)
cd 04_PRODUCTION/api
uvicorn main:app --reload

# Terminal 2 — le dashboard (port 8050)
cd 04_PRODUCTION/dashboard
python app.py
```
→ ouvrir **http://127.0.0.1:8050**  (arrêter avec `Ctrl+C` dans chaque terminal).

> Si la section « Reco en direct » affiche « API injoignable », c'est que l'API (terminal 1) n'est pas lancée.

---

## 5. Comment ça marche (technique)

- **Dash = LEGO** : la page est construite avec des blocs Python (`html.Div`, `dcc.Graph`, `dcc.Slider`…).
- **Les KPI et graphiques** sont calculés **une seule fois au démarrage** (le passé ne change pas).
- **Les parties interactives** utilisent des **callbacks** (« quand l'utilisateur touche X, recalcule Y ») :
  le simulateur, le menu de prévision, et le bouton de reco.
- **La reco** appelle l'API en HTTP avec `requests` — le dashboard est un **client** de l'API.
- **Hors-ligne** : les icônes (Font Awesome) et le fond de carte (topojson) sont **téléchargés en local**
  dans `assets/` → tout s'affiche sans internet le jour de la soutenance.

---

## 6. Charte & personnalisation

Couleurs de marque définies en haut de `app.py` (section « Charte graphique ») :
- **Navy** `#003B7A` · **Orange** `#FF7A00`

Changer une couleur là-bas la met à jour **partout**. Le thème des composants Dash
(curseur, menu, sidebar) est dans `assets/custom.css`.

> ⚠️ Dash 4.x : le curseur utilise les classes CSS `.dash-slider-*` (et non `.rc-slider-*`).

---

## 7. 🎤 Comment le présenter au jury

- **Cockpit** : « Notre dashboard ne montre pas que le passé — il propose des **décisions** chiffrées
  (prix à ajuster, remises par segment) et **surveille nos modèles**. »
- **Simulateur** : « On fait varier un prix en direct et on voit la marge évoluer — le jury peut jouer avec. »
- **Santé des modèles** : « Le voyant rouge signale que la demande a dérivé → il faut ré-entraîner. C'est le
  MLOps rendu visible. »
- **KPI branchés aux objectifs** : « Nos 3 KPI de pilotage (conversion, rotation de stock, CLTV) ne sont pas
  décoratifs — chacun répond à un **objectif SMART** du cahier des charges (O3, O2, O4) et déclenche une action. »
- **Couverture de stock** : « On croise la prévision de demande (Prophet) avec le stock → on repère les
  catégories en **surstock** (argent immobilisé) et celles à **risque de rupture**. C'est l'objectif O2
  (réduire les ruptures) rendu concret : *prévoir la demande **pour anticiper les stocks***. »
- **Bout-en-bout** : « La section reco appelle notre **API** en temps réel : toute la chaîne fonctionne. »

---

## 8. Cheat sheet des commandes

```bash
# Préparer (une fois)
pip install dash plotly
python export_forecast.py                       # -> forecast.csv

# Lancer (2 terminaux)
cd 04_PRODUCTION/api && uvicorn main:app --reload        # API  : http://127.0.0.1:8000
cd 04_PRODUCTION/dashboard && python app.py              # Dash : http://127.0.0.1:8050
```

---

*Guide Dashboard — Teranga Market. Voir aussi les guides API (`04_PRODUCTION/api/GUIDE_API.md`),
MLOps (`04_PRODUCTION/mlops/GUIDE_MLOPS.md`), Données (`02_DONNEES`) et Modèles (`03_MODELES`).*
