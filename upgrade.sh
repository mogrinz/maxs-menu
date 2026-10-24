#!/usr/bin/env bash
set -euo pipefail
release_directory="$(cd "$(dirname "$0")" && pwd)"
# Reuse the actual RC1 installation directory, even if it is version-named.
if [[ $# -gt 0 ]]; then
  menu_target="$1"
else
  menu_target="$(systemctl show bagel-menu.service -p WorkingDirectory --value 2>/dev/null || true)"
  if [[ -z "$menu_target" ]]; then
    echo "No installed service directory found. Pass your existing RC1 installation directory as the argument."
    exit 1
  fi
fi
if [[ ! -f "$menu_target/data/users.json" || ! -f "$menu_target/data/menu-state.json" ]]; then
  echo "The target must be an existing RC1-or-later installation. For a new site, use setup.sh."
  exit 1
fi
sudo python3 "$release_directory/install_network_service.py"
python3 "$release_directory/prepare_update.py" "$menu_target"
cd "$menu_target"
bash setup.sh
sudo python3 install_service.py
echo "Max’s Menu is installed and starts automatically after reboot."
echo "Open your existing editor URL. Accounts, menus, and network settings were retained."
