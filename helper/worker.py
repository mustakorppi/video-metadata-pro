# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""One background read/save job. Linux only; no server or shell metadata."""
import fcntl
import hashlib
import logging
import os
from pathlib import Path
import shutil
import sys
import tempfile
from urllib.parse import quote, unquote

FIELDS = ('artist', 'album', 'genre')
CLEAR_FIELDS = tuple('clear_' + field for field in FIELDS)


def alphabetical(entries):
    return sorted(set(entries), key=lambda value: (value.casefold(), value))


def tokens(text):
    entries = list(dict.fromkeys(text.split()))
    if not entries:
        raise ValueError('Use Clear on Save to remove an entire field')
    if any(any(ord(c) < 32 or 0xD800 <= ord(c) <= 0xDFFF or ord(c) in (0xFFFE, 0xFFFF) for c in v) for v in entries):
        raise ValueError('Invalid control character in metadata')
    return alphabetical(entries)


class ReadCancelled(Exception):
    """The editor no longer needs this read-only job."""


def fingerprint(path, cancel=None):
    digest = hashlib.sha256()
    with open(path, 'rb') as file:
        while True:
            if cancel and cancel():
                raise ReadCancelled('Load cancelled after navigation or close')
            chunk = file.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def adapter(path):
    if path.suffix.lower() == '.mkv':
        from . import mkv
        return mkv
    if path.suffix.lower() == '.mp4':
        from . import mp4
        return mp4
    raise ValueError('Choose a local MP4 or MKV file')


def wire_read(path):
    data = path.read_text(encoding='utf-8')
    if len(data) > 65536:
        raise ValueError('Request too large')
    result = {}
    for line in data.splitlines():
        key, value = line.split('=', 1)
        if key in result or key not in (*FIELDS, *CLEAR_FIELDS, 'file', 'mode', 'fingerprint', 'append_genre_to_album', 'backup_token'):
            raise ValueError('Invalid request field')
        result[key] = unquote(value, errors='strict')
    return result


def metadata_result(path, backend, cancel=None):
    metadata = backend.read(path)
    result = {'file': str(path), 'fingerprint': fingerprint(path, cancel) if cancel else fingerprint(path)}
    for field, entries in metadata.items():
        result[field] = ' '.join(entries)
        result[field + '_legacy'] = '1' if any(not v or any(c.isspace() for c in v) for v in entries) else '0'
    return result


def album_without_genre_suffix(path, backend, existing):
    """Remove the matching Genre suffix only from an extension-packed Album."""
    albums = existing['album']
    genres = alphabetical(existing['genre'])
    if genres and backend.album_packed(path) and albums[-len(genres):] == genres:
        return albums[:-len(genres)]
    return albums


def append_genres_to_album(path, backend, changes):
    """Return pending changes with the optional sorted Genre suffix applied."""
    changes = dict(changes)
    # Explicit Album removal wins over automatic appending.
    if changes.get('album') == [] or (changes.get('genre') == [] and 'album' not in changes):
        return changes
    existing = backend.read(path)
    genres = changes.get('genre', existing['genre'])
    albums = changes.get('album', album_without_genre_suffix(path, backend, existing)
                         if 'genre' in changes else existing['album'])
    # Keep the base Album and replace the previously appended Genre suffix.
    combined = alphabetical(v for v in albums if v not in genres)
    combined += alphabetical(genres)
    if combined and ('album' in changes or combined != existing['album']
                     or (len(combined) > 1 and not backend.album_packed(path))):
        changes['album'] = combined
    return changes


def requested_changes(request):
    """Keep deliberate removal separate from accidentally empty text input."""
    changes = {}
    for field in FIELDS:
        clear = request.get('clear_' + field, 'false')
        if clear not in ('true', 'false'):
            raise ValueError('Invalid clear_' + field + ' option')
        if clear == 'true':
            if field in request:
                raise ValueError('Cannot clear and replace ' + field + ' in the same request')
            changes[field] = []
        elif field in request:
            changes[field] = tokens(request[field])
    return changes


