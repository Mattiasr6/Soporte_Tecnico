#!/bin/bash
# Ventana nocturna FT. Todo lo de datos corre en la VM (vía SSH); el train en el host.
# DRY_RUN=1: solo reindex+evaluar+dataset (nunca para el server ni entrena).
set -euo pipefail
RAIZ=~/ft-wilmercito
VM=mattias@100.90.209.98
VMBASE=~/Soporte_Tecnico2/backend-fastapi
DIA=$(date +%Y%m%d)
OUT="$RAIZ/outputs/wilmercito-3b-r1"
GGUF="$HOME/modelos/wilmercito-3b-r1-q4_k_m.gguf"

exec 9>"$RAIZ/nightly.lock"
flock -n 9 || { echo "$(date) noche en curso, salgo" >> "$RAIZ/nightly.log"; exit 0; }
log() { echo "$(date '+%F %T') $1" | tee -a "$RAIZ/nightly.log"; }
alerta() { log "ALERTA: $1"; echo "- $(date '+%F %T') $1" >> "$RAIZ/ALERTAS.md"; }
rollback_serve() { sudo systemctl start llama-server; sleep 30; }

[ -f "$RAIZ/.noche.env" ] && set -a && source "$RAIZ/.noche.env" && set +a
[ -n "${NIGHTLY_JWT:-}" ] || { alerta "falta NIGHTLY_JWT en $RAIZ/.noche.env"; exit 1; }

[ "${DRY_RUN:-0}" = "1" ] || { log "stop serve"; sudo systemctl stop llama-server; }

vme() { ssh -o ConnectTimeout=15 "$VM" "$1"; }

log "reindex"
vme "cd $VMBASE && set -a; source .env; set +a; .venv/bin/python -c \"
import httpx
s = httpx.Client(base_url='http://localhost:5012', timeout=1500)
h = {'Authorization': 'Bearer $NIGHTLY_JWT'}
print(s.post('/api/ia/reindexar', headers=h).json())
\"" | tee -a "$RAIZ/nightly.log"

log "evaluar (gate)"
EV=$(vme "cd $VMBASE && set -a; source .env; set +a; .venv/bin/python -c \"
import httpx
s = httpx.Client(base_url='http://localhost:5012', timeout=1500)
h = {'Authorization': 'Bearer $NIGHTLY_JWT'}
import json
print(json.dumps(s.post('/api/ia/evaluar', headers=h).json()))
\"")
echo "$EV" | tee -a "$RAIZ/nightly.log"
CF=$(echo "$EV" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['ok'])")
N=$(echo "$EV" | python3 -c "import json,sys; print(json.load(sys.stdin)['n'])")
[ "$CF" -ge 9 ] || { alerta "evaluar ok=$CF/$N, aborto noche"; [ "${DRY_RUN:-0}" = "1" ] || rollback_serve; exit 1; }

log "dataset"
vme "cd $VMBASE && set -a; source .env; set +a; .venv/bin/python ~/Soporte_Tecnico2/scripts/ft/build_dataset.py --out ~/ft-wilmercito/data/ft_train.jsonl && .venv/bin/python ~/Soporte_Tecnico2/scripts/ft/validate_dataset.py --in ~/ft-wilmercito/data/ft_train.jsonl" | tee -a "$RAIZ/nightly.log" \
  || { alerta "dataset inválido"; [ "${DRY_RUN:-0}" = "1" ] || rollback_serve; exit 1; }
scp -q "$VM:~/ft-wilmercito/data/ft_train.jsonl" "$RAIZ/data/ft_train.jsonl"

if [ "${DRY_RUN:-0}" = "1" ]; then log "dry-run fin (sin train, serve intacto)"; exit 0; fi

log "train"
if ! timeout 12600 "$RAIZ/venv/bin/python" "$HOME/Proyectos/Soporte_Tecnico2/scripts/ft/train_qlora.py" \
    --data "$RAIZ/data/ft_train.jsonl" --out "$OUT" --epochs 1; then
  alerta "train falló o excedió 3.5h"
  rollback_serve
  exit 1
fi

log "test adapter"
if ! "$RAIZ/venv/bin/python" "$HOME/Proyectos/Soporte_Tecnico2/scripts/ft/test_adapter.py" --adapter "$OUT" --eval "$HOME/Proyectos/Soporte_Tecnico2/data/ft_eval.jsonl"; then
  alerta "adapter peor que base, no se despliega"
  rollback_serve
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

sed -i 's#qwen2.5-3b-instruct-q4_k_m.gguf#wilmercito-3b-r1-q4_k_m.gguf#' ~/run-llama.sh
rollback_serve
curl -s -m 10 http://localhost:8081/health | tee -a "$RAIZ/nightly.log"
log "noche $DIA fin (desplegado r1)"
