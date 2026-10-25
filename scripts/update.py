#!/usr/bin/env python3
"""Actualiza los datos a partir del fcbq_raw.json que descarga scripts/extract.js.

Coge el fcbq_raw.json más reciente de la carpeta de descargas (o el que se
indique), lo copia a data/, regenera data/cadet-data.js y, con --push, hace
commit y push.

Uso:
  python3 scripts/update.py                  # actualiza los datos
  python3 scripts/update.py --push           # y además hace commit y push
  python3 scripts/update.py ruta/al/archivo.json
  python3 scripts/update.py --force          # actualiza aunque la validación encuentre errores

Antes de cambiar nada se validan los datos nuevos (ver validate()): con errores
no se toca ningún archivo; los avisos solo se muestran.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / 'data' / 'fcbq_raw.json'


def downloads_dir():
    try:
        d = subprocess.run(['xdg-user-dir', 'DOWNLOAD'], capture_output=True, text=True).stdout.strip()
        if d and Path(d).is_dir():
            return Path(d)
    except FileNotFoundError:
        pass
    return next((p for p in (Path.home() / 'Descargas', Path.home() / 'Downloads') if p.is_dir()), Path.home())


def summary(d):
    played = sum(m['hs'] is not None for g in d['groups'] for m in g['matches'])
    return len(d['teams']), len(d['groups']), played


DATE = re.compile(r'^\d\d-\d\d-\d{4}( \d\d:\d\d)?$')
# Nombre de pila + inicial del apellido ("Pol H.", "Maria del Mar R.") o solo iniciales ("N.A.R.")
SHORT_NAME = re.compile(r"^[^\W\d_][\w'’.-]*( [\w'’.-]+)* [^\W\d_]\.$|^([^\W\d_]\.)+$")
ODD_NAME = re.compile(r"[^\w '’.-]|\d")


def played(m):
    return m.get('hs') is not None


def match_date(m):
    d, mo, y = m['dt'][:10].split('-')
    return f'{y}-{mo}-{d}'


def validate(new, old):
    """Devuelve (errores, avisos). Un error indica que la extracción ha fallado o que se
    filtraría algo que no debe publicarse; un aviso, algo raro pero posible en la web."""
    errors, warnings = [], []
    teams, groups = new.get('teams') or {}, new.get('groups') or []
    if not groups or not teams:
        return ['no hay datos de grupos o equipos'], []
    for k in ('season', 'scrapedAt'):
        if not new.get(k):
            errors.append(f'falta el campo {k}')
    today = (new.get('scrapedAt') or '9999')[:10]

    def where(g, m=None):
        name = f"{'Masc' if g.get('gender') == 'M' else 'Fem'} {g.get('name')}"
        if m:
            name += f" · {teams.get(m.get('h'), {}).get('name', m.get('h'))} - {teams.get(m.get('a'), {}).get('name', m.get('a'))}"
        return name

    # Estructura de grupos, clasificaciones y partidos
    seen = set()
    for g in groups:
        if g.get('gender') not in ('M', 'F'):
            errors.append(f"{where(g)}: género desconocido {g.get('gender')!r}")
        if not g.get('standings') or not g.get('matches'):
            errors.append(f'{where(g)}: sin clasificación o sin partidos')
        for s in g.get('standings', []):
            if s.get('id') not in teams:
                errors.append(f"{where(g)}: equipo {s.get('id')} de la clasificación sin ficha")
            elif s['j'] != s['w'] + s['l'] + s['np']:
                errors.append(f"{where(g)}: {teams[s['id']]['name']} tiene {s['j']} jugados ≠ {s['w']}G + {s['l']}P + {s['np']}NP")
            elif s['pts'] != 2 * s['w'] + s['l']:
                warnings.append(f"{where(g)}: {teams[s['id']]['name']} tiene {s['pts']} puntos y le tocarían {2 * s['w'] + s['l']} (¿sanción?)")
        games = {}
        for m in g.get('matches', []):
            if m.get('h') not in teams or m.get('a') not in teams:
                errors.append(f'{where(g, m)}: equipo sin ficha')
                continue
            key = (g['gid'], m['h'], m['a'])
            if key in seen:
                warnings.append(f'{where(g, m)}: partido repetido')
            seen.add(key)
            if m['dt'] and not DATE.match(m['dt']):
                errors.append(f"{where(g, m)}: fecha con formato raro {m['dt']!r}")
            if (m.get('hs') is None) != (m.get('as') is None):
                errors.append(f'{where(g, m)}: marcador a medias')
            elif played(m):
                if not (0 <= m['hs'] <= 250 and 0 <= m['as'] <= 250):
                    errors.append(f"{where(g, m)}: marcador imposible {m['hs']}-{m['as']}")
                if not m['dt']:
                    warnings.append(f'{where(g, m)}: jugado y sin fecha')
                elif match_date(m) > today:
                    errors.append(f"{where(g, m)}: tiene resultado pero es del {m['dt'][:10]}, en el futuro")
                games[m['h']] = games.get(m['h'], 0) + 1
                games[m['a']] = games.get(m['a'], 0) + 1
            bx = m.get('bx')
            if bx:
                hs, as_ = (sum(p['pts'] for p in bx[k]) for k in ('h', 'a'))
                # 0-0: partido sin estadísticas (p. ej., 20-0 por incomparecencia)
                if played(m) and (hs, as_) != (0, 0) and (hs, as_) != (m['hs'], m['as']):
                    msg = f"{where(g, m)}: los puntos de los jugadores ({hs}-{as_}) no cuadran con el marcador ({m['hs']}-{m['as']})"
                    (errors if (hs, as_) == (m['as'], m['hs']) else warnings).append(msg + (' (equipos cruzados)' if (hs, as_) == (m['as'], m['hs']) else ''))
        for s in g.get('standings', []):
            if s.get('id') in teams and games.get(s['id'], 0) != s['j']:
                warnings.append(f"{where(g)}: {teams[s['id']]['name']} tiene {games.get(s['id'], 0)} resultados y {s['j']} jugados en la clasificación (¿clasificación sin actualizar?)")

    # Fichas de equipo y nombres de jugadores (son menores: solo nombre abreviado)
    names = [(t['name'], p['n']) for t in teams.values() for p in t.get('players', [])]
    names += [(where(g, m), p['n']) for g in groups for m in g['matches'] if m.get('bx') for k in ('h', 'a') for p in m['bx'][k]]
    for who, n in names:
        if ODD_NAME.search(n):
            warnings.append(f'{who}: nombre de jugador raro {n!r} (¿una cabecera de la tabla?)')
        elif not SHORT_NAME.match(n) or len(n.split()) > 4:
            errors.append(f'{who}: nombre de jugador sin abreviar {n!r}')
    no_venue = [t['name'] for t in teams.values() if not t.get('venue')]
    if no_venue:
        warnings.append(f"{len(no_venue)} equipos sin pabellón: {', '.join(no_venue[:5])}")

    # Comparación con los datos actuales (misma temporada): una extracción a medias
    # suele notarse en que desaparecen cosas
    if old and old.get('season') != new.get('season'):
        warnings.append(f"cambio de temporada: {old.get('season')} → {new.get('season')}")
    elif old:
        lost = [old['teams'][i]['name'] for i in old['teams'] if i not in teams]
        if lost:
            errors.append(f"desaparecen {len(lost)} equipos: {', '.join(lost[:5])}")
        gids = {g['gid'] for g in groups}
        lost = [where(g) for g in old['groups'] if g['gid'] not in gids]
        if lost:
            errors.append(f"desaparecen {len(lost)} grupos: {', '.join(lost)}")
        now = {(g['gid'], m['h'], m['a']): m for g in groups for m in g['matches']}
        for g in old['groups']:
            for m in g['matches']:
                n = now.get((g['gid'], m['h'], m['a']))
                if not played(m) or (n and played(n) and (n['hs'], n['as']) == (m['hs'], m['as'])):
                    continue
                if not n or not played(n):
                    errors.append(f"{where(g, m)}: tenía resultado ({m['hs']}-{m['as']}) y ya no")
                else:
                    warnings.append(f"{where(g, m)}: el resultado cambia de {m['hs']}-{m['as']} a {n['hs']}-{n['as']}")
        lost = [t['name'] for i, t in teams.items() if not t.get('players') and old['teams'].get(i, {}).get('players')]
        if len(lost) > len(teams) // 10:
            errors.append(f'{len(lost)} equipos se quedan sin estadísticas de jugadores (¿falló la extracción?)')
        elif lost:
            warnings.append(f"equipos que se quedan sin estadísticas de jugadores: {', '.join(lost)}")
    return errors, warnings


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('file', nargs='?', type=Path, help='fcbq_raw.json descargado (por defecto, el más reciente de Descargas)')
    ap.add_argument('--push', action='store_true', help='hacer commit y push de los datos')
    ap.add_argument('--force', action='store_true', help='actualizar aunque la validación encuentre errores')
    opts = ap.parse_args()

    src = opts.file
    if not src:
        # El navegador renombra las descargas repetidas: "fcbq_raw (1).json"
        found = sorted(downloads_dir().glob('fcbq_raw*.json'), key=lambda p: p.stat().st_mtime)
        if not found:
            sys.exit(f'No hay ningún fcbq_raw*.json en {downloads_dir()}. Ejecuta antes scripts/extract.js (ver README.md)')
        src = found[-1]

    new = json.loads(src.read_text(encoding='utf-8'))
    old = json.loads(RAW.read_text(encoding='utf-8')) if RAW.exists() else None
    if old and new.get('scrapedAt', '') < old['scrapedAt']:
        sys.exit(f"{src} es del {new.get('scrapedAt', '?')[:10]}, más antiguo que los datos actuales ({old['scrapedAt'][:10]})")
    errors, warnings = validate(new, old)
    for w in warnings:
        print(f'Aviso: {w}')
    for e in errors:
        print(f'ERROR: {e}', file=sys.stderr)
    if errors and not opts.force:
        sys.exit(f'{len(errors)} errores en {src}; no se cambia nada (--force para actualizar igualmente)')

    print(f'Usando {src}', flush=True)
    shutil.copyfile(src, RAW)
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_data.py')], check=True)
    if old:
        (t0, _, p0), (t, _, p) = summary(old), summary(new)
        print(f'Partidos jugados: {p0} → {p} · equipos: {t0} → {t}')

    if opts.push:
        if not subprocess.run(['git', '-C', str(ROOT), 'status', '--porcelain', '--', 'data', 'cal'], capture_output=True, text=True).stdout.strip():
            print('Sin cambios en los datos; no hay nada que subir')
            return
        d, m, y = new['scrapedAt'][8:10], new['scrapedAt'][5:7], new['scrapedAt'][:4]
        for args in (['add', '-A', 'data/fcbq_raw.json', 'data/cadet-data.js', 'data/fcbq_box.json', 'data/cadet-box.js', 'cal'],
                     ['commit', '-q', '-m', f'Actualizar datos al {d}-{m}-{y}'], ['push', '-q']):
            subprocess.run(['git', '-C', str(ROOT), *args], check=True)
        print('Commit y push hechos')


if __name__ == '__main__':
    main()
