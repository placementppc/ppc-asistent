---
name: start
description: Průvodce prvním nastavením PPC asistenta — krok za krokem provede uvítáním, NDA, bezpečností, napojením Google Ads / Skliku / Mety / ChatGPT Ads / GA4 / AI bannerů, založením klienta s cíli a limity, hlídači, notifikacemi, nasazením a brand manuálem. Použij při „/start", „nastav mi to", „jak začít", „první spuštění", „průvodce", „napoj účet", „přidej klienta", a VŽDY, když v projektu chybí soubor s přístupy (.env) nebo clients/hlidac-ucty.json. Jde spustit znovu, hotové kroky přeskočí.
---

# Průvodce /start

Provádí studenta nastavením appky. Mluví česky, krátce, bez žargonu. Na konci má student
napojený aspoň jeden systém, jednoho klienta s cíli a nastavené hlídače.

## Pravidla průvodce (platí po celou dobu)

1. **Jeden krok, pak čekej.** Každý krok končí jasnou otázkou nebo úkolem a větou
   „Napiš **hotovo**, až to budeš mít." Dokud student neodpoví, nepokračuj dalším krokem.
   Nikdy nevysyp víc kroků naráz.
2. **Klíče nikdy do chatu.** Když student začne vkládat token, heslo nebo klíč do chatu,
   zastav ho: „Tohle do chatu nepatří. Vlož to do souboru `.env` v editoru." Když už ho vložil,
   řekni mu, ať klíč na straně platformy zneplatní a vydá nový (návod `docs/bezpecnost.md`).
3. **Soubory s klíči nečti ani nevytvářej.** `.env`, `chatgpt-ads/.env` a
   `banner-generator/.env.local` zakládá a vyplňuje člověk (hook `env_guard` ti to stejně
   zablokuje). Ty jen řekneš, který řádek vyplnit. Existenci zjistíš přes `stav.py`, funkčnost
   přes read-only ověřovací příkaz.
4. **Ověřuj, nehádej.** Tvrzení o platformách ber z `docs/napojeni/` a z oficiální dokumentace.
   Co tam není ověřené, řekni jako „neověřeno".
5. **Do účtů nic nezapisuj.** Průvodce jen čte a zakládá soubory v projektu
   (`clients/<klient>.md`, `clients/hlidac-ucty.json`).
6. **Příkazy pouštěj ty**, pokud jde o čtení (ověření napojení, stav). Příkazy, které otevírají
   soubor s klíči nebo prohlížeč (vytvoření `.env`, refresh token), dá student sám:
   v Claude Code řádkem začínajícím `!` (např. `! cp .env.example .env`) nebo v Terminálu.

## Krok 0: zjisti stav (vždy jako první, studentovi neukazuj celé JSON)

```bash
python3 scripts/start/stav.py --json
```

Z výstupu sestav krátký přehled „✅ hotovo / ⬜ chybí" a zeptej se: „Chceš projít všechno od
začátku, nebo jen to, co chybí?" Hotové kroky pak přeskakuj, jen je jednou větou připomeň.

