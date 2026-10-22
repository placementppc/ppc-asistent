/**
 * Hlídač účtu — Google Ads skript (jen čte, v účtu nic nemění)
 *
 * Běží u Googlu, takže hlídá i v sobotu večer se zavřeným počítačem.
 * Ráno porovná včerejšek s běžným dnem (medián 28 dní), večer pohlídá,
 * jestli dnešek neutíká nebo nestojí. E-mail pošle JEN když je problém.
 *
 * Stejná pravidla jako scripts/hlidac/kontroly.py (PPC asistent, skill /hlidac).
 *
 * Instalace: Google Ads → Nástroje → Hromadné akce → Skripty → „+“ → vložit
 * celý soubor → vyplnit EMAIL → Autorizovat → Náhled → Spustit.
 * Frekvence: „Každou hodinu“. Skript sám pozná, kdy je ranní a kdy večerní
 * hodina, v ostatních hodinách hned skončí.
 */

// ============================== NASTAVENÍ ==================================
const CONFIG = {
  EMAIL: '',               // kam poslat upozornění, víc adres oddělte čárkou
  RANNI_HODINA: 7,         // v kolik vyhodnotit včerejšek (časové pásmo účtu)
  VECERNI_HODINA: 20,      // v kolik zkontrolovat dnešek
  MIN_UTRATA: 100,         // účty s menší běžnou denní útratou nehlídat

  UTRATA_STOJI: 0.20,      // včera pod 20 % běžného dne → červená
  UTRATA_UTIKA: 1.60,      // včera přes 160 % běžného dne → červená
  ZOBRAZENI_PROPAD: 0.50,  // zobrazení pod 50 % → žlutá
  CPC_SKOK: 1.40,          // CPC o 40 % dráž → žlutá
  CPC_MIN_PROKLIKU: 20,
  KONVERZE_MIN_BEZNE: 2,   // nulu konverzí hlásit, když běžně padají aspoň 2 denně
  DNES_UTIKA: 1.30,        // večer: dnes víc než 130 % běžného celého dne
  DNES_STOJI: 0.20,        // večer: dnes pod 20 % běžného dne
};
// ===========================================================================

function main() {
  const tz = AdsApp.currentAccount().getTimeZone();
  const hodina = Number(Utilities.formatDate(new Date(), tz, 'H'));
  // Ruční test: dočasně nastavte RANNI_HODINA na aktuální hodinu a klikněte na Náhled.
  let rezim;
  if (hodina === CONFIG.RANNI_HODINA) rezim = 'rano';
  else if (hodina === CONFIG.VECERNI_HODINA) rezim = 'vecer';
  else { console.log('Hodina ' + hodina + ': nic k hlídání.'); return; }

  const den = (offset) => Utilities.formatDate(new Date(Date.now() - offset * 864e5), tz, 'yyyy-MM-dd');
  const dnes = den(0);
  const hodnocenyDen = rezim === 'rano' ? den(1) : dnes;
  const dny = denniSoucty(den(29), dnes);
  const zaklad = beznyDen(dny, hodnocenyDen);

  let nalezy = [];
  if (!zaklad) {
    nalezy.push(['🟡', 'Málo historie (méně než 7 dní) — není s čím porovnat.']);
  } else if (zaklad.utrata > CONFIG.MIN_UTRATA) {
    const d = dny[hodnocenyDen] || { utrata: 0, zobrazeni: 0, prokliky: 0, konverze: 0 };
    nalezy = rezim === 'rano' ? vyhodnotDen(d, zaklad) : vyhodnotDnes(d.utrata, zaklad.utrata, hodina);
  }
  const zamitnute = pocetZamitnutych();
  if (zamitnute) nalezy.push(['🟡', 'Zamítnuté aktivní reklamy: ' + zamitnute + '.']);

  const ucet = AdsApp.currentAccount().getName();
  if (!nalezy.length) { console.log(ucet + ': v pořádku.'); return; }
  const text = nalezy.map((n) => n[0] + ' ' + n[1]).join('\n');
  console.log(text);
  if (CONFIG.EMAIL) {
    const cervena = nalezy.some((n) => n[0] === '🔴');
    MailApp.sendEmail(CONFIG.EMAIL,
      (cervena ? '🔴 ' : '🟡 ') + 'Hlídač: ' + ucet + ' (' + (rezim === 'rano' ? 'včera ' : 'dnes ') + hodnocenyDen + ')',
      text + '\n\nSkript jen hlásí, v účtu nic nezměnil.');
  }
}

