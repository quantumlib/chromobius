#!/bin/bash
set -e

#########################################################################
# Regenerates doc files using the installed version of stim.
#########################################################################

# Get to this script's git repo root.
cd "$( dirname "${BASH_SOURCE[0]}" )"
cd "$(git rev-parse --show-toplevel)"

python tools/gen_chromobius_api_reference.py -dev > doc/chromobius_api_reference.md
python tools/gen_chromobius_stub_file.py -dev > doc/chromobius.pyi