def save_transaction(path, backend, changes, before, *, album_as_text=False):
    """Verify a modified copy, back up the source, then commit under the caller's lock."""
    fd, temporary = tempfile.mkstemp(prefix='.' + path.stem + '-', suffix=path.suffix, dir=path.parent)
    os.close(fd)
    temporary = Path(temporary)
    try:
        shutil.copy2(path, temporary)
        backend.update(temporary, changes, album_as_text=album_as_text)
        actual = backend.read(temporary)
        if any(actual[field] != entries for field, entries in changes.items()):
            raise ValueError('Saved metadata did not pass readback verification')
        with temporary.open('rb') as file:
            os.fsync(file.fileno())
        if fingerprint(path) != before:
            raise ValueError('Original changed during save; replacement cancelled')
        index = 0
        while True:
            backup = Path(str(path) + ('.bak' if index == 0 else '.bak.' + str(index)))
            try:
                with backup.open('xb') as output, path.open('rb') as source:
                    shutil.copyfileobj(source, output)
                    output.flush()
                    os.fsync(output.fileno())
                break
            except FileExistsError:
                index += 1
        shutil.copystat(path, backup)
        if fingerprint(backup) != before or fingerprint(path) != before:
            raise ValueError('Original changed during backup; replacement cancelled')
        # Build result before commit so metadata errors cannot masquerade as a failed write.
        result = metadata_result(temporary, backend)
        os.replace(temporary, path)
        return {**result, 'file': str(path), 'backup': str(backup)}
    finally:
        temporary.unlink(missing_ok=True)


def execute(request, jobs, cancel=None):
    # Cancellation must never interrupt a submitted save or backup deletion.
    cancel = cancel if request['mode'] == 'read' else None
    if cancel and cancel():
        raise ReadCancelled('Load cancelled after navigation or close')
    original = Path(request['file']).absolute()
    if original.is_symlink() or not original.is_file():
        raise ValueError('Choose a regular file, not a symbolic link')
    path = original.resolve(strict=True)
    backend = adapter(path)
    lock_name = hashlib.sha256(str(path).encode()).hexdigest() + '.lock'
    with (jobs / lock_name).open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another operation is working on this file')
        if request['mode'] in ('backups_preview', 'backups_delete'):
            from . import backups
            return backups.execute(path, request)
        before = fingerprint(path, cancel) if cancel else fingerprint(path)
        if request['mode'] == 'read':
            result = metadata_result(path, backend, cancel)
            if result['fingerprint'] != before:
                raise ValueError('File changed while loading; load again')
            return result
        if request['mode'] != 'save':
            raise ValueError('Unknown operation')
        if before != request.get('fingerprint'):
            raise ValueError('File changed since loading. Load it again before saving.')
        changes = requested_changes(request)
        option = request.get('append_genre_to_album', 'false')
        if option not in ('true', 'false'):
            raise ValueError('Invalid append_genre_to_album option')
        existing = backend.read(path)
        if changes.get('genre') == [] and 'album' not in changes:
            albums = album_without_genre_suffix(path, backend, existing)
            if albums != existing['album']:
                changes['album'] = albums
        for field, entries in existing.items():
            # Packed Albums retain their two groups when appending is disabled.
            # Unmarked Albums are not changed by clearing Genre.
            if field == 'album' and (changes.get('genre') == [] or backend.album_packed(path)):
                continue
            ordered = alphabetical(entries)
            if field not in changes and ordered != entries:
                changes[field] = ordered
        for field, entries in getattr(backend, 'display_changes', lambda path: {})(path).items():
            changes.setdefault(field, alphabetical(entries))
        if option == 'true':
            changes = append_genres_to_album(path, backend, changes)
        if not changes:
            return {**metadata_result(path, backend), 'message': 'No metadata changes needed.'}
        return save_transaction(path, backend, changes, before, album_as_text=option == 'true')


def main(job):
    job = Path(job)
    logger = logging.getLogger('video_metadata.worker')
    logger.setLevel(logging.INFO)
    handler = logging.FileHandler(job / 'worker.log', encoding='utf-8')
    handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
    logger.addHandler(handler)
    try:
        try:
            request = wire_read(job / 'request.txt')
            logger.info('Starting %s: %s', request.get('mode'), request.get('file'))
            result = {'state': 'success', **execute(request, job.parent, cancel=lambda: (job / 'cancel').exists())}
            logger.info('Completed %s: %s; backup=%s', request.get('mode'),
                        result.get('file'), result.get('backup', 'none'))
        except ReadCancelled as error:
            logger.info('%s', error)
            result = {'state': 'cancelled', 'message': str(error)}
        except Exception as error:
            logger.exception('Job failed')
            result = {'state': 'error', 'message': str(error)}
        temporary = job / 'result.tmp'
        temporary.write_text(''.join(k + '=' + quote(str(v), safe='') + '\n' for k, v in result.items()), encoding='utf-8')
        temporary.replace(job / 'result.txt')
        return 0 if result['state'] == 'success' else 1
    except Exception:
        logger.exception('Could not publish job result')
        raise
    finally:
        logger.removeHandler(handler)
        handler.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
