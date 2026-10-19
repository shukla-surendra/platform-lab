from fastmcp import FastMCP
from fastmcp.server.auth.providers.jwt import StaticTokenVerifier

from tools import register_tools

# Demo tokens only — StaticTokenVerifier stores tokens in plain text and is
# not safe for production use.
TOKENS = {
    "demoxxxxreadxxxxtoken": {"client_id": "demo-client", "scopes": ["tools:read"]},
    "demoxxxxadminxxxxtoken": {"client_id": "admin-client", "scopes": ["tools:read", "tools:write"]},
}

auth = StaticTokenVerifier(tokens=TOKENS, required_scopes=["tools:read"])

mcp = FastMCP("Toolbox (Bearer Auth)", auth=auth)
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8001)
