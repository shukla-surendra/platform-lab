# Appendix: JSON-RPC 2.0, Plain English

`../mcp_from_scratch/jsonrpc.py` implements this in code; this page is the "why does it look like
that" companion — what JSON-RPC actually is, in plain terms, before any MCP-specific meaning gets
layered on top.

## What "RPC" even means

RPC = **Remote Procedure Call**: calling a function that doesn't live in your program, and getting
an answer back, structured to feel like calling a normal function even though the actual work
happened somewhere else — another process, another machine. The hard part of any RPC system is
agreeing, in advance, on the shape of "here's my question" and "here's your answer" so two programs
that have never met can still understand each other.

**JSON-RPC** is one specific, small answer to that problem: use JSON (because nearly every
language can read and write it) and a handful of required fields (because JSON alone doesn't say
which message is a question vs. an answer). [The spec](https://www.jsonrpc.org/specification) is
short — about a page — which is exactly why MCP picked it as a foundation instead of inventing
something new.

## The postcard analogy

Think of a JSON-RPC request like a postcard with a return-address label glued on: you write your
question, and a number so the recipient knows which reply matches which question when several
postcards are in flight at once. A **notification** is the same postcard with the return-address
label torn off — you're saying something, not asking a question, and the recipient has no way to
reply even if they wanted to.

That single detail — whether an `"id"` field is present — is the entire mechanism JSON-RPC uses to
distinguish "please answer me" from "just so you know."

## The four message shapes

| Shape | Has `id`? | Direction | Meaning |
|---|---|---|---|
| **Request** | Yes | Sender → receiver | "Do this, and tell me the result." |
| **Notification** | No | Sender → receiver | "FYI." No reply, ever. |
| **Success response** | Yes (matches the request's) | Receiver → sender | "Here's your result." |
| **Error response** | Yes (matches the request's) | Receiver → sender | "That didn't work, here's why." |

```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
{"jsonrpc": "2.0", "method": "notifications/initialized"}
{"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}
{"jsonrpc": "2.0", "id": 1, "error": {"code": -32601, "message": "Method not found"}}
```

A response is never both a success and an error — `result` and `error` are mutually exclusive, and
exactly one of them must be present. See `../mcp_from_scratch/jsonrpc.py`'s `make_*` functions for
each shape built with one function call apiece.

## Matching replies to requests: the `id`

Because a receiver might get several requests before it finishes answering the first one (this
matters a lot over a network, less so over the strictly one-at-a-time stdio transport
`../mcp_from_scratch` uses), the `id` is what lets the sender match an incoming response to the
outgoing request it goes with — `mcp_client.py`'s `_request()` checks `response.get("id") ==
expected_id` for exactly this reason. **MCP tightens the base JSON-RPC rule here**: the official
spec requires a request's `id` to never be `null` and to never repeat a previously-used value
within the same session — stricter than base JSON-RPC, which technically allows both.

## Error codes, in plain English

| Code | Name | Plain English |
|---|---|---|
| `-32700` | Parse error | "I couldn't even read that as JSON." |
| `-32600` | Invalid Request | "That was valid JSON, but not a valid JSON-RPC message." |
| `-32601` | Method not found | "I don't know what that method name means." |
| `-32602` | Invalid params | "I understood the method, but the arguments are wrong." |
| `-32603` | Internal error | "Something broke on my end while handling this." |

These five (plus an implementation-defined range for custom codes) cover *protocol*-level
problems. Whether a `tools/call` that ran but failed on its own terms (e.g. "task not found")
should use one of these codes at all is actually the most important practical question MCP answers
on top of base JSON-RPC — see [the next appendix](16-mcp-protocol-recommendations.md#tool-safety)
and `../mcp_from_scratch/README.md`'s "Error handling" section for why the answer is "no, that's a
normal successful response with `isError: true`."

## Batching (and why you won't see it here)

The base JSON-RPC 2.0 spec technically allows sending an array of request objects as one batch and
receiving an array of responses back. Neither `../mcp_from_scratch` nor MCP's stdio transport make
use of this — every message in this project's wire trace is exactly one JSON object per line,
never an array. If you're implementing JSON-RPC for something other than MCP and batching matters
to you, it's in the base spec; MCP just doesn't lean on it.

## An envelope, not a truck

JSON-RPC only defines the message *shape* — nothing about how the bytes actually travel. That's
deliberate, and it's why MCP can run the exact same message format over two very different
transports: stdio (a subprocess's stdin/stdout, what `../mcp_from_scratch` builds) and Streamable
HTTP (a network connection). The messages `dispatch()` in `../mcp_from_scratch/mcp_server.py`
handles wouldn't change at all if you swapped the transport out — see that project's Exercise 5.

JSON-RPC isn't an MCP invention, either — it's used well beyond AI tooling, most visibly as the
standard way to talk to Ethereum (and other blockchain) nodes over HTTP. MCP is a recent, prominent
adopter of an old, boring, well-understood format — which is a feature, not a limitation: boring
and well-understood is exactly what you want the foundation of a new protocol to be.

## JSON-RPC vs. REST, for anyone coming from HTTP APIs

| | REST | JSON-RPC |
|---|---|---|
| Organized around | Nouns (resources): `/tasks/7` | Verbs (methods): `"method": "tools/call"` |
| HTTP methods | Meaningful (GET reads, POST creates, DELETE removes) | Usually irrelevant — everything is POSTed to one endpoint, or in MCP's case, isn't HTTP at all |
| Where "what to do" lives | The URL + HTTP method | The `method` field inside the body |
| Natural fit for | CRUD over resources | Calling named operations — "run this tool," "list these things" |

Neither is more correct; they optimize for different mental models. MCP's operations (`tools/call`,
`resources/read`, ...) are inherently verb-shaped — "call this tool," not "PATCH this resource" —
which is a reasonable part of why MCP reached for JSON-RPC instead of REST.

## See it in code

`../mcp_from_scratch/jsonrpc.py` is under 80 lines and has nothing MCP-specific in it — run
`python jsonrpc.py` there to see the four shapes constructed with zero framework code involved.
`../mcp_from_scratch/README.md`'s Part 1 covers the same ground with a build-it-yourself framing;
this page is the "why" companion.

For the fuller picture — batching, a real client/server over a TCP socket instead of a subprocess
pipe, and a side-by-side comparison against the standard `jsonrpcserver`/`jsonrpcclient` packages
— see [`../jsonrpc_project`](../../jsonrpc_project/README.md), which implements plain JSON-RPC
(no MCP methods) two ways: from scratch and with those packages, producing wire-identical output
either way.

Next: [Appendix: MCP Protocol Recommendations, Plain English](16-mcp-protocol-recommendations.md).
