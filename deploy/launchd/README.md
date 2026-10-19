# Hlídače přes launchd (macOS) — pro pokročilé

Běží bez aplikace Claude, jen Python skripty na tvém Macu. Výsledek je pravidlový report
v `reports/` (bez analýzy Claudem). Analýzu si pak spustíš ručně: „projdi dnešní report hlídače".

## Co launchd udělá, když Mac spí

Podle `man launchd.plist`: na rozdíl od cronu launchd zmeškaný běh **spustí po probuzení**.
Když se zmešká víc časů, spustí se **jen jednou**. Proto plist volá `deploy/spust.py --rezim auto`,
který si režim vybere podle aktuálního času:

| Čas spuštění (Praha) | Režim |
|---|---|
| před 9:00 | ráno |
| 9:00–13:59 | víkend: hlídač akcí `--vikend`, ve všední den: ráno |
| pátek 17:00–18:59 | hlídač akcí |
| od 17:00 (mimo pátek do 19:00) | večer |
| 14:00–16:59 | ráno (zmeškané ranní) |

Když Mac v sobotu prospí 7:30 i 10:05 a probudí se v 10:30, proběhne jen víkendový hlídač akcí.

## Nastavení (jednou)

1. Ověř, že hlídač jde spustit ručně z Terminálu ve složce appky:
   ```
   .venv/bin/python deploy/spust.py --rezim rano
   ```
   (Když nemáš `.venv`, uprav v plistu cestu k Pythonu, např. `/usr/bin/python3`.)
2. Zkopíruj plist a nahraď `CESTA_K_APPCE` absolutní cestou ke složce appky:
   ```
   mkdir -p reports
   cp deploy/launchd/cz.ppc-asistent.hlidac.plist ~/Library/LaunchAgents/
   ```
   Nahrazení ti udělá Claude Code: „v ~/Library/LaunchAgents/cz.ppc-asistent.hlidac.plist
   nahraď CESTA_K_APPCE cestou k téhle složce".
3. Zapni:
   ```
   launchctl load ~/Library/LaunchAgents/cz.ppc-asistent.hlidac.plist
   ```
4. Otestuj hned:
   ```
   launchctl start cz.ppc-asistent.hlidac
   ```
   Výstup: `reports/launchd-hlidac.log`, reporty v `reports/hlidac/`.
5. Vypnutí: `launchctl unload ~/Library/LaunchAgents/cz.ppc-asistent.hlidac.plist`

## Co vědět

- Zavřené víko = spánek = nic neběží (doběhne po probuzení, viz výše).
- macOS může skriptu bránit v přístupu ke složkám Dokumenty/Plocha. Když log hlásí
  „Operation not permitted", dej appku mimo tyhle složky (např. `~/ppc-asistent`).
- Klíče zůstávají v `.env` na tvém disku. Nic nejde do cloudu kromě volání reklamních API.
- Na Linuxu použij místo launchd `crontab -e` se stejnými časy a `--rezim rano|vecer|akce|vikend`.
