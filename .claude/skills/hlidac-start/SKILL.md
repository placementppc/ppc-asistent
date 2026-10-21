---
name: hlidac-start
description: >
  Průvodce, jak začít s PPC hlídačem: tři úrovně od nejjednodušší (ruční export za včerejšek a prompt),
  přes AI agenta v prohlížeči, po napojení přes API a automatický běh s e-mailem (aplikace Claude,
  GitHub Actions, Vercel cron). Zeptá se, co uživatel má, doporučí úroveň a provede ho krok za krokem.
  Použij, když uživatel řekne „chci hlídač“, „jak začít s hlídačem“, „zprovozni hlídač“, „nemám API“,
  „hlídač bez programování“, „hlídač přes prohlížeč“, „ať mi to chodí e-mailem“, „z webináře hlídač“.
---

# Hlídač: jak začít

Hlídač každé ráno porovná včerejšek s běžným dnem a ukáže jen to, co svítí. Ve výchozím stavu
**jen čte**, do účtů nesahá. Dá se rozjet ve třech úrovních. Začni nižší a přidávej.

## 1. Zeptej se (jedno kolo)

1. Které systémy: Google Ads, Meta, Sklik, GA4?
2. Máš napojené API (soubor s přístupy podle `.env.example`)? Když nevíš, nemáš.
3. Chceš to jednou denně ručně, nebo ať to běží samo a chodí e-mail?
4. Je klient pod NDA? (Pak data jen lokálně, žádné cloudové služby, viz `docs/nda-rezim.md`.)

Podle odpovědí doporuč úroveň a řekni proč, jednou větou.

## Úroveň 1: ruční export (5 minut denně, nic se nenastavuje)

1. Ať uživatel stáhne export po kampaních za včerejšek a za stejný den minulý týden:
   - **Google Ads:** Kampaně → období Včera, porovnat se stejným dnem minulý týden → Stáhnout → CSV.
     Sloupce: Náklady, Prokliky, Konverze, Hodnota konv., Rozpočet, Stav.
   - **Meta:** Správce reklam → Kampaně → Včera → Export → CSV. Utracená částka, Nákupy, Hodnota konverze nákupů.
   - **Sklik:** Kampaně → Včera → Export. Cena, Prokliky, Konverze, Hodnota konverzí, Denní rozpočet.
2. Prompt: `docs/prompty/hlidac-1-rucne.md` (funguje i v ChatGPT a Gemini). Doplní cíl PNO a denní rozpočet.
3. Když export zpracováváš ty: přečti CSV, porovnej, ukaž jen nálezy (pravidla v `.claude/skills/hlidac/SKILL.md`)
   a výstup napiš jako ranní e-mail. Nic si nedomýšlej.

## Úroveň 2: AI agent v prohlížeči (bez API)

1. Agent s prohlížečem (Claude v Chrome, případně agent v ChatGPT) otevře účty, kde je uživatel přihlášený,
   a čísla si přečte sám.
2. Prompt: `docs/prompty/hlidac-2-prohlizec.md`. Klíčové: **jen čte**, nic nemění, u přihlášení, CAPTCHA
   nebo potvrzovacího okna se zastaví.
3. Řekni na rovinu: je to pomalejší a méně spolehlivé než API, rozhraní se mění. Na denní kontrolu jednoho
   dvou účtů stačí, na víc účtů a automatický běh ne.

## Úroveň 3: API a automatický běh s e-mailem

1. **Napojení:** návody v `docs/napojeni/` (google-ads.md, meta.md, sklik.md, ga4.md). Klíče patří jen do
   souboru s přístupy podle `.env.example`, nikdy do chatu. Ověř napojení jedním čtecím během hlídače.
   Celé napojení krok za krokem ukazuje záznam webináře *Optimalizace reklam pomocí AI*:
   https://vzdelavani.placement.cz/webinare/vyhodnocovani-reklam-ai .
   Účastníci webináře Black Friday a Vánoce s AI mají 30 minut technické konzultace zdarma, ať napíšou Jakubovi.
2. **Konfigurace účtů:** `clients/hlidac-ucty.json` podle `scripts/hlidac/ucty.example.json`, cíle a limity.
3. **Kde to poběží:** skill `nasazeni` a `docs/nasazeni.md`. Stručně:
   - **AI agent v aplikaci Claude** (naplánovaná úloha, Local): nejjednodušší, Claude nálezy rovnou rozebere,
     běží když počítač nespí. Cloudová rutina Claude běží i se zavřeným notebookem (klíče v cloudu, ne pro NDA).
   - **GitHub Actions:** zdarma v privátním repu (2 000 min/měsíc), běží vždy, čas v Europe/Prague.
     Šablona `deploy/github-actions/`.
   - **Vercel cron:** když už máte Vercel Pro (Hobby jen 1× denně a jen nekomerčně). Šablona `deploy/vercel/`.
   - **Google Ads skript** `scripts/google_ads_scripts/ucet_hlidac.js`: jen Google Ads, ale běží u Googlu
     každou hodinu a e-mail pošle sám. Dobrá pojistka na víkend.
4. **E-mail:** podle `docs/notifikace.md` (Resend nebo Gmail), jen když něco svítí.
5. Na konci jeden zkušební běh a ukázka, jak vypadá e-mail.

## Pravidla

- Hlídač jen čte. Zápis (rozpočty) jen přes hlídač akcí, nanečisto a po výslovném schválení.
- Klíče nikdy nečti ani nevypisuj. Když chybí, řekni, který název proměnné doplnit.
- Na Black Friday zpřísni hranice a přidej běhy (např. každé 2 hodiny od 10 do 22), po akci vrať zpět.
