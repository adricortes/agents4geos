#!/usr/bin/env bash
# install-for-evaluators.sh
#
# Bootstraps agents4geos on a machine that doesn't have adriano's exact
# ~/codes/ layout. Clones the three editable-path dependencies to the
# locations referenced by pyproject.toml, then runs `uv sync --all-extras`.
#
# This is a WORKAROUND for the editable-path dependencies in pyproject.toml.
# A proper fix (PyPI / git URLs) is tracked in beads as agents4geos-cc4,
# agents4geos-nsu, and agents4geos-eqn.
#
# Usage:
#   cd /path/to/agents4geos
#   bash scripts/install-for-evaluators.sh
#
# Requires: git, uv (https://docs.astral.sh/uv/), Python 3.11+.

set -euo pipefail

# ---- locate this repo regardless of CWD --------------------------------
SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
AGENTS4GEOS_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# pyproject.toml uses these relative paths:
#   geos-tui     = "../../geos-tui"
#   pyrestoolbox = "../pyResToolbox"
#   pyvista      = "../pyvista"
GEOS_TUI_DIR="$( cd "$AGENTS4GEOS_DIR/../.." && pwd )/geos-tui"
PYRTB_DIR="$( cd "$AGENTS4GEOS_DIR/.." && pwd )/pyResToolbox"
PYVISTA_DIR="$( cd "$AGENTS4GEOS_DIR/.." && pwd )/pyvista"

echo "agents4geos:         $AGENTS4GEOS_DIR"
echo "geos-tui target:     $GEOS_TUI_DIR"
echo "pyResToolbox target: $PYRTB_DIR"
echo "pyvista target:      $PYVISTA_DIR"
echo

# ---- preflight ---------------------------------------------------------
for cmd in git uv; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "ERROR: '$cmd' is not on PATH." >&2
        echo "Install it before re-running this script." >&2
        exit 1
    fi
done

# ---- clone helper ------------------------------------------------------
clone_if_missing() {
    local target="$1"
    local url="$2"
    local label="$3"

    if [[ -d "$target/.git" ]]; then
        echo "[$label] already cloned at $target — skipping."
        return 0
    fi
    if [[ -e "$target" ]]; then
        echo "ERROR: $target exists but is not a git repo." >&2
        echo "Move it aside or delete it before re-running." >&2
        exit 1
    fi
    echo "[$label] cloning $url → $target"
    git clone --depth 1 "$url" "$target"
}

# ---- clone the three deps ---------------------------------------------
clone_if_missing "$GEOS_TUI_DIR" \
    "https://github.com/adricortes/geos-tui.git" \
    "geos-tui"

clone_if_missing "$PYRTB_DIR" \
    "https://github.com/adricortes/pyResToolbox.git" \
    "pyResToolbox (SI fork)"

clone_if_missing "$PYVISTA_DIR" \
    "https://github.com/pyvista/pyvista.git" \
    "pyvista"

# ---- uv sync -----------------------------------------------------------
echo
echo "Running 'uv sync --all-extras' in $AGENTS4GEOS_DIR ..."
cd "$AGENTS4GEOS_DIR"
uv sync --all-extras

# ---- smoke check -------------------------------------------------------
echo
echo "Verifying core imports ..."
uv run python - <<'PY'
import sys
errs = []
for label, mod in [
    ("geos-tui",      "geos_tui.schema.parser"),
    ("pyResToolbox",  "pyrestoolbox.gas"),
    ("PyVista",       "pyvista"),
    ("agents4geos",   "agents4geos"),
]:
    try:
        __import__(mod)
        print(f"  ok  {label:14s} ({mod})")
    except Exception as e:
        errs.append(f"  FAIL {label:14s} ({mod}): {e}")
if errs:
    print("\n".join(errs), file=sys.stderr)
    sys.exit(1)
PY

# ---- schema check ------------------------------------------------------
echo
echo "Verifying bundled schema is loadable (no GEOS build required) ..."
uv run python - <<'PY'
from agents4geos.config import get_schema
schema = get_schema()
print(f"  ok  schema loaded ({len(schema.elements)} elements)")
PY

echo
echo "Done. agents4geos is installed and the bundled GEOS schema works."
echo "Next: register the MCP server with Claude Code — see the 'Quick Start"
echo "for Evaluators' section in the README."
