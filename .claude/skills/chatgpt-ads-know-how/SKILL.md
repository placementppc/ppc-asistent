---
name: chatgpt-ads-know-how
description: Použij tuto skill, kdykoli se uživatel ptá na "ChatGPT Ads", reklamu v ChatGPT, reklamní platformu OpenAI (OpenAI ads platform / Ads Manager), sponzorované výsledky v ChatGPT, jak nastavit kampaň v ChatGPT, ceny/bidding (CPC/CPM/oCPC), targeting přes context hints, měření (Pixel/Conversions API), reklamní politiky OpenAI, benchmarky a case studies, nebo srovnání ChatGPT Ads s Google/Meta ads. Skill obsahuje 100 ověřených mezinárodních (anglicky psaných) zdrojů a shrnutí know-how pro výkonnostní/PPC agenturu.
---

# ChatGPT Ads — Know-how pro PPC agenturu

> Poznámka k rozsahu: Sestaveno **100 ověřených zdrojů** v primární kategorii (reklama jako platforma) plus doplňkové sekundární zdroje (LLM visibility / ChatGPT pro tvorbu reklam) uvedené zvlášť. Všechny URL pocházejí z reálných vyhledávání (stav k 10. 9. 2026); žádná nebyla vymyšlena. U dat, která nebyla explicitně na stránce, je uveden pouze rok/měsíc – před citací ověřit.

## Co je ChatGPT Ads

ChatGPT Ads je reklamní platforma OpenAI, která zobrazuje placené, jasně označené ("Sponsored"/"Ads") reklamní karty pod odpověďmi ChatGPT. Reklamu vidí pouze uživatelé na tarifech **Free a Go**; Plus, Pro, Business, Enterprise a Edu reklamy nemají. Reklamy se nezobrazují účtům identifikovaným jako mladší 18 let a v Temporary Chats [1][5][7].

**Timeline (2026):** OpenAI oznámilo přístup k reklamě 16. ledna 2026 [57]; ostrý test v USA začal **9. února 2026** pro logged-in dospělé na Free/Go, na startu s CPM cenou ~$60 a managed minimem **$200 000–$250 000** (přes agenturní holdingy Dentsu, Omnicom, Publicis, WPP) [1][5][51]. Minimum bylo sníženo na **$50 000** a poté zcela zrušeno při otevření self-serve **Ads Manageru 5. května 2026** všem US inzerentům [47][48]. Následoval pilot v Kanadě, Austrálii a na Novém Zélandu, poté UK, Mexiko, Brazílie, Japonsko, Jižní Korea (srpen) [5]. Ke konci srpna 2026 se ChatGPT Ads rozšířilo do **31 evropských trhů** (self-serve od 31. 8. 2026) a do Indie/MENA [4][35]. K 31. 8. 2026 platforma podle OpenAI dosáhla **$1 miliardy annualized revenue run rate za méně než 200 dní** a používaly ji "desítky tisíc inzerentů"; OpenAI cílí na **$2,5 mld. reklamních tržeb za rok 2026** [5][51][58].

**Formáty:** základní jednotka je sponzorovaná karta (chat_card) pod odpovědí — brand name, logo, titulek, popis, obrázek, odkaz [73][7]. Přibyly **product feed / shopping kampaně** a **product carousels** pro e-commerce [42][34].

**Kdo může inzerovat:** self-serve v otevřených trzích + přes OpenAI Ads Solutions team, agenturní partneři (Dentsu, Omnicom, Publicis, WPP) a tech partneři (Criteo, StackAdapt, Pacvue, Kargo, Adobe) [75][69].

**Cenový model:** CPM (**default max bid $60**; reálná cena dle Digiday klesla z $60 na "as low as $25" po ~10 týdnech) a CPC (OpenAI doporučuje start **$3–5/klik**); přibyl **oCPC / conversion-optimized (CPA)** bidding. Aukce je **relevance-weighted second-price** — relevantní reklama může vyhrát za nižší bid [74][77][39][45].

