"""
============================================================================
 5.2 DASHBOARD — Cockpit Décisionnel Teranga Market  (Dash + Plotly)
============================================================================
ÉTAPE 1 : squelette de la page + bandeau KPI (4 cadrans).
Les briques suivantes (opportunités de prix, simulateur, reco) viendront après.

Lancer (depuis 04_PRODUCTION/dashboard) :
    python app.py
Puis ouvrir dans le navigateur :  http://127.0.0.1:8050
============================================================================
"""
import os
from pathlib import Path
import duckdb
import pandas as pd
import requests
import plotly.graph_objects as go
from dash import Dash, html, dcc, Input, Output, State

# Adresse de l'API (doit tourner en parallèle : uvicorn main:app --reload)
API_URL = os.environ.get("API_URL", "http://127.0.0.1:8000")
if API_URL and not API_URL.startswith("http"):
    API_URL = "https://" + API_URL

# --- 1) Connexion aux données (warehouse DuckDB) ----------------------------
ICI = Path(__file__).resolve().parent            # .../04_PRODUCTION/dashboard
DB = ICI.parents[1] / "02_DONNEES" / "warehouse" / "teranga.duckdb"

def charger_kpis():
    """Calcule les indicateurs clés une seule fois au démarrage."""
    con = duckdb.connect(str(DB), read_only=True)
    ca, marge, nb_clients, nb_cmd, unites = con.execute("""
        SELECT SUM(t.quantite * t.prix_unitaire),
               SUM(t.quantite * (t.prix_unitaire - p.cout_unitaire)),
               COUNT(DISTINCT t.id_client),
               COUNT(DISTINCT t.id_transaction),
               SUM(t.quantite)
        FROM transactions t JOIN produits p ON t.id_produit = p.id_produit
    """).fetchone()
    vues  = con.execute("SELECT COUNT(*) FROM navigation WHERE action = 'vue'").fetchone()[0]
    stock = con.execute("SELECT SUM(stock) FROM produits").fetchone()[0]
    con.close()
    return {
        "ca": ca,
        "marge": marge,
        "taux_marge": marge / ca * 100,
        "clients": nb_clients,
        "panier": ca / nb_cmd,
        "conversion": nb_cmd / vues * 100,   # entonnoir vue -> achat
        "rotation": unites / stock,          # nb de fois que le stock tourne sur 12 mois
        "cltv": marge / nb_clients,          # marge nette moyenne par client
    }

KPIS = charger_kpis()

# --- Opportunités de prix : gain de marge estimé par produit ----------------
PRICING = ICI.parents[0] / "api" / "artefacts" / "pricing.csv"

def charger_opportunites(top_n=5):
    """Croise prix optimal (modèle 4.2) et quantités vendues -> gain de marge."""
    con = duckdb.connect(str(DB), read_only=True)
    qte = con.execute("SELECT id_produit, SUM(quantite) qte FROM transactions GROUP BY 1").fetchdf()
    con.close()
    df = pd.read_csv(PRICING).merge(qte, on="id_produit")
    # la demande baisse quand le prix monte : qte_new = qte * (popt/pact)^elasticite
    ratio = df["prix_optimal"] / df["prix_actuel"]
    df["qte_new"]   = df["qte"] * ratio ** df["elasticite"]
    df["marge_act"] = (df["prix_actuel"] - df["cout"]) * df["qte"]
    df["marge_new"] = (df["prix_optimal"] - df["cout"]) * df["qte_new"]
    df["gain"]      = df["marge_new"] - df["marge_act"]
    top = df.sort_values("gain", ascending=False).head(top_n)
    gain_total = df.loc[df["gain"] > 0, "gain"].sum()
    return top, gain_total

TOP_PRIX, GAIN_TOTAL = charger_opportunites()

# --- Données du simulateur : tous les produits (prix, coût, élasticité, ventes) ---
def charger_produits_sim():
    con = duckdb.connect(str(DB), read_only=True)
    qte = con.execute("SELECT id_produit, SUM(quantite) qte FROM transactions GROUP BY 1").fetchdf()
    con.close()
    return pd.read_csv(PRICING).merge(qte, on="id_produit").set_index("id_produit")

SIM = charger_produits_sim()
OPTIONS_SIM = [{"label": f"{r['nom']}  #{i}", "value": int(i)} for i, r in SIM.iterrows()]

# --- Données pour les graphiques CA (calculées une fois) --------------------
MOIS_FR = {"01": "janv", "02": "févr", "03": "mars", "04": "avr", "05": "mai", "06": "juin",
           "07": "juil", "08": "août", "09": "sept", "10": "oct", "11": "nov", "12": "déc"}

def charger_ca():
    con = duckdb.connect(str(DB), read_only=True)
    mois = con.execute("""
        SELECT strftime(CAST(date_vente AS DATE), '%Y-%m') m, SUM(quantite * prix_unitaire) ca
        FROM transactions GROUP BY 1 ORDER BY 1
    """).fetchdf()
    cat = con.execute("""
        SELECT p.categorie, SUM(t.quantite * t.prix_unitaire) ca
        FROM transactions t JOIN produits p ON t.id_produit = p.id_produit
        GROUP BY 1 ORDER BY 2
    """).fetchdf()
    con.close()
    return mois, cat

CA_MOIS, CA_CAT = charger_ca()

# --- Santé des modèles : rapport de monitoring (PSI, calculé par le MLOps) ---
MONITORING = ICI.parents[0] / "mlops" / "monitoring_rapport.csv"
LIB_MODELE = {"demande_quotidienne": "Prévision de la demande",
              "prix_unitaire": "Modèle de prix",
              "mix_categories": "Mix catégories"}

