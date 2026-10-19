from mcp.server.auth.settings import ClientRegistrationOptions

from fastmcp import FastMCP
from fastmcp.server.auth.providers.in_memory import InMemoryOAuthProvider

from tools import register_tools

# Simulates the full OAuth 2.1 flow (dynamic client registration, authorization
# code grant, token exchange) entirely in-memory with no external identity
# provider — for local development/testing only.
auth = InMemoryOAuthProvider(
    base_url="http://127.0.0.1:8002",
    required_scopes=["tools:read"],
    client_registration_options=ClientRegistrationOptions(
        enabled=True, valid_scopes=["tools:read", "tools:write"]
    ),
)

mcp = FastMCP("Toolbox (OAuth 2.1)", auth=auth)
register_tools(mcp)

if __name__ == "__main__":
    mcp.run(transport="http", host="127.0.0.1", port=8002)