**Targeting:** žádná keywords — místo nich **context hints** (přirozený popis konverzací, kde je reklama relevantní, na úrovni ad group, ~280 znaků), plus platform/geo targeting, **custom audiences** (min. ~25 000 matched, doporučeno 100 000+) [85][12][95]. Bez negativních keywords (limit ~25 v setupu); OpenAI testuje exclusion targeting [77][53].

**Měření:** OpenAI **Pixel** a **Conversions API**, UTM parametry, měřicí partneři a MMP integrace (vč. AppsFlyer); reporting v Ads Manageru (impressions, clicks, spend, CTR, CPC, CPM, conversions) [13][14][54]. Landing page nesmí blokovat OAI-AdsBot/OAI-SearchBot [80].

**Klíčové politiky:** reklama neovlivňuje odpovědi ("Answer Independence"), konverzace zůstávají soukromé, žádný prodej dat; zakázané kategorie (adult, gambling, alkohol/tabák, zbraně), restrikce na finance/zdraví/legal (manuální schválení), **žádná politická reklama**; brand safety vyloučení citlivých kontextů [20][68][11].

## Klíčové principy / best practices

1. **Nezaměňuj ChatGPT Ads za Google Search** — CTR je strukturálně nižší (~0,3–1,5 %), zobrazuje se jedna reklama pod odpovědí; měř konverze a blended výsledky, ne CTR [97][94].
2. **Context hints piš jako přirozený jazyk zákazníka**, ne keywords — struktura persona + intent + scope + disqualifier; hint je jediný nástroj vyloučení [85][84].
3. **Landing page je součást targetingu** — OpenAI čte URL a obsah stránky; tematicky přesné stránky, ne homepage [84].
4. **Začni s CPC**, ne CPM — platíš až za klik, čistší data, nižší riziko [77].
5. **Nastav měření (Pixel + Conversions API + UTM) před spuštěním** — last-click podceňuje konverzační kanál; GA4 segment chatgpt/cpc + assisted conversions [99][100].
6. **První ~30 dní ber jako diagnostiku** — neoptimalizuj agresivně v prvním týdnu [78][88].
7. **Účet je částečně nevratný** — country, currency, timezone nelze změnit po potvrzení; připrav business údaje, logo a LP předem [77][81].
8. **Relevance = cena** — v relevance-weighted aukci vyhrává přesnější match za nižší bid [87][85].
9. **Min. 30 dní beze změn kreativy/targetingu** před hodnocením [99].
10. **ChatGPT Ads jako doplněk, ne náhrada** Google/Meta — ovlivňuje fázi zvažování; Google sbírá poptávku, Meta ji tvoří [PMAcademy][Aurelius].
11. **E-commerce: připoj product feed** (CSV/TSV/XML/JSON, refresh až po 15 min) — shopping kampaně a carousels [42][Lengow].
12. **Custom audiences mají vysoké prahy** (~25k min., 100k+ doporučeno) — malé listy nekvalifikují; dej jim vlastní ad group [95].
13. **Sleduj brand safety a relevance** — studie SE Ranking (50 006 komerčních promptů, 20 nik, USA, 23. 7. 2026): reklama na **25,94 %** promptů, **14,35 %** sémanticky nesouvisejících [33][RelevantAudience].
14. **Buduj know-how a data teď** — CPM klesají, konkurence tenká; historie bude výhoda [87][Averi].
15. **Ověřuj kategorii vůči ad policies** před spuštěním — finance, zdraví, legal vyžadují manuální schválení; politika zakázána [20][90].

## Zdroje (100)

