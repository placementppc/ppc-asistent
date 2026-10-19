# NDA klienti — jak s nimi v PPC asistentovi pracovat

> Stav ověřený v dokumentaci Anthropicu 19. 10. 2026 (zdroje dole). Tohle není právní rada:
> u NDA s vysokými pokutami ať znění smlouvy porovná právník s podmínkami poskytovatele.

## Proč to řešíme

Claude běží na serverech Anthropicu. Všechno, co v relaci uvidí (výstupy skriptů, přečtené
soubory), tam odchází. Rozhoduje, **pod jakými podmínkami**:

| Jak se přihlašuješ | Podmínky | Trénink na datech | Jak dlouho se data drží |
|---|---|---|---|
| Tarif **Free / Pro / Max** (aplikace Claude i terminál) | spotřebitelské | jen když je zapnutý přepínač pro zlepšování modelů | 30 dní (vypnuto) / 5 let (zapnuto) |
| **API klíč** z Claude Console — NDA relace `./nda.sh` | obchodní + DPA | ne | 30 dní |
| Tarif **Team / Enterprise** | obchodní + DPA | ne | 30 dní (Enterprise po dohodě i nulové uchování) |

Přepínač tréninku: claude.ai/settings/data-privacy-controls. Pro klientská data ho měj vypnutý.

**Pozor na cron:** token z `claude setup-token` (pro běh v GitHub Actions a podobně) podle
dokumentace autentizuje tvým předplatným Pro / Max, takže běh pod ním je pořád pod
spotřebitelskými podmínkami. NDA klient v režimu `plna-data` do takového běhu nepatří.

## Tři cesty pro NDA klienta

### A) Režim `anonymizace` — funguje hned, v aplikaci Claude
Skripty data před zobrazením anonymizují: názvy kampaní se nahradí značkami, zmizí
vyhledávací dotazy, texty reklam, URL a brandové kampaně. Metriky, struktura a zápisy změn
přes číselná ID fungují.
**Ztráta:** nejde čistit dotazy (negativa) ani psát texty reklam podle dat.

```bash
.venv/bin/python scripts/google_ads/fetch_safe.py 123-456-7890 --client muj-eshop --days 30
.venv/bin/python scripts/sklik/fetch.py --user-id 123456 campaigns --anon muj-eshop
```

Syrová data a mapa značek leží v `clients/.secret/` (v `.gitignore`). Claude je nikdy nečte,
hook to zastaví.

### B) Režim `plna-data` — NDA relace přes API klíč
Plnohodnotná analýza jako u běžného klienta, ale v samostatné relaci v Terminálu, placené
podle spotřeby tokenů (ceník na claude.com/pricing). Desktopová aplikace Claude API klíč
nepoužije (dokumentace: Claude Desktop nevolá `apiKeyHelper` ani nečte `ANTHROPIC_API_KEY`),
proto Terminál.

### C) Tarif Team / Enterprise
Všechno (i aplikace Claude) pak běží pod obchodními podmínkami a cesta B není potřeba.
Ceny a minimální počet míst: claude.com/pricing (aktuální stav si ověř tam, mění se).
Kontrola v projektu Team pozná podle typu organizace po přihlášení; hodnoty pro Team /
Enterprise jsme na reálném účtu neověřili, při pochybnostech chrání (bere relaci jako
spotřebitelskou).

## Nastavení cesty B (jednorázově, asi 10 minut, macOS)

`./nda.sh` používá Klíčenku macOS. Na Windows a Linuxu tahle cesta tak, jak je, nefunguje.

1. **Účet v Claude Console** (platform.claude.com): založ organizaci, nastav fakturaci
   a doporučeně i měsíční limit útraty.
2. **API klíč**: v Console vytvoř API klíč a zkopíruj ho (přesné názvy položek v menu
   neověřeny, hledej sekci API keys).
3. **Ulož klíč do Klíčenky** — v Terminálu spusť a klíč vlož do skryté výzvy (nezůstane
   v historii ani v žádném souboru):
   ```bash
   security add-generic-password -s ppc-asistent-anthropic-api -a "$USER" -w
   ```
