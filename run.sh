#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ ! -f .menu.env ]]; then
  echo "Run bash setup.sh first."
  exit 1
fi
set -a
source .menu.env
set +a
exec .venv/bin/python app.py
