Udělej test claimů na bannery pro Království zdraví před Black Friday. Výsledkem budou dvě sady po 6 bannerech: ze života (UGC) a od grafika.

Produkt: Královské Magnesium bisglycinát, 90 kapslí
https://www.kralovstvizdravi.cz/doplnky-stravy-spanek--nervy--stres/kralovske-magnesium-bisglycinate-90-kapsli/
Fotka produktu bez pozadí: banner-generator/banners-kz/magnesium-cutout.png (když ji nemáš, stáhni hlavní fotku ze stránky produktu).

Řiď se skilly (v PPC asistentovi je máš, jinak si je přečti tady):
- hooky: https://github.com/placementppc/ppc-asistent/blob/main/.claude/skills/hooky/SKILL.md
- bannery: https://github.com/placementppc/ppc-asistent/blob/main/.claude/skills/bannery/SKILL.md
- brand manuál: https://github.com/placementppc/ppc-asistent/blob/main/.claude/skills/brand-manual/SKILL.md

SADA ZE ŽIVOTA (složka UGC)

1. Nejdřív si přečti stránku produktu a recenze. Zákazník Království zdraví: hlavně ženy 45–54, vaření a domácnost, mluví se jako kamarád, ne jako laboratoř.
2. Navrhni 8 hooků na situaci zákazníka (situace, moment dne, námitka, pro koho). Každý ohodnoť 1–5: zastaví scroll? je jasné, co prodáváme? sedí na pravidla pro doplňky stravy? Vyber 3 nejlepší různých typů a napiš proč. Žádná sleva, žádné „Black Friday“, žádné superlativy.
3. Ke každému hooku napiš podnadpis se schváleným zdravotním tvrzením EU (hořčík přispívá ke snížení míry únavy a vyčerpání) a CTA „Vyzkoušet“.
4. Ke každému hooku navrhni jiný koncept: jiná mikro-persona a jiný styl. Jeden profi lifestyle foto, jeden UGC fotka z mobilu (jako by ji vyfotila zákaznice), jeden nativní obrázek ze života (třeba ručně psaný pondělní seznam úkolů na kuchyňské lince, text píše kód). Prázdné pozadí s malým produktem nestačí. Žádné dva bannery se stejným obrázkem: Meta (Andromeda) by je brala jako jednu reklamu. Počkej, až to schválím.
5. Pak vygeneruj 3 bannery 1080×1350, každý s vlastním obrázkem (vzor configs/ukazka-black-friday.ts). Barvy a font podle brand manuálu.
6. K nim udělej Black Friday verzi vítěze (než test doběhne, toho s nejlepším hodnocením hooku), poslední den a Vánoce (vzor BF1, BF2 a V1 ve stejném configu). Slevu a termín se mě zeptej, nevymýšlej je.
7. Zkontroluj text na každém banneru (diakritika, překlepy). Kde text nesedí do volného místa, posuň ho (--relayout, nic nestojí).

SADA OD GRAFIKA (složka grafika)

8. Pak znovu podle skillu bannery udělej sadu „od grafika“: 6 bannerů 1080×1350 bez obrazové AI (vzor banner-generator/configs/kz-grafik.ts, když ho nemáš: configs/ukazka-grafik.ts; podklad skládá kód přes lib/grafik.ts).
   - Skutečná fotka produktu se stínem, logo z banners-kz/brand/, barvy a font podle brand manuálu.
   - Jen skutečná data z webu: hvězdy s průměrným hodnocením a počtem hodnocení, 2–3 fakta ze stránky produktu. Nic nevymýšlej.
   - Stejné 3 hooky jako v sadě ze života, každý jiné rozvržení: produkt v kruhu s fakty a hodnocením, velké číslo jako hlavní prvek, přeškrtnutý seznam.
   - K tomu Black Friday verze (zlaté kolečko se slevou, termín ve štítku, i 1080×1920 pro Stories), poslední den (tmavé pozadí, obří sleva) a Vánoce (tmavé teplé pozadí se světýlky). Sleva a termín stejné jako v kroku 6.
   - Druhý řádek nadpisu v akcentní barvě, nic menšího než 30 px, CTA jako zaoblená pilulka.

ULOŽENÍ A TEST

9. Ulož všechno na plochu do složky „KZ test claimů“ se dvěma podsložkami: „UGC“ (6 bannerů ze života) a „grafika“ (6 bannerů od grafika a k tomu Stories verze Black Friday). Ukaž mi obě sady vedle sebe.
10. Napiš, jak je nastavit do testu v Metě: jedna sada reklam, stejný rozpočet, 5–7 dní, rozhoduje cena za nákup.
