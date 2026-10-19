/**
 * PMax hlídač kanálů — Google Ads skript (jen čte, v účtu nic nemění)
 *
 * Každý den zapíše do Google Sheetu, kam Performance Max posílá peníze
 * (nákupy, textové vyhledávání, YouTube, Display, Discover, Gmail), jak se
 * hýbe ROAS, cena prokliku, konverzní poměr a průměrná objednávka, a upozorní,
 * když se něco vychýlí. V pondělí (volitelně) pošle týdenní souhrn e-mailem.
 *
 * Instalace: Google Ads → Nástroje → Hromadné akce → Skripty → „+“ → vložit
 * celý tento soubor → Autorizovat → Náhled → Spustit. Pak nastavit frekvenci
 * „Denně“ (doporučeno ráno, např. 7:00).
 *
 * Listy v tabulce: Přehled · Týdně · Denně · Změny · Historie upozornění
 * Metodika: .claude/skills/pmax-kanaly/SKILL.md.
 */

// ============================== NASTAVENÍ ==================================
const CONFIG = {
  // URL Google Sheetu. Prázdné = skript při prvním běhu vytvoří nový a URL
  // vypíše do logu — pak ji sem vložte, jinak vznikne při každém běhu nový.
  SPREADSHEET_URL: '',

  // ID kampaní, které hlídat. Prázdné = všechny PMax kampaně v účtu.
  CAMPAIGN_IDS: [],

  BREAK_EVEN_ROAS: 2.00,   // hranice ziskovosti (1 / marže), 2.00 = 200 % — doplň podle marže klienta
  TARGET_ROAS: 2.50,       // cílový ROAS kampaně — doplň podle cíle klienta

  // E-mail: '' = neposílat. Víc adres oddělte čárkou.
  EMAIL: '',
  EMAIL_ON_ALERT: true,    // poslat i mimo pondělí, když je červené upozornění

  WEEKS: 16,               // kolik celých týdnů (Po–Ne) ukazovat
  DAYS: 42,                // kolik dní ukazovat v listu Denně
  LAG_DAYS: 3,             // posledních N dní se konverze ještě dopočítávají

  MIMO_WARN: 0.05,         // podíl útraty mimo vyhledávání: žlutá od 5 %
  MIMO_ALERT: 0.10,        //                                červená od 10 %
  CPC_WEEK_WARN: 1.15,     // CPC týdne vs. průměr 8 týdnů: žlutá od +15 %
  CPC_DAY_ALERT: 1.5,      // CPC dne vs. průměr 28 dní: žlutá od +50 %
  SPEND_DAY_ALERT: 1.5,    // útrata dne vs. průměr 28 dní: červená od +50 %
  MIN_CONV: 30,            // pod tolik konverzí ROAS nehodnotit (šum)
};
// ===========================================================================

const CHANNELS = [
  { key: 'NAKUPY', label: 'Nákupy (feed)', search: true },
  { key: 'TEXT', label: 'Vyhledávání – text', search: true },
  { key: 'YOUTUBE', label: 'YouTube' },
  { key: 'DISPLAY', label: 'Display' },
  { key: 'DISCOVER', label: 'Discover' },
  { key: 'GMAIL', label: 'Gmail' },
  { key: 'OSTATNI', label: 'Ostatní (Mapy, TV…)' },
];
const CHART_COLORS = ['#1e8e3e', '#4285f4', '#ea4335', '#fbbc04', '#a142f4', '#24c1e0', '#9aa0a6'];
// Číselné kódy enumu AdNetworkType pro případ, že by přišly místo názvů.
const NETWORK_BY_CODE = {
  2: 'SEARCH', 3: 'SEARCH_PARTNERS', 4: 'CONTENT', 7: 'MIXED', 8: 'YOUTUBE',
  9: 'GOOGLE_TV', 10: 'GOOGLE_OWNED_CHANNELS', 11: 'GMAIL', 12: 'DISCOVER', 13: 'MAPS',
};
const RESOURCE_LABELS = {
  CAMPAIGN: 'Kampaň', CAMPAIGN_BUDGET: 'Rozpočet', CAMPAIGN_CRITERION: 'Cílení / vylučování kampaně',
  ASSET_GROUP: 'Skupina podkladů', ASSET_GROUP_ASSET: 'Podklad ve skupině',
  ASSET_GROUP_LISTING_GROUP_FILTER: 'Skupina produktů (listing group)', ASSET_GROUP_SIGNAL: 'Signál publika',
  CAMPAIGN_ASSET: 'Rozšíření kampaně', ASSET: 'Podklad', 5: 'Kampaň', 6: 'Rozpočet',
};
const OPERATION_LABELS = { CREATE: 'přidáno', UPDATE: 'změněno', REMOVE: 'odstraněno', 2: 'přidáno', 3: 'změněno', 4: 'odstraněno' };
const DAY_NAMES = ['Po', 'Út', 'St', 'Čt', 'Pá', 'So', 'Ne'];
const COL = {
  header: '#202124', headerText: '#ffffff', section: '#e8eaed',
  red: '#f4c7c3', yellow: '#fce8b2', green: '#b7e1cd', grey: '#80868b',
};

