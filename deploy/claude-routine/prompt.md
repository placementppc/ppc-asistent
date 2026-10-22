# Prompt pro naplánovanou úlohu / cloudovou rutinu

Použij pro **naplánovanou úlohu v aplikaci Claude** (Code → Routines → New routine → Local)
i pro **cloudovou rutinu** (`/schedule` nebo claude.ai/code/routines → Cloud).
Nastavení obou je v `docs/nasazeni.md`.

Doporučené úlohy (čas Europe/Prague):

| Úloha | Kdy | Režim v promptu |
|---|---|---|
| Hlídač ráno | denně 7:30 | `rano` |
| Hlídač večer | denně 19:05 | `vecer` |
| Hlídač akcí | pátek 18:05 | `akce` |
| Hlídač akcí víkend | sobota a neděle 10:05 | `vikend` |

Minuty mimo celou hodinu jsou schválně — dokumentace Claude Code píše, že běh naplánovaný
přesně na celou hodinu může začít o několik minut později.

---

## Prompt (zkopíruj celý, změň jen REŽIM)

```
REŽIM: rano

Jsi hlídač reklamních účtů. V účtech NIC neměň. Nespouštěj nic s --apply ani --confirm,
nezakládej, nepauzuj, neměň rozpočty. Jen čti a navrhuj.

1. Příprava (jen v cloudu, lokálně přeskoč):
   - Když chybí clients/hlidac-ucty.json, vytvoř ho z proměnné prostředí HLIDAC_UCTY_JSON
     (python3 -c "import os,pathlib; pathlib.Path('clients').mkdir(exist_ok=True); pathlib.Path('clients/hlidac-ucty.json').write_text(os.environ['HLIDAC_UCTY_JSON'])").
   - Soubor s přístupy (.env) NEZAKLÁDEJ, nečti ani neupravuj. Skripty si přístupy načtou
     samy z proměnných prostředí (nastavené v prostředí rutiny se stejnými názvy jako
     v .env.example). Když je soubor potřeba, založí ho krok mimo Clauda (setup skript
     prostředí, workflow) — ty ne. Hodnoty proměnných nikdy nevypisuj, ani zkrácené.
   - Když chybí knihovny: pip install -r requirements.txt
2. Spusť: python3 deploy/spust.py --rezim <REŽIM>
3. Exit 0 → napiš jednu větu „✅ vše v pořádku" a skonči.
4. Exit 1 nebo 2 → každý 🔴 nález projdi postupem skillu anomalie (měření → změny v účtu →
   web a nabídka → trh a sezóna → aukce), jen čtecími skripty. U hlídače cílů a akcí ber
   návrhy z reportu, ověř je v datech a nic nespouštěj.
5. Výsledek napiš do reports/analyza-<datum>-<REŽIM>.md:
   - nahoře „🔴 X účtů má problém" nebo „✅ vše v pořádku",
   - ke každému účtu s problémem 1–2 věty: co se stalo, ověřená příčina, návrh kroku,
   - co jsi neověřil, označ jako domněnku.
6. Notifikace: zatím žádná. (Když ji napojíš podle docs/notifikace.md, doplň sem krok
   „pošli shrnutí z bodu 5 na <kanál>".)
7. Nic necommituj a nepushuj. V cloudu je výsledek vidět v relaci rutiny.
```

---

## Poznámky

- **Lokální úloha:** pracovní složka = složka appky. `.env` a `clients/` už tam jsou, bod 1 se
  přeskočí. Po vytvoření dej **Run now** a povol nástroje („always allow"), jinak další
  běhy čekají na schválení.
- **Cloudová rutina:** běží na čistém klonu repa z GitHubu, bez `.env` a bez `clients/`.
  Klíče a konfigurace musí být v **proměnných prostředí** cloudového prostředí. Proč ne
  „network secrets" a jak nastavit síť: `docs/nasazeni.md`, varianta B.
- **Krycí plán v cloudu:** `plans/` v klonu chybí (je v `.gitignore`), krok se přeskočí.
