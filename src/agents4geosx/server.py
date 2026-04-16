"""Agents4GEOSX MCP Server — tool definitions and registration."""

from fastmcp import FastMCP

mcp = FastMCP("Agents4GEOSX")


@mcp.tool
def health_check() -> dict:
    """Check that the Agents4GEOSX MCP server is running."""
    return {"status": "ok", "version": "0.1.0"}


def register_all_tools() -> None:
    """Import all tool modules so their @mcp.tool decorators execute."""
    import agents4geosx.tools.schema_tools  # noqa: F401
    import agents4geosx.tools.fluid_tools   # noqa: F401
    import agents4geosx.tools.mesh_tools    # noqa: F401
    import agents4geosx.tools.xml_tools     # noqa: F401
    import agents4geosx.tools.postproc_tools  # noqa: F401
    import agents4geosx.tools.preproc_tools   # noqa: F401


# Register tools at import time so they're available regardless of entry point
register_all_tools()
