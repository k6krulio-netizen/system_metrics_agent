#!/bin/sh
# Healthcheck Docker, adapté au rôle du conteneur.
#
# - Pour le rôle "api"   : on interroge la route /health en HTTP (via le
#   module standard urllib, pour éviter d'installer curl/wget et garder
#   l'image finale légère).
# - Pour le rôle "agent" : l'agent n'expose aucun port HTTP, on vérifie
#   donc simplement que le process app.agent tourne toujours (via pgrep,
#   fourni par le paquet procps installé dans le Dockerfile de prod).
set -e

ROLE="${SERVICE_ROLE:-api}"

if [ "$ROLE" = "api" ]; then
  python -c "
import sys
import urllib.request
try:
    with urllib.request.urlopen('http://localhost:8000/health', timeout=3) as r:
        sys.exit(0 if r.status == 200 else 1)
except Exception:
    sys.exit(1)
"
else
  pgrep -f "app.agent" > /dev/null 2>&1
fi
