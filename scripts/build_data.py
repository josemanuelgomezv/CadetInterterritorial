#!/usr/bin/env python3
"""Convierte data/fcbq_raw.json (de scripts/extract.js) en data/cadet-data.js.

Asigna a cada equipo el código INE del municipio de su pabellón, usando los
municipios de es-atlas (los mismos que dibuja el mapa).

Genera también un calendario por equipo e idioma (cal/ca/<id>.ics, cal/es/<id>.ics)
para suscribirse desde Google Calendar, Apple, Outlook…: al publicar datos nuevos,
los calendarios suscritos se actualizan solos.

Uso: python3 scripts/build_data.py
"""
import json
import re
import shutil
import sys
import unicodedata
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'fcbq_raw.json'
OUT = ROOT / 'data' / 'cadet-data.js'
CAL = ROOT / 'cal'
ATLAS_URL = 'https://cdn.jsdelivr.net/npm/es-atlas@0.6.0/es/municipalities.json'
CAT_PROVINCES = ('08', '17', '25', '43')


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]', '', s)


# Calendars (RFC 5545). Texts per language; the events keep a stable UID per game, so a
# rescheduled game moves in the subscribed calendars instead of appearing twice.
ICS_TEXT = {
    'ca': {'gender': {'M': 'masculí', 'F': 'femení'}, 'postponed': ' (ajornat)',
           'desc': 'Cadet Interterritorial {g} · {group}. Horari segons basquetcatala.cat a {d}; pot canviar.'},
    'es': {'gender': {'M': 'masculino', 'F': 'femenino'}, 'postponed': ' (aplazado)',
           'desc': 'Cadet Interterritorial {g} · {group}. Horario según basquetcatala.cat a {d}; puede cambiar.'},
}
ICS_TZ = ['BEGIN:VTIMEZONE', 'TZID:Europe/Madrid',
          'BEGIN:DAYLIGHT', 'TZOFFSETFROM:+0100', 'TZOFFSETTO:+0200', 'TZNAME:CEST', 'DTSTART:19700329T020000',
          'RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU', 'END:DAYLIGHT',
          'BEGIN:STANDARD', 'TZOFFSETFROM:+0200', 'TZOFFSETTO:+0100', 'TZNAME:CET', 'DTSTART:19701025T030000',
          'RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU', 'END:STANDARD',
          'END:VTIMEZONE']


def ics_text(s):
    return re.sub(r'([\\;,])', r'\\\1', str(s)).replace('\n', '\\n')


def ics_fold(line):
    """Lines of at most 75 octets; continuation lines start with a space."""
    parts, cur = [], ''
    for ch in line:
        if len((cur + ch).encode()) > (74 if parts else 75):
            parts.append(cur)
            cur = ch
        else:
            cur += ch
    return '\r\n '.join(parts + [cur])


def write_calendars(teams, groups, scraped_at):
    shutil.rmtree(CAL, ignore_errors=True)
    stamp = scraped_at[:19].replace('-', '').replace(':', '') + 'Z'
    day = f'{scraped_at[8:10]}/{scraped_at[5:7]}/{scraped_at[:4]}'
    for lang, tx in ICS_TEXT.items():
        (CAL / lang).mkdir(parents=True)
        for g in groups:
            for tid in (s['id'] for s in g['standings']):
                t = teams[tid]
                events = []
                for m in g['matches']:
                    dt = re.match(r'(\d\d)-(\d\d)-(\d{4})(?: (\d\d):(\d\d))?', m['dt'] or '')
                    if tid not in (m['h'], m['a']) or not dt:
                        continue
                    d, mo, y, hh, mm = dt.groups()
                    home, away = teams[m['h']], teams[m['a']]
                    score = f" {m['hs']}-{m['as']} " if m['hs'] is not None else ' – '
                    if hh:
                        end_min = min(int(hh) * 60 + int(mm) + 90, 23 * 60 + 59)   # 90 min, same day
                        when = [f'DTSTART;TZID=Europe/Madrid:{y}{mo}{d}T{hh}{mm}00',
                                f'DTEND;TZID=Europe/Madrid:{y}{mo}{d}T{end_min // 60:02d}{end_min % 60:02d}00']
                    else:
                        when = [f'DTSTART;VALUE=DATE:{y}{mo}{d}']
                    events += ['BEGIN:VEVENT',
                               f"UID:fcbq-{g['gid']}-{m['h']}-{m['a']}@cadet-interterritorial",
                               f'DTSTAMP:{stamp}', *when,
                               'SUMMARY:' + ics_text(f"🏀 {home['name']}{score}{away['name']}" + (tx['postponed'] if m['st'] == 'ajornat' else '')),
                               'LOCATION:' + ics_text(', '.join(x for x in (home.get('venue'), home.get('street'),
                                                                            ' '.join(x for x in (home.get('cp'), home.get('town')) if x)) if x)),
                               'DESCRIPTION:' + ics_text(tx['desc'].format(g=tx['gender'][g['gender']], group=g['name'], d=day)),
                               'END:VEVENT']
                lines = ['BEGIN:VCALENDAR', 'VERSION:2.0', 'PRODID:-//Cadet Interterritorial//' + lang.upper(),
                         'CALSCALE:GREGORIAN', 'METHOD:PUBLISH', 'X-WR-CALNAME:' + ics_text(f"🏀 {t['name']}"),
                         'X-WR-TIMEZONE:Europe/Madrid', 'REFRESH-INTERVAL;VALUE=DURATION:PT12H', 'X-PUBLISHED-TTL:PT12H',
                         *ICS_TZ, *events, 'END:VCALENDAR']
                (CAL / lang / f'{tid}.ics').write_text('\r\n'.join(map(ics_fold, lines)) + '\r\n', encoding='utf-8', newline='')


def main():
    raw = json.loads(RAW.read_text(encoding='utf-8'))
    with urllib.request.urlopen(ATLAS_URL) as r:
        atlas = json.load(r)

    munis = {}
    for g in atlas['objects']['municipalities']['geometries']:
        if str(g['id'])[:2] in CAT_PROVINCES:
            munis.setdefault(norm(g['properties']['name']), []).append(g['id'])

    group_of = {s['id']: (g['gender'], g['gid']) for g in raw['groups'] for s in g['standings']}

    # Round ("jornada") of each game: the federation lists the games round by round, n/2 per round
    # (one team rests when n is odd). Checked: a team can't play twice in the same round.
    for g in raw['groups']:
        size = len(g['standings']) // 2
        for i, m in enumerate(g['matches']):
            m['j'] = i // size + 1
        rounds = {}
        for m in g['matches']:
            rounds.setdefault(m['j'], []).extend((m['h'], m['a']))
        if any(len(ids) != len(set(ids)) for ids in rounds.values()):
            print(f"⚠ {g['name']} ({g['gid']}): las jornadas no cuadran; se omiten", file=sys.stderr)
            for m in g['matches']:
                m.pop('j')
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

    write_calendars(teams, raw['groups'], raw['scrapedAt'])
    print(f'{OUT.relative_to(ROOT)}: {len(teams)} equipos, {len(raw["groups"])} grupos (datos del {raw["scrapedAt"][:10]})')
    if unmatched:
        print('⚠ Equipos sin municipio en el mapa:', *unmatched, sep='\n  ', file=sys.stderr)


if __name__ == '__main__':
    main()
