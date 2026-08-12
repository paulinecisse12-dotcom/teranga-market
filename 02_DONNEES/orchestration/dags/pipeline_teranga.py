# -*- coding: utf-8 -*-
"""
DAG Airflow — Pipeline data de Teranga Market.
Enchaine automatiquement : Generation -> Ingestion -> Warehouse -> Controle qualite.

Ce fichier decrit l'ORCHESTRATION (l'ordre des taches et leurs dependances).
Les chemins sont ceux DANS le conteneur : 02_DONNEES est monte sur /opt/airflow/projet.
"""
from datetime import datetime
from airflow import DAG
from airflow.operators.bash import BashOperator

PROJ = "/opt/airflow/projet"   # = 02_DONNEES monte dans le conteneur

default_args = {
    "owner": "equipe-teranga",
    "retries": 1,
}

with DAG(
    dag_id="pipeline_teranga",
    description="Pipeline data Teranga Market : generation -> ingestion -> warehouse -> qualite",
    start_date=datetime(2026, 1, 1),
    schedule=None,              # declenchement manuel (bouton Play). Mettre '@daily' pour un run quotidien.
    catchup=False,
    tags=["teranga", "data"],
    default_args=default_args,
) as dag:

    # 1) Generation des 5 tables synthetiques (produits, clients, promotions, transactions, navigation)
    generation = BashOperator(
        task_id="1_generation",
        bash_command=(
            f"cd {PROJ}/generation && "
            "python 01_produits.py && python 02_clients.py && python 03_promotions.py && "
            "python 04_transactions.py && python 05_navigation.py"
        ),
    )

    # 2) Ingestion : CSV -> Parquet (version pandas, adaptee au conteneur)
    ingestion = BashOperator(
        task_id="2_ingestion_parquet",
        bash_command=f"python {PROJ}/ingestion/02_ingestion_pandas.py",
    )

    # 3) Chargement du Data Warehouse (DuckDB)
    warehouse = BashOperator(
        task_id="3_warehouse_duckdb",
        bash_command=f"python {PROJ}/warehouse/01_charger_duckdb.py",
    )

    # 4) Controles qualite
    qualite = BashOperator(
        task_id="4_controle_qualite",
        bash_command=f"python {PROJ}/qualite/01_controles_qualite.py",
    )

    # Dependances : chaque etape attend la precedente
    generation >> ingestion >> warehouse >> qualite
