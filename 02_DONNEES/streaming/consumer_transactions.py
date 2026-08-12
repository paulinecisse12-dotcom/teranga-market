# -*- coding: utf-8 -*-
"""
DONNEES — 3.5 STREAMING KAFKA : le CONSOMMATEUR.
Lit en temps reel les ventes qui arrivent dans le topic "transactions"
et affiche un petit tableau de bord live (compteur + CA cumule).

Lancement (venv, Kafka demarre) :
    python consumer_transactions.py
(Ctrl+C pour arreter)
"""
import json
from kafka import KafkaConsumer

TOPIC = "transactions"
SERVEUR = "localhost:9092"

consumer = KafkaConsumer(
    TOPIC,
    bootstrap_servers=SERVEUR,
    auto_offset_reset="earliest",       # lit depuis le debut du topic
    value_deserializer=lambda m: json.loads(m.decode("utf-8")),
    consumer_timeout_ms=30000,          # s'arrete apres 30s sans nouveau message
)

print(f"Consommateur a l'ecoute du topic '{TOPIC}'... (Ctrl+C pour arreter)\n")

nb = 0
ca_cumule = 0
par_categorie = {}

for message in consumer:
    e = message.value
    nb += 1
    ca_cumule += e["montant_total"]
    par_categorie[e["categorie"]] = par_categorie.get(e["categorie"], 0) + 1

    print(f"  Recu #{e['id_transaction']:>6} | {e['produit'][:30]:<30} | {e['montant_total']:>10,} FCFA"
          f"   ||  Total ventes : {nb:>4} | CA cumule : {ca_cumule:>14,} FCFA")

print(f"\n--- Flux termine ---")
print(f"Total ventes recues : {nb}")
print(f"CA cumule           : {ca_cumule:,} FCFA")
print("Ventes par categorie :")
for cat, n in sorted(par_categorie.items(), key=lambda x: -x[1]):
    print(f"  {cat:<26} : {n}")