### Oficiální OpenAI [oficiální]
1. Our approach to advertising and expanding access to ChatGPT — https://openai.com/index/our-approach-to-advertising-and-expanding-access/ — OpenAI, led 2026 — Principy přístupu OpenAI k reklamě, plán testování v USA.
2. Testing ads in ChatGPT — https://openai.com/index/testing-ads-in-chatgpt/ — OpenAI, úno 2026 (updaty) — Oznámení testu 9. 2. 2026 + průběžné updaty o expanzi trhů.
3. New ways to buy ChatGPT ads — https://openai.com/index/new-ways-to-buy-chatgpt-ads/ — OpenAI, 2026 — Ads Manager beta, CPC bidding, měřicí nástroje.
4. ChatGPT Ads expands across Europe — https://openai.com/index/chatgpt-ads-expands-across-europe/ — OpenAI, srp 2026 — Rozšíření do 31 evropských trhů.
5. A milestone in expanding access to AI — https://openai.com/index/expanding-access-to-ai-with-chatgpt-ads/ — OpenAI, 31. 8. 2026 — $1 mld. run rate za <200 dní, expanze Indie/EU/MENA.
6. Ads in ChatGPT (FAQ) — https://help.openai.com/en/articles/20001047-ads-in-chatgpt — OpenAI Help, 2026 — Eligibility, personalizace, soukromí, ovládání reklam.
7. Ads in ChatGPT: The Basics — https://help.openai.com/en/articles/20001207-ads-in-chatgpt-the-basics — OpenAI Help, 2026 — Formát, delivery, pricing, měření pro inzerenty.
8. ChatGPT Ads (collection) — https://help.openai.com/en/collections/20001223-chatgpt-ads — OpenAI Help, 2026 — Rozcestník všech help článků.
9. Quickstart: Launch your first campaign — https://help.openai.com/en/articles/20001224 — OpenAI Help, 2026 — Vytvoření, spuštění a monitoring první kampaně.
10. Launch Campaigns — https://help.openai.com/en/articles/20001209-launch-campaigns — OpenAI Help, 2026 — Krok-za-krokem spuštění, limity účtu.
11. Create Ads for ChatGPT Ads — https://help.openai.com/en/articles/20001212-create-ads-for-chatgpt-ads — OpenAI Help, 2026 — Best practices pro kreativu a soulad s policies.
12. Create Ad Groups for ChatGPT Ads — https://help.openai.com/en/articles/20001211-create-ad-groups-for-chatgpt-ads — OpenAI Help, 2026 — Organizace ad groups a context hints.
13. Conversion Measurement — https://help.openai.com/en/articles/20001409-conversion-measurement — OpenAI Help, 2026 — Měření konverzí, Pixel vs. CAPI, atribuce.
14. Measure Results — https://help.openai.com/en/articles/20001214-measure-results — OpenAI Help, 2026 — Reporting v Ads Manager Beta.
15. Set up Custom Audiences — https://help.openai.com/en/articles/20001346-set-up-custom-audiences-for-your-campaign — OpenAI Help, 2026 — Custom audiences a jejich nastavení.
16. Set up Measurement Partner Integrations — https://help.openai.com/en/articles/20001416-set-up-measurement-partner-integrations — OpenAI Help, 2026 — Připojení měřicího partnera.
17. Set up Mobile Measurement Partner Integrations — https://help.openai.com/en/articles/20001372-set-up-mobile-measurement-partner-integrations — OpenAI Help, 2026 — Připojení MMP.
18. Conversion-optimized Campaigns — https://help.openai.com/en/articles/20001412-conversion-optimized-campaigns — OpenAI Help, 2026 — Nastavení oCPC kampaní.
19. Ads Manager Availability — https://help.openai.com/en/articles/20001245-ads-manager-availability — OpenAI Help, 2026 — Dostupnost Ads Manageru podle zemí.
20. Ad policies — https://openai.com/policies/ad-policies/ — OpenAI, 2026 — Povolené/zakázané kategorie, obsahové standardy.
21. Advertising Terms — https://openai.com/policies/advertising-terms/ — OpenAI, 2026 — Právní podmínky reklamních služeb.
22. Measurement Pixel (developer docs) — https://developers.openai.com/ads/measurement-pixel — OpenAI, 2026 — oaiq JS Pixel SDK, eventy, advanced matching.
23. OpenAI Ads (developer hub) — https://developers.openai.com/ads — OpenAI, 2026 — Vývojářský rozcestník pro reklamní API/měření.
24. Buy it in ChatGPT: Instant Checkout & Agentic Commerce Protocol — https://openai.com/index/buy-it-in-chatgpt/ — OpenAI, zář 2025 — Instant Checkout, ACP, Stripe.
25. Key concepts – Agentic Commerce — https://developers.openai.com/commerce/guides/key-concepts — OpenAI, 2026 — Product feeds a checkout flows.