def charger_sante():
    return pd.read_csv(MONITORING)

SANTE = charger_sante()

# --- Impact des promotions : CA/jour avec vs sans promo ---------------------
def charger_promo():
    con = duckdb.connect(str(DB), read_only=True)
    avec, sans = con.execute("""
        WITH j AS (
            SELECT CAST(date_vente AS DATE) d,
                   MAX(CASE WHEN id_promo <> 0 THEN 1 ELSE 0 END) jour_promo,
                   SUM(quantite * prix_unitaire) ca_jour
            FROM transactions GROUP BY 1)
        SELECT AVG(CASE WHEN jour_promo = 1 THEN ca_jour END),
               AVG(CASE WHEN jour_promo = 0 THEN ca_jour END)
        FROM j
    """).fetchone()
    ca_promo, ca_tot = con.execute("""
        SELECT SUM(CASE WHEN id_promo <> 0 THEN quantite * prix_unitaire END),
               SUM(quantite * prix_unitaire)
        FROM transactions
    """).fetchone()
    con.close()
    return {"avec": avec, "sans": sans, "ratio": avec / sans, "part": ca_promo / ca_tot * 100}

PROMO = charger_promo()

# --- Prévisions de demande (pré-calculées par export_forecast.py) -----------
FORECAST = pd.read_csv(ICI / "forecast.csv", parse_dates=["ds"])
CATS_PREV = sorted(FORECAST["categorie"].unique())

# --- CA par ville + coordonnées géographiques (carte du Sénégal) -------------
COORDS = {
    "Dakar": (14.6928, -17.4467), "Thies": (14.7910, -16.9256),
    "Touba": (14.8500, -15.8833), "Rufisque": (14.7167, -17.2667),
    "Saint-Louis": (16.0179, -16.4896), "Kaolack": (14.1592, -16.0757),
    "Mbour": (14.4200, -16.9700), "Ziguinchor": (12.5833, -16.2719),
    "Tambacounda": (13.7708, -13.6672), "Kolda": (12.8833, -14.9500),
    "Diourbel": (14.6561, -16.2314), "Louga": (15.6144, -16.2144),
}

def charger_ca_ville():
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute("""
        SELECT c.ville, SUM(t.quantite * t.prix_unitaire) ca, COUNT(DISTINCT c.id_client) clients
        FROM transactions t JOIN clients c ON t.id_client = c.id_client
        GROUP BY 1 ORDER BY 2 DESC
    """).fetchdf()
    con.close()
    df["lat"] = df["ville"].map(lambda v: COORDS[v][0])
    df["lon"] = df["ville"].map(lambda v: COORDS[v][1])
    return df

CA_VILLE = charger_ca_ville()

# --- Remise recommandée par segment (règle métier, pas un modèle) ------------
REGLE_REMISE = {
    "Premium":     {"taux": 5,  "objectif": "Rétention",    "logique": "Protéger nos plus gros clients"},
    "Regulier":    {"taux": 5,  "objectif": "Rétention",    "logique": "Fidéliser une base large et régulière"},
    "Occasionnel": {"taux": 8,  "objectif": "Réactivation", "logique": "Inciter à acheter plus souvent"},
    "Nouveau":     {"taux": 10, "objectif": "Acquisition",  "logique": "Déclencher le premier achat"},
}
ORDRE_SEGMENTS = ["Premium", "Regulier", "Occasionnel", "Nouveau"]

def charger_segments():
    con = duckdb.connect(str(DB), read_only=True)
    df = con.execute("""
        SELECT c.segment,
               COUNT(DISTINCT c.id_client) nb,
               AVG(dep.total) depense_moy
        FROM clients c
        JOIN (SELECT id_client, SUM(quantite * prix_unitaire) total
              FROM transactions GROUP BY 1) dep ON c.id_client = dep.id_client
        GROUP BY 1
    """).fetchdf().set_index("segment")
    con.close()
    return df

SEGMENTS = charger_segments()

# --- 2) Charte graphique Teranga --------------------------------------------
BLEU   = "#003B7A"      # bleu navy (charte Teranga Market)
ORANGE = "#FF7A00"      # orange (charte Teranga Market)
FOND   = "#F1F5FA"      # fond de page (gris bleuté)
CARTE  = "#FFFFFF"      # fond des cartes
TEXTE  = "#1B2A3A"      # texte foncé (navy sombre)
GRIS   = "#6B7887"      # texte secondaire

def fcfa(n):
    """Formate un nombre en FCFA avec des espaces (ex. 1 234 567)."""
    return f"{n:,.0f}".replace(",", " ")

def millions(n):
    """Formate un gain en millions de FCFA (ex. +41,0 M)."""
    return f"+{n/1e6:.1f} M".replace(".", ",")

GAIN_MAX = float(TOP_PRIX["gain"].max())   # pour dimensionner les barres