function main() {
  const account = AdsApp.currentAccount();
  const tz = account.getTimeZone();
  const cur = account.getCurrencyCode();
  const today = Utilities.formatDate(new Date(), tz, 'yyyy-MM-dd');
  const yesterday = addDays(today, -1);

  // Poslední celý týden Po–Ne a okno 16 týdnů + stejné období loni (364 dní = stejný den v týdnu).
  const lastWeekEnd = weekday(yesterday) === 6 ? yesterday : addDays(mondayOf(yesterday), -1);
  const lastWeekStart = mondayOf(lastWeekEnd);
  const weeksStart = addDays(lastWeekStart, -7 * (CONFIG.WEEKS - 1));
  const fetchStart = addDays(weeksStart, -364);

  const data = fetchData(fetchStart, yesterday);
  const d = data.byDay;

  // --- týdny ---
  const weeks = [];
  for (let w = weeksStart; w <= lastWeekStart; w = addDays(w, 7)) {
    const m = metricsOf(sumRange(d, w, addDays(w, 6)));
    const ly = metricsOf(sumRange(d, addDays(w, -364), addDays(w, -358)));
    weeks.push({ start: w, m: m, ly: ly });
  }
  weeks.forEach(function (wk, i) {
    const prev = weeks.slice(Math.max(0, i - 8), i).map(function (x) { return x.start; });
    wk.prev8 = prev.length ? metricsOf(sumRange(d, prev[0], addDays(prev[prev.length - 1], 6))) : null;
    wk.alerts = weekAlerts(wk);
  });

  // --- dny ---
  const days = [];
  for (let i = 0; i < CONFIG.DAYS; i++) {
    const day = addDays(yesterday, -i);
    const m = metricsOf(d[day] || emptyBucket());
    const avg28 = metricsOf(sumRange(d, addDays(day, -28), addDays(day, -1)));
    const lag = i < CONFIG.LAG_DAYS;
    days.push({ date: day, m: m, avg28: avg28, lag: lag, alerts: dayAlerts(m, avg28) });
  }

  // --- souhrnná období pro Přehled ---
  const last = weeks[weeks.length - 1];
  const periods = [
    { label: 'Včera (' + fmtDay(yesterday) + ') *', m: days[0].m, alerts: days[0].alerts },
    { label: 'Posledních 7 dní *', m: metricsOf(sumRange(d, addDays(yesterday, -6), yesterday)), alerts: [] },
    { label: 'Poslední celý týden (' + fmtDay(lastWeekStart) + '–' + fmtDay(lastWeekEnd) + ')', m: last.m, alerts: last.alerts },
    { label: 'Průměrný týden z 8 předchozích', m: scale(last.prev8, 1 / 8), alerts: [] },
    { label: 'Stejný týden loni', m: last.ly, alerts: [] },
  ];
  const roas28 = metricsOf(sumRange(d, addDays(yesterday, -27), yesterday));
  const decomposition = decompose(
    metricsOf(sumRange(d, addDays(lastWeekStart, -7 * 11), addDays(lastWeekStart, -7 * 3 - 1))),
    metricsOf(sumRange(d, addDays(lastWeekStart, -7 * 3), lastWeekEnd)));

  const alerts = [].concat(
    days[0].alerts.map(function (a) { return prefix(a, 'Včera'); }),
    last.alerts.map(function (a) { return prefix(a, 'Minulý týden'); }),
    roasAlerts(roas28));

  const changes = fetchChanges(addDays(today, -14), addDays(today, 1), data.campaignIds);

  // --- zápis ---
  const ss = openSpreadsheet();
  writeWeeks(ss, weeks, cur);
  writeDays(ss, days, cur);
  writeChanges(ss, changes, data.campaignNames);
  writeOverview(ss, {
    account: account.getName(), cur: cur, periods: periods, alerts: alerts,
    decomposition: decomposition, campaigns: campaignTable(data, yesterday),
    changesCount: changes.filter(function (c) { return c.date >= lastWeekStart; }).length,
  });
  writeHistory(ss, today, alerts, tz);
  ss.setActiveSheet(ss.getSheetByName('Přehled'));

  maybeEmail(ss, account.getName(), today, periods, alerts, cur);
  Logger.log('Hotovo: %s', ss.getUrl());
}

// ================================ DATA =====================================

function fetchData(start, end) {
  let where = "campaign.advertising_channel_type = 'PERFORMANCE_MAX' " +
    "AND segments.date BETWEEN '" + start + "' AND '" + end + "'";
  if (CONFIG.CAMPAIGN_IDS.length) where += ' AND campaign.id IN (' + CONFIG.CAMPAIGN_IDS.join(',') + ')';
  const rows = AdsApp.search(
    'SELECT campaign.id, campaign.name, campaign.status, segments.date, ' +
    'segments.ad_network_type, segments.ad_using_product_data, ' +
    'metrics.cost_micros, metrics.clicks, metrics.impressions, ' +
    'metrics.conversions, metrics.conversions_value ' +
    'FROM campaign WHERE ' + where);

  const byDay = {}, byCampDay = {}, campaignNames = {}, campaignStatus = {};
  while (rows.hasNext()) {
    const r = rows.next();
    const id = String(r.campaign.id);
    campaignNames[id] = r.campaign.name;
    campaignStatus[id] = String(r.campaign.status);
    const date = r.segments.date;
    const ch = channelOf(r.segments.adNetworkType, r.segments.adUsingProductData);
    const v = {
      cost: Number(r.metrics.costMicros || 0) / 1e6,
      clicks: Number(r.metrics.clicks || 0),
      conv: Number(r.metrics.conversions || 0),
      value: Number(r.metrics.conversionsValue || 0),
    };
    addTo(byDay[date] = byDay[date] || emptyBucket(), ch, v);
    const key = id + '|' + date;
    addTo(byCampDay[key] = byCampDay[key] || emptyBucket(), ch, v);
  }
  return {
    byDay: byDay, byCampDay: byCampDay, campaignNames: campaignNames,
    campaignStatus: campaignStatus, campaignIds: Object.keys(campaignNames),
  };
}

function channelOf(network, usingProduct) {
  let n = String(network);
  if (/^\d+$/.test(n)) n = NETWORK_BY_CODE[Number(n)] || 'UNKNOWN';
  const product = usingProduct === true || usingProduct === 'true';
  if (n === 'SEARCH' || n === 'SEARCH_PARTNERS') return product ? 'NAKUPY' : 'TEXT';
  if (n === 'YOUTUBE') return 'YOUTUBE';
  if (n === 'CONTENT') return 'DISPLAY';
  if (n === 'DISCOVER') return 'DISCOVER';
  if (n === 'GMAIL') return 'GMAIL';
  return 'OSTATNI';
}