4. **Spusť NDA relaci** z běžného Terminálu (ne z aplikace Claude), ve složce appky:
   ```bash
   ./nda.sh
   ```
   Skript zruší `ANTHROPIC_API_KEY`, `ANTHROPIC_AUTH_TOKEN` a `ANTHROPIC_BASE_URL` (přebily by
   klíč), založí složku `~/ppc-asistent-nda` s právy jen pro tebe a spustí Claude Code
   s `apiKeyHelper`, který klíč vydá z Klíčenky.
5. V relaci napiš `/status` a zkontroluj, že se používá **apiKeyHelper**, ne přihlášení
   předplatným.
6. Ověř stav: `CLAUDECODE=1 .venv/bin/python scripts/lib/nda.py` → „Relace: obchodni".

## Založení NDA klienta v režimu plná data

- Soubory klienta **nepatří do `clients/`**. Patří do NDA složky v domovském adresáři:
  `~/ppc-asistent-nda/<klient>/<klient>.md` + plány a exporty. Jiné umístění nastavíš
  proměnnou `PPC_NDA_DIR`. Složka není v Dokumentech ani na Ploše, takže ji nesynchronizuje
  iCloud; **zálohuj ji** (Time Machine).
- V `.md` klienta vyplň:
  ```
  - **NDA:** true
  - **NDA režim:** plna-data
  - **NDA účty:** google:123-456-7890, sklik:123456, meta:act_1234567890
  ```
- Zápisové skripty berou cestu k plánu jako argument — plán ulož do NDA složky.
- Do `knowledge/_learnings.md` a do paměti Claude nepatří nic konkrétního o NDA klientovi
  (čtou se v každé relaci) — jen zobecněný vzorec.
- Do `clients/hlidac-ucty.json` NDA účty v režimu plná data nedávej, dokud hlídače neběží
  pod obchodními podmínkami.

## Co kontrola vynucuje — a co ne

**Vynucuje:**
- Skripty (`scripts/lib/nda.py`): Google Ads (každý skript přes `normalize_cid`), Sklik,
  Meta (`fetch.py`, `apply.py` podle `act_…`), GA4. Mimo povolenou relaci skončí hláškou „🔒 NDA".
- Výpisy účtů skryjí NDA klienty (MCC, Meta accounts, GA4 properties).
- Hook `.claude/hooks/nda_guard.py`: mimo NDA relaci nepustí čtení ani úpravy NDA složky
  a tajné složky v `clients/` (u souborových nástrojů podle cesty, u příkazů podle textu).
- `scripts/sanitize.py --reverse` nevypíše skutečné názvy na výstup, jen do souboru v tajné složce.
- **Soubory s klíči** Claude nečte v ŽÁDNÉ relaci, ani NDA (`docs/bezpecnost.md`).

**Nevynucuje (známé limity):**
- Kontrola ve skriptech běží jen uvnitř Claude Code (proměnná `CLAUDECODE`). Skript, který
  pustíš sám v Terminálu nebo v cronu bez Clauda, data k modelu neposílá a nekontroluje se.
- Meta dotaz podle ID kampaně / sestavy (bez `act_…`) — z ID nejde poznat klienta.
- Skript, který si chráněný soubor otevře sám, nebo `grep -r` spuštěný o úroveň výš —
  úplné zamčení by vyžadovalo sandbox Claude Code.
- Když ručně nastavíš proměnnou `PPC_NDA_SESSION=1`, kontrola uvěří, že běží NDA relace.

Testy: `.venv/bin/python -m unittest tests/test_nda.py tests/test_env_guard.py -v`

## Zdroje (ověřeno 19. 10. 2026)

- code.claude.com/docs/en/data-usage — trénink a uchování dat podle typu účtu
- code.claude.com/docs/en/legal-and-compliance — spotřebitelské podmínky pro Free / Pro / Max,
  obchodní pro Team / Enterprise / API
- code.claude.com/docs/en/authentication — pořadí přihlašovacích údajů, `apiKeyHelper`,
  Claude Desktop API klíč nečte, `claude setup-token` = předplatné
- anthropic.com/legal/commercial-terms — „Anthropic may not train models on Customer Content
  from Services", DPA je součástí podmínek
