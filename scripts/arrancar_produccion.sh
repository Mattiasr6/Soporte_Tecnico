#!/usr/bin/env bash
# Arranca los dos procesos de la v2 en modo produccion: DEBUG=0, sin --reload y con
# los logs en logs/ (no en /tmp, que se limpia al reiniciar la maquina).
#
# Uso: bash scripts/arrancar_produccion.sh
#
# No reinicia nada: si un puerto ya esta escuchando, lo avisa y sigue con el otro.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS="$RAIZ/logs"
mkdir -p "$LOGS"

if ss -tln | grep -q ":5002 "; then
  echo "la API ya esta escuchando en 5002"
else
  cd "$RAIZ/backend-fastapi"
  set -a; source .env; set +a
  nohup .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 5002 >> "$LOGS/api.log" 2>&1 &
  echo "API arrancada -> $LOGS/api.log"
fi

if ss -tln | grep -q ":8001 "; then
  echo "el front ya esta escuchando en 8001"
else
  cd "$RAIZ/frontend-django"
  set -a; source .env; set +a
  nohup .venv/bin/python manage.py runserver --insecure 0.0.0.0:8001 >> "$LOGS/web.log" 2>&1 &
  echo "front arrancado -> $LOGS/web.log"
fi

echo
echo "front: http://$(hostname -I | awk '{print $1}'):8001"