function fetchChanges(since, until, campaignIds) {
  const out = [];
  try {
    const rows = AdsApp.search(
      'SELECT change_event.change_date_time, change_event.user_email, ' +
      'change_event.change_resource_type, change_event.resource_change_operation, ' +
      'change_event.changed_fields, change_event.campaign, change_event.client_type ' +
      "FROM change_event WHERE change_event.change_date_time >= '" + since + "' " +
      "AND change_event.change_date_time <= '" + until + "' " +
      'ORDER BY change_event.change_date_time DESC LIMIT 1000');
    while (rows.hasNext()) {
      const e = rows.next().changeEvent;
      const campId = String(e.campaign || '').split('/').pop();
      if (campaignIds.indexOf(campId) < 0) continue;
      const fields = typeof e.changedFields === 'string' ? e.changedFields
        : ((e.changedFields && e.changedFields.paths) || []).join(', ');
      out.push({
        date: String(e.changeDateTime).slice(0, 10), time: String(e.changeDateTime).slice(0, 16),
        user: e.userEmail || '', type: label(RESOURCE_LABELS, e.changeResourceType),
        op: label(OPERATION_LABELS, e.resourceChangeOperation), fields: fields, campaignId: campId,
      });
    }
  } catch (err) {
    Logger.log('Historii změn se nepodařilo načíst: %s', err);
  }
  return out;
}

// ============================== VÝPOČTY ====================================

function emptyBucket() {
  const ch = {};
  CHANNELS.forEach(function (c) { ch[c.key] = { cost: 0, clicks: 0, conv: 0, value: 0 }; });
  return { cost: 0, clicks: 0, conv: 0, value: 0, ch: ch };
}

function addTo(b, chKey, v) {
  ['cost', 'clicks', 'conv', 'value'].forEach(function (k) { b[k] += v[k]; b.ch[chKey][k] += v[k]; });
}

function sumRange(byDay, from, to) {
  const b = emptyBucket();
  for (let day = from; day <= to; day = addDays(day, 1)) {
    const x = byDay[day];
    if (!x) continue;
    CHANNELS.forEach(function (c) { addTo(b, c.key, x.ch[c.key]); });
  }
  return b;
}

function metricsOf(b) {
  const share = {};
  CHANNELS.forEach(function (c) { share[c.key] = b.cost ? b.ch[c.key].cost / b.cost : 0; });
  const inSearch = share.NAKUPY + share.TEXT;
  return {
    cost: b.cost, clicks: b.clicks, conv: b.conv, value: b.value,
    roas: b.cost ? b.value / b.cost : null,
    cpc: b.clicks ? b.cost / b.clicks : null,
    cr: b.clicks ? b.conv / b.clicks : null,
    aov: b.conv ? b.value / b.conv : null,
    share: share,
    mimo: b.cost ? 1 - inSearch : null,
  };
}

// Průměrný týden: útrata, konverze a hodnota se dělí, poměrové metriky zůstávají.
function scale(m, f) {
  if (!m) return null;
  const out = Object.assign({}, m);
  out.cost = m.cost * f; out.conv = m.conv * f; out.value = m.value * f; out.clicks = m.clicks * f;
  return out;
}

// ROAS = konverzní poměr × průměrná objednávka / CPC → rozklad změny na tři vlivy.
function decompose(before, after) {
  if (!before.roas || !after.roas || !before.cpc || !after.cpc || !before.cr || !after.cr || !before.aov || !after.aov) return null;
  const parts = [
    { label: 'Cena prokliku (CPC)', from: before.cpc, to: after.cpc, effect: before.cpc / after.cpc - 1, log: Math.log(before.cpc / after.cpc) },
    { label: 'Konverzní poměr', from: before.cr, to: after.cr, effect: after.cr / before.cr - 1, log: Math.log(after.cr / before.cr) },
    { label: 'Průměrná objednávka', from: before.aov, to: after.aov, effect: after.aov / before.aov - 1, log: Math.log(after.aov / before.aov) },
  ];
  const total = Math.log(after.roas / before.roas);
  parts.forEach(function (p) { p.share = total ? p.log / total : 0; });
  // Hlavní faktor = největší vliv ve směru celkové změny (když žádný, tak největší vůbec).
  const sameDir = parts.filter(function (p) { return Math.sign(p.log) === Math.sign(total); });
  const driver = (sameDir.length ? sameDir : parts).slice()
    .sort(function (a, b) { return Math.abs(b.log) - Math.abs(a.log); })[0];
  return { before: before, after: after, change: after.roas / before.roas - 1, parts: parts, driver: driver };
}

function weekAlerts(wk) {
  const a = [], m = wk.m;
  if (!m.cost) return a;
  if (m.mimo >= CONFIG.MIMO_ALERT) a.push(alert('red', 'Mimo vyhledávání ' + pct(m.mimo) + ' útraty (limit ' + pct(CONFIG.MIMO_ALERT) + ') — ' + topOutside(m)));
  else if (m.mimo >= CONFIG.MIMO_WARN) a.push(alert('yellow', 'Mimo vyhledávání ' + pct(m.mimo) + ' útraty — ' + topOutside(m)));
  if (wk.prev8 && wk.prev8.cpc && m.cpc && m.cpc >= wk.prev8.cpc * CONFIG.CPC_WEEK_WARN) {
    a.push(alert('yellow', 'CPC ' + num(m.cpc, 1) + ' je o ' + pct(m.cpc / wk.prev8.cpc - 1) + ' nad průměrem 8 týdnů (' + num(wk.prev8.cpc, 1) + ')'));
  }
  if (m.roas !== null && m.conv >= CONFIG.MIN_CONV && m.roas < CONFIG.BREAK_EVEN_ROAS) {
    a.push(alert('red', 'ROAS týdne ' + pct(m.roas) + ' pod hranicí ziskovosti ' + pct(CONFIG.BREAK_EVEN_ROAS)));
  }
  return a;
}

