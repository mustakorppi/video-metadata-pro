# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""VLC-compatible global Matroska tags; preserve other scopes and languages."""
import copy
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from . import album_values

FIELDS = {'artist': ('ARTIST', '30'), 'album': ('TITLE', '50'), 'genre': ('GENRE', '30')}
ALBUM_RECORD = 'VIDEO_METADATA_PRO_ALBUM_VALUES'
GENRE_RECORD = 'VIDEO_METADATA_PRO_GENRE_VALUES'


def value_records(root, name):
    for tag in root.findall('Tag'):
        targets = tag.find('Targets')
        if targets is not None and any(t.tag.endswith('UID') for t in targets):
            continue
        for node in tag.findall('Simple'):
            if (node.findtext('Name') == name
                    and node.findtext('TagLanguage', 'und') == 'und'
                    and node.findtext('TagLanguageIETF', 'und') == 'und'
                    and node.findtext('DefaultLanguage', '1') == '1'):
                yield tag, node


def album_records(root):
    return value_records(root, ALBUM_RECORD)


def run(*args):
    result = subprocess.run(args, capture_output=True, text=True)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr or result.stdout)


def extract(path):
    with tempfile.TemporaryDirectory() as directory:
        xml = Path(directory) / 'tags.xml'
        run('mkvextract', str(path), 'tags', str(xml))
        return ET.parse(xml).getroot() if xml.exists() else ET.Element('Tags')


def matches(root, field):
    for tag in root.findall('Tag'):
        targets = tag.find('Targets')
        if targets is not None and any(t.tag.endswith('UID') for t in targets):
            continue
        level = tag.findtext('Targets/TargetTypeValue', '50')
        for node in tag.findall('Simple'):
            name = node.findtext('Name')
            match = ((field == 'artist' and name == 'ARTIST' and level != '50')
                     or (field == 'album' and (name == 'ALBUM' or (name == 'TITLE' and level == '50')))
                     or (field == 'genre' and name == 'GENRE'))
            if (match and node.findtext('TagLanguage', 'und') == 'und'
                    and node.findtext('TagLanguageIETF', 'und') == 'und'
                    and node.findtext('DefaultLanguage', '1') == '1'):
                yield tag, node


def values(root):
    result = {field: list(dict.fromkeys(n.findtext('String') for _, n in matches(root, field)
                                      if n.find('String') is not None))
              for field in FIELDS}
    for _, node in album_records(root):
        result['album'] = album_values.unpack(result['album'], node.findtext('String'))
    for _, node in value_records(root, GENRE_RECORD):
        result['genre'] = album_values.unpack(result['genre'], node.findtext('String'))
    return result


def album_packed(path):
    root = extract(path)
    raw = list(dict.fromkeys(n.findtext('String') for _, n in matches(root, 'album')
                             if n.find('String') is not None))
    return any(album_values.is_packed(raw, node.findtext('String'))
               for _, node in album_records(root))


def read(path):
    return values(extract(path))


def display_changes(path):
    """Convert repeated Genre values to a single VLC-readable display string."""
    root = extract(path)
    raw = {node.findtext('String') for _, node in matches(root, 'genre')
           if node.find('String') is not None}
    return {'genre': values(root)['genre']} if len(raw) > 1 else {}


def update(path, changes, album_as_text=False):
    root = extract(path)
    changes = dict(changes)
    if 'genre' in changes:
        for tag, node in list(value_records(root, GENRE_RECORD)):
            tag.remove(node)
            if not tag.findall('Simple') and tag in list(root):
                root.remove(tag)
        if changes['genre']:
            tag = ET.SubElement(root, 'Tag')
            ET.SubElement(tag, 'Targets')
            node = ET.SubElement(tag, 'Simple')
            ET.SubElement(node, 'Name').text = GENRE_RECORD
            ET.SubElement(node, 'String').text = album_values.pack(changes['genre'])
            changes['genre'] = [' '.join(changes['genre'])]
    if 'album' in changes:
        for tag, node in list(album_records(root)):
            tag.remove(node)
            if not tag.findall('Simple') and tag in list(root):
                root.remove(tag)
        if album_as_text and changes['album']:
            tag = ET.SubElement(root, 'Tag')
            ET.SubElement(tag, 'Targets')
            node = ET.SubElement(tag, 'Simple')
            ET.SubElement(node, 'Name').text = ALBUM_RECORD
            ET.SubElement(node, 'String').text = album_values.pack(changes['album'])
            changes['album'] = [' '.join(changes['album'])]
    for field, entries in changes.items():
        found = list(matches(root, field))
        if not entries:
            for tag, node in found:
                if node.find('Binary') is not None:
                    raise ValueError('Cannot clear a binary tag')
                if node.findall('Simple'):
                    # Retain the named parent and its nested metadata, removing
                    # only its own value so the children keep their meaning.
                    for string in list(node.findall('String')):
                        node.remove(string)
                else:
                    tag.remove(node)
                if not tag.findall('Simple') and tag in list(root):
                    root.remove(tag)
            continue
        if not found:
            name, level = FIELDS[field]
            tag = ET.SubElement(root, 'Tag')
            ET.SubElement(ET.SubElement(tag, 'Targets'), 'TargetTypeValue').text = level
            node = ET.SubElement(tag, 'Simple')
            ET.SubElement(node, 'Name').text = name
            found = [(tag, node)]
        # Preserve each existing scope/alias and any nested information.
        groups = {}
        for tag, node in found:
            if node.find('Binary') is not None:
                raise ValueError('Cannot replace a binary tag')
            groups.setdefault((id(tag), node.findtext('Name')), []).append((tag, node))
        for group in groups.values():
            tag, template = group[0]
            for index, (_, node) in enumerate(group):
                string = node.find('String')
                if string is None:
                    string = ET.SubElement(node, 'String')
                string.text = entries[min(index, len(entries) - 1)]
            for entry in entries[len(group):]:
                node = copy.deepcopy(template)
                for nested in list(node.findall('Simple')):
                    node.remove(nested)
                node.find('String').text = entry
                tag.append(node)
    with tempfile.TemporaryDirectory() as directory:
        xml = Path(directory) / 'tags.xml'
        ET.ElementTree(root).write(xml, encoding='utf-8', xml_declaration=True)
        run('mkvpropedit', str(path), '--tags', 'all:' + str(xml))
