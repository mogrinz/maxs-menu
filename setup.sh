#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if [[ "$EUID" -eq 0 ]]; then
  echo "Run setup as your regular Pi user, without sudo."
  exit 1
fi
umask 077
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
if [[ ! -f .menu.env ]]; then
  printf '%s\n' 'MENU_PORT=8080' > .menu.env
fi
chmod 600 .menu.env
.venv/bin/python configure.py
printf '%s\n' "Setup complete. Run: sudo python3 install_service.py"