function dayAlerts(m, avg28) {
  const a = [];
  const avgDailyCost = avg28.cost / 28;
  if (!m.cost || !avgDailyCost) return a;
  if (m.cost >= avgDailyCost * CONFIG.SPEND_DAY_ALERT) {
    a.push(alert('red', 'Útrata ' + num(m.cost, 0) + ' je o ' + pct(m.cost / avgDailyCost - 1) + ' nad průměrem 28 dní (' + num(avgDailyCost, 0) + ')'));
  }
  if (m.cpc && avg28.cpc && m.cpc >= avg28.cpc * CONFIG.CPC_DAY_ALERT) {
    a.push(alert('yellow', 'CPC ' + num(m.cpc, 1) + ' je o ' + pct(m.cpc / avg28.cpc - 1) + ' nad průměrem 28 dní (' + num(avg28.cpc, 1) + ')'));
  }
  if (m.mimo >= CONFIG.MIMO_ALERT && m.cost >= avgDailyCost * 0.3) {
    a.push(alert('yellow', 'Mimo vyhledávání ' + pct(m.mimo) + ' útraty — ' + topOutside(m)));
  }
  return a;
}

function roasAlerts(m) {
  if (m.roas === null) return [];
  const base = 'ROAS posledních 28 dní ' + pct(m.roas) + ' (' + num(m.conv, 0) + ' konverzí)';
  if (m.conv < CONFIG.MIN_CONV) return [alert('info', base + ' — málo konverzí na hodnocení')];
  if (m.roas < CONFIG.BREAK_EVEN_ROAS) return [alert('red', base + ' je pod hranicí ziskovosti ' + pct(CONFIG.BREAK_EVEN_ROAS))];
  if (m.roas < CONFIG.TARGET_ROAS) return [alert('yellow', base + ' je pod cílem ' + pct(CONFIG.TARGET_ROAS))];
  return [];
}

function topOutside(m) {
  return CHANNELS.filter(function (c) { return !c.search && m.share[c.key] > 0.005; })
    .sort(function (a, b) { return m.share[b.key] - m.share[a.key]; })
    .map(function (c) { return c.label + ' ' + pct(m.share[c.key]); }).join(', ') || 'rozprostřeno';
}

function alert(level, text) { return { level: level, text: text }; }
function prefix(a, p) { return { level: a.level, text: p + ': ' + a.text }; }

function campaignTable(data, yesterday) {
  const from = addDays(yesterday, -27);
  return data.campaignIds.map(function (id) {
    const b = emptyBucket();
    for (let day = from; day <= yesterday; day = addDays(day, 1)) {
      const x = data.byCampDay[id + '|' + day];
      if (x) CHANNELS.forEach(function (c) { addTo(b, c.key, x.ch[c.key]); });
    }
    return { id: id, name: data.campaignNames[id], status: data.campaignStatus[id], m: metricsOf(b) };
  }).filter(function (c) { return c.m.cost > 0; })
    .sort(function (a, b) { return b.m.cost - a.m.cost; });
}

// ============================== TABULKA ====================================

function openSpreadsheet() {
  if (CONFIG.SPREADSHEET_URL) return SpreadsheetApp.openByUrl(CONFIG.SPREADSHEET_URL);
  const ss = SpreadsheetApp.create('PMax hlídač — ' + AdsApp.currentAccount().getName());
  ss.setSpreadsheetLocale('cs_CZ');
  Logger.log('!!! Vytvořen nový Sheet. Vložte jeho URL do CONFIG.SPREADSHEET_URL: %s', ss.getUrl());
  return ss;
}

function resetSheet(ss, name, index) {
  let sh = ss.getSheetByName(name);
  if (!sh) sh = ss.insertSheet(name, index);
  sh.getCharts().forEach(function (c) { sh.removeChart(c); });
  sh.getBandings().forEach(function (b) { b.remove(); });
  sh.clearConditionalFormatRules();
  sh.getRange(1, 1, sh.getMaxRows(), sh.getMaxColumns()).breakApart();
  sh.clear();
  sh.setHiddenGridlines(true);
  // Výchozí list „List1“/„Sheet1“ z nově vytvořené tabulky smazat.
  ['List1', 'Sheet1', 'List 1'].forEach(function (n) {
    const s = ss.getSheetByName(n);
    if (s && ss.getSheets().length > 1) ss.deleteSheet(s);
  });
  return sh;
}

function styleHeader(range) {
  range.setBackground(COL.header).setFontColor(COL.headerText).setFontWeight('bold')
    .setWrap(true).setVerticalAlignment('middle').setHorizontalAlignment('center');
}

function money(cur) { return '#,##0" ' + cur + '"'; }
const PCT = '0.0%';
const PCT0 = '0%';

function channelHeaders() { return CHANNELS.map(function (c) { return c.label; }); }
function channelValues(m) { return CHANNELS.map(function (c) { return m.share[c.key]; }); }

