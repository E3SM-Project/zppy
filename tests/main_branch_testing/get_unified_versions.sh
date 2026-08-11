#!/usr/bin/env bash
# get_unified_versions.sh
#
# Captures the resolved package versions from an E3SM-Unified environment by
# sourcing its load script and introspecting the resulting Python
# environment directly (via `pip list --format=json`, falling back to
# `importlib.metadata`). This deliberately does NOT rely on `pixi list` or
# `conda list`: the Unified load script just puts a prebuilt environment on
# PATH, not a pixi project directory, and asking Python what's actually
# installed works no matter which tool (conda, mamba, pixi/rattler) built
# that environment.
#
# Usage:
#   ./get_unified_versions.sh <path-to-load-script> <output-file.json>
#
# Example (Chrysalis):
#   ./get_unified_versions.sh \
#       /lcrc/soft/climate/e3sm-unified/load_latest_e3sm_unified_chrysalis.sh \
#       unified_versions.json
#
# IMPORTANT: "load_latest_..." tracks whatever Unified release is currently
# newest. Make sure this is the SAME release that was active on the date
# the expected results were generated (Step 1) -- if your site keeps a
# dated/archived load script for that specific release, source that one
# instead, or you'll be comparing against a newer Unified than the one that
# actually produced the expected-results images.

set -euo pipefail

LOAD_SCRIPT="${1:?Usage: $0 <path-to-load-script> <output-file.json>}"
OUT_FILE="${2:?Usage: $0 <path-to-load-script> <output-file.json>}"

if [ ! -f "$LOAD_SCRIPT" ]; then
    echo "ERROR: load script not found: $LOAD_SCRIPT" >&2
    exit 1
fi

echo "Sourcing: $LOAD_SCRIPT"
# Third-party activation scripts (conda/pixi/etc.) are often not written to
# be safe under `set -u`/`set -e` -- e.g. they may reference environment
# variables that are only conditionally set. Relax our strict flags just
# for the source call so an unrelated unbound-variable check in someone
# else's script doesn't abort ours.
set +euo pipefail
# shellcheck disable=SC1090
source "$LOAD_SCRIPT"
set -euo pipefail

PY="$(command -v python || command -v python3 || true)"
if [ -z "$PY" ]; then
    echo "ERROR: no python/python3 on PATH after sourcing the load script." >&2
    echo "       Check that the load script actually activated an environment." >&2
    exit 1
fi

echo "Using interpreter: $PY"
"$PY" -c "import sys; print('sys.prefix:', sys.prefix)"

if "$PY" -m pip list --format=json > "$OUT_FILE" 2>/dev/null && [ -s "$OUT_FILE" ]; then
    echo "Wrote package list (via pip) -> $OUT_FILE"
else
    echo "pip unavailable (or failed) in this env; falling back to importlib.metadata"
    "$PY" -c "
import json, importlib.metadata as m
pkgs = []
for d in m.distributions():
    try:
        pkgs.append({'name': d.metadata['Name'], 'version': d.version})
    except Exception:
        pass
print(json.dumps(pkgs))
" > "$OUT_FILE"
    echo "Wrote package list (via importlib.metadata) -> $OUT_FILE"
fi

# `pip list` does not include the interpreter itself as a package, but
# dev.yml files almost always pin `python=`, so inject it explicitly.
"$PY" -c "
import json, sys
with open(sys.argv[1]) as f:
    pkgs = json.load(f)
py_version = '.'.join(str(v) for v in sys.version_info[:3])
pkgs = [p for p in pkgs if p.get('name', '').lower() != 'python']
pkgs.append({'name': 'python', 'version': py_version})
with open(sys.argv[1], 'w') as f:
    json.dump(pkgs, f)
" "$OUT_FILE"

COUNT=$("$PY" -c "import json,sys; print(len(json.load(open(sys.argv[1]))))" "$OUT_FILE" 2>/dev/null || echo "?")
echo "Captured $COUNT packages from the Unified environment (including python itself)."
