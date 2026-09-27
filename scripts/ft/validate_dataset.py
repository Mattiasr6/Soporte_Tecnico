"""Valida data/ft_train.jsonl: JSON, roles, no vacíos, sin duplicados, balance.

Uso: .venv/bin/python scripts/ft/validate_dataset.py --in ~/ft-wilmercito/data/ft_train.jsonl
Falla (exit 1) si el dataset no sirve para entrenar.
"""

import argparse
import json
import sys
from collections import Counter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    args = ap.parse_args()

    vistos: set[str] = set()
    clases: Counter[str] = Counter()
    n = 0
    with open(args.inp, encoding="utf-8") as f:
        for i, linea in enumerate(f, 1):
            try:
                obj = json.loads(linea)
            except ValueError:
                print(f"línea {i}: JSON inválido")
                return 1
            msgs = obj.get("messages", [])
            roles = [m.get("role") for m in msgs]
            if roles != ["system", "user", "assistant"]:
                print(f"línea {i}: roles {roles}")
                return 1
            if not all(m.get("content", "").strip() for m in msgs):
                print(f"línea {i}: contenido vacío")
                return 1
            clave = msgs[1]["content"]
            if clave in vistos:
                print(f"línea {i}: duplicada")
                return 1
            vistos.add(clave)
            clases["total"] += 1
            n += 1
    if n < 100:
        print(f"solo {n} pares (mínimo 100)")
        return 1
    print(f"OK: {n} pares válidos, sin duplicados")
    return 0


if __name__ == "__main__":
    sys.exit(main())