### Oborová média [oborové médium]
26. OpenAI will begin testing ChatGPT ads in the U.S. — https://searchengineland.com/openai-begins-testing-ads-inside-chatgpt-467637 — Search Engine Land, led 2026.
27. OpenAI starts testing ChatGPT ads — https://searchengineland.com/openai-starts-testing-chatgpt-ads-468593 — SEL, úno 2026 — Výběr a umístění reklam.
28. ChatGPT ads spotted and they are quite aggressive — https://searchengineland.com/chatgpt-ads-spotted-and-they-are-quite-aggressive-469651 — SEL, 2026 — První reklamy (Adthena).
29. ChatGPT ads expand as more brands and trigger patterns emerge — https://searchengineland.com/acceleration-in-chatgpt-ad-activity-spotted-470346 — SEL, 2026 — Analýza 1 500+ promptů.
30. ChatGPT ads are showing up – a lot — https://searchengineland.com/chatgpt-ads-are-showing-up-alot-472791 — SEL, 2026 — Test 500 dotazů, ~1 z 5 spustí reklamu.
31. ChatGPT ads pilot leaves advertisers without proof of ROI — https://searchengineland.com/openais-ad-platform-cant-tell-advertisers-if-their-money-is-working-472233 — SEL, 2026.
32. ChatGPT ads collapse the wall between SEO and paid media — https://searchengineland.com/chatgpt-ads-collapse-the-wall-between-seo-and-paid-media-469489 — SEL, 2026.
33. Study: ChatGPT ads appear on 26% of commercial prompts — https://searchengineland.com/study-chatgpt-ads-appear-on-26-of-commercial-prompts-484590 — SEL, 2026 — SE Ranking studie.
34. ChatGPT Ads rolls out oCPC campaigns, AAM and product carousels — https://searchengineland.com/chatgpt-ads-rolls-out-ocpc-campaigns-aam-and-product-carousels-484494 — SEL, 2026.
35. ChatGPT Ads are expanding to 31 European countries — https://searchengineland.com/chatgpt-ads-are-expanding-to-31-european-countries-485468 — SEL, srp 2026.
36. OpenAI expands ChatGPT ads globally and builds out its ad stack — https://searchengineland.com/openai-expands-chatgpt-ads-globally-and-builds-out-its-ad-stack-487125 — SEL, 2026.
37. OpenAI takes ChatGPT ads into Europe — https://digiday.com/marketing/openais-ads-business-hits-europe-at-the-six-month-mark/ — Digiday, srp 2026 — 31 EU trhů, GDPR.
38. 'Expand thoughtfully': OpenAI offers ChatGPT ads to new markets — https://digiday.com/media-buying/expand-thoughtfully-openai-offers-chatgpt-ads-to-new-markets-including-the-u-k-brazil-and-japan/ — Digiday, 2026.
39. OpenAI turns on cost-per-click ads inside ChatGPT — https://digiday.com/marketing/openai-turns-on-cost-per-click-ads-inside-chatgpt/ — Digiday, 2026 — CPC $3–5, CPM z $60 na ~$25.
40. As OpenAI's ChatGPT ad delivery improves, the doubts aren't so easily fixed — https://digiday.com/marketing/as-openais-chatgpt-ad-delivery-improves-the-doubts-it-created-arent-so-easily-fixed/ — Digiday, 2026.
41. A closer look at OpenAI's ads manager — https://digiday.com/marketing/a-closer-look-at-openais-ads-manager-and-how-much-work-it-still-needs/ — Digiday, 2026.
42. OpenAI makes it easier to run shopping ads in ChatGPT — https://digiday.com/marketing/openai-makes-it-easier-to-run-shopping-ads-in-chatgpt/ — Digiday, 2026 — Product feed kampaně.
43. OpenAI builds tool to track whether ChatGPT ads convert — https://digiday.com/marketing/openai-builds-tool-to-track-whether-chatgpt-ads-convert/ — Digiday, dub 2026.
44. OpenAI opens up ChatGPT ads manager to the U.S. — https://digiday.com/marketing/openai-opens-up-chatgpt-ads-manager-to-the-u-s-while-promising-third-party-measurement-cpa-bidding/ — Digiday, kvě 2026.
45. OpenAI turns on cost-per-action ads inside ChatGPT — https://digiday.com/marketing/openai-turns-on-cost-per-action-ads-inside-chatgpt/ — Digiday, 2026.
46. ChatGPT Ads Are Here. Now Comes the Hard Part. — https://www.adexchanger.com/inside-the-stack/chatgpt-ads-are-here-now-comes-the-hard-part/ — AdExchanger, srp 2026 — Podcast o měření/atribuci.
47. ChatGPT Ads Have Begun Showing Up For Logged-Out Users — https://www.adexchanger.com/ai/chatgpt-ads-have-begun-showing-up-for-logged-out-users/ — AdExchanger, 2026.
48. Will OpenAI's New Measurement Tools And Ads Manager Prove Its Worth — https://www.adexchanger.com/ai/will-openais-new-measurement-tools-and-ads-manager-prove-its-worth-as-an-ad-channel/ — AdExchanger, kvě 2026.
49. ChatGPT Ads Hit A $1 Billion Run Rate — https://www.adexchanger.com/ai/chatgpt-ads-hit-a-1-billion-run-rate-heres-what-advertisers-say-will-get-them-to-spend-more/ — AdExchanger, zář 2026.
50. How ChatGPT Justifies Its CPMs — https://www.adexchanger.com/daily-news-roundup/friday-28082026/ — AdExchanger, srp 2026.
51. ChatGPT Surpasses $1 Billion in Annualized Ads Revenue — https://www.adweek.com/programmatic/chatgpt-openai-billion-advertising-revenue/ — Adweek, srp 2026.
52. OpenAI Sees Fewer Users Dismissing ChatGPT Ads as It Scales — https://www.adweek.com/media/openai-sees-fewer-users-dismissing-chatgpt-ads-as-it-scales/ — Adweek, 2026.
53. EXCLUSIVE: OpenAI Is Testing Exclusion Targeting for ChatGPT Ads — https://www.adweek.com/programmatic/exclusive-openai-is-testing-exclusion-targeting-for-chatgpt-ads/ — Adweek, 2026.
54. Grubhub and 40 Other Brands Test In-App Measurement in ChatGPT Ads — https://www.adweek.com/media/grubhub-and-40-other-brands-test-in-app-measurement-in-chatgpt-ads/ — Adweek, 2026 — AppsFlyer integrace.
55. How to measure ChatGPT ads as part of the marketing mix — https://adage.com/technology/ai/aa-chatgpt-ads-measurement-tips/ — Ad Age, 2026.
56. How ChatGPT advertising works now—and what's still missing — https://adage.com/technology/ai/aa-chatgpt-ads-ad-tech-what-marketers-still-need/ — Ad Age, 2026.
57. OpenAI to begin testing ads on ChatGPT in the U.S. — https://www.cnbc.com/2026/01/16/open-ai-chatgpt-ads-us.html — CNBC, 16. 1. 2026.
58. OpenAI's ChatGPT ads hits $1 billion annualized run rate — https://www.cnbc.com/2026/08/31/open-ai-chatgpt-ads-revenue.html — CNBC, 31. 8. 2026.
59. OpenAI to start showing ads on ChatGPT in India — https://techcrunch.com/2026/08/27/openai-to-start-showing-ads-on-chatgpts-free-and-go-tiers-in-india/ — TechCrunch, 27. 8. 2026.
60. OpenAI starts testing ads in ChatGPT — https://www.nbcnews.com/tech/internet/openai-starts-testing-ads-chatgpt-rcna258242 — NBC News, úno 2026.
61. OpenAI kicks off test phase for ChatGPT ads — https://www.mmm-online.com/news/openai-kicks-off-test-phase-for-chatgpt-ads/ — MM+M, 2026.
62. OpenAI can't avoid advertising in 2026 — https://www.emarketer.com/content/openai-can-t-avoid-advertising-2026 — eMarketer, 2026.
63. FAQ on ChatGPT Advertising: Formats, costs, early strategies — https://www.emarketer.com/content/faq-on-chatgpt-advertising--formats--costs--early-strategies-win — eMarketer, 2026.
64. OpenAI to introduce ads to all ChatGPT free and Go users in US — https://www.aol.com/articles/openai-expand-ads-chatgpt-free-161835879.html — Reuters (via AOL), 21. 3. 2026.
65. OpenAI to unveil chatbot ads to advertisers — https://tech.yahoo.com/ai/chatgpt/articles/openai-unveil-chatbot-ads-advertisers-034745834.html — Reuters (via Yahoo), 20. 1. 2026.
66. OpenAI to test ads in ChatGPT as it burns through billions — https://tagteam.harvard.edu/hub_feeds/3382/feed_items/17188507 — Ars Technica, 16. 1. 2026.
67. OpenAI Reportedly Planning to "Prioritize" Advertisers — https://futurism.com/artificial-intelligence/openai-chatgpt-sponsored-ads — Futurism, 2026 — Nepotvrzená reportáž The Information.
68. OpenAI Sets Guardrails for Ads in ChatGPT — https://adtechradar.com/2026/03/22/openai-chatgpt-ad-policies/ — AdTechRadar, 22. 3. 2026.
69. Over 1,000 brands now live on ChatGPT ads via Criteo — https://ppc.land/over-1-000-brands-now-live-on-chatgpt-ads-via-criteo-as-ai-conversions-near-2x/ — PPC Land, kvě 2026 — Konverze ~2× vs. search.
70. ChatGPT Serves Ads In Results On Irrelevant Topics — https://www.mediapost.com/publications/article/417172/chatgpt-serves-ads-in-results-on-irrelevant-topics.html — MediaPost, srp 2026.
71. PPC Pulse: Google's Podcast Launch, Demand Gen, ChatGPT Ads — https://www.searchenginejournal.com/ppc-pulse-googles-podcast-launch-demand-gen-chatgpt-ads/565685/ — SEJ, úno 2026.
72. PPC Pulse: ChatGPT Ads CPMs, Ads Decoded Talks Analytics — https://www.searchenginejournal.com/ppc-pulse-chatgpt-ads-cpms-ads-decoded-talks-analytics/566190/ — SEJ, 2026.