| Klíč ve výstupu | Když je hotovo, přeskoč |
|---|---|
| `python_venv` | instalaci Pythonu v kroku C |
| `env_soubor` | založení `.env` v kroku D (napojení systémů ale ověř příkazem) |
| `env_guard_globalne` | `setup_env_guard.py` v kroku C |
| `klienti` | krok E (nabídni „přidat dalšího klienta") |
| `klienti_bez_nda_udaje` | NDA otázku u všech klientů, kteří v seznamu nejsou (už NDA pole mají). `nda_klienti` jsou jen počty — jména NDA klientů stav.py záměrně nevypisuje |
| `hlidac.existuje` | krok F (nabídni úpravu) |
| `brand_manualy` | krok I u klientů, kteří manuál mají |

Když `stav.py` chybí nebo spadne, zjisti stav ručně: `ls clients/`, `ls -a` (jen existence
souborů, obsah souboru s klíči nikdy).

---

## Krok A: uvítání a co appka umí

Představ appku v pár větách a jedné tabulce:

| Oblast | Co dělá | Jak se spouští |
|---|---|---|
| Bannery | AI bannery a videa pro Metu, Google a Sklik podle brand manuálu klienta | skill `brand-manual`, pak `bannery` |
| Napojení | čte Google Ads, Sklik, Metu, ChatGPT Ads a GA4 přes API | skripty v `scripts/`, `chatgpt-ads/run.sh` |
| Forecast a krycí plán | odhad měsíce a denní plán rozpočtu a obratu | skilly `forecast`, `kryci-plan` |
| Optimalizace | projde účet, navrhne změny, po schválení je zapíše a za čas vyhodnotí | skill `ppc-fachman` + `perf*`, `optimalizace-recepty` |
| Hlídač výkyvů | ráno včerejšek, večer dnešek: stojí, utíká, propad, zamítnuté reklamy | skill `hlidac` |
| Hlídač cílů | plní účet PNO / ROAS / CPA od poslední změny? co s tím | skill `hlidac-cilu` |
| Hlídač akcí | prostor pro škálování i v pátek večer a o víkendu (jen návrhy) | skill `hlidac-akci` |
| Nasazení | hlídače běží samy podle plánu | skill `nasazeni` |

Doplň dvě věty: „Nic v účtech nemění bez tvého schválení. Zápisy jdou vždy nejdřív nanečisto
(dry-run)."

Zeptej se: „Pustíme se do nastavení? Zabere to 30 až 60 minut podle toho, kolik systémů
napojíš. Napiš **hotovo** a jdeme na to."

## Krok B: NDA a podmínky, pod kterými Claude běží

Vysvětli jednou, krátce (fakta ověřená v dokumentaci 19. 10. 2026, zdroje v `docs/nda-rezim.md`):

- Claude zpracovává data na serverech Anthropicu. Co uvidí v relaci, tam odchází.
- **Přihlášení tarifem Pro / Max** = **spotřebitelské podmínky**. Data se použijí k tréninku,
  jen když je v nastavení zapnutý přepínač pro zlepšování modelů
  (claude.ai/settings/data-privacy-controls). Uchování 30 dní při vypnutém, 5 let při zapnutém.
- **API klíč z Claude Console, tarif Team / Enterprise** = **obchodní podmínky** + smlouva
  o zpracování (DPA). Na datech se netrénuje, standardní uchování 30 dní.
- Desktopová aplikace Claude API klíč nepoužije, proto NDA relace běží v Terminálu (`./nda.sh`).

Doporuč: „Zkontroluj si v claude.ai/settings/data-privacy-controls, jak máš nastavený
trénink. Pro klientská data ho měj vypnutý." Počkej na hotovo.

Pak se ptej **u každého klienta zvlášť** (v kroku E, při zakládání klienta):

1. „Je klient pod NDA (smlouva o mlčenlivosti, která zakazuje předávat data třetím stranám)?"
2. Když ano: „Který režim?"
   - **`anonymizace`** — pracuje se v aplikaci Claude, ale data jdou jen přes
     `scripts/google_ads/fetch_safe.py` a `scripts/sklik/fetch.py --anon <klient>`. Názvy
     kampaní se nahradí značkami, zmizí dotazy, texty reklam, URL a brandové kampaně.
     Nejde čistit dotazy ani psát texty podle dat.
   - **`plna-data`** — plná práce, ale jen v NDA relaci `./nda.sh` (API klíč z Klíčenky macOS,
     obchodní podmínky, platí se za spotřebu). Soubor klienta pak **nepatří do `clients/`**, ale
     do `~/ppc-asistent-nda/<klient>/<klient>.md`. Nastavení: `docs/nda-rezim.md`.
3. Zapiš do sekce „Účty a přístupy" v `.md` klienta:
   ```
   - **NDA:** true
   - **NDA režim:** anonymizace
   - **NDA účty:** google:123-456-7890, sklik:123456, meta:act_1234567890
   ```
   Bez NDA stačí `- **NDA:** false`.

Hlídá to kód, ne jen dobrá vůle: `scripts/lib/nda.py` zastaví skript nad NDA účtem v nesprávné
relaci, hook `.claude/hooks/nda_guard.py` nepustí Clauda k NDA složce. Když se objeví hláška
„🔒 NDA", neobcházej ji, řekni studentovi, co má udělat.

## Krok C: bezpečnost (5 minut)

Projdi jako checklist, po každém bodu krátce potvrď. Detail v `docs/bezpecnost.md`.

1. **Python prostředí** (když `python_venv` chybí). Pusť sám:
   ```bash
   python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
   ```
2. **Zákaz čtení klíčů pro všechny projekty na počítači.** Pusť sám (bezpečně opakovatelné):
   ```bash
   python3 scripts/setup_env_guard.py
   ```
   V projektu už pravidla jsou (`.claude/settings.json` → `permissions.deny` + hook
   `nda_guard.py`, který volá `env_guard.py`). Tenhle příkaz je zapne i jinde.
3. **Klíče jen v souborech s klíči**, nikdy v chatu, v e-mailu, ve sdíleném dokumentu ani
   v Gitu. `.gitignore` je hlídá, nemaž z něj řádky.
4. **2FA** na Google účtu, Seznam účtu, Meta Business a OpenAI Ads Manageru. Zeptej se, jestli
   ho student má všude. Když ne, ať si ho zapne dřív, než vydá klíče.
5. **Minimální oprávnění.** Kde to jde, jen čtení: Meta systémový uživatel s `ads_read`
   (stačí na hlídače a analýzy), GA4 role Viewer. Zápisová práva až ve chvíli, kdy je potřebuješ.
6. **Zápisy:** každý zápisový skript jede nejdřív nanečisto. Ostře až `--apply` (Python skripty)
   nebo `--confirm` (ChatGPT Ads), a jen po tvém schválení.
7. **Když klíč unikne:** zneplatni ho na straně platformy a vydej nový. Postup pro každý systém
   je v `docs/bezpecnost.md`.

„Napiš **hotovo**, až budeš mít 2FA a projdeme napojení."

## Krok D: napojení systémů

1. Zeptej se: „Které systémy chceš napojit? Google Ads, Sklik, Meta, ChatGPT Ads, GA4,
   AI bannery (Gemini, volitelně OpenAI)." Doporuč začít Sklikem nebo Metou (jeden token,
   pár minut), Google Ads až potom (pět kroků, asi 20 minut).
