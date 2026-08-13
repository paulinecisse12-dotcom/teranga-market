# ============================================================
#  API Teranga Market — image Docker
#  Build (depuis 04_PRODUCTION/api) :  docker build -t teranga-api .
#  Run  :  docker run -p 8000:8000 teranga-api
#  NB : lancer d'abord `python export_modeles.py` pour generer artefacts/
# ============================================================
FROM python:3.13-slim

WORKDIR /app

# 1) Dependances (couche mise en cache tant que requirements.txt ne change pas)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2) Code + artefacts pre-calcules
COPY main.py .
COPY artefacts/ ./artefacts/

# 3) L'API ecoute sur le port 8000
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