### Praktické návody & agentury [praktik/agentura]
73. ChatGPT ads are live: A complete breakdown — https://launchcodex.com/blog/performance-marketing/chatgpt-ads-breakdown/ — Launchcodex, 2026.
74. ChatGPT Ads in 2026: The Complete Guide for Marketers — https://segwise.ai/blog/chatgpt-ads-2026-guide — Segwise, 2026 — Aukce, entry bidy, CPM/CPC rozsahy.
75. ChatGPT Advertising: The Complete 2026 Guide — https://www.2pointagency.com/guides/chatgpt-advertising-the-complete-2026-guide-to-openais-revolutionary-ad-platform/ — 2POINT Agency, 2026.
76. ChatGPT Ads Launch — OpenAI Ads Manager 2026 — https://www.explainx.ai/blog/openai-advertise-in-chatgpt-ads-launch-july-2026 — explainx.ai, 2026.
77. OpenAI Ads Manager: How to set up your first campaign — https://simplified.com/blog/ai-writing/chatgpt-ads-manager-setup — Simplified, 2026 — Setup, nevratná nastavení, bidy.
78. How to Get Started with ChatGPT Ads — https://www.commercepundit.com/blog/openai-ads-manager-guide/ — Commerce Pundit, 2026 — Prvních 30 dní.
79. How to Set Up ChatGPT Ads Manager: Step-by-Step (2026) — https://www.trylapis.com/resources/chatgpt-ads-manager-self-serve-setup-guide — Lapis, 2026 — 5 chyb.
80. ChatGPT Ads step by step (Ads Manager) — https://synlig.ai/en/guides/chatgpt-ads-step-by-step/ — Synlig.ai, srp 2026 — Context hints, pixel/UTM, OAI-AdsBot.
81. How to Set Up ChatGPT Ads in OpenAI Ads Manager (2026) — https://www.ai.cc/blogs/how-to-set-up-chatgpt-ads-campaign-openai-ads-manager-2026-guide/ — AICC, 2026.
82. ChatGPT Advertising: Meet Your Next Revenue Channel — https://www.seo.com/blog/chatgpt-advertising/ — SEO.com, 2026.
83. How to advertise on ChatGPT: What you need to know — https://www.stackadapt.com/resources/blog/how-to-advertise-on-chatgpt — StackAdapt, 2026.
84. ChatGPT Ads Best Practices Guide & B2B Playbook — https://justglobal.com/chatgpt-ads-best-practices-guide-b2b-playbook/ — Just Global, 2026.
85. How to Write Context Hints for ChatGPT Ads — https://guptadeepak.com/guides/context-hints/ — Deepak Gupta, 2026 — 4dílná struktura hintů, 6 chyb.
86. How to Write ChatGPT Ads Context Hints: 12 Best Practices — https://www.trylapis.com/resources/how-to-write-chatgpt-ads-context-hints — Lapis, 2026.
87. ChatGPT Ads: the best practices guide (2026) — https://www.botrank.ai/post/chatgpt-ads-best-practices-guide — Botrank, 2026 — EU launch, min. €15/den.
88. ChatGPT Advertising Best Practices 2026 — https://www.lyfemarketing.com/blog/chatgpt-advertising-best-practices/ — LYFE Marketing, 2026.
89. OpenAI Ad Specs, Creative Guidelines & FAQs — https://www.accuracast.com/faq/openai-ads-specs/ — Accuracast, 2026.
90. OpenAI Ads Policy 2026: What Gets Approved (and Rejected) — https://abmatic.ai/blog/openai-ads-policy-approval-guide-2026 — Abmatic AI, 2026.
91. ChatGPT Ads: Everything Advertisers Need to Know — https://greghal.no/en/blog/chatgpt-ads-everything-advertisers-need-to-know/ — Greg Hal, 2026.
92. ChatGPT Ads, what they cost, how they work, setup guide — https://www.thegrowthsyndicate.com/resources/chatgpt-ads — The Growth Syndicate, 2026.
93. ChatGPT Ads Manager Is Now Open to Everyone — https://neilpatel.com/blog/chatgpt-ads-manager/ — Neil Patel / NP Digital, kvě 2026.