2. Když `env_soubor` chybí, ať student sám založí soubor a otevře ho v editoru:
   ```
   ! cp .env.example .env
   ```
   Pak ho otevře v editoru (macOS `! open -e .env`, jinak libovolný textový editor).
3. Pak **jeden systém po druhém**: pošli odkaz na návod, nech studenta projít kroky a vyplnit
   řádky, počkej na hotovo, pusť ověřovací příkaz. Když selže, podívej se do sekce
   „Typické chyby" daného návodu, ne do paměti.

| Systém | Návod | Kam klíč | Ověření (jen čte) |
|---|---|---|---|
| Google Ads | `docs/napojeni/google-ads.md` | `.env` | `.venv/bin/python scripts/google_ads/fetch.py --list-clients` |
| Sklik | `docs/napojeni/sklik.md` | `.env` | `.venv/bin/python scripts/sklik/fetch.py --call client.get` |
| Meta | `docs/napojeni/meta.md` | `.env` | `.venv/bin/python scripts/meta/fetch.py accounts` |
| GA4 | `docs/napojeni/ga4.md` | `.env` (stejné OAuth jako Google Ads) | `.venv/bin/python scripts/ga4/fetch.py properties` |
| ChatGPT Ads | `docs/napojeni/chatgpt-ads.md` | **`chatgpt-ads/.env`** (vlastní soubor) | `chatgpt-ads/run.sh account` |
| AI bannery | `docs/napojeni/bannery-ai.md` | **`banner-generator/.env.local`** | `python3 scripts/start/stav.py --ai` |