function writeWeeks(ss, weeks, cur) {
  const sh = resetSheet(ss, 'Týdně', 1);
  const header = ['Týden (od)', 'Útrata', 'Konverze', 'Hodnota', 'ROAS', 'Break-even', 'CPC', 'Konv. poměr', 'Prům. objednávka']
    .concat(channelHeaders(), ['Mimo vyhledávání', 'ROAS loni', 'CPC loni', 'Stav']);
  const rows = weeks.map(function (w) {
    const m = w.m;
    return [fmtDay(w.start) + ' ' + w.start.slice(0, 4), m.cost, m.conv, m.value, blank(m.roas), CONFIG.BREAK_EVEN_ROAS,
      blank(m.cpc), blank(m.cr), blank(m.aov)]
      .concat(channelValues(m), [blank(m.mimo), blank(w.ly.roas), blank(w.ly.cpc), statusText(w.alerts)]);
  });
  const n = rows.length, nc = header.length;
  sh.getRange(1, 1, 1, nc).setValues([header]);
  styleHeader(sh.getRange(1, 1, 1, nc));
  sh.getRange(2, 1, n, nc).setValues(rows);
  sh.getRange(2, 2, n, 1).setNumberFormat(money(cur));
  sh.getRange(2, 3, n, 1).setNumberFormat('0.0');
  sh.getRange(2, 4, n, 1).setNumberFormat(money(cur));
  sh.getRange(2, 5, n, 2).setNumberFormat(PCT0);
  sh.getRange(2, 7, n, 1).setNumberFormat('0.0');
  sh.getRange(2, 8, n, 1).setNumberFormat('0.00%');
  sh.getRange(2, 9, n, 1).setNumberFormat(money(cur));
  sh.getRange(2, 10, n, CHANNELS.length + 1).setNumberFormat(PCT);
  sh.getRange(2, 10 + CHANNELS.length + 1, n, 1).setNumberFormat(PCT0);
  sh.getRange(2, 10 + CHANNELS.length + 2, n, 1).setNumberFormat('0.0');
  sh.getRange(2, 1, n, nc).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);
  sh.setFrozenRows(1);
  sh.setFrozenColumns(1);
  sh.setColumnWidths(1, nc, 92);
  sh.setColumnWidth(nc, 360);
  sh.setRowHeight(1, 42);

  const rules = [];
  roasRules(sh.getRange(2, 5, n, 1)).forEach(function (r) { rules.push(r); });
  roasRules(sh.getRange(2, 10 + CHANNELS.length + 1, n, 1)).forEach(function (r) { rules.push(r); });
  mimoRules(sh.getRange(2, 10 + CHANNELS.length, n, 1)).forEach(function (r) { rules.push(r); });
  rules.push(outsideGradient(sh.getRange(2, 12, n, CHANNELS.length - 2)));
  statusRules(sh.getRange(2, nc, n, 1)).forEach(function (r) { rules.push(r); });
  sh.setConditionalFormatRules(rules);
}

function writeDays(ss, days, cur) {
  const sh = resetSheet(ss, 'Denně', 2);
  const header = ['Datum', 'Den', 'Útrata', 'Konverze', 'ROAS', 'CPC', 'Konv. poměr', 'Prům. objednávka']
    .concat(channelHeaders(), ['Mimo vyhledávání', 'Stav']);
  const rows = days.map(function (x) {
    const m = x.m;
    return [x.date, DAY_NAMES[weekday(x.date)], m.cost, m.conv, blank(m.roas), blank(m.cpc), blank(m.cr), blank(m.aov)]
      .concat(channelValues(m), [blank(m.mimo), (x.lag ? '⏳ konverze se dopočítávají' + (x.alerts.length ? ' · ' : '') : '') + statusText(x.alerts, x.lag)]);
  });
  const n = rows.length, nc = header.length;
  sh.getRange(1, 1, 1, nc).setValues([header]);
  styleHeader(sh.getRange(1, 1, 1, nc));
  sh.getRange(2, 1, n, nc).setValues(rows);
  sh.getRange(2, 1, n, 1).setNumberFormat('d. M. yyyy');
  sh.getRange(2, 3, n, 1).setNumberFormat(money(cur));
  sh.getRange(2, 4, n, 1).setNumberFormat('0.0');
  sh.getRange(2, 5, n, 1).setNumberFormat(PCT0);
  sh.getRange(2, 6, n, 1).setNumberFormat('0.0');
  sh.getRange(2, 7, n, 1).setNumberFormat('0.00%');
  sh.getRange(2, 8, n, 1).setNumberFormat(money(cur));
  sh.getRange(2, 9, n, CHANNELS.length + 1).setNumberFormat(PCT);
  sh.getRange(2, 1, n, nc).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);
  // Víkendy tučně, dny s nedopočítanými konverzemi šedou kurzívou.
  days.forEach(function (x, i) {
    if (x.lag) sh.getRange(i + 2, 1, 1, nc - 1).setFontColor(COL.grey).setFontStyle('italic');
    if (weekday(x.date) >= 5) sh.getRange(i + 2, 2).setFontWeight('bold');
  });
  sh.setFrozenRows(1);
  sh.setColumnWidths(1, nc, 88);
  sh.setColumnWidth(nc, 380);
  sh.setRowHeight(1, 42);

  const rules = [];
  roasRules(sh.getRange(2, 5, n, 1)).forEach(function (r) { rules.push(r); });
  mimoRules(sh.getRange(2, 9 + CHANNELS.length, n, 1)).forEach(function (r) { rules.push(r); });
  rules.push(outsideGradient(sh.getRange(2, 11, n, CHANNELS.length - 2)));
  statusRules(sh.getRange(2, nc, n, 1)).forEach(function (r) { rules.push(r); });
  sh.setConditionalFormatRules(rules);
}

function writeChanges(ss, changes, names) {
  const sh = resetSheet(ss, 'Změny', 3);
  const header = ['Kdy', 'Kdo', 'Kampaň', 'Co', 'Operace', 'Změněná pole'];
  sh.getRange(1, 1, 1, header.length).setValues([header]);
  styleHeader(sh.getRange(1, 1, 1, header.length));
  const rows = changes.map(function (c) {
    return [c.time.replace('T', ' '), c.user, names[c.campaignId] || c.campaignId, c.type, c.op, c.fields];
  });
  if (rows.length) {
    sh.getRange(2, 1, rows.length, header.length).setValues(rows);
    sh.getRange(2, 1, rows.length, header.length).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);
  } else {
    sh.getRange(2, 1).setValue('Za posledních 14 dní žádné změny v hlídaných kampaních.');
  }
  sh.setFrozenRows(1);
  sh.setColumnWidths(1, 5, 150);
  sh.setColumnWidth(3, 280);
  sh.setColumnWidth(6, 420);
}

