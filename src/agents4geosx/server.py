"""Agents4GEOSX MCP Server."""
from fastmcp import FastMCP

mcp = FastMCP("Agents4GEOSX")

@mcp.tool
def health_check() -> dict:
    """Check that the Agents4GEOSX MCP server is running."""
    return {"status": "ok", "version": "0.1.0"}

if __name__ == "__main__":
    mcp.run()