function denniSoucty(od, doDne) {
  const out = {};
  const rows = AdsApp.search(
    'SELECT segments.date, metrics.cost_micros, metrics.impressions, metrics.clicks, metrics.conversions ' +
    "FROM customer WHERE segments.date BETWEEN '" + od + "' AND '" + doDne + "'");
  for (const r of rows) {
    out[r.segments.date] = {
      utrata: Number(r.metrics.costMicros) / 1e6,
      zobrazeni: Number(r.metrics.impressions),
      prokliky: Number(r.metrics.clicks),
      konverze: Number(r.metrics.conversions),
    };
  }
  return out;
}

function median(xs) {
  const s = xs.slice().sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

// Běžný den = medián posledních 28 dní s daty před hodnoceným dnem (stejně jako kontroly.py).
function beznyDen(dny, datum) {
  const hist = Object.keys(dny).filter((d) => d < datum).sort().slice(-28).map((d) => dny[d]);
  if (hist.length < 7) return null;
  const prokliky = hist.reduce((a, d) => a + d.prokliky, 0);
  return {
    utrata: median(hist.map((d) => d.utrata)),
    zobrazeni: median(hist.map((d) => d.zobrazeni)),
    cpc: prokliky ? hist.reduce((a, d) => a + d.utrata, 0) / prokliky : 0,
    konverze: hist.reduce((a, d) => a + d.konverze, 0) / hist.length,
  };
}

function kc(x) { return Math.round(x).toLocaleString('cs-CZ'); }

function vyhodnotDen(d, z) {
  const c = CONFIG, out = [];
  if (d.utrata < c.UTRATA_STOJI * z.utrata) {
    out.push(['🔴', 'Útrata spadla na ' + kc(d.utrata) + ' (běžně ' + kc(z.utrata) + '). Zkontroluj platbu, zamítnuté reklamy a pozastavené kampaně.']);
  } else if (d.utrata > c.UTRATA_UTIKA * z.utrata) {
    out.push(['🔴', 'Útrata vyletěla na ' + kc(d.utrata) + ' (běžně ' + kc(z.utrata) + '). Zkontroluj změny rozpočtů a cílů.']);
  }
  if (!out.length && z.zobrazeni && d.zobrazeni < c.ZOBRAZENI_PROPAD * z.zobrazeni) {
    out.push(['🟡', 'Zobrazení spadla na ' + kc(d.zobrazeni) + ' (běžně ' + kc(z.zobrazeni) + ').']);
  }
  if (d.prokliky >= c.CPC_MIN_PROKLIKU && z.cpc && d.utrata / d.prokliky > c.CPC_SKOK * z.cpc) {
    out.push(['🟡', 'Cena prokliku ' + (d.utrata / d.prokliky).toFixed(2) + ' (běžně ' + z.cpc.toFixed(2) + ').']);
  }
  if (z.konverze >= c.KONVERZE_MIN_BEZNE && d.konverze === 0) {
    out.push(['🔴', 'Nula konverzí (běžně ' + z.konverze.toFixed(1) + ' denně). Nejdřív ověř měření.']);
  }
  return out;
}

function vyhodnotDnes(utraceno, bezne, hodina) {
  if (utraceno > CONFIG.DNES_UTIKA * bezne) {
    return [['🔴', 'Dnes už utraceno ' + kc(utraceno) + ', víc než běžný celý den (' + kc(bezne) + ').']];
  }
  if (hodina >= 18 && utraceno < CONFIG.DNES_STOJI * bezne) {
    return [['🟡', 'Do ' + hodina + ':00 utraceno jen ' + kc(utraceno) + ' (běžný den ' + kc(bezne) + '). Reklamy možná nejedou.']];
  }
  return [];
}

function pocetZamitnutych() {
  let n = 0;
  const rows = AdsApp.search(
    'SELECT ad_group_ad.ad.id FROM ad_group_ad ' +
    'WHERE ad_group_ad.status = ENABLED AND ad_group.status = ENABLED AND campaign.status = ENABLED ' +
    'AND ad_group_ad.policy_summary.approval_status = DISAPPROVED');
  for (const r of rows) n++; // eslint-disable-line no-unused-vars
  return n;
}
