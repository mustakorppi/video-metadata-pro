#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""Install for conventional Linux VLC 3; never overwrite user presets."""
import argparse
from datetime import date
import json
import re
import os
from pathlib import Path
import shutil
import sys


def lua_string(value):
    return '"' + ''.join('\\%03d' % byte for byte in str(value).encode('utf-8')) + '"'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', type=Path, default=Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local/share')) / 'vlc')
    parser.add_argument('--python', default=sys.executable, help='Python interpreter with Mutagen installed')
    args = parser.parse_args()
    root = Path(__file__).resolve().parent
    try:
        release = json.loads((root / 'release.json').read_text(encoding='utf-8'))
        version, build_date = release['version'], release['build_date']
        if not isinstance(version, str) or not re.fullmatch(r'[0-9]+(?:\.[0-9]+){1,2}(?: RC[1-9][0-9]*)?', version):
            raise ValueError('version must contain two or three numeric components, optionally followed by RC1, RC2, etc.')
        if not isinstance(build_date, str) or date.fromisoformat(build_date).isoformat() != build_date:
            raise ValueError('build_date must use YYYY-MM-DD')
    except (OSError, ValueError, KeyError, TypeError) as error:
        parser.error(f'Invalid release.json: {error}')
    # Keep Snap's current symlink so refreshes do not pin the helper to an old revision.
    destination = args.data_dir.expanduser().absolute() / 'lua/extensions'
    support = destination / 'video_metadata_support'
    (support / 'jobs').mkdir(parents=True, exist_ok=True, mode=0o700)
    (support / 'config').mkdir(exist_ok=True)
    (support / 'helper').mkdir(exist_ok=True)
    for source in (root / 'helper').glob('*.py'):
        shutil.copy2(source, support / 'helper' / source.name)
    shutil.copy2(root / 'run_worker.py', support / 'run_worker.py')
    for name in ('LICENSE', 'COPYRIGHT.md', 'release.json'):
        shutil.copy2(root / name, support / name)
    for template in (root / 'config').glob('*.txt.example'):
        source = template.with_suffix('')
        target = support / 'config' / source.name
        if not target.exists():
            shutil.copy2(source if source.is_file() else template, target)
    config = ('local SUPPORT_DIR = ' + lua_string(support) + '\nlocal PYTHON = ' + lua_string(args.python)
              + '\nlocal VERSION = ' + lua_string(version)
              + '\nlocal BUILD_DATE = ' + lua_string(build_date))
    extension = (root / 'vlc/video_metadata.lua').read_text().replace('-- @CONFIG@', config)
    (destination / 'video_metadata.lua').write_text(extension)
    print('Installed:', destination / 'video_metadata.lua')
    print('Presets:', support / 'config')
    print('Restart VLC, then select View > Metadata Pro.')


if __name__ == '__main__':
    main()
