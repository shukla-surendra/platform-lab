# fastmcp_auth_tools

A general-purpose MCP toolbox built on the standalone [`fastmcp`](https://gofastmcp.com) package, demonstrating both ways to authenticate a remote MCP server. The same tools (`tools.py`) are served by two separate, independently runnable servers — one per auth style — since auth only applies to network transports (HTTP), not local stdio.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Tools (shared by both servers)

- `fetch_url(url)` — HTTP GET via `httpx`; returns status, headers, truncated body
- `extract_links(html)` — pull all `href` links from HTML via `beautifulsoup4`
- `extract_text(html)` — strip tags/scripts/styles, return visible text
- `csv_summary(csv_text)` — parse CSV via `pandas`; returns shape, dtypes, `describe()`

## Auth mode 1: Bearer token / API key (`server_bearer.py`)

Simplest, most common setup for a self-hosted MCP server. Uses fastmcp's `StaticTokenVerifier` — a fixed dict of valid tokens with associated scopes, checked on every request. **Demo-only**: tokens are plain text in source, not for production.

```bash
python server_bearer.py   # serves on http://127.0.0.1:8001/mcp
```

Demo tokens (both scoped `tools:read`, `tools:write` also on `demo-admin-token`):
- `demo-read-token`
- `demo-admin-token`

Call it:

```python
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

async with Client("http://127.0.0.1:8001/mcp", auth=BearerAuth("demo-read-token")) as client:
    tools = await client.list_tools()
```

No token, or a token missing the required scope, returns `401`.

## Auth mode 2: Full OAuth 2.1 flow (`server_oauth.py`)

Implements the MCP spec's full remote-auth model: authorization server metadata discovery, dynamic client registration (RFC 7591), PKCE authorization-code grant, and token exchange — via fastmcp's `InMemoryOAuthProvider`, which simulates all of this in memory with no real external identity provider (dev/test only; a production server would swap in a real IdP-backed provider, e.g. `fastmcp.server.auth.providers.auth0` or `.workos`).

```bash
python server_oauth.py   # serves on http://127.0.0.1:8002/mcp
```

Discovery metadata: `curl http://127.0.0.1:8002/.well-known/oauth-authorization-server`

Full flow (register → authorize → exchange → call), condensed:

```python
import base64, hashlib, secrets
import httpx
from urllib.parse import urlparse, parse_qs

base = "http://127.0.0.1:8002"

client = httpx.post(f"{base}/register", json={
    "redirect_uris": ["http://localhost:9999/callback"],
    "client_name": "my-client",
    "grant_types": ["authorization_code", "refresh_token"],
    "response_types": ["code"],
    "scope": "tools:read",   # must match a scope requested at /authorize
}).json()

verifier = secrets.token_urlsafe(64)
challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()

authz = httpx.get(f"{base}/authorize", params={
    "client_id": client["client_id"],
    "redirect_uri": "http://localhost:9999/callback",
    "response_type": "code",
    "code_challenge": challenge,
    "code_challenge_method": "S256",
    "state": "xyz",
    "scope": "tools:read",
}, follow_redirects=False)  # InMemoryOAuthProvider auto-approves — no login page
code = parse_qs(urlparse(authz.headers["location"]).query)["code"][0]

token = httpx.post(f"{base}/token", data={
    "grant_type": "authorization_code",
    "code": code,
    "redirect_uri": "http://localhost:9999/callback",
    "client_id": client["client_id"],
    "client_secret": client.get("client_secret", ""),
    "code_verifier": verifier,
}).json()["access_token"]
```

Then use `token` the same way as the bearer example above (`BearerAuth(token)`).

A real MCP client (Claude Desktop, MCP Inspector) that supports the OAuth spec will drive this whole flow itself via a browser redirect — you won't normally do it by hand like this.

## Notes

- Both servers run on the `http` transport (`mcp.run(transport="http", ...)`) since auth requires a network-addressable server; stdio servers run locally under the same user and don't need it.
- Dynamic client registration must be explicitly enabled (`ClientRegistrationOptions(enabled=True, ...)`) — it's off by default.
- Registering a client without a `scope` field means it has no allowed scopes, and any `/authorize` request for a scope will fail with `invalid_scope`.
