#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
if [[ "$(uname -s)" != Darwin ]]; then
  echo 'This setup script must be run on macOS.' >&2
  exit 2
fi
command -v xcrun >/dev/null || { echo 'Install Xcode Command Line Tools: xcode-select --install' >&2; exit 2; }
xcrun --find clang++ >/dev/null || { echo 'Install Xcode Command Line Tools: xcode-select --install' >&2; exit 2; }
command -v python3 >/dev/null || { echo 'Python 3 not found. Install Python 3.11+ from python.org or Homebrew.' >&2; exit 2; }
python3 - <<'PY'
import sys
if sys.version_info < (3, 11):
    raise SystemExit('EdgeVision requires Python 3.11 or newer')
print('Python:', sys.version)
PY
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
bash scripts/build.sh
python -m pytest -q
printf '\nSetup and tests complete. Next: source .venv/bin/activate; python -m edgevision.camera_probe --index 0 --frames 30\n'
