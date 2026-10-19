# JSON-RPC 2.0: From Scratch vs. With a Package

A plain JSON-RPC 2.0 client/server — not MCP this time, just the underlying protocol on its own —
implemented two ways side by side:

- **`from_scratch/`** — zero dependencies, only `json`/`socket`/`socketserver` from the standard
  library.
- **`with_package/`** — the same calculator service, same wire behavior, built on
  [`jsonrpcserver`](https://pypi.org/project/jsonrpcserver/) and
  [`jsonrpcclient`](https://pypi.org/project/jsonrpcclient/), the standard minimal Python packages
  for exactly this.

Read [`../docs/Agentic_Concepts/15-jsonrpc-explained.md`](../docs/Agentic_Concepts/15-jsonrpc-explained.md)
first if you want the plain-English protocol tour before the code — this README assumes you
already know what a request/notification/response/error looks like and focuses on the
client-server mechanics and the from-scratch-vs-package comparison.

This is a sibling to [`../mcp_from_scratch`](../mcp_from_scratch), not a replacement — that project
builds MCP (JSON-RPC plus a specific set of methods) over a subprocess's stdin/stdout. This one
builds plain JSON-RPC (no MCP methods, just whatever methods you define) over a real TCP socket,
between two genuinely separate OS processes that don't share a parent-child relationship. Two
different transports for the same message format is exactly the point made in
[Chapter 15](../docs/Agentic_Concepts/15-jsonrpc-explained.md#an-envelope-not-a-truck) — "an
envelope, not a truck."

## The service

Both versions expose the same five methods, over the same wire framing (one JSON message per
line, same as `../mcp_from_scratch`'s stdio framing, just over a socket instead of a pipe):

| Method | Kind | Behavior |
|---|---|---|
| `add(x, y)` | request | returns `x + y` |
| `subtract(x, y)` | request | returns `x - y` |
| `multiply(x, y)` | request | returns `x * y` |
| `divide(x, y)` | request | returns `x / y`, or an **application-level error** (code `-32000`) on `y == 0` |
| `log(message)` | **notification only** | prints server-side, no reply — the real use case for a notification: "tell the server something, don't wait" |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt      # only needed for with_package/
```

`from_scratch/` needs nothing installed at all.

## Run

Two terminals, both from this directory:

```bash
# terminal 1
python from_scratch/server.py            # listens on 127.0.0.1:9000

# terminal 2
python from_scratch/client.py
```

Same for the package version:

```bash
python with_package/server.py
python with_package/client.py
```

Or, one command each via the bundled script (starts the server, runs the client demo, shuts the
server down afterward — see [Troubleshooting](#troubleshooting) for why this needed a real
`trap`-based script rather than a one-line `make` recipe):

```bash
./run_demo.sh from_scratch
./run_demo.sh with_package
make demo-scratch     # same, via Makefile
make demo-package
make diff             # diff the two server.py/client.py pairs directly
```

## Verified output — the two versions are wire-identical

Real output from both demos, side by side. Same five requests, same notification, same two
protocol errors, same application error, same batch — the only difference in the wire trace is
formatting whitespace from each library's `json.dumps`:

**from_scratch:**
```
add(2, 3) = 5
multiply(6, 7) = 42
caught expected RPCError: [-32000] Division by zero
caught expected RPCError: [-32601] Method not found
caught expected RPCError: [-32602] Invalid params (add() missing 1 required positional argument: 'y')
```

**with_package:**
```
add(2, 3) = 5
multiply(6, 7) = 42
caught expected error: [-32000] Division by zero
caught expected error: [-32601] Method not found (no_such_method)
caught expected error: [-32602] Invalid params (missing a required argument: 'y')
```

And the batch request — one round trip, four calls, order preserved — from both:
```
from_scratch: [{'id': 6, 'result': 2}, {'id': 7, 'result': 6}, {'id': 8, 'result': 9}, {'id': 9, 'result': 4.0}]
with_package: [Ok(result=2, id=6), Ok(result=6, id=7), Ok(result=9, id=8), Ok(result=4.0, id=9)]
```

Same values, same order, same ids — `with_package`'s client just hands them back as typed
`Ok`/`Error` objects instead of raw dicts.

## What the package buys you

| | `from_scratch/jsonrpc.py` | `jsonrpcserver` / `jsonrpcclient` |
|---|---|---|
| Message shape construction | Hand-written `make_request`/`make_notification`/... | `request()`/`notification()` |
| Method registration | A dict + `@register(name)` decorator (~10 lines) | `@method` decorator |
| Dispatch (single + batch) | `dispatch()` — a hand-rolled ~40-line function | `dispatch()` — one call |
| Missing/wrong argument → Invalid params | Manual `except TypeError` | Automatic, from introspecting the function signature |
| Unknown method → Method not found | Manual dict lookup + error | Automatic |
| Response parsing (client side) | Manual dict indexing + a custom `RPCError` | `parse()`/`parse_json()` → typed `Ok`/`Error` |
| Batch response ordering | Hand-rolled `dict` keyed by id, reordered by caller | Returned in request order automatically |
| Lines of protocol-handling code | ~120 (`jsonrpc.py`) | ~0 — both files are almost entirely the calculator methods themselves |

Notably, **neither version's transport code changes size** — `socket_transport.py` is nearly
identical in both folders, because neither `jsonrpcserver` nor `jsonrpcclient` ships a transport at
all. That's worth sitting with: a JSON-RPC package's job is entirely "parse this text as a valid
JSON-RPC message, route it, validate arguments, serialize the result" — moving the bytes is always
your problem, whether you're on stdio (`../mcp_from_scratch`), a raw socket (this project), or
HTTP (neither project builds, but the shape would be the same: swap the transport file, keep
`jsonrpc.py`/`dispatch()` unchanged).

## A real bug this project surfaced

Worth keeping, because it's a genuinely easy mistake and not obvious until it happens: the first
version of `from_scratch/server.py` used `socketserver.StreamRequestHandler`'s built-in `self.rfile`
directly for reading. That attribute is **binary** by default — `self.rfile.readline()` returns
`bytes`, not `str`. `socket_transport.py`'s EOF check (`if line == "": return None`) was written
assuming text mode (matching `../mcp_from_scratch`'s stdio version, where `sys.stdin` genuinely is
text), so it silently never matched `b""` on a clean client disconnect. The result: every clean
shutdown fell through to `json.loads(b"")`, which raises `JSONDecodeError: Expecting value: line 1
column 1 (char 0)` — a confusing error that looks like a malformed message, not what it actually
was (a normal disconnect hitting the wrong code path).

The fix (already applied, see `server.py`'s `handle()`): build a text-mode file object explicitly
with `self.request.makefile("r")` instead of relying on `self.rfile`, matching what `client.py`
already did on its side of the same socket. Lesson: **when wrapping a raw socket, always check
whether you're getting `bytes` or `str` back before writing an EOF/parsing check that assumes one
or the other** — the two look identical in code (`readline()` either way) and only diverge at
runtime, exactly the kind of bug that's invisible until you test a clean disconnect specifically.

## Extending it

- **Add a method**: in `from_scratch/`, add a function + `@jsonrpc.register("name")`; in
  `with_package/`, add a function + `@method`, returning `Success(...)` or `Error(code, message)`.
  Same shape either way.
- **Swap the transport for HTTP**: replace `socket_transport.py` with something using
  `http.server` (from-scratch) or a tiny Flask/`aiohttp` app (with-package, since `jsonrpcserver`
  already has framework-agnostic `dispatch()` ready to sit behind any HTTP handler) — `jsonrpc.py`
  and the method definitions don't need to change at all, proof of the transport/protocol split
  above.
- **Add authentication**: neither version has any — a raw socket accepts any connection. A
  realistic next step would be a shared secret sent as the first line of a connection before any
  JSON-RPC traffic, checked in `Handler.handle()` before entering the message loop.

## Troubleshooting

- **`ModuleNotFoundError: No module named 'jsonrpcserver'`** — activate the venv
  (`source .venv/bin/activate`) before running anything in `with_package/`, or the script is
  running under a different Python than the one `pip install -r requirements.txt` targeted.
- **Client hangs** — the server isn't running yet, or is on a different port; both default to
  `9000`, pass `--port` to match on both sides.
- **`Address already in use`** — a previous server run is still bound to the port (check with
  `lsof -i :9000` / `ps aux | grep server.py` and kill it), or wait a few seconds for the OS to
  release the socket.
- **Why `run_demo.sh` and not a one-line `make` recipe with `&`?** — an earlier version tried
  exactly that (`server.py & ...; kill $PID` inline in the Makefile) and it hung indefinitely: the
  backgrounded server is a job of the *same shell* Make spawns for the recipe, and that shell
  doesn't return control to Make until every background job it started has actually been reaped —
  `kill` alone sends the signal but doesn't wait for the process to actually exit. `run_demo.sh`
  uses a real `trap ... EXIT` with an explicit `wait`, which is the correct pattern for
  "start something in the background, guarantee it's stopped when I'm done" in any shell script.
