# PPC asistent — projektová konfigurace

PPC asistent pro Google Ads, Sklik, Meta Ads a ChatGPT Ads: analýza a optimalizace účtů,
forecast a denní krycí plán, hlídače výkyvů, cílů a akcí, AI bannery podle brand manuálu.
Mozek optimalizace je skill `ppc-fachman` (`.claude/skills/ppc-fachman/SKILL.md`).

## Začátek

**Když chybí `.env` nebo `clients/hlidac-ucty.json`, nabídni `/start`** (průvodce nastavením,
skill `start`). Stav zjistíš příkazem `python3 scripts/start/stav.py` — soubory s klíči
sám neotvírej, ani kvůli kontrole.

Jinak řekni např. „projdi účet klienta muj-eshop" / „vyhodnoť změny u muj-eshop" /
„pusť hlídač". Workflow: identifikace klienta → vyhodnocení minulých změn → analýza →
návrhy → (po schválení) zápis.

## 🔴 TVRDÁ PRAVIDLA — porušení = chyba, ne styl

1. **Nikdy neprezentuj domněnku jako fakt.** Každé tvrzení je buď **ověřené** (a řekni čím —
   odpověď API, dokumentace, screenshot), nebo **výslovně označené jako domněnka**. Když nevíš,
   řekni „nevím" a ověř to.
2. **U API a knihoven napřed DOKUMENTACE, pak teprve pokusy.** Aktuální dokumentaci ber
   z Context7 MCP (když ho máš) nebo z oficiálních stránek platformy. Žádné střílení endpointů
   a hádání URL. API Googlu, Mety, Skliku i OpenAI se mění.
3. **Chybová hláška platformy je symptom, ne návod.** Než podle hlášky pošleš uživatele
   klikat do administrace, ověř, že to místo opravdu existuje.
4. **Než pošleš uživatele do administrace:** vyčerpej všechno, co jde ověřit programově,
   a pošli ho tam **jednou se všemi body**. Ruční kroky pak po jednom, počkej na „hotovo".
5. **Když stavíš podle funkční reference, udělej diff pole po poli na VŠECH úrovních předem**
   (kampaň / sestava / kreativa / reklama). Detail: `.claude/skills/ppc-fachman/SKILL.md` krok 4b.
6. **Chybu přiznej rovnou a jednou.** Oprav fakt a pokračuj.

## Klíčová pravidla (vždy)

1. **Nikdy neprováděj změny v účtu bez schválení uživatele.** Čtecí skripty (`fetch*.py`,
   hlídače, forecast) jen čtou. Zápisové skripty nejdřív nanečisto (dry-run), ostře až
   `--apply` / `--confirm` a jen se schváleným plánem. Žádné výjimky, ani pro automaty v cronu:
   hlídače a hlídač akcí jen navrhují.
2. **Vše s ohledem na cíle klienta** z `clients/<klient>.md` (cíl PNO / ROAS / CPA / konverze,
   měsíční rozpočet a obrat, limity navýšení).
3. **Vždy zapisuj a uč se** — changelog s baseline v `clients/<klient>.md` → příští běh
   vyhodnotí → poučení. Obecné vzorce do `knowledge/_learnings.md`.
4. Styl: **senior konzervativní** (statistická významnost, postupné kroky, neměnit vše naráz).
4b. **🔴 Nikdy nesuď účet z krátkého okna.** Žádné doporučení k rozpočtu, měřítku ani větu
   „účet nefunguje" nestav na 7denním / 30denním součtu. Povinné minimum je **8 týdnů po
   týdnech** + **měsíční řada za celou historii účtu** (měřítko, sezóna, drift AOV). Krátké
   okno slouží výhradně k vyhodnocení konkrétní změny. Detail:
   `.claude/skills/ppc-fachman/SKILL.md` → Tři pravidla hloubky, bod 1b.
4c. **🔴 Při stavbě remarketingu VŽDY vyluč nakupující** — když funkční publikum v účtu není,
   založ ho (děkovací stránka, `useHistoricData`). **Dělení PC / mobil po kampaních = −100 %
   na úrovni KAMPANĚ** (+ na sestavách jako pojistka). Detail: SKILL.md krok 4b, body 7–8.
5. **Respektuj API limity** (Google Ads kvóty, Sklik `api.limits` / 429, Meta rate limit,
   ChatGPT Ads 600/min na endpoint), ať nezablokujeme klientský účet: žádný paralelní souběh,
   dávkuj, backoff na rate-limit, žádné hromadné zápisy bez schválení a lidské kontroly textů.
   Viz `knowledge/api-limity-bezpecnost.md`.
6. **NDA klienti:** u nového klienta se vždy zeptej, jestli je pod NDA, a zapiš `NDA:`.
   Když `NDA: true`, zeptej se na **režim** a zapiš `NDA režim:` + `NDA účty:`:
   - `anonymizace` — jen `scripts/google_ads/fetch_safe.py` / `scripts/sklik/fetch.py --anon`,
     tajnou složku `clients/.secret/` nikdy nečti;
   - `plna-data` — jen v NDA relaci `./nda.sh` (API klíč, obchodní podmínky), soubory klienta
     mimo repo v `~/ppc-asistent-nda/`.
   Režim **vynucují** `scripts/lib/nda.py` (skripty) a hook `.claude/hooks/nda_guard.py` (soubory).
   Hlášku „🔒 NDA" neobcházej — řekni uživateli, co má udělat. Návod: `docs/nda-rezim.md`.
   Přihlášení tarifem Pro / Max = spotřebitelské podmínky, i když běží v aplikaci Claude.
