# -*- coding: utf-8 -*-
"""
Etape 1 — Generation de la table PRODUITS (catalogue).
Teranga Market : 500 produits, 7 categories, prix en FCFA.
Chaque marque est associee a ses vrais modeles (noms coherents).
"""
import numpy as np
import pandas as pd

RANDOM_SEED = 42
rng = np.random.default_rng(RANDOM_SEED)

# --- Configuration par categorie ---
# categorie : (nb_produits, prix_min, prix_max, variantes, {marque: [modeles reels]})
CATALOGUE = {
    "Smartphones & tablettes": (90, 40_000, 800_000,
        ["", " 64 Go", " 128 Go", " 256 Go"],
        {
            "Samsung": ["Galaxy A14", "Galaxy A54", "Galaxy S23", "Galaxy Tab A9"],
            "Xiaomi":  ["Redmi Note 12", "Redmi 13C", "Poco X5", "Mi Pad 6"],
            "Tecno":   ["Spark 10", "Camon 20", "Pova 5"],
            "Infinix": ["Hot 40", "Note 30", "Zero 30"],
            "Apple":   ["iPhone 13", "iPhone 14", "iPad 10"],
            "Oppo":    ["Reno 8", "A78", "A98"],
            "Itel":    ["A70", "P55", "S23"],
        }),
    "Ordinateurs": (80, 150_000, 1_500_000,
        ["", " 8 Go RAM", " 16 Go RAM", " SSD 256 Go", " SSD 512 Go"],
        {
            "HP":     ["Pavilion 15", "EliteBook 840", "ProBook 450"],
            "Dell":   ["Inspiron 15", "XPS 13", "Latitude 5420"],
            "Lenovo": ["IdeaPad 3", "ThinkPad E14", "Legion 5"],
            "Asus":   ["VivoBook 15", "ZenBook 14", "ROG Strix"],
            "Acer":   ["Aspire 5", "Swift 3", "Nitro 5"],
            "Apple":  ["MacBook Air M1", "MacBook Pro 14"],
        }),
    "Audio": (80, 5_000, 250_000,
        ["", " Pro", " 2024"],
        {
            "JBL":     ["Tune 510", "Boombox 3", "Flip 6", "Go 3"],
            "Sony":    ["WH-1000XM4", "WF-C500", "ULT Wear"],
            "Anker":   ["Soundcore Life", "Soundcore Q30"],
            "Samsung": ["Galaxy Buds 2", "Galaxy Buds FE"],
            "Oraimo":  ["FreePods 3", "OpenPods", "BoomPop"],
            "Bose":    ["QuietComfort 45", "SoundLink Flex"],
        }),
    "TV & image": (50, 90_000, 1_200_000,
        ["", " 2024"],
        {
            "Samsung": ["Smart TV 43\"", "QLED 55\"", "QLED 65\""],
            "LG":      ["Smart TV 43\"", "OLED 55\"", "NanoCell 50\""],
            "TCL":     ["Smart TV 32\"", "Smart TV 43\"", "QLED 55\""],
            "Hisense": ["Smart TV 40\"", "Smart TV 50\"", "ULED 55\""],
            "Sony":    ["Bravia 43\"", "Bravia 55\"", "Projecteur"],
        }),
    "Gaming": (50, 15_000, 500_000,
        ["", " Edition Standard"],
        {
            "Sony":      ["PlayStation 5", "Manette DualSense"],
            "Microsoft": ["Xbox Series X", "Xbox Series S", "Manette Xbox"],
            "Nintendo":  ["Switch", "Switch Lite", "Switch OLED"],
            "Logitech":  ["Clavier Gamer G213", "Souris Gamer G502", "Casque G435"],
            "Razer":     ["Clavier BlackWidow", "Souris DeathAdder", "Casque Kraken"],
        }),
    "Accessoires": (100, 2_000, 50_000,
        ["", " (noir)", " (blanc)"],
        {
            "Oraimo": ["Chargeur", "Cable USB-C", "Powerbank", "Ecouteurs filaires"],
            "Anker":  ["Chargeur", "Powerbank", "Cable USB-C"],
            "Baseus": ["Cable USB-C", "Support telephone", "Adaptateur"],
            "Samsung":["Chargeur", "Coque Galaxy", "Cable"],
            "Generic":["Coque", "Protection ecran", "Support voiture"],
            "Belkin": ["Chargeur", "Cable", "Adaptateur secteur"],
        }),
    "Objets connectes": (50, 15_000, 350_000,
        ["", " Pro", " 2024"],
        {
            "Xiaomi":  ["Mi Band 8", "Smart Band 7", "Mi Watch"],
            "Samsung": ["Galaxy Watch 6", "Galaxy Fit 3"],
            "Huawei":  ["Watch GT 4", "Band 8"],
            "Amazfit": ["Bip 5", "GTS 4", "GTR 4"],
            "Oraimo":  ["Smartwatch", "Tempo"],
        }),
}

rows = []
pid = 1
for categorie, (n, pmin, pmax, variantes, marques_modeles) in CATALOGUE.items():
    marques = list(marques_modeles.keys())
    for _ in range(n):
        marque = rng.choice(marques)
        modele = rng.choice(marques_modeles[marque])   # modele REEL de la marque
        variante = rng.choice(variantes)
        nom = f"{marque} {modele}{variante}".strip()

        prix = int(rng.integers(pmin, pmax) // 500 * 500)          # arrondi a 500 FCFA
        cout = int(prix * rng.uniform(0.55, 0.80) // 100 * 100)    # 55-80% du prix
        stock = int(rng.integers(0, 300))

        rows.append({
            "id_produit": pid,
            "nom": nom,
            "categorie": categorie,
            "marque": marque,
            "prix_catalogue": prix,
            "cout_unitaire": cout,
            "stock": stock,
        })
        pid += 1

produits = pd.DataFrame(rows)

# --- Sauvegarde ---
import os
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "brut")
os.makedirs(OUT_DIR, exist_ok=True)
produits.to_csv(os.path.join(OUT_DIR, "produits.csv"), index=False, encoding="utf-8-sig")

# --- Verification ---
print(f"Total produits : {len(produits)}")
print(f"Nombre de categories : {produits['categorie'].nunique()}")
print("\nRepartition par categorie :")
print(produits["categorie"].value_counts().to_string())
print("\nApercu (12 produits au hasard) :")
print(produits.sample(12, random_state=1).to_string(index=False))
print("\nPrix par categorie (min / moyen / max) :")
print(produits.groupby("categorie")["prix_catalogue"].agg(["min", "mean", "max"]).astype(int).to_string())