def ligne_opportunite(rang, r):
    """Une ligne enrichie : rang, catégorie, variation %, barre de gain proportionnelle."""
    var_pct = (r["prix_optimal"] / r["prix_actuel"] - 1) * 100
    hausse = var_pct >= 0
    fleche = "↑" if hausse else "↓"
    coul_var = ORANGE if hausse else "#C0392B"
    largeur = max(6, r["gain"] / GAIN_MAX * 100)   # % de la barre
    prem = rang == 1
    return html.Div(
        style={"padding": "13px 0", "borderBottom": f"1px solid {FOND}"},
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "gap": "14px"},
                children=[
                    # pastille de rang
                    html.Div(str(rang), style={
                        "width": "28px", "height": "28px", "borderRadius": "50%", "flexShrink": "0",
                        "background": ORANGE if prem else "#E3EDF7", "color": "#FFFFFF" if prem else BLEU,
                        "fontSize": "14px", "fontWeight": "700",
                        "display": "flex", "alignItems": "center", "justifyContent": "center"}),
                    # nom + catégorie + prix
                    html.Div(style={"flex": "1", "minWidth": "0"}, children=[
                        html.Div([
                            html.Span(r["nom"], style={"color": TEXTE, "fontSize": "15px", "fontWeight": "500"}),
                            html.Span(f"  #{int(r['id_produit'])}", style={"color": GRIS, "fontSize": "12px"}),
                            html.Span(r["categorie"], style={
                                "marginLeft": "8px", "background": FOND, "color": GRIS, "fontSize": "11px",
                                "padding": "2px 8px", "borderRadius": "10px"}),
                        ]),
                        html.Div([
                            html.Span(f"{fcfa(r['prix_actuel'])} → {fcfa(r['prix_optimal'])} FCFA",
                                      style={"color": GRIS, "fontSize": "12px"}),
                            html.Span(f"  {fleche} {abs(var_pct):.0f}%",
                                      style={"color": coul_var, "fontSize": "12px", "fontWeight": "700"}),
                        ], style={"marginTop": "2px"}),
                    ]),
                    # badge gain
                    html.Span(millions(r["gain"]), style={
                        "background": BLEU, "color": "#FFFFFF", "fontSize": "14px", "fontWeight": "700",
                        "padding": "5px 13px", "borderRadius": "8px", "whiteSpace": "nowrap"}),
                ],
            ),
            # barre de gain proportionnelle
            html.Div(style={"height": "5px", "background": FOND, "borderRadius": "3px",
                            "marginTop": "9px", "marginLeft": "42px", "overflow": "hidden"},
                     children=[html.Div(style={
                         "width": f"{largeur:.0f}%", "height": "100%",
                         "background": ORANGE if prem else BLEU, "borderRadius": "3px"})]),
        ],
    )

def carte_opportunites():
    """La carte 'Opportunités de prix' complète."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "borderLeft": f"4px solid {ORANGE}"},
        children=[
            html.Div(
                style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                       "flexWrap": "wrap", "gap": "10px", "marginBottom": "6px"},
                children=[
                    html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px"}, children=[
                        html.Div(html.I(className="fa-solid fa-coins"), style={
                            "width": "34px", "height": "34px", "borderRadius": "10px", "background": "#FFE8D2",
                            "color": ORANGE, "fontSize": "16px",
                            "display": "flex", "alignItems": "center", "justifyContent": "center"}),
                        html.Div([
                            html.Div("Opportunités de prix", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                            html.Div("Produits à re-tarifer en priorité · gain estimé sur 12 mois",
                                     style={"color": GRIS, "fontSize": "12px"}),
                        ]),
                    ]),
                    # gain total mis en avant
                    html.Div(style={"textAlign": "right"}, children=[
                        html.Div(f"{millions(GAIN_TOTAL)} FCFA", style={"color": ORANGE, "fontSize": "22px", "fontWeight": "700"}),
                        html.Div("gain potentiel / an", style={"color": GRIS, "fontSize": "12px"}),
                    ]),
                ],
            ),
            html.Div(style={"marginTop": "8px"},
                     children=[ligne_opportunite(i, r) for i, (_, r) in enumerate(TOP_PRIX.iterrows(), start=1)]),
        ],
    )

def mini_stat(titre, id_valeur):
    """Petit cadran de sortie du simulateur (rempli par le callback)."""
    return html.Div(style={"background": FOND, "borderRadius": "10px", "padding": "12px 14px", "flex": "1"},
                    children=[
                        html.Div(titre, style={"color": GRIS, "fontSize": "12px", "marginBottom": "5px"}),
                        html.Div(id=id_valeur, style={"color": TEXTE, "fontSize": "20px", "fontWeight": "700"}),
                    ])

def carte_simulateur():
    """Brique 3 : simulateur de prix interactif (piloté par un callback)."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "borderLeft": f"4px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "6px"}, children=[
                html.I(className="fa-solid fa-sliders", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Simulateur « et si… »", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div("Choisis un produit, fais varier son prix, observe la marge",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),

            # Interrupteur 1 : le produit
            html.Div("Produit", style={"color": GRIS, "fontSize": "12px", "margin": "12px 0 5px"}),
            dcc.Dropdown(id="sim-produit", options=OPTIONS_SIM, value=85, clearable=False),

            # Interrupteur 2 : la variation de prix
            html.Div(style={"display": "flex", "justifyContent": "space-between", "margin": "16px 0 2px"}, children=[
                html.Span("Variation de prix", style={"color": GRIS, "fontSize": "12px"}),
                html.Span(id="sim-prix", style={"color": TEXTE, "fontSize": "16px", "fontWeight": "700"}),
            ]),
            dcc.Slider(id="sim-var", min=-30, max=60, step=1, value=0,
                       marks={-30: "-30%", 0: "prix actuel", 30: "+30%", 60: "+60%"},
                       tooltip={"placement": "bottom", "always_visible": False}),

            # Ampoules : les sorties
            html.Div(style={"display": "flex", "gap": "12px", "marginTop": "14px"}, children=[
                mini_stat("Ventes prévues / an", "sim-qte"),
                mini_stat("Marge prévue / an", "sim-marge"),
            ]),
            html.Div(id="sim-verdict", style={"textAlign": "center", "fontSize": "14px",
                                              "fontWeight": "700", "marginTop": "14px"}),
            html.Div(id="sim-optimal", style={"textAlign": "center", "fontSize": "12px",
                                              "color": GRIS, "marginTop": "4px"}),
        ],
    )