function writeOverview(ss, o) {
  const sh = resetSheet(ss, 'Přehled', 0);
  const W = 10;
  sh.setColumnWidth(1, 300);
  sh.setColumnWidths(2, W - 1, 105);

  sh.getRange(1, 1, 1, W).merge().setValue('PMax hlídač — ' + o.account)
    .setFontSize(18).setFontWeight('bold').setBackground(COL.header).setFontColor(COL.headerText);
  sh.setRowHeight(1, 40);
  sh.getRange(2, 1, 1, W).merge().setValue(
    'Aktualizováno ' + Utilities.formatDate(new Date(), AdsApp.currentAccount().getTimeZone(), 'd. M. yyyy HH:mm') +
    ' · hranice ziskovosti ROAS ' + pct(CONFIG.BREAK_EVEN_ROAS) + ' · cíl ' + pct(CONFIG.TARGET_ROAS) +
    ' · * konverze posledních ' + CONFIG.LAG_DAYS + ' dní se ještě dopočítávají')
    .setFontColor(COL.grey).setFontStyle('italic');

  let row = 4;
  // --- KPI ---
  section(sh, row++, W, 'Jak si PMax vede');
  const kHeader = ['Období', 'Útrata', 'Konverze', 'ROAS', 'CPC', 'Konv. poměr', 'Prům. objednávka', 'Nákupy', 'Mimo vyhledávání', 'Stav'];
  sh.getRange(row, 1, 1, W).setValues([kHeader]);
  styleHeader(sh.getRange(row, 1, 1, W));
  row++;
  const kRows = o.periods.map(function (p) {
    const m = p.m || metricsOf(emptyBucket());
    return [p.label, m.cost, m.conv, blank(m.roas), blank(m.cpc), blank(m.cr), blank(m.aov), m.share.NAKUPY, blank(m.mimo), statusText(p.alerts)];
  });
  sh.getRange(row, 1, kRows.length, W).setValues(kRows);
  sh.getRange(row, 2, kRows.length, 1).setNumberFormat(money(o.cur));
  sh.getRange(row, 3, kRows.length, 1).setNumberFormat('0.0');
  sh.getRange(row, 4, kRows.length, 1).setNumberFormat(PCT0);
  sh.getRange(row, 5, kRows.length, 1).setNumberFormat('0.0');
  sh.getRange(row, 6, kRows.length, 1).setNumberFormat('0.00%');
  sh.getRange(row, 7, kRows.length, 1).setNumberFormat(money(o.cur));
  sh.getRange(row, 8, kRows.length, 2).setNumberFormat(PCT);
  sh.getRange(row, 1, kRows.length, W).applyRowBanding(SpreadsheetApp.BandingTheme.LIGHT_GREY, false, false);
  sh.getRange(row + 2, 1, 1, W).setFontWeight('bold');
  const rules = [];
  roasRules(sh.getRange(row, 4, kRows.length, 1)).forEach(function (r) { rules.push(r); });
  mimoRules(sh.getRange(row, 9, kRows.length, 1)).forEach(function (r) { rules.push(r); });
  statusRules(sh.getRange(row, 10, kRows.length, 1)).forEach(function (r) { rules.push(r); });
  row += kRows.length + 1;

  // --- upozornění ---
  section(sh, row++, W, 'Upozornění');
  if (!o.alerts.length) {
    sh.getRange(row, 1, 1, W).merge().setValue('✅ Vše v normě — kanály, cena prokliku i ROAS jsou v mezích.').setBackground(COL.green);
    row++;
  }
  o.alerts.forEach(function (a) {
    sh.getRange(row, 1, 1, W).merge().setValue(icon(a.level) + ' ' + a.text)
      .setBackground(a.level === 'red' ? COL.red : a.level === 'yellow' ? COL.yellow : COL.section).setWrap(true);
    row++;
  });
  if (o.changesCount) {
    sh.getRange(row, 1, 1, W).merge().setValue('🛠 Změny v kampaních za poslední celý týden a dál: ' + o.changesCount + ' (viz list Změny) — při hodnocení počítat s učením.')
      .setFontColor(COL.grey);
    row++;
  }
  row++;

  // --- rozklad ROAS ---
  section(sh, row++, W, 'Proč se hýbe ROAS: poslední 4 týdny vs. 8 týdnů před nimi');
  const dcmp = o.decomposition;
  if (dcmp) {
    const dh = ['Faktor', 'Předtím', 'Teď', 'Vliv na ROAS', 'Podíl na změně'];
    sh.getRange(row, 1, 1, dh.length).setValues([dh]);
    styleHeader(sh.getRange(row, 1, 1, dh.length));
    row++;
    const drows = [['ROAS', dcmp.before.roas, dcmp.after.roas, dcmp.change, 1]].concat(dcmp.parts.map(function (p) {
      return [p.label, p.from, p.to, p.effect, p.share];
    }));
    sh.getRange(row, 1, drows.length, dh.length).setValues(drows);
    sh.getRange(row, 2, 1, 2).setNumberFormat(PCT0);
    sh.getRange(row + 1, 2, 1, 2).setNumberFormat('0.0');
    sh.getRange(row + 2, 2, 1, 2).setNumberFormat('0.00%');
    sh.getRange(row + 3, 2, 1, 2).setNumberFormat(money(o.cur));
    sh.getRange(row, 4, drows.length, 2).setNumberFormat('+0%;-0%;0%');
    sh.getRange(row, 1, 1, dh.length).setFontWeight('bold');
    rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(-0.05)
      .setBackground(COL.red).setRanges([sh.getRange(row, 4, drows.length, 1)]).build());
    rules.push(SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(0.05)
      .setBackground(COL.green).setRanges([sh.getRange(row, 4, drows.length, 1)]).build());
    row += drows.length;
    sh.getRange(row, 1, 1, W).merge().setValue('➜ Změnu ROAS nejvíc nese: ' + dcmp.driver.label.toLowerCase() +
      ' (' + signed(dcmp.driver.effect) + ' vliv na ROAS).').setFontWeight('bold');
    row++;
  } else {
    sh.getRange(row++, 1).setValue('Málo dat na rozklad.');
  }
  row++;

  // --- kampaně ---
  section(sh, row++, W, 'Kampaně — posledních 28 dní');
  const ch = ['Kampaň', 'Stav', 'Útrata', 'ROAS', 'Konverze', 'Nákupy', 'Vyhl. – text', 'Discover', 'YouTube', 'Mimo vyhledávání'];
  sh.getRange(row, 1, 1, W).setValues([ch]);
  styleHeader(sh.getRange(row, 1, 1, W));
  row++;
  if (o.campaigns.length) {
    const crows = o.campaigns.map(function (c) {
      return [c.name, statusLabel(c.status), c.m.cost, blank(c.m.roas), c.m.conv, c.m.share.NAKUPY, c.m.share.TEXT,
        c.m.share.DISCOVER, c.m.share.YOUTUBE, blank(c.m.mimo)];
    });
    sh.getRange(row, 1, crows.length, W).setValues(crows);
    sh.getRange(row, 3, crows.length, 1).setNumberFormat(money(o.cur));
    sh.getRange(row, 4, crows.length, 1).setNumberFormat(PCT0);
    sh.getRange(row, 5, crows.length, 1).setNumberFormat('0.0');
    sh.getRange(row, 6, crows.length, 5).setNumberFormat(PCT);
    roasRules(sh.getRange(row, 4, crows.length, 1)).forEach(function (r) { rules.push(r); });
    mimoRules(sh.getRange(row, 10, crows.length, 1)).forEach(function (r) { rules.push(r); });
    row += crows.length;
  } else {
    sh.getRange(row++, 1).setValue('Za 28 dní žádná útrata v PMax.');
  }
  sh.setConditionalFormatRules(rules);
  row += 1;

  // --- grafy z listu Týdně ---
  const wk = ss.getSheetByName('Týdně');
  const n = wk.getLastRow();
  const chartW = 640, chartH = 300;
  sh.insertChart(sh.newChart().setChartType(Charts.ChartType.COLUMN)
    .addRange(wk.getRange(1, 1, n, 1)).addRange(wk.getRange(1, 10, n, CHANNELS.length))
    .setOption('isStacked', 'percent').setOption('title', 'Kam jde útrata PMax po týdnech')
    .setOption('colors', CHART_COLORS).setOption('legend', { position: 'right' })
    .setOption('width', chartW).setOption('height', chartH)
    .setPosition(row, 1, 0, 0).build());
  sh.insertChart(sh.newChart().setChartType(Charts.ChartType.LINE)
    .addRange(wk.getRange(1, 1, n, 1)).addRange(wk.getRange(1, 5, n, 2))
    .setOption('title', 'ROAS po týdnech vs. hranice ziskovosti')
    .setOption('colors', ['#1a73e8', '#d93025']).setOption('vAxis', { format: 'percent' })
    .setOption('series', { 1: { lineDashStyle: [6, 4] } })
    .setOption('width', chartW).setOption('height', chartH)
    .setPosition(row, 6, 0, 0).build());
  sh.insertChart(sh.newChart().setChartType(Charts.ChartType.LINE)
    .addRange(wk.getRange(1, 1, n, 1)).addRange(wk.getRange(1, 7, n, 1))
    .setOption('title', 'Cena prokliku (CPC) po týdnech').setOption('colors', ['#e37400'])
    .setOption('width', chartW).setOption('height', chartH)
    .setPosition(row + 16, 1, 0, 0).build());
  sh.insertChart(sh.newChart().setChartType(Charts.ChartType.LINE)
    .addRange(wk.getRange(1, 1, n, 1)).addRange(wk.getRange(1, 10 + CHANNELS.length, n, 1))
    .setOption('title', 'Podíl útraty mimo vyhledávání (limit ' + pct(CONFIG.MIMO_ALERT) + ')')
    .setOption('colors', ['#a142f4']).setOption('vAxis', { format: 'percent', viewWindow: { min: 0 } })
    .setOption('width', chartW).setOption('height', chartH)
    .setPosition(row + 16, 6, 0, 0).build());
}

