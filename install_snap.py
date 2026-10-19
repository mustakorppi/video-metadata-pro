#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""Install into this user's VLC Snap using an existing compatible MKVToolNix runtime."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path,
                        default=root.parent / 'video-metadata/.runtime/mkvtoolnix',
                        help='Staged MKVToolNix directory containing usr/bin and usr/lib')
    args = parser.parse_args()
    try:
        import mutagen
    except ImportError:
        parser.error('The installer needs Mutagen available to this Python interpreter.')
    # Include mkvinfo for Super Playlist, which reuses this shared runtime.
    for tool in ('mkvextract', 'mkvpropedit', 'mkvinfo'):
        if not (args.runtime / 'usr/bin' / tool).is_file():
            parser.error('Missing staged tool: ' + str(args.runtime / 'usr/bin' / tool))
    snap = Path.home() / 'snap/vlc'
    if not (snap / 'current').is_dir():
        parser.error('Launch Snap VLC once before installing this extension.')
    runtime = snap / 'common/video-metadata-runtime'
    runtime.mkdir(parents=True, exist_ok=True)
    shutil.copytree(args.runtime, runtime / 'mkvtoolnix', dirs_exist_ok=True)
    shutil.copytree(Path(mutagen.__file__).parent, runtime / 'python/mutagen',
                    dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    launcher = runtime / 'python-launcher'
    shutil.copy2(root / 'launcher.sh', launcher)
    launcher.chmod(0o755)
    subprocess.run([sys.executable, str(root / 'install.py'),
                    '--data-dir', str(snap / 'current/.local/share/vlc'),
                    '--python', str(launcher)], check=True)


if __name__ == '__main__':
    main()
