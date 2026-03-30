#!/bin/bash
# PostToolUse hook: notify when VTK files are created
f="$CLAUDE_TOOL_OUTPUT_PATH"
if [[ "$f" == *.vtu ]] || [[ "$f" == *.vtk ]] || [[ "$f" == *.vti ]] || [[ "$f" == *.vtr ]]; then
    echo "VTK file created: $f — use /geos:mesh to visualize"
fi
