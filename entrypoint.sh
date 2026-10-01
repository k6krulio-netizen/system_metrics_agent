#!/bin/sh
# Point d'entrée unique de l'image de production.
#
# Le projet contient deux processus applicatifs (API et agent). Plutôt que
# de construire deux images quasi identiques, ce script choisit au
# démarrage lequel des deux lancer, en fonction de la variable
# d'environnement SERVICE_ROLE (valeurs attendues : "api" ou "agent").
# Ce choix est documenté et justifié dans le README (section "Choix
# techniques").
set -e

ROLE="${SERVICE_ROLE:-api}"

case "$ROLE" in
  api)
    exec uvicorn app.api:app --host 0.0.0.0 --port 8000
    ;;
  agent)
    exec python -m app.agent
    ;;
  *)
    echo "SERVICE_ROLE invalide: '$ROLE' (valeurs attendues: api|agent)" >&2
    exit 1
    ;;
esac
