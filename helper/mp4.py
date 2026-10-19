# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""Space-separated MP4 display strings with lossless editable value records."""
from mutagen.mp4 import MP4
from . import album_values

FIELDS = {'artist': '\xa9ART', 'album': '\xa9alb', 'genre': '\xa9gen'}
DISPLAY_RECORDS = {field: '----:org.video-metadata-pro:display-' + field + '-values' for field in FIELDS}
ALBUM_RECORD = '----:org.video-metadata-pro:album-values'


def read(path):
    tags = MP4(path).tags or {}
    result = {field: list(dict.fromkeys(tags.get(atom, []))) for field, atom in FIELDS.items()}
    for field, record in DISPLAY_RECORDS.items():
        result[field] = album_values.unpack(result[field], tags.get(record, [None])[0])
    result['album'] = album_values.unpack(result['album'], tags.get(ALBUM_RECORD, [None])[0])
    return result


def album_packed(path):
    tags = MP4(path).tags or {}
    values = tags.get(FIELDS['album'], [])
    return ALBUM_RECORD in tags and album_values.is_packed(values, tags[ALBUM_RECORD][0])


def display_changes(path):
    """Migrate repeated atoms on Save even when their logical values are unchanged."""
    tags = MP4(path).tags or {}
    values = read(path)
    return {field: values[field] for field, atom in FIELDS.items()
            if len(tags.get(atom, [])) > 1}


def update(path, changes, album_as_text=False):
    media = MP4(path)
    if media.tags is None:
        media.add_tags()
    for field, entries in changes.items():
        media.tags.pop(DISPLAY_RECORDS[field], None)
        if entries:
            media.tags[FIELDS[field]] = [' '.join(entries)]
            media.tags[DISPLAY_RECORDS[field]] = [album_values.pack(entries).encode('utf-8')]
        else:
            media.tags.pop(FIELDS[field], None)
        if field == 'album':
            media.tags.pop(ALBUM_RECORD, None)
            if album_as_text and entries:
                media.tags.pop(DISPLAY_RECORDS[field], None)
                media.tags[FIELDS[field]] = [' '.join(entries)]
                media.tags[ALBUM_RECORD] = [album_values.pack(entries).encode('utf-8')]
        if field == 'genre':
            media.tags.pop('gnre', None)
    media.save()