### Case studies & benchmarky [praktik/analytik]
94. ChatGPT Ads Case Studies & Examples: 6 měsíců dat — https://www.contexthints.com/guide/chatgpt-ads-case-studies.html — Context Hints, 2026 — Opascope $60k → 1,49× ROAS.
95. ChatGPT Ads Results: Real Data From Live Campaigns — https://www.q1media.com/pages/case-studies-blogs/chatgpt-ads-part2 — Q1 Media, 2026 — Custom audiences prahy.
96. ChatGPT Advertising Case Study: 5 OpenAI Ads Strategies — https://www.interteammarketing.com/case-study/chatgpt-ads-case-study — InterTeam Marketing, 2026 — B2B SaaS, CPL < 1/2 Google.
97. ChatGPT Ads Conversion Rate Benchmarks by Industry — https://www.trylapis.com/resources/chatgpt-ads-conversion-rate-benchmarks — Lapis, 2026 — CTR 0,3–1,5 %, CVR 4–7 %.
98. 9.2% of ChatGPT Prompts Now Show a Sponsored Ad — https://growbydata.com/chatgpt-advertising-what-the-data-actually-shows/ — GrowByData, čvn 2026.
99. How do you measure the performance of ChatGPT ads? — https://wpseoai.com/blog/how-do-you-measure-the-performance-of-chatgpt-ads/ — WP SEO AI, 2026 — 7 metrik, GA4, ~1,5× ROAS.
100. 5 Performance Benchmarks Early ChatGPT Advertisers Report — https://adventuremedia.ai/blog/5-performance-benchmarks-early-chatgpt-advertisers-are-already-reporting — AdVenture Media, 2026.

