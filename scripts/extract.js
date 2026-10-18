// Extractor de la Cadet Interterritorial (masculina y femenina) de basquetcatala.cat.
//
// Uso:
//   1. Abre https://www.basquetcatala.cat/ en el navegador y espera a que pase la
//      verificación de seguridad.
//   2. Abre la consola (F12 → Console), pega este archivo entero y pulsa Enter.
//   3. Al terminar (~3-4 min) el navegador descarga `fcbq_raw.json`.
//      Muévelo a data/fcbq_raw.json y ejecuta: python3 scripts/build_data.py
//
// Solo guarda datos deportivos (grupos, clasificaciones, partidos, pabellón, horario, escudo
// del club y estadísticas de jugadores con el nombre abreviado: "Pol H.").
// NO guarda los datos de contacto del responsable de club que muestran las fichas de
// equipo, ni nombres completos, fotos u otros datos de los jugadores (son menores).
(async () => {
  const now = new Date();
  // La temporada 2026-27 es "2026" en la web; empieza en agosto
  const SEASON = now.getMonth() >= 7 ? now.getFullYear() : now.getFullYear() - 1;
  const TERRITORIAL_CATALUNYA = 1;
  const DELAY = 300; // ms entre peticiones, para no cargar el servidor

  const wait = ms => new Promise(r => setTimeout(r, ms));
  const html = async url => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url} → ${r.status}`);
    await wait(DELAY);
    return new DOMParser().parseFromString(await r.text(), 'text/html');
  };
  const options = async url => {
    const d = await html(url);
    return [...d.querySelectorAll('option')].map(o => ({ value: o.value, text: o.textContent.trim() }));
  };
  const idOf = h => ((h || '').match(/(\d+)$/) || [])[1];
  const leafs = e => [...e.querySelectorAll('*')].filter(x => !x.children.length).map(x => x.textContent.trim()).filter(Boolean);
  const log = (...a) => console.log('%c[cadet]', 'color:#d4700a;font-weight:bold', ...a);

  const data = { source: 'basquetcatala.cat', season: `${SEASON}-${String(SEASON + 1).slice(2)}`, category: 'Cadet Interterritorial',
                 scrapedAt: new Date().toISOString(), teams: {}, groups: [] };

  for (const gender of ['M', 'F']) {
    const cats = await options(`/ajax/combo_categories2/${gender}/${TERRITORIAL_CATALUNYA}/${SEASON}`);
    const cat = cats.find(c => /cadet/i.test(c.text) && /interterritorial/i.test(c.text) && !/1r\.? any/i.test(c.text));
    if (!cat) throw new Error(`No se encuentra la Cadet Interterritorial ${gender} en la temporada ${SEASON}`);
    const comps = (await options(`/ajax/combo_competicions_ant2/${cat.value}/${gender}/${TERRITORIAL_CATALUNYA}/${SEASON}`))
      .filter(o => idOf(o.value) && o.value !== '0');
    log(`${cat.text}: ${comps.length} grupos`);

    for (const [i, comp] of comps.entries()) {
      const gid = +idOf(comp.value);

      // Clasificación (vista de la última jornada)
      const d = await html(`/competicions/resultats/${gid}`);
      const label = [...d.querySelectorAll('body *')].find(e => /^\s*Classificació a la jornada/.test(e.textContent) && e.textContent.length < 60);
      const box = label?.nextElementSibling?.nextElementSibling;
      const standings = box ? [...box.children].map(r => {
        const a = r.querySelector('a[href*="/equip/"]') || r.querySelector('a');
        const n = leafs(r).filter(x => /^-?\d+$/.test(x)).map(Number);
        return { id: idOf(a?.getAttribute('href')), name: a?.textContent.trim(), j: n[1], w: n[2], l: n[3], np: n[4], pf: n[5], pa: n[6], pts: n[7] };
      }).filter(s => s.id) : [];

      // Todos los partidos
      const d2 = await html(`/competicions/resultats/${gid}/0`);
      const rows = [...d2.querySelectorAll('.rowsJornada .row.rowJornada')].filter(r => !r.parentElement.closest('.row.rowJornada'));
      const matches = rows.map(r => {
        const t = [...r.querySelectorAll('a.teamNameLink')];
        const lf = leafs(r);
        const sc = lf.filter(x => /^\d+$/.test(x)).map(Number);
        return { h: idOf(t[0]?.getAttribute('href')), a: idOf(t[1]?.getAttribute('href')),
                 dt: lf.find(x => /^\d\d-\d\d-\d{4}( \d\d:\d\d)?$/.test(x)) || '',
                 hs: sc.length >= 2 ? sc[sc.length - 2] : null, as: sc.length >= 2 ? sc[sc.length - 1] : null,
                 st: /ajornat/i.test(lf.join(' ')) ? 'ajornat' : '' };
      });

      // Escudos: cada partido lleva el de los dos equipos (versión de 150 px del CDN de la Federació)
      const logos = {};
      for (const img of d2.querySelectorAll('.rowJornada img.circle-img')) {
        const a = img.closest('a[href*="/equip/"]') || img.parentElement?.parentElement?.querySelector('a[href*="/equip/"]');
        const id = idOf(a?.getAttribute('href'));
        if (id) logos[id] ||= (img.getAttribute('src') || '').split('/').pop();
      }

      data.groups.push({ gender, gid, name: `Grup ${String(i + 1).padStart(2, '0')}`,
                         standings: standings.map(({ name, ...s }) => s), matches });
      for (const s of standings) data.teams[s.id] = { name: s.name, logo: logos[s.id] || '' };
      log(`  ${comp.text}: ${standings.length} equipos, ${matches.length} partidos`);
    }
  }

  // Ficha de cada equipo: solo pabellón, horario y club
  const ids = Object.keys(data.teams);
  for (const [i, id] of ids.entries()) {
    const d = await html(`/equip/${id}`);
    const main = [...d.querySelectorAll('body *')].find(e => /Dades de l.equip/.test(e.textContent) && /Terreny de joc/.test(e.textContent)
                                                          && e.textContent.length < 4000 && !/Departaments/.test(e.textContent));
    const lines = (main?.innerText || main?.textContent || '').split('\n').map(x => x.trim()).filter(Boolean);
    const after = (label, n = 1) => { const k = lines.findIndex(l => l.startsWith(label)); return k < 0 ? [] : lines.slice(k + 1, k + 1 + n); };
    const [venue, street, cpTown] = after('Terreny de joc', 3);
    const m = (cpTown || '').match(/^(\d{5}),\s*(.+?)\s*\((.+)\)$/);
    const club = d.querySelector('a[href*="/club/"]')?.getAttribute('href');
    Object.assign(data.teams[id], {
      venue: venue || '', street: street || '', cp: m?.[1] || '', town: m?.[2] || '', prov: m?.[3] || '',
      day: after('Dia de joc')[0] || '', hour: after('Hora de joc')[0] || '',
      club: after('Informació del club')[0] || '', clubId: (club?.match(/\/club\/(\d+)/) || [])[1] || '',
    });
    if (i % 10 === 9) log(`  fichas de equipo: ${i + 1}/${ids.length}`);
  }

  // Estadísticas de jugadores. La web las pinta en el navegador (no vienen en el HTML),
  // así que cada página de estadísticas de equipo se carga en un iframe oculto y se lee
  // el texto ya renderizado. Los nombres se abrevian AQUÍ ("Pol H."): son menores y el
  // nombre completo no sale del navegador. No se guardan fotos.
  const PARTICLES = new Set(['DE', 'DEL', 'LA', 'LAS', 'LOS', 'LES', 'I', 'Y', 'DA', 'DO', 'DOS', 'VAN', 'VON', 'DI', 'EL']);
  const shortName = full => {
    // Algunos nombres ya los publica la Federació solo con iniciales ("N.A.R."): se respetan
    if (/^(\p{L}\.)+$/u.test(full.replace(/\s+/g, ''))) return full.replace(/\s+/g, '').toUpperCase();
    // "MARTINEZ - SOLER" → "MARTINEZ-SOLER" (un solo apellido compuesto)
    const w = full.trim().replace(/\s*-\s*/g, '-').split(/\s+/);
    const takeSurname = () => { const g = [w.pop()]; while (w.length > 1 && PARTICLES.has(w[w.length - 1].toUpperCase())) g.unshift(w.pop()); return g; };
    // "NOM COGNOM1 COGNOM2": la inicial es la del primer apellido
    let first = null;
    if (w.length >= 3) { const second = takeSurname(); first = w.length >= 2 ? takeSurname() : second; }
    else if (w.length === 2) first = takeSurname();
    const tc = s => s.toLowerCase().replace(/(^|[\s'’-])(\p{L})/gu, (m, a, b) => a + b.toUpperCase());
    const main = first?.find(x => !PARTICLES.has(x.toUpperCase())) || first?.[0];
    return tc(w.join(' ')) + (main ? ' ' + main[0].toUpperCase() + '.' : '');
  };
  // Cabecera "NOM PJ MIN MIN/P PTS PTS/P FC/P TL T2 T3"; luego, por jugador, el nombre y 12 valores:
  // PJ, MIN, MIN/P, PTS, PTS/P, FC/P, TL%, TL a/i, T2%, T2 a/i, T3%, T3 a/i (de T2 y T3 solo se registran anotados)
  const parsePlayers = text => {
    const L = text.split('\n').map(s => s.trim()).filter(Boolean);
    const h = L.findIndex((l, i) => l === 'NOM' && L[i + 1] === 'PJ' && L[i + 9] === 'T3');
    if (h < 0) return null;
    const num = s => /^\d+([.,]\d+)?$/.test(s), pair = s => (/^(\d+)\/(\d+)$/.exec(s) || []).slice(1).map(Number);
    // Una fila = nombre + 12 valores con este formato exacto. Se busca el patrón en vez de
    // contar posiciones: si un jugador no tiene foto, la web pinta su inicial antes del nombre.
    const int = /^\d+$/, dec = /^\d+([.,]\d+)?$/, pct = /^(\d+%|-)$/, frac = /^\d+\/\d+$/;
    const SHAPE = [int, int, dec, int, dec, dec, pct, frac, pct, frac, pct, frac];
    const out = [];
    for (let i = h + 10; i + 12 < L.length; i++) {
      const v = L.slice(i + 1, i + 13);
      if (num(L[i]) || L[i].length < 3 || !SHAPE.every((re, k) => re.test(v[k]))) continue;
      out.push({ n: shortName(L[i]), pj: +v[0], min: +v[1], pts: +v[3], fcpg: +v[5], tl: pair(v[7]), t2: pair(v[9])[0], t3: pair(v[11])[0] });
      i += 12;
    }
    return out;
  };
  const playersOf = async (id, name) => {
    const f = Object.assign(document.createElement('iframe'), { src: `/estadistiques/equip/3/${SEASON}/${id}/${encodeURIComponent(name)}` });
    // opacity, not visibility:hidden: innerText skips invisible text
    f.style.cssText = 'position:fixed;left:-10000px;top:0;width:1200px;height:900px;opacity:0;pointer-events:none';
    document.body.appendChild(f);
    try {
      await new Promise((ok, ko) => { f.onload = ok; setTimeout(() => ko(new Error('timeout')), 30000); });
      // Espera a que aparezca la tabla y deje de crecer
      let last = null, stable = 0;
      for (let k = 0; k < 60 && stable < 3; k++) {
        await wait(250);
        const r = parsePlayers(f.contentDocument?.body?.innerText || '');
        stable = r && last && r.length === last.length ? stable + 1 : 0;
        last = r;
      }
      return last || [];
    } finally { f.remove(); }
  };
  const queue = [...ids];
  let done = 0;
  await Promise.all([1, 2, 3].map(async () => {   // 3 páginas a la vez
    for (let id; (id = queue.shift());) {
      try { data.teams[id].players = await playersOf(id, data.teams[id].name); }
      catch (e) { data.teams[id].players = []; console.warn('[cadet] sin estadísticas de jugadores:', data.teams[id].name, e.message); }
      if (++done % 10 === 0) log(`  jugadores: ${done}/${ids.length} equipos`);
    }
  }));

  const blob = new Blob([JSON.stringify(data)], { type: 'application/json' });
  const a = Object.assign(document.createElement('a'), { href: URL.createObjectURL(blob), download: 'fcbq_raw.json' });
  document.body.appendChild(a); a.click(); a.remove();
  log(`Listo: ${ids.length} equipos, ${data.groups.length} grupos → fcbq_raw.json`);
})().catch(e => console.error('[cadet] Error:', e));
