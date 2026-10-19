# Bidding strategie — metodika

Cíl: strategie musí sedět na cíl klienta a na objem dat. Konzervativně, postupně.

## Mapa strategie → cíl
| Cíl klienta | Vhodná strategie | Pozn. |
|---|---|---|
| Max objem leadů při daném CPA | tCPA (cílová cena za akci) | potřebuje ~30+ konverzí/měsíc |
| E-shop, návratnost | tROAS (cílová návratnost) | potřebuje hodnoty konverzí + dost dat |
| Max konverze při rozpočtu | Maximalizace konverzí | bez cíle hlídej CPA, ať neujede |
| Max hodnota při rozpočtu | Maximalizace hodnoty konverzí | u e-shopů s hodnotami |
| Málo dat / nová kampaň / kontrola | Manuál / eCPC | dokud není dost konverzí pro smart bidding |
| Brand / max viditelnost | Podíl zobrazení (Target IS) | brandové, ne výkonové |

## Úpravy cílů (tCPA / tROAS) — konzervativně
- Měň cíl **postupně, max o ~10–15 %** za krok, nech doběhnout učící fázi (7–14 dní).
- **Snížení tCPA / zvýšení tROAS** = tlak na efektivitu, ale obvykle nižší objem. Sleduj, ať neutlumí výkon.
- **Zvýšení tCPA / snížení tROAS** = víc objemu, ale dražší. Dělej jen když je prostor v poptávce a plníme cíl s rezervou.
- Nikdy neměň cíl a rozpočet velký skok naráz — nepoznáš, co zabralo.

## Přechody mezi strategiemi
- Na smart bidding (tCPA/tROAS) přejdi, až je **dost konverzí** (řádově 30+/měsíc, ideál 50+).
- Při přechodu počítej s **resetem učení** — krátkodobý výkyv je normální, nehodnoť hned.
- Před přechodem zapiš baseline (CPC, CPA/ROAS, objem) — kvůli vyhodnocení.

## Manuál / eCPC
- Bid úpravy podle pozice, konverzního poměru sestavy, marže.
- Zařízení / lokality / čas — bid adjustmenty jen s dostatkem dat.

## Časté chyby
- Nasazení tROAS/tCPA na kampaň bez dostatku konverzí → divoké chování, špatný výkon.
- Příliš agresivní cíl (moc nízký tCPA / moc vysoký tROAS) → kampaň "umře" (přestane utrácet).
- Hodnocení smart biddingu během učící fáze.
- Ignorování kvality konverzí — optimalizuj na konverze, které mají reálnou hodnotu pro klienta.

## ⚠️ ZMĚNA OD 17. 8. 2026 — Smart Bidding u kampaní omezených rozpočtem

**Co se mění (oznámeno Googlem ~měsíc předem):** Kampaně **omezené rozpočtem** se strategií
založenou na cíli (tCPA, tROAS — včetně optimalizace na marži = tROAS s jinou hodnotou;
platí pro Search, Shopping/PMax i Demand Gen) se od 17. 8. 2026 budou **konzistentně snažit
dosáhnout NASTAVENÉHO cíle** i při změnách rozpočtu. Dnes budget-capped kampaň často cíl
„přestřeluje" (cíl tCPA 200 Kč, reálně nakupuje za 100 Kč); nově Google dotáhne skutečné
CPA/ROAS k povolenému stropu — bere cíl jako cenu, kterou jsi ochoten platit.

**Dvě rizika:**
- **Scénář A — zruinovaná marže:** cíl volnější než reálný výkon → CPA skokově vzroste k cíli
  (v příkladu z GAds: reál 52,61 vs. cíl 80 Kč = +52 % nákladů na objednávku).
- **Scénář B — zruinovaný obrat:** cíl přísnější než reálný výkon → algoritmus ztratí
  konkurenceschopnost v aukcích, kampaň se utlumí, propad objednávek.

**Audit (proveď u KAŽDÉHO klienta před 17. 8. 2026):**
1. Najdi kampaně **„omezené rozpočtem"** (lost IS budget) **a zároveň** s tCPA/tROAS.
2. Porovnej **reálné CPA/ROAS (posledních ~30 d) vs. nastavený cíl**:
   - reál výrazně LEPŠÍ než cíl → riziko A → **stáhnout cíl k reálnému výkonu** (Google k tomu
     nasazuje nový nástroj v Doporučeních — „úprava cílů nabídek", tlačítko Použít), pokud je
     klient se současnou ziskovostí spokojen;
   - reál výrazně HORŠÍ než cíl → riziko B → povolit cíl, nebo vyřešit příčinu (struktura).
3. **Budget-capped PMax se vším zbožím** = nejčastější případ: místo živení spirály „chce víc
   spendu" rozdělit strukturu (produkty podle výkonu/kategorií, vlastní rozpočty/cíle).
4. **Po 17. 8.:** denní monitoring klíčových kampaní, automatická pravidla/alerty (Ads i GA4),
   případně skripty. Strategie BEZ cíle (Max. konverze / Max. hodnota bez tCPA/tROAS) se změna
   přímo netýká.

Zdroj: klukzmarketingu.cz (červenec 2026), interpretace oznámení Google.
