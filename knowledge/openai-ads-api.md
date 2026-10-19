# OpenAI Ads (ChatGPT Ads) — kde je znalost

> ⚠️ **Tenhle soubor není zdroj pravdy**, jen ukazatel — ať kanál nemá dvě rozcházející se
> dokumentace.

**Zdroj pravdy:**
- skill **`/chatgpt-ads`** (`.claude/skills/chatgpt-ads/` — CLI, bezpečnostní pravidla, playbook
  a reklamní politiky),
- `chatgpt-ads/docs/api-notes.md` (chování API, gating, retry),
- `knowledge/chatgpt-ads-optimalizace.md` (postup optimalizace účtu a ověřené páky).

**Jak s kanálem pracovat:** skill **`/chatgpt-ads`**, který si potřebné načte sám.
CLI: `chatgpt-ads/run.sh <příkaz>` (94 příkazů, dry-run bez `--confirm`).

**Klíč:** `OPENAI_ADS_API_KEY_<NAME>` v konfiguraci appky `chatgpt-ads/`. Napojení krok za krokem:
`docs/napojeni/chatgpt-ads.md`.
