# System Metrics Agent — Conteneurisation, Orchestration & CI/CD

Agent Python modulaire (FastAPI + psutil) collectant des métriques système
(CPU, mémoire, charge système) et les transmettant à une API de réception,
le tout conteneurisé avec Docker, orchestré avec Docker Compose et publié
automatiquement via un pipeline CI/CD GitHub Actions.

## Sommaire

- [Architecture](#architecture)
- [Prérequis](#prérequis)
- [Lancer en développement](#lancer-en-développement)
- [Lancer en production](#lancer-en-production)
- [Pipeline CI/CD](#pipeline-cicd)
- [Images Docker Hub](#images-docker-hub)
- [Choix techniques et difficultés rencontrées](#choix-techniques-et-difficultés-rencontrées)
- [Preuves de fonctionnement](#preuves-de-fonctionnement)

## Architecture

```text
system_metrics_agent/
├── app/
│   ├── __init__.py
│   ├── agent.py          # orchestration : collecte -> format -> envoi
│   ├── api.py             # API FastAPI de réception des métriques
│   ├── collector.py       # collecte CPU / RAM / charge (psutil, subprocess)
│   ├── config.py          # configuration via variables d'environnement
│   ├── formatter.py       # mise en forme du payload JSON
│   └── sender.py          # envoi HTTP des métriques
├── tests/                  # suite pytest (unitaire + intégration API)
├── .github/workflows/
│   └── ci-cd.yml           # pipeline build / test / push
├── Dockerfile.dev           # image de développement (hot-reload)
├── Dockerfile                # image de production (multi-stage)
├── docker-compose.yaml       # orchestration de production
├── docker-compose.override.yml  # bascule automatique en mode dev (bonus)
├── entrypoint.sh              # choisit api|agent au démarrage du conteneur
├── healthcheck.sh             # healthcheck adapté au rôle du conteneur
├── .dockerignore
├── .env.example
└── requirements.txt
```

Le service **api** (FastAPI/uvicorn) expose `/health`, `/metrics` (GET/POST)
et `/metrics/latest`. Le service **agent** collecte les métriques toutes les
`COLLECTION_INTERVAL` secondes et les envoie à `METRICS_ENDPOINT`. Les deux
services sont construits à partir de la **même image de production** (voir
[Choix techniques](#choix-techniques-et-difficultés-rencontrées)).

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (ou
  Docker Engine + Docker Compose v2) installé et fonctionnel.
- Un compte [Docker Hub](https://hub.docker.com) (pour publier/tirer les
  images).
- Un compte GitHub avec Git installé localement (pour le pipeline CI/CD).

Aucune installation de Python locale n'est nécessaire : tout tourne dans des
conteneurs.

## Lancer en développement

Le mode développement utilise `Dockerfile.dev` et monte le code en volume
pour un rechargement à chaud. `docker-compose.override.yml` est chargé
**automatiquement** par Compose en plus de `docker-compose.yaml`, donc une
simple commande suffit :

```bash
cp .env.example .env
docker compose up --build
```

- L'API est disponible sur <http://localhost:8000> (documentation Swagger
  sur `/docs`), avec rechargement automatique à chaque modification d'un
  fichier dans `app/`.
- L'agent tourne en parallèle et envoie ses métriques à l'API toutes les
  `COLLECTION_INTERVAL` secondes.

Pour arrêter et nettoyer :

```bash
docker compose down
```

Pour exécuter uniquement la suite de tests, en local (sans conteneur) :

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -v
```

## Lancer en production

### Option A — build local à partir des Dockerfiles du dépôt

```bash
cp .env.example .env
docker compose -f docker-compose.yaml up --build
```

`-f docker-compose.yaml` explicite empêche Compose de fusionner
`docker-compose.override.yml` (réservé au développement) : les deux services
tournent avec l'image de production (`Dockerfile`), en utilisateur non-root.

### Option B — déploiement à partir des images publiées sur Docker Hub

Sans utiliser le code source local, uniquement les images publiées par le
pipeline CI/CD :

```bash
export DOCKERHUB_USERNAME=<votre-identifiant-docker-hub>
docker compose -f docker-compose.yaml pull
docker compose -f docker-compose.yaml up -d
```

Vérification :

```bash
curl http://localhost:8000/health
# {"status":"ok"}

docker compose ps
```

## Pipeline CI/CD

Fichier : [`.github/workflows/ci-cd.yml`](.github/workflows/ci-cd.yml)

**Déclenchement** : à chaque `push` sur `main`, et à chaque `pull_request`
ciblant `main`.

**Étapes** (deux jobs séquentiels) :

1. **`test`** (toujours exécuté) : checkout, installation des dépendances,
   exécution de `pytest -v`. Le pipeline s'arrête ici si un test échoue.
2. **`build-and-push`** (`needs: test`, uniquement sur `push` vers `main`,
   jamais sur une pull request) :
   - build de l'image de production à partir du `Dockerfile` ;
   - connexion à Docker Hub via `docker/login-action` ;
   - push de l'image avec **deux tags** : `latest` et le SHA du commit
     (`${{ github.sha }}`), pour pouvoir toujours revenir à une version
     précise.

**Secrets requis** (à créer dans *Settings → Secrets and variables →
Actions* du dépôt GitHub) :

| Secret | Contenu |
|---|---|
| `DOCKERHUB_USERNAME` | votre identifiant Docker Hub |
| `DOCKERHUB_TOKEN` | un *access token* Docker Hub (Account Settings → Security → New Access Token) — **jamais votre mot de passe** |

Ces identifiants ne sont jamais écrits en clair dans le code : ils ne sont
accessibles que via le contexte `secrets` de GitHub Actions, et le job de
publication ne se déclenche jamais sur une pull request externe (ce qui
évite qu'un fork puisse y accéder).

## Images Docker Hub

Dépôt d'image : `https://hub.docker.com/r/<votre-identifiant>/metrics-agent`
*(à remplacer par votre lien réel une fois la première publication faite par
le pipeline)*.

Tags publiés à chaque merge sur `main` :

- `latest` — dernière version stable ;
- `<sha-du-commit>` — version figée correspondant exactement à ce commit.

## Choix techniques et difficultés rencontrées

- **Une seule image de production pour `api` et `agent`.** Les deux
  processus partagent le même code (`app/`) et les mêmes dépendances ; seule
  la commande de démarrage diffère. Plutôt que maintenir deux Dockerfiles
  quasi identiques (et risquer qu'ils divergent avec le temps), l'image
  unique choisit son rôle au démarrage via la variable d'environnement
  `SERVICE_ROLE` (`api` ou `agent`), interprétée par `entrypoint.sh`. Les
  deux services de `docker-compose.yaml` référencent donc la même image et
  le même tag Docker Hub — ce qui garantit aussi qu'ils tournent
  exactement sur le même code publié, sans dérive possible entre les deux.
- **Build multi-stage pour limiter la taille de l'image finale.** L'étape
  `builder` installe les dépendances (en filtrant `pytest`, inutile en
  production) ; seul le résultat de cette installation (`~/.local`) est
  copié dans l'image finale, sans les caches ni les outils de build.
- **Healthcheck différencié selon le rôle.** Le service `api` expose un
  port HTTP et peut être vérifié via `/health` ; le service `agent` n'en a
  pas. `healthcheck.sh` gère les deux cas : requête HTTP (via le module
  standard `urllib`, pour éviter d'installer `curl`) pour l'API, ou
  vérification du process via `pgrep` (paquet `procps`) pour l'agent.
- **`METRICS_ENDPOINT` différent entre `.env` et `docker-compose.yaml`.**
  `.env.example` documente une valeur par défaut adaptée à une exécution
  locale hors conteneur (`127.0.0.1`). En Compose, le service `agent`
  surcharge explicitement cette variable avec `http://api:8000/metrics` :
  entre deux conteneurs d'un même réseau Docker, on communique par le nom
  DNS du service, jamais par `127.0.0.1` (qui désignerait le conteneur de
  l'agent lui-même).
- **Absence de tests dans le dépôt fourni.** Le sujet indique que le projet
  contient déjà une suite pytest, ce qui n'était pas le cas dans le dépôt
  cloné ; le dossier `tests/` (18 tests unitaires et d'intégration, décrits
  ci-dessus) a donc été écrit pour ce TP, sans modifier la logique métier
  de `app/`. `httpx` a été ajouté à `requirements.txt` car requis par le
  `TestClient` de FastAPI utilisé dans `tests/test_api.py`.
- **Tests exécutés sur le runner plutôt que dans un conteneur.** Le sujet
  autorise les deux approches ; exécuter `pytest` directement sur le
  runner GitHub Actions (job `test`) est plus rapide qu'un build Docker
  complet juste pour lancer les tests, et permet d'échouer le pipeline tôt,
  avant même de tenter un build Docker.

## Preuves de fonctionnement

*(À compléter avant la remise finale : capture d'écran du pipeline en vert
dans l'onglet **Actions** de GitHub, capture de `docker compose ps` montrant
les deux conteneurs `Up (healthy)`, et capture d'un appel réussi à
`/health` ou `/metrics/latest`.)*
#   s y s t e m _ m e t r i c s _ a g e n t  
 #   s y s t e m _ m e t r i c s _ a g e n t  
 