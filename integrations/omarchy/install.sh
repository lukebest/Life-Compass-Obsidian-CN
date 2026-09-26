#!/usr/bin/env bash
# Install or remove the Compass Omarchy integration.
# Usage: install.sh [--uninstall]
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
if [[ ${1:-} == "--uninstall" ]]; then
  exec python3 "$here/bin/compass" uninstall
fi
exec python3 "$here/bin/compass" install