Po každém úspěšném ověření řekni jednou větou, co vidíš (počet účtů, název účtu), a ID účtů
si poznamenej pro krok E. Hodnoty klíčů nikdy nevypisuj.

## Krok E: klient, cíle a limity

Pro každého klienta zvlášť:

1. **Slug**: krátký název bez diakritiky a mezer (`muj-eshop`). Zeptej se na název a web.
2. Zeptej se na NDA (krok B). Při `plna-data` další kroky dělej až v NDA relaci `./nda.sh`
   a soubor ulož do `~/ppc-asistent-nda/<klient>/`, ne do `clients/`.
3. Založ `clients/<klient>.md` z `clients/_TEMPLATE.md` a vyplň:
   - **Profil**: web, obor, typ (e-shop / leady / lokální), sezónnost.
   - **Cíle**: hlavní metrika a hodnota. Vysvětli stručně:
     PNO = náklady / obrat v % (nižší je lepší), ROAS = obrat / náklady,
     CPA = cena za konverzi v Kč, konverze = počet za měsíc.
     Zeptej se i na **měsíční rozpočet** a **měsíční obrat** (cíl), použije je krycí plán.
   - **Limity**: max. denní rozpočet na účet, max. navýšení najednou v % (doporuč 20 %),
     max. navýšení za týden v % (doporuč 30 %). Hlídač akcí nad ně nic nenavrhne.
   - **Účty a přístupy**: ID účtů z kroku D, NDA pole.
4. Ukaž studentovi vyplněnou sekci Cíle a Limity, ať potvrdí čísla. Počkej na hotovo.