### Doplňkové sekundární zdroje (mimo 100) — LLM visibility & srovnání
- AI Search Advertising: ChatGPT vs Google vs Perplexity — https://www.digitalapplied.com/blog/ai-search-advertising-chatgpt-google-perplexity-2026 — Digital Applied [analytik].
- OpenAI Ads vs Google vs Meta: Three-Way Comparison — https://adventuremedia.ai/blog/openai-ads-platform-vs-google-ads-vs-meta-ads-a-three-way-comparison-for-digital — AdVenture Media [praktik].
- ChatGPT Ads vs Google Ads vs Meta Ads (2026) — https://www.aureliusmedia.co/blog/chatgpt-ads-vs-google-ads-vs-meta-ads — Aurelius Media [praktik].
- ChatGPT Ads Explained: OpenAI Ads Manager Guide (2026) — https://performancemarketingacademy.in/blog/chatgpt-ads — PMAcademy [praktik].
- What Is ChatGPT Instant Checkout — https://coalitiontechnologies.com/blog/what-is-chatgpt-instant-checkout — Coalition Technologies [praktik].
- ChatGPT Product Feed (2026) specification — https://www.lengow.com/get-to-know-more/chatgpt-product-feed/ — Lengow [praktik].
- How to Get Your Products Discoverable on ChatGPT Shopping — https://www.e2msolutions.com/blog/how-to-get-your-products-discoverable-on-chatgpt/ — E2M [praktik].
- ChatGPT Instant Checkout: ACP Protocol Retailer Guide — https://www.ekamoira.com/blog/chatgpt-instant-checkout-agentic-commerce-protocol-2026 — Ekamoira [praktik].
- OpenAI revamps shopping experience after Instant Checkout — https://www.cnbc.com/2026/03/24/openai-revamps-shopping-experience-in-chatgpt-after-instant-checkout.html — CNBC [oborové médium].
- Why Optmyzr's AI Beats ChatGPT and Claude at Managing Google Ads — https://www.optmyzr.com/blog/optmyzr-ai-beats-chatgpt-claude-for-google-ads/ — Optmyzr [praktik].
- Inside Google Ads podcast — https://jyll.ca/insidegoogleads — Jyll Saskin Gales [praktik].
- PPC Town Hall — https://www.optmyzr.com/ppctownhall/ — Fred Vallaeys / Optmyzr [praktik].

