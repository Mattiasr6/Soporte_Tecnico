#!/bin/bash
# Ventana nocturna FT: stop serve -> reindex -> evaluar(gate) -> dataset ->
# train -> test adapter -> merge+GGUF -> start serve. Con lock y rollback.
#
# Requiere: ~/ft-wilmercito/venv (unsloth), ~/ft-wilmercito/.noche.env con:
#   NIGHTLY_JWT=<jwt largo de un jefe, solo lectura+reindex>
# Uso manual diurno (no toca el server): DRY_RUN=1 ./nightly.sh
set -euo pipefail
RAIZ=~/ft-wilmercito
RAMA=~/Proyectos/Soporte_Tecnico2
DIA=$(date +%Y%m%d)
OUT="$RAIZ/outputs/wilmercito-3b-r1"
GGUF="$HOME/modelos/wilmercito-3b-r1-q4_k_m.gguf"

exec 9>"$RAIZ/nightly.lock"
flock -n 9 || { echo "$(date) noche en curso, salgo" >> "$RAIZ/nightly.log"; exit 0; }
log() { echo "$(date '+%F %T') $1" | tee -a "$RAIZ/nightly.log"; }
alerta() { log "ALERTA: $1"; echo "- $(date '+%F %T') $1" >> "$RAIZ/ALERTAS.md"; }
rollback_serve() { sudo systemctl start llama-server; sleep 30; }

[ "${DRY_RUN:-0}" = "1" ] || { log "stop serve"; sudo systemctl stop llama-server; }
[ -f "$RAIZ/.noche.env" ] && set -a && source "$RAIZ/.noche.env" && set +a

cd "$RAMA/backend-fastapi" && set -a && source .env && set +a
API=http://localhost:5012
H="Authorization: Bearer ${NIGHTLY_JWT:?falta NIGHTLY_JWT en ~/.ft-wilmercito/.noche.env}"

log "reindex"
curl -s -m 1500 -X POST "$API/api/ia/reindexar" -H "$H" | tee -a "$RAIZ/nightly.log"

log "evaluar (gate)"
EV=$(curl -s -m 1500 -X POST "$API/api/ia/evaluar" -H "$H")
echo "$EV" | tee -a "$RAIZ/nightly.log"
CF=$(echo "$EV" | python3 -c "import json,sys; print(json.load(sys.stdin)['con_fuente'])")
[ "$CF" -ge 9 ] || { alerta "evaluar con_fuente=$CF, aborto noche"; [ "${DRY_RUN:-0}" = "1" ] || rollback_serve; exit 1; }

log "dataset"
"$RAMA/backend-fastapi/.venv/bin/python" "$RAMA/scripts/ft/build_dataset.py" --out "$RAIZ/data/ft_train.jsonl"
"$RAMA/backend-fastapi/.venv/bin/python" "$RAMA/scripts/ft/validate_dataset.py" --in "$RAIZ/data/ft_train.jsonl" \
  || { alerta "dataset inválido"; [ "${DRY_RUN:-0}" = "1" ] || rollback_serve; exit 1; }

log "train"
if ! timeout 12600 "$RAIZ/venv/bin/python" "$RAMA/scripts/ft/train_qlora.py" \
    --data "$RAIZ/data/ft_train.jsonl" --out "$OUT" --epochs 1; then
  alerta "train falló o excedió 3.5h"
  [ "${DRY_RUN:-0}" = "1" ] || rollback_serve
  exit 1
fi

log "test adapter"
if ! "$RAIZ/venv/bin/python" "$RAMA/scripts/ft/test_adapter.py" --adapter "$OUT" --eval "$RAMA/data/ft_eval.jsonl"; then
  alerta "adapter peor que base, no se despliega"
  [ "${DRY_RUN:-0}" = "1" ] || rollback_serve
  exit 1
fi

log "merge+GGUF"
"$RAIZ/venv/bin/python" -c "
from unsloth import FastLanguageModel
model, tok = FastLanguageModel.from_pretrained(model_name='$OUT', load_in_4bit=True)
model.save_pretrained_gguf('$OUT-gguf', tok, quantization_method='q4_k_m')
import glob, shutil
gg = glob.glob('$OUT-gguf/*.gguf')[0]
shutil.move(gg, '$GGUF')
print('GGUF_OK $GGUF')
" | tee -a "$RAIZ/nightly.log"

if [ "${DRY_RUN:-0}" = "1" ]; then log "dry-run fin (serve intacto)"; exit 0; fi
sed -i 's#qwen2.5-3b-instruct-q4_k_m.gguf#wilmercito-3b-r1-q4_k_m.gguf#' ~/run-llama.sh
rollback_serve
curl -s -m 10 http://localhost:8081/health | tee -a "$RAIZ/nightly.log"
log "noche $DIA fin (desplegado r1)"
