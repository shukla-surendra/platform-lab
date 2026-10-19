# official_mcp_tools

A calculator/string toy server built on the official [`mcp`](https://pypi.org/project/mcp/) Python SDK's `mcp.server.fastmcp.FastMCP` — as opposed to `../fastmcp_tools`, which uses the standalone third-party `fastmcp` package.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py       # run the server directly (stdio) — what Claude Desktop/Cursor expect
mcp dev app.py       # run with the MCP Inspector UI for interactive testing
```

The Inspector defaults to UI port 6274 and proxy port 6277. If another Inspector session (e.g. from `fastmcp_tools`) already holds those ports, stop it first or the launch will fail with `Proxy Server PORT IS IN USE`.

## Tools

- `add(a, b)` — sum of two integers
- `subtract(a, b)` — difference of two integers
- `multiply(a, b)` — product of two integers
- `divide(a, b)` — quotient of two floats; raises on division by zero
- `reverse_string(text)` — reverse a string's characters
- `word_count(text)` — count whitespace-separated words in a string
