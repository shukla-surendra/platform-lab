# Usage: running + testing with MCP Inspector

## 1. Setup (once)

```bash
cd genai_lab/fastmcp_auth_tools
python3 -m venv .venv          # if not already created
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Which bearer token to use

`server_bearer.py` has two demo tokens hardcoded in `TOKENS` — use either:

| Token | scopes |
|---|---|
| `demo-read-token` | `tools:read` |
| `demo-admin-token` | `tools:read`, `tools:write` |

The server requires `tools:read`, so both work identically against the current tools. Any other string (e.g. `bogus-token`) or no token at all gets rejected with `401`. These are plain-text demo tokens (`StaticTokenVerifier`) — never reuse this pattern in production.

## 3. Run the server(s)

Each auth mode is its own script, its own port, run with a plain `python` command — no special CLI needed:

```bash
# terminal 1
source .venv/bin/activate
python server_bearer.py        # http://127.0.0.1:8001/mcp

# terminal 2 (separate — see note below)
source .venv/bin/activate
python server_oauth.py         # http://127.0.0.1:8002/mcp
```

**They can run at once** — different ports (8001 vs 8002), no conflict. Run one, both, or neither depending on which auth flow you want to poke at. There's no combined "run both" command; start each with its own `python <file>.py` in its own terminal/background process.

## 4. Run MCP Inspector against them

Important: don't use `fastmcp dev inspector server_bearer.py`. That launcher spawns your script over **stdio** and expects it to behave as a stdio server — but both scripts hardcode `transport="http"`, so that mismatch breaks it. Instead, start the server yourself (step 3) as a standing HTTP process, then point the standalone Inspector at its URL.

### Bearer server

```bash
npx @modelcontextprotocol/inspector \
  --transport http \
  --server-url http://127.0.0.1:8001/mcp \
  --header "Authorization: Bearer demo-read-token"
```

This opens a browser at `http://localhost:6274` with the connection pre-filled — click **Connect** and the tools list appears. If you'd rather fill it in by hand: run `npx @modelcontextprotocol/inspector` with no flags, then in the UI set **Transport Type: Streamable HTTP**, **URL: http://127.0.0.1:8001/mcp**, and add header `Authorization: Bearer demo-read-token` (or use the UI's dedicated Bearer Token field if shown).

### OAuth server

```bash
npx @modelcontextprotocol/inspector \
  --transport http \
  --server-url http://127.0.0.1:8002/mcp
```

No `--header` needed — leave auth blank and click **Connect**. Inspector detects the server requires OAuth (via the `/.well-known/oauth-authorization-server` metadata it exposes), and walks you through the full browser-based flow itself: dynamic client registration → authorization redirect (auto-approved instantly by `InMemoryOAuthProvider`, no login page) → token exchange. You end up connected with a token Inspector obtained on its own.

### Running Inspector against both at once

Each `npx @modelcontextprotocol/inspector` invocation starts its own proxy (default ports 6274 UI / 6277 proxy) and will fail with `PORT IS IN USE` if one is already running. To inspect both servers simultaneously, give the second instance different ports:

```bash
npx @modelcontextprotocol/inspector \
  --transport http --server-url http://127.0.0.1:8002/mcp \
  # (second instance needs its own inspector ports if the first is still up)
```

In practice it's simpler to inspect one server at a time: connect, poke around, disconnect (Ctrl+C the `npx` process), then launch Inspector again against the other URL.

## 5. Quick sanity check without a browser

```bash
# should 401 — no token
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/mcp

# should succeed
python3 -c "
import asyncio
from fastmcp import Client
from fastmcp.client.auth import BearerAuth

async def main():
    async with Client('http://127.0.0.1:8001/mcp', auth=BearerAuth('demo-read-token')) as c:
        print([t.name for t in await c.list_tools()])

asyncio.run(main())
"
```
