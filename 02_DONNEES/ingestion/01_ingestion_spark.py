# -*- coding: utf-8 -*-
"""
DONNEES — 3.2 INGESTION avec Spark.
Lit les 5 CSV bruts, verifie/type les colonnes, nettoie, et ecrit en Parquet.
    CSV bruts  ->  [Spark : lit + type + nettoie]  ->  Parquet (Data Lake)

Lancement (Ubuntu/WSL, ou Spark est configure) :
    spark-submit 02_DONNEES/ingestion/01_ingestion_spark.py
"""
import os
# --- Force l'adresse locale (evite le warning loopback sous WSL/Windows) ---
os.environ.setdefault("SPARK_LOCAL_IP", "127.0.0.1")

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (
    StructType, StructField, IntegerType, LongType, DoubleType,
    StringType, DateType, TimestampType
)

# ------------------------------------------------------------------
# 0. Chemins (relatifs au dossier 02_DONNEES)
#    Ce script est dans 02_DONNEES/ingestion/ , donc :
#    dirname(dirname(__file__)) = 02_DONNEES
# ------------------------------------------------------------------
DONNEES = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BRUT = os.path.join(DONNEES, "brut")     # entree : CSV
LAKE = os.path.join(DONNEES, "lake")     # sortie : Parquet
os.makedirs(LAKE, exist_ok=True)

# ------------------------------------------------------------------
# 1. Demarrage de Spark
# ------------------------------------------------------------------
spark = (
    SparkSession.builder
    .appName("TerangaMarket-Ingestion")
    .master("local[*]")                       # utilise tous les coeurs de la machine
    .config("spark.sql.shuffle.partitions", "8")   # peu de partitions (petit volume local)
    .config("spark.ui.showConsoleProgress", "false")
    .config("spark.ui.enabled", "false")           # pas d'interface web (evite l'ouverture de ports)
    .config("spark.driver.host", "127.0.0.1")
    .config("spark.driver.bindAddress", "127.0.0.1")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")        # moins de messages dans la console

# ------------------------------------------------------------------
# 2. Schemas explicites (on IMPOSE le type de chaque colonne)
#    -> garantit que prix = nombre, date_vente = date, etc.
# ------------------------------------------------------------------
schema_produits = StructType([
    StructField("id_produit", IntegerType(), False),
    StructField("nom", StringType(), True),
    StructField("categorie", StringType(), True),
    StructField("marque", StringType(), True),
    StructField("prix_catalogue", LongType(), True),
    StructField("cout_unitaire", LongType(), True),
    StructField("stock", IntegerType(), True),
])

schema_clients = StructType([
    StructField("id_client", IntegerType(), False),
    StructField("nom", StringType(), True),
    StructField("age", IntegerType(), True),
    StructField("ville", StringType(), True),
    StructField("date_inscription", DateType(), True),
    StructField("segment", StringType(), True),
    StructField("canal_acquisition", StringType(), True),
])

schema_promotions = StructType([
    StructField("id_promo", IntegerType(), False),
    StructField("nom_campagne", StringType(), True),
    StructField("type", StringType(), True),
    StructField("taux_reduction", DoubleType(), True),
    StructField("date_debut", DateType(), True),
    StructField("date_fin", DateType(), True),
])

schema_transactions = StructType([
    StructField("id_transaction", IntegerType(), False),
    StructField("id_client", IntegerType(), True),
    StructField("id_produit", IntegerType(), True),
    StructField("id_promo", IntegerType(), True),
    StructField("date_vente", DateType(), True),
    StructField("quantite", IntegerType(), True),
    StructField("prix_unitaire", LongType(), True),
    StructField("montant_total", LongType(), True),
])

schema_navigation = StructType([
    StructField("id_navigation", IntegerType(), False),
    StructField("id_client", IntegerType(), True),
    StructField("id_produit", IntegerType(), True),
    StructField("horodatage", TimestampType(), True),
    StructField("action", StringType(), True),
])

TABLES = {
    "produits":     ("produits.csv",     schema_produits,     ["id_produit"]),
    "clients":      ("clients.csv",      schema_clients,      ["id_client"]),
    "promotions":   ("promotions.csv",   schema_promotions,   ["id_promo"]),
    "transactions": ("transactions.csv", schema_transactions, ["id_transaction"]),
    "navigation":   ("navigation.csv",   schema_navigation,   ["id_navigation"]),
}

# ------------------------------------------------------------------
# 3. Ingestion table par table
# ------------------------------------------------------------------
for nom, (fichier, schema, cle) in TABLES.items():
    chemin_csv = os.path.join(BRUT, fichier)
    print(f"\n=== Ingestion : {nom} ===")

    # 3a. LECTURE du CSV avec le schema impose
    df = (
        spark.read
        .option("header", True)
        .option("encoding", "UTF-8")
        .schema(schema)
        .csv(chemin_csv)
    )
    n_brut = df.count()

    # 3b. NETTOYAGE : on retire les doublons sur la cle et les cles nulles
    df_propre = df.dropDuplicates(cle).filter(F.col(cle[0]).isNotNull())
    n_propre = df_propre.count()

    # 3c. ECRITURE en Parquet (Data Lake)
    chemin_parquet = os.path.join(LAKE, nom)
    df_propre.write.mode("overwrite").parquet(chemin_parquet)

    print(f"  Lignes lues       : {n_brut:,}")
    print(f"  Lignes conservees : {n_propre:,}  ({n_brut - n_propre} doublon(s)/nul(s) retire(s))")
    print(f"  Ecrit dans        : {chemin_parquet}")
    df_propre.printSchema()

print("\nIngestion terminee. Les donnees propres sont dans 02_DONNEES/lake/ (Parquet).")
spark.stop()
