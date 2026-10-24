#!/usr/bin/env python3
"""Actualiza los datos a partir del fcbq_raw.json que descarga scripts/extract.js.

Coge el fcbq_raw.json más reciente de la carpeta de descargas (o el que se
indique), lo copia a data/, regenera data/cadet-data.js y, con --push, hace
commit y push.

Uso:
  python3 scripts/update.py                  # actualiza los datos
  python3 scripts/update.py --push           # y además hace commit y push
  python3 scripts/update.py ruta/al/archivo.json
"""
import argparse
import json
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


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('file', nargs='?', type=Path, help='fcbq_raw.json descargado (por defecto, el más reciente de Descargas)')
    ap.add_argument('--push', action='store_true', help='hacer commit y push de los datos')
    opts = ap.parse_args()

    src = opts.file
    if not src:
        # El navegador renombra las descargas repetidas: "fcbq_raw (1).json"
        found = sorted(downloads_dir().glob('fcbq_raw*.json'), key=lambda p: p.stat().st_mtime)
        if not found:
            sys.exit(f'No hay ningún fcbq_raw*.json en {downloads_dir()}. Ejecuta antes scripts/extract.js (ver README.md)')
        src = found[-1]

    new = json.loads(src.read_text(encoding='utf-8'))
    if not new.get('groups') or not new.get('teams'):
        sys.exit(f'{src} no tiene datos de grupos o equipos; no se cambia nada')
    old = json.loads(RAW.read_text(encoding='utf-8')) if RAW.exists() else None
    if old and new['scrapedAt'] < old['scrapedAt']:
        sys.exit(f"{src} es del {new['scrapedAt'][:10]}, más antiguo que los datos actuales ({old['scrapedAt'][:10]})")

    print(f'Usando {src}', flush=True)
    shutil.copyfile(src, RAW)
    subprocess.run([sys.executable, str(ROOT / 'scripts' / 'build_data.py')], check=True)
    if old:
        (t0, _, p0), (t, _, p) = summary(old), summary(new)
        print(f'Partidos jugados: {p0} → {p} · equipos: {t0} → {t}')

    if opts.push:
        if not subprocess.run(['git', '-C', str(ROOT), 'diff', '--quiet', '--', 'data']).returncode:
            print('Sin cambios en los datos; no hay nada que subir')
            return
        d, m, y = new['scrapedAt'][8:10], new['scrapedAt'][5:7], new['scrapedAt'][:4]
        for args in (['add', 'data/fcbq_raw.json', 'data/cadet-data.js'],
                     ['commit', '-q', '-m', f'Actualizar datos al {d}-{m}-{y}'], ['push', '-q']):
            subprocess.run(['git', '-C', str(ROOT), *args], check=True)
        print('Commit y push hechos')


if __name__ == '__main__':
    main()
