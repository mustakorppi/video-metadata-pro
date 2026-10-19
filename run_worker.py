#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-only
# Copyright and licensing scope: see COPYRIGHT.md in the project root.
"""Launch a job from either the checkout or an installed support directory."""
import sys

from helper.worker import main


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))
