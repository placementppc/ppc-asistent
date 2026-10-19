#!/bin/zsh
# NDA relace: Claude Code přes API klíč (obchodní podmínky Anthropicu, bez tréninku, DPA).
# Použití (v běžném Terminálu, ne v aplikaci Claude):  ./nda.sh
# Podrobnosti: docs/nda-rezim.md
set -euo pipefail

DIR="${0:A:h}"
SERVICE="ppc-asistent-anthropic-api"
NDA_DIR="${PPC_NDA_DIR:-$HOME/ppc-asistent-nda}"

if [[ -n "${CLAUDE_CODE_DESKTOP_APP_VERSION:-}" || -n "${CLAUDECODE:-}" ]]; then
  echo "⛔ Spouštěj z běžného Terminálu (Terminal.app), ne z aplikace Claude ani z jiné relace Claude Code."
  exit 1
fi
if ! /usr/bin/security find-generic-password -s "$SERVICE" -a "$USER" >/dev/null 2>&1; then
  echo "⛔ V Klíčence chybí API klíč. Ulož ho (klíč vložíš do skryté výzvy):"
  echo "   security add-generic-password -s $SERVICE -a \"\$USER\" -w"
  exit 1
fi
if ! command -v claude >/dev/null 2>&1; then
  echo "⛔ Nenašel jsem příkaz 'claude' (Claude Code). Nainstaluj ho podle code.claude.com/docs/en/setup."
  exit 1
fi

mkdir -p "$NDA_DIR" && chmod 700 "$NDA_DIR"

# Přednost musí mít náš klíč — tyto proměnné by ho přebily (pořadí ověřeno v dokumentaci).
unset ANTHROPIC_API_KEY ANTHROPIC_AUTH_TOKEN
if [[ -n "${ANTHROPIC_BASE_URL:-}" ]]; then
  echo "⚠️  Ruším ANTHROPIC_BASE_URL — požadavky musí jít přímo na Anthropic."
  unset ANTHROPIC_BASE_URL
fi

SETTINGS=$(printf '{"apiKeyHelper":"%s/scripts/nda/api_key_helper.sh","env":{"PPC_NDA_SESSION":"1","PPC_NDA_DIR":"%s"}}' "$DIR" "$NDA_DIR")

echo "🔐 NDA relace — API klíč z Klíčenky, NDA složka: $NDA_DIR"
echo "   Po startu si ověř příkazem /status, že se používá apiKeyHelper (ne přihlášení Max)."
cd "$DIR"
exec claude --settings "$SETTINGS" --add-dir "$NDA_DIR" "$@"
