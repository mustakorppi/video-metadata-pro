# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""Lossless token record for the optional VLC-readable combined Album string."""
import json


def is_packed(values, record):
    try:
        entries = json.loads(record)
        if (isinstance(entries, list) and entries
                and all(isinstance(v, str) and v for v in entries)
                and values == [' '.join(entries)]):
            return True
    except (ValueError, TypeError, UnicodeError):
        pass
    return False


def unpack(values, record):
    return json.loads(record) if is_packed(values, record) else values


def pack(entries):
    return json.dumps(entries, ensure_ascii=False)
