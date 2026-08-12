# -*- coding: utf-8 -*-
"""
DONNEES — 3.5 STREAMING KAFKA : le PRODUCTEUR.
Envoie les transactions une par une dans le topic Kafka "transactions",
avec un petit delai pour simuler un flux temps reel (streaming simule).

Lancement (venv, Kafka demarre) :
    python producer_transactions.py
"""
import os
import json
import time
import pandas as pd
from kafka import KafkaProducer

# --- Parametres ---
TOPIC = "transactions"
SERVEUR = "localhost:9092"
N_EVENTS = 300      # nombre de ventes a diffuser (mets plus si tu veux)
DELAI = 0.15        # secondes entre deux ventes (simule le temps reel)

# --- Chemins ---
DONNEES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUT = os.path.join(DONNEES, "brut")

# --- Charge les donnees ---
transactions = pd.read_csv(os.path.join(BRUT, "transactions.csv"))
produits = pd.read_csv(os.path.join(BRUT, "produits.csv"))
# petit dictionnaire id_produit -> (nom, categorie) pour enrichir l'evenement
info_produit = {r.id_produit: (r.nom, r.categorie) for r in produits.itertuples()}

# --- Connexion au broker Kafka ---
producer = KafkaProducer(
    bootstrap_servers=SERVEUR,
    value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
)

print(f"Producteur pret. Diffusion de {N_EVENTS} ventes dans le topic '{TOPIC}'...\n")

# --- Diffusion des ventes une par une ---
for i, row in transactions.head(N_EVENTS).iterrows():
    nom_prod, cat = info_produit.get(row["id_produit"], ("?", "?"))
    evenement = {
        "id_transaction": int(row["id_transaction"]),
        "id_client": int(row["id_client"]),
        "produit": nom_prod,
        "categorie": cat,
        "date_vente": str(row["date_vente"]),
        "quantite": int(row["quantite"]),
        "montant_total": int(row["montant_total"]),
    }
    producer.send(TOPIC, evenement)
    print(f"  -> Vente #{evenement['id_transaction']:>6} | {evenement['produit'][:35]:<35} | {evenement['montant_total']:>10,} FCFA")
    time.sleep(DELAI)

producer.flush()
producer.close()
print(f"\nTermine : {N_EVENTS} ventes envoyees dans Kafka.")