function writeHistory(ss, today, alerts, tz) {
  let sh = ss.getSheetByName('Historie upozornění');
  if (!sh) {
    sh = ss.insertSheet('Historie upozornění');
    sh.getRange(1, 1, 1, 3).setValues([['Den běhu', 'Úroveň', 'Upozornění']]);
    styleHeader(sh.getRange(1, 1, 1, 3));
    sh.setFrozenRows(1);
    sh.setColumnWidth(3, 700);
  }
  const last = sh.getLastRow();
  const existing = last > 1 ? sh.getRange(2, 1, last - 1, 3).getValues()
    .filter(function (r) {
      const v = r[0] instanceof Date ? Utilities.formatDate(r[0], tz, 'yyyy-MM-dd') : String(r[0]);
      return v === today;
    }).map(function (r) { return r[2]; }) : [];
  const rows = alerts.filter(function (a) { return a.level !== 'info' && existing.indexOf(a.text) < 0; })
    .map(function (a) { return [today, icon(a.level), a.text]; });
  if (!rows.length) return;
  sh.getRange(last + 1, 1, rows.length, 1).setNumberFormat('@'); // datum jako text, ať jde porovnat
  sh.getRange(last + 1, 1, rows.length, 3).setValues(rows);
}

function section(sh, row, w, text) {
  sh.getRange(row, 1, 1, w).merge().setValue(text).setFontWeight('bold').setFontSize(12).setBackground(COL.section);
  sh.setRowHeight(row, 28);
}

