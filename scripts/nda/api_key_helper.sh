#!/bin/sh
# Claude Code `apiKeyHelper` pro NDA relaci: vydá API klíč z Klíčenky macOS.
# Klíč tak neleží v žádném souboru ani v historii příkazů.
# Uložení (jednorázově, klíč se zadá do skryté výzvy):
#   security add-generic-password -s ppc-asistent-anthropic-api -a "$USER" -w
exec /usr/bin/security find-generic-password -s ppc-asistent-anthropic-api -a "${USER:-$(id -un)}" -w