## Jak skill používat

- **Pro fakta preferuj oficiální OpenAI zdroje** (#1–25). Když trade médium a OpenAI odporují, věř OpenAI docs a označ rozpor.
- **Vždy uváděj číslo zdroje** v hranatých závorkách u konkrétních tvrzení (např. "CPC start $3–5 [39]").
- **Hlídej datum** — platforma se rychle mění. U čísel starších než ~2 měsíce upozorni, že mohou být neaktuální; doporuč ověřit v Ads Manageru nebo OpenAI Help Center.
- **Odděluj primární kategorii** (#1–100) od **sekundární** (LLM visibility / ChatGPT pro tvorbu reklam).
- **Rozlišuj ověřená fakta od spekulací** — "could/plan/reportedly" (např. [67]) prezentuj jako nepotvrzené.
- **Benchmarky jsou směrné** — OpenAI nezveřejnilo cross-advertiser benchmarky; čísla (CTR 0,3–1,5 %, CVR 4–7 %, ~1,5× ROAS, CPM $25–60, CPC $3–5) jsou z třetích stran s velkým rozptylem podle kategorie.
- **Pro český trh:** ČR spadá pod evropskou expanzi (od srpna 2026 [4][35]); před nabídkou klientům ověř aktuální dostupnost self-serve v ČR [19], nastav GDPR-compliant consent [37] a připrav měření (Pixel/CAPI/UTM) dřív, než klient utratí první euro.
