#!/usr/bin/env bash
# CoastSentinel — démarrage local (Linux / macOS)
set -euo pipefail
cd "$(dirname "$0")"

command -v python3 >/dev/null || { echo "Python 3 requis."; exit 1; }
command -v node >/dev/null || { echo "Node.js requis — https://nodejs.org"; exit 1; }

if [ ! -x backend/.venv/bin/python ]; then
  echo "[1/3] Création de l'environnement Python…"
  python3 -m venv backend/.venv
  backend/.venv/bin/pip install -q --upgrade pip
  backend/.venv/bin/pip install -q -e "backend[science]"
else
  echo "[1/3] Environnement Python déjà prêt."
fi

if [ ! -d frontend/node_modules ]; then
  echo "[2/3] Installation des dépendances frontend…"
  (cd frontend && npm install --no-audit --no-fund)
else
  echo "[2/3] Dépendances frontend déjà installées."
fi

echo "[3/3] Démarrage…"
backend/.venv/bin/python -m uvicorn coastsentinel.api:app --app-dir backend --reload --port 8000 &
API=$!
trap 'kill $API 2>/dev/null || true' EXIT
sleep 3
(cd frontend && npm run dev)
