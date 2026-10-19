#!/bin/bash
# Připraví deploy/vercel/balik/ = kopie skriptů, které funkce na Vercelu spouští.
# Spouštěj z kořene appky:  bash deploy/vercel/priprav.sh
# Klíče ani clients/ se NEKOPÍRUJÍ — ty jdou do Environment Variables ve Vercelu.
set -euo pipefail

KOREN="$(cd "$(dirname "$0")/../.." && pwd)"
CIL="$KOREN/deploy/vercel/balik"

rm -rf "$CIL"
mkdir -p "$CIL/deploy"
# Jen kód (*.py) a vzory konfigurace (*.example.json) — žádná data, reporty ani jiné soubory.
rsync -a --prune-empty-dirs \
  --exclude '__pycache__/' \
  --include '*/' --include '*.py' --include '*.example.json' --exclude '*' \
  "$KOREN/scripts/" "$CIL/scripts/"
cp "$KOREN/deploy/spust.py" "$CIL/deploy/spust.py"

# Pojistka: v balíku nesmí být žádný soubor s klíči
if find "$CIL" -name '.env*' -o -name 'google-ads.yaml' | grep -q .; then
  echo "🔴 V balíku je soubor s klíči — smaž ho a spusť znovu." >&2
  exit 2
fi
echo "✅ Balík připraven v deploy/vercel/balik ($(du -sh "$CIL" | cut -f1))."