Měsíční rozpočet a cíl ber od studenta, nedopočítávej je z krátkého okna dat. Když chce radu,
pusť skill `forecast` až po napojení (pravidlo „nesuď z krátkého okna" v `CLAUDE.md`).

## Krok F: hlídače

1. Vysvětli čtyři druhy (student vybere, které chce u kterého účtu):

   | `hlidat` | Co | Skript |
   |---|---|---|
   | `vykyvy` | náhlé výkyvy proti běžnému dni (ráno včerejšek, večer dnešek) | `scripts/hlidac/hlidac.py` (`--dnes` večer) |
   | `cile` | plnění cíle od poslední změny v účtu + návrhy | `scripts/hlidac/cile.py` |
   | `akce` | kde je prostor škálovat (jen návrhy, nic nemění) | `scripts/hlidac/akce.py` |
   | `kryci-plan` | skutečnost vs. denní krycí plán | `scripts/plan/plneni.py --klient <k>` |

2. Zeptej se **kdy**: frekvence (`denne`, `pracovni-dny`, `tydne`, `vlastni`), časy (doporuč
   7:30 a 19:00), hlídač akcí (doporuč pátek 18:00, sobota a neděle 10:00 — o víkendu se
   v účtu nikdo nedívá a přitom se tam rozhoduje o rozpočtech). Časové pásmo Europe/Prague.
3. Zapiš `clients/hlidac-ucty.json` (vzor `scripts/hlidac/ucty.example.json`):
   ```json
   {
     "planovani": {"frekvence": "denne", "casy": ["07:30", "19:00"],
                   "akce_casy": ["fri 18:00", "sat 10:00", "sun 10:00"], "timezone": "Europe/Prague"},
     "notifikace": {"kanal": "zadny", "poznamka": "napojení viz docs/notifikace.md"},
     "ucty": [{
       "nazev": "Můj e-shop", "klient": "muj-eshop", "system": "google",
       "id": "123-456-7890", "min_utrata": 100,
       "hlidat": ["vykyvy", "cile", "akce", "kryci-plan"],
       "cile": {"typ": "pno", "hodnota": 15, "mesicni_rozpocet": 30000, "mesicni_obrat": 200000},
       "limity": {"max_denni_rozpocet": 1500, "max_navyseni_pct": 20, "max_navyseni_tyden_pct": 30}
     }]
   }
   ```
   - `system`: `sklik | meta | google`. ChatGPT Ads hlídače zatím nečtou.
   - `id`: Sklik userId (číslo), Meta `act_…`, Google customer ID.
   - `cile` a `limity` přepiš z `clients/<klient>.md`, ať se neliší.
   - `posledni_zmena` (YYYY-MM-DD) jen když ji student zná; jinak ji hlídač cílů najde
     v changelogu klienta.
   - NDA účty v režimu `plna-data` sem nedávej, dokud hlídače neběží v NDA relaci.
4. Ověř hned (jen čte):
   ```bash
   .venv/bin/python scripts/hlidac/hlidac.py
   ```
   Exit 0 = v pořádku, 1 = něco žluté, 2 = červené nebo účet nejde načíst. Ukaž první řádky
   reportu z `reports/hlidac/<datum>.md`. Když účet nejde načíst, vrať se k ověření v kroku D.

## Krok G: notifikace (jen nabídnout)

Řekni: „Hlídač píše report do `reports/`. Aby ti přišel sám, potřebuje kanál: e-mail, Slack,
Telegram nebo jiný. Možnosti a postup jsou v `docs/notifikace.md`. Napojení si doladíš
se svým Claude Code, já zapíšu jen volbu." Zapiš zvolený kanál do `notifikace.kanal`
v `clients/hlidac-ucty.json` (`email | slack | telegram | jiny | zadny`). Žádné tokeny ani
webhooky do toho souboru nepatří, ty jdou do `.env`.

## Krok H: kde to poběží

Shrň čtyři varianty jednou větou každou a nech vybrat (detail v `docs/nasazeni.md`,
nastavení pak skill `nasazeni`):

1. **Naplánovaná úloha v aplikaci Claude** — nejjednodušší, ale běží jen když je počítač
   zapnutý a aplikace otevřená.
2. **Claude Code cloud routine** — běží u Anthropicu i při zavřeném počítači, klíče ale musí
   do cloudového prostředí.
3. **GitHub Actions** — běží v cronu na GitHubu, klíče v GitHub Secrets.
4. **Vercel cron** — podobně jako GitHub Actions, klíče v proměnných projektu na Vercelu.

Volbu předej skillu `nasazeni`, ten to nastaví. Připomeň: u NDA klienta v režimu `plna-data`
nedávej klíče ani data do cloudu bez souhlasu klienta.

## Krok I: brand manuál a bannery

Když student chce bannery: „Nejdřív brand manuál klienta (barvy, písmo, tón, co nesmí).
Spusť skill `brand-manual`, vznikne `banner-generator/banners-<klient>/BRAND-MANUAL.md`.
Bannery pak dělej jen přes skill `bannery`, ten načte pravidla generátoru." Předpoklad:
`npm install` v `banner-generator/` a klíč v `banner-generator/.env.local` (krok D).

## Krok J: závěr

1. Pusť znovu `python3 scripts/start/stav.py` a ukaž studentovi přehled.
2. Shrň v pár řádcích: napojené systémy, klienti (s NDA režimem), hlídače a kdy běží, kanál
   notifikací, kde poběží, co ještě chybí.
3. Dej **tři první příkazy**, které vyzkoušet (napiš je přesně tak, jak je má napsat Claudovi):
   - „Projdi účet klienta muj-eshop" (skill `ppc-fachman`, nic nemění)
   - „Udělej krycí plán pro muj-eshop na příští měsíc" (skill `kryci-plan`)
   - „Pusť hlídač akcí" (skill `hlidac-akci`, jen návrhy)
   Místo `muj-eshop` dosaď slug skutečného klienta.
4. Rozluč se větou: „Průvodce kdykoli pustíš znovu přes `/start`, hotové kroky přeskočí."
