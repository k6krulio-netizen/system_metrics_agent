# =============================================================================
# Dockerfile — environnement de PRODUCTION (multi-stage)
# =============================================================================
# Cette image sert à la fois pour le service "api" et le service "agent" :
# les deux partagent le même code (app/) et les mêmes dépendances, seule
# la commande de démarrage change. Le choix du rôle se fait au lancement
# via la variable d'environnement SERVICE_ROLE (voir entrypoint.sh), et non
# au build : cela évite de maintenir deux Dockerfiles quasi identiques et
# garantit que les deux services tournent depuis EXACTEMENT la même image
# publiée sur Docker Hub (même tag, même empreinte de sécurité).
#
# -----------------------------------------------------------------------------
# Étape 1/2 : "builder" — installe les dépendances de PRODUCTION uniquement
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

# pytest (dernière ligne de requirements.txt) est une dépendance de
# développement/test : elle n'a rien à faire dans l'image de production.
# On la filtre ici plutôt que de maintenir un second fichier requirements
# à la main, pour rester sûr que les deux listes ne divergent jamais.
COPY requirements.txt .
RUN grep -vi '^pytest' requirements.txt > requirements.prod.txt \
    && pip install --no-cache-dir --user -r requirements.prod.txt

# -----------------------------------------------------------------------------
# Étape 2/2 : image finale — minimale, non-root, healthcheck
# -----------------------------------------------------------------------------
FROM python:3.12-slim

# procps fournit pgrep, utilisé par healthcheck.sh pour vérifier que le
# processus de l'agent est toujours vivant (l'agent n'a pas de port HTTP
# à interroger, contrairement à l'API).
RUN apt-get update && apt-get install -y --no-install-recommends \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin appuser

WORKDIR /app

# On récupère uniquement les paquets installés par pip (pas les outils de
# build), ce qui garde l'image finale légère.
COPY --from=builder /root/.local /home/appuser/.local

COPY app/ ./app/
COPY entrypoint.sh healthcheck.sh ./
RUN chmod +x entrypoint.sh healthcheck.sh \
    && chown -R appuser:appuser /app /home/appuser/.local

USER appuser

ENV PATH=/home/appuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SERVICE_ROLE=api

# Utile uniquement pour le rôle "api" ; sans effet pour "agent".
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ["./healthcheck.sh"]

ENTRYPOINT ["./entrypoint.sh"]