def _mise_en_forme(fig, titre):
    """Style commun aux graphiques (fond transparent, charte Teranga)."""
    fig.update_layout(
        title=dict(text=titre, font=dict(size=15, color=TEXTE, family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", color=GRIS, size=12),
        margin=dict(l=10, r=15, t=40, b=10), height=300,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor=FOND, zeroline=False)
    return fig

def fig_ca_mois():
    labels = [f"{MOIS_FR[m[5:7]]} {m[2:4]}" for m in CA_MOIS["m"]]
    fig = go.Figure(go.Scatter(
        x=labels, y=CA_MOIS["ca"] / 1e9, mode="lines+markers", fill="tozeroy",
        line=dict(color=BLEU, width=3), marker=dict(size=7, color=BLEU),
        fillcolor="rgba(0,59,122,0.12)",
        hovertemplate="%{x}<br><b>%{y:.2f} Md FCFA</b><extra></extra>"))
    return _mise_en_forme(fig, "Chiffre d'affaires par mois (Md FCFA)")

def fig_ca_categorie():
    fig = go.Figure(go.Bar(
        x=CA_CAT["ca"] / 1e9, y=CA_CAT["categorie"], orientation="h",
        marker=dict(color=BLEU),
        hovertemplate="%{y}<br><b>%{x:.2f} Md FCFA</b><extra></extra>"))
    return _mise_en_forme(fig, "Chiffre d'affaires par catégorie (Md FCFA)")

def carte_graphiques():
    """Brique 5 : graphiques du chiffre d'affaires."""
    cfg = {"displayModeBar": False}
    base = {"flex": "1", "minWidth": "320px", "background": CARTE, "borderRadius": "14px",
            "padding": "10px 14px", "border": "1px solid #E6EBE8"}
    return html.Div(style={"display": "flex", "gap": "16px", "marginTop": "18px", "flexWrap": "wrap"}, children=[
        html.Div(dcc.Graph(figure=fig_ca_mois(), config=cfg),
                 style={**base, "borderTop": f"3px solid {ORANGE}"}),
        html.Div(dcc.Graph(figure=fig_ca_categorie(), config=cfg),
                 style={**base, "borderTop": f"3px solid {ORANGE}"}),
    ])

def _statut_psi(psi):
    """PSI -> (couleur, libellé). Seuils standards du Population Stability Index."""
    if psi < 0.10:
        return "#2E9E5B", "Stable"
    if psi < 0.25:
        return ORANGE, "À surveiller"
    return "#C0392B", "À ré-entraîner"

def voyant(row):
    coul, libelle = _statut_psi(row["PSI"])
    return html.Div(
        style={"flex": "1", "minWidth": "200px", "display": "flex", "alignItems": "flex-start", "gap": "11px",
               "background": FOND, "borderRadius": "10px", "padding": "12px 14px"},
        children=[
            html.Div(style={"width": "12px", "height": "12px", "borderRadius": "50%",
                            "background": coul, "marginTop": "4px", "flexShrink": "0"}),
            html.Div([
                html.Div(LIB_MODELE.get(row["indicateur"], row["indicateur"]),
                         style={"color": TEXTE, "fontSize": "14px", "fontWeight": "500"}),
                html.Div(f"{libelle} · PSI {row['PSI']:.2f}",
                         style={"color": coul, "fontSize": "12px", "fontWeight": "700", "marginTop": "2px"}),
                html.Div(row["detail"], style={"color": GRIS, "fontSize": "11px", "marginTop": "2px"}),
            ]),
        ],
    )

def carte_sante():
    """Brique A : santé des modèles (dérive des données / monitoring MLOps)."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "18px 22px",
               "marginTop": "18px", "border": "1px solid #E6EBE8", "borderTop": f"3px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "12px"}, children=[
                html.I(className="fa-solid fa-heart-pulse", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Santé des modèles", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div("Surveillance de la dérive des données (PSI) · issu du monitoring MLOps",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            html.Div(style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
                     children=[voyant(r) for _, r in SANTE.iterrows()]),
        ],
    )

def _barre_promo(libelle, valeur, largeur_pct, couleur):
    return html.Div(style={"marginBottom": "10px"}, children=[
        html.Div(style={"display": "flex", "justifyContent": "space-between", "marginBottom": "4px"}, children=[
            html.Span(libelle, style={"color": GRIS, "fontSize": "13px"}),
            html.Span(f"{valeur/1e6:.1f} M FCFA".replace(".", ","),
                      style={"color": TEXTE, "fontSize": "13px", "fontWeight": "700"}),
        ]),
        html.Div(style={"height": "16px", "background": FOND, "borderRadius": "8px", "overflow": "hidden"},
                 children=[html.Div(style={"width": f"{largeur_pct:.0f}%", "height": "100%",
                                           "background": couleur, "borderRadius": "8px"})]),
    ])

def carte_promo():
    """Brique E : impact des promotions sur le chiffre d'affaires."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "marginTop": "18px", "borderLeft": f"4px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                            "flexWrap": "wrap", "gap": "10px", "marginBottom": "14px"}, children=[
                html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px"}, children=[
                    html.I(className="fa-solid fa-tag", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                    html.Div([
                        html.Div("Impact des promotions", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                        html.Div("Chiffre d'affaires moyen par jour · avec vs sans promo",
                                 style={"color": GRIS, "fontSize": "12px"}),
                    ]),
                ]),
                html.Div(style={"textAlign": "right"}, children=[
                    html.Div(f"×{PROMO['ratio']:.1f}".replace(".", ","),
                             style={"color": ORANGE, "fontSize": "26px", "fontWeight": "700"}),
                    html.Div("de CA les jours de promo", style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            _barre_promo("Jour avec promo", PROMO["avec"], 100, ORANGE),
            _barre_promo("Jour sans promo", PROMO["sans"], PROMO["sans"] / PROMO["avec"] * 100, "#AFC1D6"),
            html.Div(
                f"💡 {PROMO['part']:.0f}% du CA annuel se réalise pendant les promotions. "
                "Le panier moyen reste stable → les promos dopent le volume d'activité, pas la taille du panier.",
                style={"color": GRIS, "fontSize": "12px", "marginTop": "10px",
                       "background": FOND, "padding": "10px 12px", "borderRadius": "10px"}),
        ],
    )

def ligne_remise(seg):
    r = REGLE_REMISE[seg]
    stat = SEGMENTS.loc[seg]
    retention = r["objectif"] == "Rétention"
    coul_obj = BLEU if retention else ORANGE
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "14px",
               "padding": "13px 0", "borderBottom": f"1px solid {FOND}"},
        children=[
            # segment + valeur
            html.Div(style={"flex": "1", "minWidth": "0"}, children=[
                html.Div(seg, style={"color": TEXTE, "fontSize": "15px", "fontWeight": "700"}),
                html.Div(f"{int(stat['nb'])} clients · {stat['depense_moy']/1e6:.1f} M FCFA/client".replace(".", ","),
                         style={"color": GRIS, "fontSize": "12px", "marginTop": "2px"}),
                html.Div(r["logique"], style={"color": GRIS, "fontSize": "12px", "marginTop": "2px", "fontStyle": "italic"}),
            ]),
            # objectif
            html.Span(r["objectif"], style={
                "background": "#E3EDF7" if retention else "#FFE8D2", "color": coul_obj,
                "fontSize": "12px", "fontWeight": "700", "padding": "4px 11px", "borderRadius": "10px",
                "whiteSpace": "nowrap"}),
            # remise
            html.Span(f"−{r['taux']}%", style={
                "background": coul_obj, "color": "#FFFFFF", "fontSize": "17px", "fontWeight": "700",
                "padding": "5px 14px", "borderRadius": "8px", "whiteSpace": "nowrap"}),
        ],
    )

def carte_remise():
    """Section : remise recommandée par segment (règle métier CRM)."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "marginTop": "18px", "borderLeft": f"4px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "6px"}, children=[
                html.I(className="fa-solid fa-bullseye", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Remise recommandée par segment", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div("Règle métier CRM · fidéliser les gros clients, déclencher l'achat des nouveaux",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            html.Div(style={"marginTop": "8px"}, children=[ligne_remise(s) for s in ORDRE_SEGMENTS]),
            html.Div(
                "💡 Toutes nos catégories sont élastiques (~−2,5) : une remise booste le volume de façon fiable. "
                "On la cible donc par valeur client — remise de fidélité pour retenir les Premium/Réguliers, "
                "remise d'accroche plus forte pour convertir les Nouveaux/Occasionnels. "
                "Règle métier basée sur les données existantes, sans nouveau modèle.",
                style={"color": GRIS, "fontSize": "12px", "marginTop": "12px",
                       "background": FOND, "padding": "10px 12px", "borderRadius": "10px"}),
        ],
    )

def fig_carte():
    d = CA_VILLE
    fig = go.Figure(go.Scattergeo(
        lat=d["lat"], lon=d["lon"], text=d["ville"],
        customdata=(d["ca"] / 1e9).round(2),
        mode="markers+text", textposition="top center",
        textfont=dict(size=9, color=TEXTE),
        marker=dict(size=d["ca"], sizemode="area",
                    sizeref=2 * d["ca"].max() / (60 ** 2), sizemin=4,
                    color=BLEU, opacity=0.72, line=dict(width=1, color="white")),
        hovertemplate="<b>%{text}</b><br>%{customdata:.2f} Md FCFA<extra></extra>"))
    fig.update_geos(scope="africa", resolution=50, showcountries=True, countrycolor="#B9C6BF",
                    showland=True, landcolor="#EAF1EE", showocean=True, oceancolor="#DCE9F5",
                    lataxis_range=[11.5, 17.5], lonaxis_range=[-18.5, -11], showframe=False)
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=430, paper_bgcolor="rgba(0,0,0,0)")
    return fig

def carte_geographie():
    """Brique C : répartition géographique du CA (carte du Sénégal)."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "marginTop": "18px", "border": "1px solid #E6EBE8", "borderTop": f"3px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "6px"}, children=[
                html.I(className="fa-solid fa-map-location-dot", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Répartition géographique du CA", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div("Chiffre d'affaires par ville · taille des bulles = CA",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            # topojsonURL local -> la carte marche SANS internet (soutenance)
            dcc.Graph(figure=fig_carte(),
                      config={"displayModeBar": False, "topojsonURL": "/assets/topojson/"}),
        ],
    )

