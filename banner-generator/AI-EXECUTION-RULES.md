# STRIKTNÍ INSTRUKCE PRO AI AGENTA: SPRÁVA SOUBORŮ, PRODUKTOVÝCH FOTEK A SPOLEHLIVOST

> **URČENO PRO:** Všechny AI asistenty a agentické modely pracující na projektu Banner Generátor.
> **STATUS:** ZÁVAZNÝ PROTOKOL. Porušení těchto pravidel vede k selhání bannerů a nepoužitelným výstupům pro klienta.

---

## 1. ZÁKLADNÍ PRINCIP: STOP HALUCINACÍM A IGNOROVÁNÍ LIMITY

1. **Nikdy nehlaste úspěch před provedením akce:**
   * Je **přísně zakázáno** napsat *"Soubor jsem uložil na plochu"* nebo *"Obrázek je hotový"*, pokud jste fyzicky nesputili příkaz pro uložení/generování a nepřesvědčili se, že soubor na dané cestě opravdu existuje.
2. **Transparentní přiznání neschopnosti / chybějících práv:**
   * Pokud nemáte technickou možnost provést požadovaný krok (např. nemáte přístup k internetu pro stažení fotky z URL, nebo nemáte oprávnění zapisovat na plochu), **OKAMŽITĚ to uživateli napište**:
     > *"Nemohu automaticky stáhnout obrázek z této URL (nemám přístup ke stahování z webu / chybí oprávnění). Prosím, stáhněte fotku ručně a uložte ji do složky X."*
   * **NIKDY** nesmíte neschopnost stažení zamlčet a místo toho vygenerovat fejkový/vymyslený produkt!

---

## 2. PROTOKOL PRO PRÁCI S PRODUKTOVOU FOTKOU (POVINNÝ POSTUP)

Kdykoliv uživatel zadá URL produktu nebo vloží produktovou fotku, musíte postupovat podle následujících 4 kroků bez zkratek:

### KROK 1: Získání reálné fotky z URL
* Pokud uživatel pošle URL odkaz na e-shop:
  1. Použijte své systémové nástroje (`curl`, `wget` nebo stahovač) a stáhněte originální fotku na disk do složky klienta (např. `banners-<klient>/produkt.png`).
  2. Pokud stáhnutí selže, **ZASTAVTE SE** a požádejte uživatele o ruční stažení. 
  3. **ZÁKAZ:** Nikdy nevkládejte pouze textovou URL adresu do promptu obrazového generátoru (Gemini/OpenAI) v naději, že si ji generátor stáhne sám — generátor to NEUMÍ.

### KROK 2: Odstranění bílého pozadí (Pravidlo č. 6)
* Produkty z e-shopů mají často bílé neprůhledné pozadí (JPEG/PNG).
* **ZÁKAZ:** Nikdy neposílejte fotku s bílým čtvercem přímo do obrazového generátoru a nespoléhejte na to, že generátor bílé pozadí vymaže na základě textového přání.
* **POVINNÝ POSTUP:** Ještě PŘED spuštěním generování banneru musíte spustit lokální skript / obrázkový nástroj (např. knihovnu `sharp`, `rembg` nebo ořezový skript), který:
  1. Projde pixely produktové fotky.
  2. Vymaže bílé/jednobarevné pozadí.
  3. Uloží čirý transparentní PNG soubor (např. `produkt_transparent.png`).

### KROK 3: Vždy předávat referenční fotku (Reference Image)
* V konfiguraci banneru (`configs/<projekt>.ts`) musíte **vždy natvrdo nastavit cestu k transparentnímu PNG souboru** (`referenceImage` / `inlineData`).
* **ZÁKAZ:** Nikdy nepoužívejte čistě textový prompt bez přiložené fotky pro produkty, které mají reálnou předlohu. Při čistě textovém promptu si AI vymyslí úplně jiný produkt, jiný obal a jinou značku!

### KROK 4: Zachování kontextu při opravách
* Pokud uživatel napíše *"oprav pozadí"* nebo *"uprav text"*, **NESMÍTE** zahodit odkaz na produktovou fotku!
* Produktová fotka musela a musí zůstat stálou referencí pro každý pokus o regeneraci banneru.

---

## 3. VERIFIKAČNÍ CHECKLIST PŘED ODPOVĚDÍ UŽIVATELI

Než napíšete uživateli odpověď, že je úkol hotový, musíte v duchu projít tento checklist:

1. [ ] **Existuje soubor na disku?** (Pokud jsem tvrdil, že ukládám na Plochu, ověřil jsem příkazem, že na `~/Desktop/` soubor skutečně leží?)
2. [ ] **Použil jsem reálný produkt?** (Obsahuje banner přesnou fotku z e-shopu, nebo si generátor vymyslel vlastní obal/krabici?)
3. [ ] **Má produkt transparentní pozadí?** (Není na hnědém/barevném pozadí banneru nehezký bílý obdélník z originální fotky?)
4. [ ] **Zkontroloval jsem text na překlepy?** (Pravidlo č. 8 — přečetl jsem všechny české znaky a diakritiku?)

---

## 4. SHRNUTÍ CHOVÁNÍ AI

| Situace | ❌ ŠPATNÉ CHOVÁNÍ (Zakázáno) | ✅ SPRÁVNÉ CHOVÁNÍ (Povinné) |
| :--- | :--- | :--- |
| **Uživatel dal URL na fotku** | Vloží URL do textu a čeká, že to generátor stáhne. Generátor si vymyslí jiný produkt. | Stáhne fotku na disk. Pokud to neumí, požádá uživatele o stažení. |
| **Fotka má bílé pozadí** | Pošle fotku do generátoru a napíše do promptu "odstraň pozadí". Vznikne bílý box na banneru. | Použije lokální skript (`sharp`/`rembg`), odstraní bílé pozadí na disku a teprve čiré PNG pošle generátoru. |
| **Uživatel chce soubor na Plochu** | Napíše "Máš to na ploše", ale příkaz nespustí nebo selže. | Spustí příkaz pro kopírování, ověří existenci souboru a teprve pak nahlásí hotovo. |
| **Uživatel chce opravu** | AI zapomene na staženou fotku a vygeneruje úplně nový náhodný produkt. | AI zachová referenční fotku a upraví pouze požadovaný prvek. |
