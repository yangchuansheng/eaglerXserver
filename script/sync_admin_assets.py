#!/usr/bin/env python3
"""Materialize shared admin assets into the 1.12 web root."""

import shutil
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'web-1.8'
MIRROR = ROOT / 'web-1.12'
ASSETS = ('admin.html', 'admin.js', 'admin.css', 'admin-i18n.js', 'eaglercraft-server.svg', 'admin-world.png')


def main():
    check = sys.argv[1:] == ['--check']
    if sys.argv[1:] not in ([], ['--check']):
        raise SystemExit('usage: sync_admin_assets.py [--check]')
    stale = [
        name for name in ASSETS
        if not (MIRROR / name).is_file() or (SOURCE / name).read_bytes() != (MIRROR / name).read_bytes()
    ]
    if check:
        if stale:
            raise SystemExit('stale admin mirrors: ' + ', '.join(stale))
        return
    for name in stale:
        shutil.copy2(SOURCE / name, MIRROR / name)


if __name__ == '__main__':
    main()
