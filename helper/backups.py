# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""Inspect and remove only exact sibling backups for one video."""
import hashlib
import json
import re
import stat


def inventory(path):
    pattern = re.compile(re.escape(path.name) + r'\.bak(?:\.[1-9][0-9]*)?\Z')
    entries = []
    for candidate in path.parent.iterdir():
        if not pattern.fullmatch(candidate.name):
            continue
        info = candidate.lstat()
        if stat.S_ISREG(info.st_mode):
            entries.append((candidate.name, info.st_dev, info.st_ino,
                            info.st_size, info.st_mtime_ns, info.st_ctime_ns))
    return sorted(entries)


def inspect(path):
    entries = inventory(path)
    source = path.stat()
    signature = [str(path), source.st_dev, source.st_ino, source.st_size,
                 source.st_mtime_ns, source.st_ctime_ns, entries]
    token = hashlib.sha256(json.dumps(signature).encode()).hexdigest()
    return entries, token


def execute(path, request):
    entries, token = inspect(path)
    if request['mode'] == 'backups_delete':
        if not request.get('backup_token') or request['backup_token'] != token:
            raise ValueError('Video or backups changed. Click Remove backups to review them again.')
        removed = 0
        try:
            for entry in entries:
                candidate = path.parent / entry[0]
                info = candidate.lstat()
                if not stat.S_ISREG(info.st_mode) or entry[1:] != (
                        info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns):
                    raise OSError('Backup changed; review again')
                candidate.unlink()
                removed += 1
        except OSError as error:
            raise RuntimeError('Removed %d of %d backups; cleanup stopped: %s' %
                               (removed, len(entries), error)) from error
        return {'file': str(path), 'message': 'Removed %d backup files. Video unchanged.' % removed}
    return {'file': str(path), 'backup_count': str(len(entries)),
            'backup_bytes': str(sum(entry[3] for entry in entries)), 'backup_token': token}
