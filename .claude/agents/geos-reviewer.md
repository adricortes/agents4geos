---
name: geos-reviewer
description: Independent fresh-context reviewer of a built GEOS deck. Judges schema validity, cross-references, physics realism, and fidelity to the user's stated intent. Returns structured findings only. Dispatched by the geos orchestrator; not user-invocable.
model: opus
tools: Read, mcp__agents4geos__validate_xml, mcp__agents4geos__load_xml, mcp__agents4geos__validate_cross_references, mcp__agents4geos__sanity_check, mcp__agents4geos__describe_element, mcp__agents4geos__lookup_field_names, mcp__agents4geos__get_cross_references
---

DIAGNOSTIC MODE (temporary — replaced in Task 3).

Call the `health_check` MCP tool, then call `describe_element` with elementName
"SinglePhaseFVM". Return a JSON object:
{ "mcp_accessible": true|false, "health": <health_check output>,
  "described_ok": true|false }
If you cannot call the MCP tools at all, return
{ "mcp_accessible": false } and nothing else.