7. **ChatGPT Ads: každá reklama musí mít UTM pro GA4.** Na každé sestavě plná šablona
   `utm_source=chatgpt&utm_medium=cpc&utm_campaign=…&utm_content=…&utm_term={ad_id}`.
   Před každou aktivací ověř, že žádná sestava nemá prázdnou šablonu (dry-run
   `chatgpt-ads/run.sh plan-apply --file plan.json` ji vypíše u každé sestavy, u běžící kampaně
   `adgroup-detail --json` → `landing_page_configuration.query_string_template`). Chybí-li,
   nespouštět. Za 48–72 h po spuštění ověř v GA4, že návštěvy padají do `chatgpt / cpc`.
   Postup: `docs/napojeni/chatgpt-ads.md`.

## Přístupy a bezpečnost

- `.env` (Google Ads, GA4, Sklik, Meta), `chatgpt-ads/.env` (ChatGPT Ads),
  `banner-generator/.env.local` (Gemini, OpenAI). Vzor `.env.example`.
- **Claude soubory s klíči nikdy nečte, nezakládá ani nevypisuje** — blokuje to
  `permissions.deny` v `.claude/settings.json` i hook `env_guard.py`. Pro všechny projekty
  na počítači to zapne `python3 scripts/setup_env_guard.py` (jednou).
- Když chybí proměnná, řekni uživateli, ať ji doplní podle `.env.example` a návodu
  v `docs/napojeni/`. Hodnotu klíče nikdy nechtěj do chatu.
- ID účtů klientů patří do `clients/<klient>.md`, ne do `.env`.
- Souhrn: `docs/bezpecnost.md`.

## Rozcestník skillů

| Skill | Kdy |
|---|---|
| `start` | první nastavení, nový systém, nový klient, nové hlídače |
| `ppc-fachman` | projít / optimalizovat účet, vyhodnotit změny (mozek) |
| `optimalizace-recepty` | „optimalizuj účet" a není jasné co — vybere správný skill |
| `perf` + `perf_srch` / `perf_shop` / `perf_disp` / `perf_meta` | analýza výkonu, srovnání období |
| `anomalie`, `aukce-konkurence`, `dotazy-vylouceni`, `mereni-audit`, `konverze-vs-ga4`, `tempo-rozpoctu`, `report-majitel`, `reklama-vs-stranka` | konkrétní úlohy (viz popis skillu) |
| `pmax-kanaly`, `pmax-produkty`, `nakupy-mobil-pc`, `produktovy-report` | produktové kampaně |
| `meta-strop`, `meta-katalog`, `coverage-matrix` | Meta Ads |
| `forecast` | odhad měsíce z historie účtu |
| `black-friday` | průvodce plánem Black Friday a Vánoc po týdnech, PDF |
| `kryci-plan` | denní krycí plán rozpočtu a obratu, plnění k dnešku |
| `hlidac` | náhlé výkyvy ráno / večer (jen čte) |
| `hlidac-cilu` | plnění cílů od poslední změny + návrhy |
| `hlidac-akci` | prostor pro škálování, i v pátek večer a o víkendu (jen návrhy) |
| `nasazeni` | běh hlídačů v cronu (aplikace Claude, cloud routine, GitHub Actions, Vercel) |
| `brand-manual` | brand manuál klienta před bannery |
| `bannery` | výroba bannerů a videí — **jen přes tenhle skill** |
| `chatgpt-ads`, `chatgpt-ads-know-how` | ChatGPT Ads přes `chatgpt-ads/run.sh` |
| `sklik-ppc`, `sklik-kombinovana-reklama` | tvorba Sklik kampaní a kombinované reklamy |

## Struktura

- `clients/<klient>.md` — vše o klientovi (zdroj pravdy). Šablona `clients/_TEMPLATE.md`.
- `clients/hlidac-ucty.json` — konfigurace hlídačů, vzor `scripts/hlidac/ucty.example.json`.
- `scripts/` — konektory Google Ads, Sklik, Meta, GA4 (`fetch*.py` čtou, ostatní zapisují jen
  s `--apply`), `scripts/hlidac/` (hlídače), `scripts/plan/` (forecast, krycí plán).
  Setup a příkazy: `scripts/README.md`.
- `chatgpt-ads/` — CLI pro ChatGPT Ads (`chatgpt-ads/run.sh`, dry-run bez `--confirm`).
  Playbook kanálu: `.claude/skills/chatgpt-ads/chatgpt-ads-campaign-playbook.md`,
  optimalizace: `knowledge/chatgpt-ads-optimalizace.md`.
- `banner-generator/` — AI bannery, brand manuály v `banner-generator/banners-<klient>/`.
- `knowledge/` — metodika PPC + `_learnings.md`; `knowledge/tvorba-kampani/` pro zakládání
  nových kampaní a reklam.
- `docs/` — napojení systémů (`docs/napojeni/`), bezpečnost, NDA, nasazení, notifikace.
- `reports/`, `plans/` — výstupy (v `.gitignore`).
