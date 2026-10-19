#!/bin/sh
# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
: "${SNAP_USER_COMMON:?Run this launcher inside Snap VLC}"
metadata_runtime="$SNAP_USER_COMMON/video-metadata-runtime"
export PYTHONPATH="$metadata_runtime/python${PYTHONPATH:+:$PYTHONPATH}"
export PATH="$metadata_runtime/mkvtoolnix/usr/bin:$PATH"
export LD_LIBRARY_PATH="$metadata_runtime/mkvtoolnix/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
exec /usr/bin/python3 "$@"
