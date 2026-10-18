#!/usr/bin/env python3
"""Convierte data/fcbq_raw.json (de scripts/extract.js) en data/cadet-data.js.

Asigna a cada equipo el código INE del municipio de su pabellón, usando los
municipios de es-atlas (los mismos que dibuja el mapa).

Uso: python3 scripts/build_data.py
"""
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'fcbq_raw.json'
OUT = ROOT / 'data' / 'cadet-data.js'
ATLAS_URL = 'https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/municipalities.json'
CAT_PROVINCES = ('08', '17', '25', '43')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


def main():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    with urllib.request.urlopen(ATLAS_URL) as r:
        atlas = json.load(r)

    munis = {}
    for g in atlas['objects']['municipalities']['geometries']:
        if str(g['id'])[:2] in CAT_PROVINCES:
            munis.setdefault(norm(g['properties']['name']), []).append(g['id'])

    group_of = {s['id']: (g['gender'], g['gid']) for g in raw['groups'] for s in g['standings']}
    teams, unmatched = {}, []
    for tid, t in raw['teams'].items():
        t = dict(t, name=re.sub(r'\s+', ' ', t['name']).strip())
        # The postal code's first two digits are the province code, which disambiguates names
        ids = [i for i in munis.get(norm(t.get('town')), []) if not t.get('cp') or i[:2] == t['cp'][:2]]
        t['muni'] = ids[0] if len(ids) == 1 else ''
        if not t['muni']:
            if 'ANDORRA' in t['name'].upper():
                t.update(town='Andorra la Vella', prov='Andorra')
            else:
                unmatched.append(f"{tid} {t['name']} ({t.get('town')})")
        t['gender'], t['group'] = group_of[tid]
        teams[tid] = t

    out = {k: raw[k] for k in ('source', 'season', 'category', 'scrapedAt')}
    out.update(teams=teams, groups=raw['groups'])
    OUT.write_text(
        '// Cadet Interterritorial (FCBQ) — copia de basquetcatala.cat. Generado por scripts/build_data.py; no editar a mano.\n'
        '// Para actualizar los datos, ver README.md.\n'
        'window.FCBQ_DATA = ' + json.dumps(out, ensure_ascii=False, separators=(',', ':')) + ';\n',
        encoding='utf-8')

    print(f'{OUT.relative_to(ROOT)}: {len(teams)} equipos, {len(raw["groups"])} grupos (datos del {raw["scrapedAt"][:10]})')
    if unmatched:
        print('⚠ Equipos sin municipio en el mapa:', *unmatched, sep='\n  ', file=sys.stderr)


if __name__ == '__main__':
    main()
