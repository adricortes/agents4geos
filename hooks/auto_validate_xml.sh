#!/bin/bash
# PostToolUse hook: auto-validate XML files after Write/Edit
f="$CLAUDE_TOOL_OUTPUT_PATH"
if [[ "$f" == *.xml ]]; then
    schema="${GEOS_SCHEMA:-../../geos-tui/geos/build/schema.xsd}"
    xmllint --schema "$schema" "$f" --noout 2>&1 || true
fi
