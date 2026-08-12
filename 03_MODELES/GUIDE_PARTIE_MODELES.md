# 📘 Guide — Partie 4 : Les Modèles

> Guide d'équipe pour comprendre, exécuter et **présenter** la partie modèles du projet **Teranga Market**.
> Partie 4 = **25 % de la note** (« Modèles & validation »).

---

## 1. Ce qu'on a construit

**3 modèles** de data science, chacun **évalué contre une baseline** (le minimum à battre), plus une **synthèse**.

| # | Modèle | Question à laquelle il répond |
|---|---|---|
| 4.1 | **Prévision de la demande** | Combien va-t-on vendre demain / le mois prochain ? (→ stock) |
| 4.2 | **Optimisation des prix** | À quel prix vendre pour maximiser la marge ? |
| 4.3 | **Recommandation** | Quels produits suggérer à chaque client ? (→ cross-sell) |
| 4.4 | **Synthèse** | Récapitulatif des résultats des 3 modèles |

Chaque modèle est un **notebook Jupyter** (`.ipynb`) — format demandé par le sujet (« notebooks reproductibles »).

---

## 2. Où sont les fichiers

```
03_MODELES/
├── forecasting/      4.1_prevision_demande.ipynb
├── pricing/          4.2_optimisation_prix.ipynb
├── recommandation/   4.3_recommandation.ipynb
└── evaluation/       4.4_synthese_evaluation.ipynb   + les métriques (.csv)
```

Les résultats chiffrés (livrables) sont dans `03_MODELES/evaluation/` :
`metriques_forecasting.csv`, `metriques_pricing.csv`, `metriques_recommandation.csv`, `synthese_scorecard.csv`.

---

## 3. Comment lancer les notebooks

**Prérequis** : l'environnement `.venv` à la racine du projet, avec les bibliothèques installées
(`prophet`, `scikit-learn`, `duckdb`, `matplotlib`, `pandas`…).

1. Ouvrir le notebook dans **VS Code** (ou JupyterLab).
2. En haut à droite, choisir le **noyau** = **`.venv (Python 3.13)`**.
3. **Run All** (ou `Maj+Entrée` cellule par cellule pour bien suivre).

> ⏱️ Les cellules Prophet (notebook 4.1) prennent ~1-2 min : c'est normal, il entraîne 7 modèles.
> Toutes les données viennent de l'entrepôt `02_DONNEES/warehouse/teranga.duckdb`.

---

## 4. Les modèles en détail

### 4.1 — Prévision de la demande 📈
- **Données** : demande **quotidienne par catégorie** (7 séries), sur 12 mois.
- **Méthode** : modèle de séries temporelles **Prophet** (tendance + saisonnalité), enrichi du **calendrier des promotions** comme variable explicative.
- **Baseline** : prévision naïve (« demain = même jour la semaine dernière »).
- **Résultat** : MAE moyen **66 → 43,5 → 37,3** (baseline → Prophet → Prophet+promo) = **−43 % d'erreur**.
- **Graphique business** : le notebook affiche aussi le **chiffre d'affaires (CA) par mois** et le **CA quotidien avec les périodes de promotion surlignées** → on voit clairement les **pics de CA pendant les promos** (**+~87 % de CA/jour**), ce qui confirme la cohérence des données.
- **À retenir** : intégrer une connaissance métier (les promos) améliore nettement la prévision.

### 4.2 — Optimisation des prix 💰
- **Idée** : mesurer l'**élasticité-prix** (quand le prix baisse de 1 %, de combien les ventes montent ?).
- **Astuce** : on l'estime grâce aux **promotions** = de vraies baisses de prix observées (expérimentation naturelle).
- **Résultat** : élasticité ≈ **−2,5** (demande élastique). On maximise la **marge** → prix optimal = `coût × E/(E+1)`.
  Recommandation : **+~13 % de prix** → **+~4 % de marge**.
- **À retenir** : on maximise la **marge**, pas le chiffre d'affaires (sinon le prix optimal tendrait vers 0).

### 4.3 — Recommandation 🛒
- **Méthode hybride** : **content-based** (produits similaires : catégorie, marque, prix) + **collaboratif** (« les clients qui ont acheté X ont aussi acheté Y »), via **similarité cosinus**.
- **Baselines** : le **hasard** (~1 %) et les **produits populaires** (~7 %).
- **Résultat** : le collaboratif fait **~7× mieux que le hasard**, et **égale** la baseline populaire.
- **À retenir (important)** : la popularité est une baseline connue pour être très forte. Notre modèle la rejoint ;
  la vraie valeur d'un recommandeur (personnalisation, diversité, cross-sell) se mesure en production via un **test A/B**.

### 4.4 — Synthèse ✅
Regroupe les 3 tableaux en un **scorecard** : *modèle / métrique / baseline / notre modèle / résultat*.

---

## 5. 🏆 Le scorecard (à montrer en soutenance)

| Modèle | Métrique | Baseline | Notre modèle | Résultat |
|---|---|---|---|---|
| Prévision demande | MAE | 66 (naïf) | 37 (Prophet+promo) | **−43 % d'erreur** |
| Optimisation prix | Marge | prix actuels | +14 % de prix | **+3,8 % de marge** |
| Recommandation | Recall@5 | 1 % (hasard) | 6,8 % (collaboratif) | **~7× le hasard** |

---

## 6. 🎤 Comment le présenter au jury (points clés)

- **Prévision** : « On prévoit la demande par catégorie avec Prophet. En ajoutant le calendrier des promos, on réduit l'erreur de 43 % par rapport à une prévision naïve. »
- **Prix** : « On mesure l'élasticité grâce aux promotions, puis on calcule le prix qui maximise la marge. Le modèle montre qu'on est légèrement sous-tarifé (+13 % possible). »
- **Reco** : « Reco hybride content + collaboratif. On est ~7× meilleur que le hasard. La popularité est une baseline forte qu'on égale ; la vraie valeur se valide par A/B test. »
- **Honnêteté = maturité** : assumer que la popularité est dure à battre est **mieux vu** qu'un modèle "magique" qui bat tout (le jury se méfierait).

---

## 7. ⚠️ Limites à mentionner (montre de la rigueur)

- **Élasticité** : les promos tombent souvent en période de forte demande → une partie de la hausse est saisonnière (élasticité légèrement surestimée).
- **Recommandation** : sur des données **synthétiques**, le signal comportemental est limité ; un vrai jeu de données ferait mieux ressortir la personnalisation.
- **Promotions** : toutes les promos sont modélisées comme **efficaces** (elles boostent le CA). Nos données ne contiennent pas de promo « ratée » qui ferait baisser le CA ; en montrer une nécessiterait de régénérer le dataset. À la place, on peut souligner que **certaines campagnes rapportent plus que d'autres**.
- **Validation finale** : en production, via **A/B testing** (taux de clic, panier moyen, marge réelle).

---

## 8. Répartition des données (rappel)

500 produits · 10 000 clients · 100 000 transactions · 1 000 000 événements de navigation · 12 mois (juil. 2025 → juin 2026) · données 100 % synthétiques (graine = 42, reproductible).

---

*Guide Partie 4 — Teranga Market. Voir aussi `02_DONNEES/GUIDE_PARTIE_DONNEES.md` pour la partie données.*