def carte_prevision():
    """Brique B : prévision de la demande (modèle Prophet, notebook 4.1)."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "marginTop": "18px", "border": "1px solid #E6EBE8", "borderTop": f"3px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "10px"}, children=[
                html.I(className="fa-solid fa-chart-line", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Prévision de la demande", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div("Modèle Prophet · demande réelle + prévision à 30 jours (unités/jour)",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            html.Div("Catégorie", style={"color": GRIS, "fontSize": "12px", "margin": "0 0 5px"}),
            dcc.Dropdown(id="prev-cat", options=[{"label": c, "value": c} for c in CATS_PREV],
                         value="Smartphones & tablettes", clearable=False),
            dcc.Graph(id="prev-graph", config={"displayModeBar": False}),
        ],
    )

def carte_reco():
    """Brique 4 : recommandations en direct, en appelant l'API (port 8000)."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 24px",
               "borderLeft": f"4px solid {ORANGE}", "marginTop": "18px"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "6px"}, children=[
                html.I(className="fa-solid fa-robot", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Recommandations en direct", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div("Le dashboard interroge l'API en temps réel pour un client",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            # Interrupteur : n° de client + bouton
            html.Div(style={"display": "flex", "gap": "10px", "alignItems": "center", "margin": "14px 0"}, children=[
                html.Span("Client n°", style={"color": GRIS, "fontSize": "13px"}),
                dcc.Input(id="reco-client", type="number", value=1, min=1, step=1,
                          style={"width": "110px", "padding": "8px 10px", "borderRadius": "8px",
                                 "border": f"1px solid #D5DCD8", "fontSize": "14px"}),
                html.Button("Recommander", id="reco-btn", n_clicks=0,
                            style={"background": BLEU, "color": "#FFFFFF", "border": "none",
                                   "padding": "9px 18px", "borderRadius": "8px", "fontSize": "14px",
                                   "fontWeight": "700", "cursor": "pointer"}),
            ]),
            # Ampoule : la sortie (remplie par le callback)
            dcc.Loading(html.Div(id="reco-sortie"), type="circle", color=BLEU),
        ],
    )