function roasRules(range) {
  return [
    SpreadsheetApp.newConditionalFormatRule().whenNumberLessThan(CONFIG.BREAK_EVEN_ROAS).setBackground(COL.red).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberBetween(CONFIG.BREAK_EVEN_ROAS, CONFIG.TARGET_ROAS).setBackground(COL.yellow).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThan(CONFIG.TARGET_ROAS).setBackground(COL.green).setRanges([range]).build(),
  ];
}

function mimoRules(range) {
  return [
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThanOrEqualTo(CONFIG.MIMO_ALERT).setBackground(COL.red).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenNumberGreaterThanOrEqualTo(CONFIG.MIMO_WARN).setBackground(COL.yellow).setRanges([range]).build(),
  ];
}

function outsideGradient(range) {
  return SpreadsheetApp.newConditionalFormatRule()
    .setGradientMinpointWithValue('#ffffff', SpreadsheetApp.InterpolationType.NUMBER, '0')
    .setGradientMaxpointWithValue('#e67c73', SpreadsheetApp.InterpolationType.NUMBER, String(CONFIG.MIMO_ALERT))
    .setRanges([range]).build();
}

function statusRules(range) {
  return [
    SpreadsheetApp.newConditionalFormatRule().whenTextContains('🔴').setBackground(COL.red).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextContains('🟡').setBackground(COL.yellow).setRanges([range]).build(),
    SpreadsheetApp.newConditionalFormatRule().whenTextContains('✅').setFontColor('#137333').setRanges([range]).build(),
  ];
}

function statusText(alerts, lag) {
  if (!alerts || !alerts.length) return lag ? '' : '✅';
  return alerts.map(function (a) { return icon(a.level) + ' ' + a.text; }).join(' · ');
}

function statusLabel(s) {
  const map = { ENABLED: 'aktivní', PAUSED: 'pozastavená', REMOVED: 'odstraněná', 2: 'aktivní', 3: 'pozastavená', 4: 'odstraněná' };
  return map[s] || s;
}

// =============================== E-MAIL ====================================

function maybeEmail(ss, accountName, today, periods, alerts, cur) {
  if (!CONFIG.EMAIL) return;
  const monday = weekday(today) === 0;
  const red = alerts.filter(function (a) { return a.level === 'red'; });
  if (!monday && !(CONFIG.EMAIL_ON_ALERT && red.length)) return;

  const subject = 'PMax hlídač — ' + accountName + ': ' +
    (red.length ? '🔴 ' + red.length + '× upozornění' : alerts.length ? '🟡 k pozornosti' : '✅ v normě') +
    (monday ? ' (týden ' + periods[2].label.replace(/^.*\(|\)$/g, '') + ')' : '');
  const td = 'style="padding:4px 8px;border-bottom:1px solid #eee;text-align:right"';
  const rows = periods.map(function (p) {
    const m = p.m || metricsOf(emptyBucket());
    return '<tr><td style="padding:4px 8px;border-bottom:1px solid #eee">' + p.label + '</td>' +
      '<td ' + td + '>' + num(m.cost, 0) + ' ' + cur + '</td><td ' + td + '>' + (m.roas === null ? '–' : pct(m.roas)) + '</td>' +
      '<td ' + td + '>' + (m.cpc === null ? '–' : num(m.cpc, 1)) + '</td><td ' + td + '>' + (m.cr === null ? '–' : pct(m.cr, 2)) + '</td>' +
      '<td ' + td + '>' + (m.mimo === null ? '–' : pct(m.mimo, 1)) + '</td></tr>';
  }).join('');
  const html = '<div style="font-family:Arial,sans-serif;font-size:14px">' +
    '<h2 style="margin:0 0 8px">PMax hlídač — ' + accountName + '</h2>' +
    (alerts.length ? '<ul>' + alerts.map(function (a) { return '<li>' + icon(a.level) + ' ' + a.text + '</li>'; }).join('') + '</ul>'
      : '<p>✅ Vše v normě.</p>') +
    '<table style="border-collapse:collapse"><tr style="background:#202124;color:#fff">' +
    '<th style="padding:4px 8px">Období</th><th>Útrata</th><th>ROAS</th><th>CPC</th><th>Konv. poměr</th><th>Mimo vyhl.</th></tr>' +
    rows + '</table>' +
    '<p style="color:#80868b">* konverze posledních dnů se ještě dopočítávají. Hranice ziskovosti ROAS ' + pct(CONFIG.BREAK_EVEN_ROAS) + '.</p>' +
    '<p><a href="' + ss.getUrl() + '">Otevřít tabulku s grafy</a></p></div>';
  MailApp.sendEmail({ to: CONFIG.EMAIL, subject: subject, htmlBody: html });
}

// ============================== POMOCNÉ ====================================

function addDays(s, n) {
  const d = new Date(s + 'T00:00:00Z');
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}
function weekday(s) { return (new Date(s + 'T00:00:00Z').getUTCDay() + 6) % 7; } // 0 = pondělí
function mondayOf(s) { return addDays(s, -weekday(s)); }
function fmtDay(s) { return Number(s.slice(8, 10)) + '. ' + Number(s.slice(5, 7)) + '.'; }
function blank(v) { return v === null || v === undefined || !isFinite(v) ? '' : v; }
function num(v, dec) {
  return Number(v).toFixed(dec).replace('.', ',').replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}
function pct(v, dec) { return num(v * 100, dec === undefined ? 0 : dec) + ' %'; }
function signed(v) { return (v >= 0 ? '+' : '') + pct(v); }
function label(map, v) { return map[v] || String(v); }
function icon(level) { return level === 'red' ? '🔴' : level === 'yellow' ? '🟡' : 'ℹ️'; }