def ligne_reco(p):
    """Une recommandation affichée."""
    return html.Div(
        style={"display": "flex", "alignItems": "center", "gap": "10px", "padding": "9px 12px",
               "background": FOND, "borderRadius": "10px"},
        children=[
            html.Span(p["nom"], style={"color": TEXTE, "fontSize": "14px", "fontWeight": "500"}),
            html.Span(f"#{p['id_produit']}", style={"color": GRIS, "fontSize": "11px"}),
            html.Span(p["categorie"], style={"marginLeft": "auto", "color": GRIS, "fontSize": "11px",
                                             "background": "#FFFFFF", "padding": "2px 8px", "borderRadius": "10px"}),
        ],
    )

def carte_kpi(titre, valeur, unite=""):
    """Un cadran KPI = un bloc LEGO réutilisable."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "20px 22px",
               "flex": "1", "minWidth": "180px",
               "borderTop": f"3px solid {ORANGE}"},
        children=[
            html.Div(titre, style={"color": GRIS, "fontSize": "14px", "marginBottom": "8px"}),
            html.Div([
                html.Span(valeur, style={"color": BLEU, "fontSize": "28px", "fontWeight": "700"}),
                html.Span(f" {unite}", style={"color": GRIS, "fontSize": "15px"}),
            ]),
        ],
    )

# --- Couverture de stock : demande prévue (Prophet) vs stock disponible -----
FORECAST_CSV = ICI / "forecast.csv"

def charger_couverture_stock():
    """Croise la demande prévue (Prophet) et le stock, par catégorie.

    jours de couverture = stock disponible / demande quotidienne prévue.
    <30 j = risque de rupture · 30–90 j = sain · >90 j = surstock.
    """
    prev = pd.read_csv(FORECAST_CSV)
    prev = prev[prev["type"] == "prevision"]
    horizon = int(prev["ds"].nunique())
    dem = prev.groupby("categorie")["yhat"].sum().clip(lower=0)   # demande prévue sur l'horizon
    con = duckdb.connect(str(DB), read_only=True)
    stock = con.execute("SELECT categorie, SUM(stock) AS s FROM produits GROUP BY 1").fetchdf()
    con.close()
    df = stock.set_index("categorie")
    df["demande"] = dem
    df["jours"] = (df["s"] / (df["demande"] / horizon)).round(0)
    return df.sort_values("jours"), horizon

STOCK_COUV, STOCK_HORIZON = charger_couverture_stock()

def _statut_stock(jours):
    """Jours de couverture -> (couleur, libellé)."""
    if jours < 30:
        return "#C0392B", "Risque de rupture"
    if jours <= 90:
        return "#2E9E5B", "Sain"
    return ORANGE, "Surstock"

def _voyant_stock(cat, row):
    coul, libelle = _statut_stock(row["jours"])
    return html.Div(
        style={"flex": "1", "minWidth": "210px", "display": "flex", "alignItems": "flex-start", "gap": "11px",
               "background": FOND, "borderRadius": "10px", "padding": "12px 14px"},
        children=[
            html.Div(style={"width": "12px", "height": "12px", "borderRadius": "50%",
                            "background": coul, "marginTop": "4px", "flexShrink": "0"}),
            html.Div([
                html.Div(cat, style={"color": TEXTE, "fontSize": "14px", "fontWeight": "500"}),
                html.Div(f"{libelle} · {row['jours']:.0f} j de couverture",
                         style={"color": coul, "fontSize": "12px", "fontWeight": "700", "marginTop": "2px"}),
                html.Div(f"stock {int(row['s'])} u · demande prévue {int(row['demande'])} u / {STOCK_HORIZON} j",
                         style={"color": GRIS, "fontSize": "11px", "marginTop": "2px"}),
            ]),
        ],
    )

def carte_stock():
    """Brique : couverture de stock (demande prévue vs stock) — repère rupture ET surstock."""
    return html.Div(
        style={"background": CARTE, "borderRadius": "14px", "padding": "18px 22px",
               "marginTop": "18px", "border": "1px solid #E6EBE8", "borderTop": f"3px solid {ORANGE}"},
        children=[
            html.Div(style={"display": "flex", "alignItems": "center", "gap": "10px", "marginBottom": "12px"}, children=[
                html.I(className="fa-solid fa-boxes-stacked", style={"fontSize": "17px", "color": ORANGE, "width": "24px", "textAlign": "center"}),
                html.Div([
                    html.Div("Couverture de stock", style={"color": TEXTE, "fontSize": "17px", "fontWeight": "700"}),
                    html.Div(f"Demande prévue ({STOCK_HORIZON} j, Prophet) vs stock · rupture < 30 j · sain 30–90 j · surstock > 90 j",
                             style={"color": GRIS, "fontSize": "12px"}),
                ]),
            ]),
            html.Div(style={"display": "flex", "gap": "12px", "flexWrap": "wrap"},
                     children=[_voyant_stock(cat, r) for cat, r in STOCK_COUV.iterrows()]),
        ],
    )

# --- 3) Navigation (sidebar) ------------------------------------------------
NAV = [
    ("sec-kpi",       "fa-gauge-high",       "Indicateurs"),
    ("sec-sante",     "fa-heart-pulse",      "Santé des modèles"),
    ("sec-prix",      "fa-coins",            "Prix & simulateur"),
    ("sec-remise",    "fa-bullseye",         "Remises segment"),
    ("sec-ca",        "fa-chart-column",     "Chiffre d'affaires"),
    ("sec-prevision", "fa-chart-line",       "Prévision demande"),
    ("sec-stock",     "fa-boxes-stacked",    "Couverture stock"),
    ("sec-promo",     "fa-tag",              "Promotions"),
    ("sec-carte",     "fa-map-location-dot", "Carte Sénégal"),
    ("sec-reco",      "fa-robot",            "Recommandations"),
]

def lien_nav(anchor, icone, label):
    return html.A(href="#" + anchor, className="nav-item", children=[
        html.I(className="fa-solid " + icone,
               style={"width": "22px", "textAlign": "center", "marginRight": "12px", "fontSize": "15px"}),
        html.Span(label, style={"fontSize": "14px"}),
    ])

def sidebar():
    return html.Div(
        className="sidebar",
        style={"width": "300px", "background": BLEU, "height": "100vh",
               "position": "fixed", "top": "0", "left": "0", "overflowY": "auto",
               "padding": "18px 14px", "boxSizing": "border-box"},
        children=[
            html.Div(html.Img(src="/assets/logo.png", style={"width": "100%", "display": "block"}),
                     style={"background": "#FFFFFF", "borderRadius": "12px", "padding": "8px", "marginBottom": "22px"}),
            html.Div([lien_nav(*n) for n in NAV]),
        ],
    )

# --- 4) L'application Dash ---------------------------------------------------
app = Dash(__name__, title="Dashboard Teranga")
server = app.server            # exposé pour gunicorn (déploiement en ligne)

app.layout = html.Div(
    style={"background": FOND, "minHeight": "100vh",
           "fontFamily": "Segoe UI, Arial, sans-serif"},
    children=[

        sidebar(),

        # Zone principale (décalée pour laisser la place à la sidebar fixe)
        html.Div(
            style={"marginLeft": "300px", "padding": "24px 30px"},
            children=[

                # Barre de titre
                html.Div(
                    style={"display": "flex", "alignItems": "center", "justifyContent": "space-between",
                           "flexWrap": "wrap", "gap": "10px", "marginBottom": "22px"},
                    children=[
                        html.Div([
                            html.Span("Dashboard ", style={"color": BLEU, "fontSize": "24px", "fontWeight": "700"}),
                            html.Span("Décisionnel", style={"color": ORANGE, "fontSize": "24px", "fontWeight": "700"}),
                        ]),
                        html.Span("juillet 2025 → juin 2026",
                                  style={"color": GRIS, "fontSize": "13px", "background": CARTE,
                                         "padding": "7px 16px", "borderRadius": "20px", "border": "1px solid #E6EBE8"}),
                    ],
                ),

                # KPI
                html.Div(id="sec-kpi", children=[
                    html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap"},
                             children=[
                                 carte_kpi("Chiffre d'affaires", fcfa(KPIS["ca"]), "FCFA"),
                                 carte_kpi("Marge totale", fcfa(KPIS["marge"]), f"FCFA · {KPIS['taux_marge']:.1f}%"),
                                 carte_kpi("Clients actifs", fcfa(KPIS["clients"])),
                                 carte_kpi("Panier moyen", fcfa(KPIS["panier"]), "FCFA"),
                             ]),
                    html.Div(style={"display": "flex", "gap": "16px", "flexWrap": "wrap", "marginTop": "16px"},
                             children=[
                                 carte_kpi("Taux de conversion", f"{KPIS['conversion']:.1f} %".replace(".", ","), "vue → achat"),
                                 carte_kpi("Rotation de stock", f"{KPIS['rotation']:.1f}×".replace(".", ","), "sur 12 mois"),
                                 carte_kpi("CLTV", fcfa(KPIS["cltv"]), "marge nette / client"),
                             ]),
                ]),

                html.Div(carte_sante(), id="sec-sante"),

                html.Div(id="sec-prix",
                         style={"display": "flex", "gap": "16px", "marginTop": "18px", "flexWrap": "wrap"},
                         children=[
                             html.Div(carte_opportunites(), style={"flex": "1", "minWidth": "320px"}),
                             html.Div(carte_simulateur(), style={"flex": "1", "minWidth": "320px"}),
                         ]),

                html.Div(carte_remise(), id="sec-remise"),
                html.Div(carte_graphiques(), id="sec-ca"),
                html.Div(carte_prevision(), id="sec-prevision"),
                html.Div(carte_stock(), id="sec-stock"),
                html.Div(carte_promo(), id="sec-promo"),
                html.Div(carte_geographie(), id="sec-carte"),
                html.Div(carte_reco(), id="sec-reco"),
            ],
        ),
    ],
)

# --- CALLBACK du simulateur : recalcule à chaque changement -----------------
@app.callback(
    Output("sim-prix", "children"),
    Output("sim-qte", "children"),
    Output("sim-marge", "children"),
    Output("sim-verdict", "children"),
    Output("sim-verdict", "style"),
    Output("sim-optimal", "children"),
    Input("sim-produit", "value"),   # interrupteur 1
    Input("sim-var", "value"),       # interrupteur 2
)
def maj_simulateur(id_produit, variation):
    r = SIM.loc[id_produit]
    prix   = r["prix_actuel"] * (1 + variation / 100)
    qte    = r["qte"] * (prix / r["prix_actuel"]) ** r["elasticite"]
    marge  = (prix - r["cout"]) * qte
    ref    = (r["prix_actuel"] - r["cout"]) * r["qte"]      # marge au prix actuel
    delta  = (marge - ref) / 1e6                             # écart en millions

    style_base = {"textAlign": "center", "fontSize": "14px", "fontWeight": "700", "marginTop": "14px"}
    if delta >= 0.05:
        verdict, couleur = f"+{delta:.1f} M FCFA de marge vs prix actuel".replace(".", ","), BLEU
    elif delta <= -0.05:
        verdict, couleur = f"{delta:.1f} M FCFA de marge vs prix actuel".replace(".", ","), "#C0392B"
    else:
        verdict, couleur = "Prix actuel — marge de référence", GRIS

    optimal = f"💡 Prix optimal du modèle : {fcfa(r['prix_optimal'])} FCFA  (soit {(r['prix_optimal']/r['prix_actuel']-1)*100:+.0f}%)"
    return (f"{fcfa(prix)} FCFA", fcfa(qte),
            f"{marge/1e6:.1f} M".replace(".", ","),
            verdict, {**style_base, "color": couleur}, optimal)


# --- CALLBACK prévision : redessine le graphe selon la catégorie choisie -----
@app.callback(
    Output("prev-graph", "figure"),
    Input("prev-cat", "value"),
)
def maj_prevision(categorie):
    d = FORECAST[FORECAST["categorie"] == categorie]
    hist = d[d["type"] == "historique"]
    fc = d[d["type"] == "prevision"]

    fig = go.Figure()
    # zone d'incertitude (80%) autour de la prévision
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_upper"], mode="lines",
                             line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat_lower"], mode="lines", line=dict(width=0),
                             fill="tonexty", fillcolor="rgba(232,131,58,0.15)",
                             showlegend=False, hoverinfo="skip"))
    # demande réellement observée
    fig.add_trace(go.Scatter(x=hist["ds"], y=hist["y"], mode="lines", name="Demande réelle",
                             line=dict(color=BLEU, width=2),
                             hovertemplate="%{x|%d %b}<br>%{y:.0f} u/j<extra></extra>"))
    # prévision des 30 prochains jours
    fig.add_trace(go.Scatter(x=fc["ds"], y=fc["yhat"], mode="lines", name="Prévision 30 j",
                             line=dict(color=ORANGE, width=2.5, dash="dash"),
                             hovertemplate="%{x|%d %b}<br>%{y:.0f} u/j (prévu)<extra></extra>"))
    _mise_en_forme(fig, None)
    fig.update_layout(margin=dict(l=10, r=15, t=10, b=10),
                      legend=dict(orientation="h", y=1.08, x=0, font=dict(size=11)))
    return fig


# --- CALLBACK reco : appelle l'API quand on clique sur "Recommander" --------
@app.callback(
    Output("reco-sortie", "children"),
    Input("reco-btn", "n_clicks"),
    State("reco-client", "value"),
    prevent_initial_call=True,
)
def maj_reco(n_clicks, id_client):
    if id_client is None:
        return html.Div("Entre un numéro de client.", style={"color": GRIS, "fontSize": "13px"})
    try:
        rep = requests.get(f"{API_URL}/recommander/{int(id_client)}", timeout=3)
        rep.raise_for_status()
        data = rep.json()
    except requests.exceptions.RequestException:
        return html.Div(
            "⚠️ API injoignable. Lance-la dans un autre terminal : "
            "cd 04_PRODUCTION/api puis uvicorn main:app --reload (port 8000).",
            style={"color": "#C0392B", "fontSize": "13px", "background": "#FBEAE7",
                   "padding": "12px 14px", "borderRadius": "10px"})

    entete = html.Div(style={"display": "flex", "gap": "10px", "flexWrap": "wrap",
                             "marginBottom": "10px", "fontSize": "12px"}, children=[
        html.Span(f"Source : {data['source']}", style={"background": "#E3EDF7", "color": BLEU,
                  "padding": "3px 10px", "borderRadius": "10px", "fontWeight": "700"}),
        html.Span(f"{data['nb_achats_connus']} achats connus", style={"color": GRIS}),
    ])
    lignes = [ligne_reco(p) for p in data["recommandations"]]
    return html.Div([entete, html.Div(lignes, style={"display": "flex", "flexDirection": "column", "gap": "7px"})])


if __name__ == "__main__":
    app.run(debug=True)
