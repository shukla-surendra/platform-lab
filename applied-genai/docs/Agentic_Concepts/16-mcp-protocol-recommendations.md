# Appendix: MCP Protocol Recommendations, Plain English

`../mcp_from_scratch` builds the *wire protocol* — the mechanics of getting messages between a
client and a server correctly. This page is a different layer: what the official spec
*recommends* around that protocol — mostly about trust, consent, and safety — translated out of
spec language into plain terms. Direct quotes below are from
[modelcontextprotocol.io](https://modelcontextprotocol.io)'s specification (fetched 2026-07-22);
everything under each quote is the plain-English translation, not more spec text.

The spec is upfront about why this page has to exist as *guidance* rather than something the
protocol itself enforces:

> "While MCP itself cannot enforce these security principles at the protocol level, implementors
> **SHOULD**: build robust consent and authorization flows into their applications..."

In other words: JSON-RPC and MCP's method names define *how* a message gets from A to B correctly.
They say nothing about *whether B should be allowed to do what the message asks* — that's a
decision left to whoever builds the client, and this page is the spec's guidance for making it
well.

## The four design goals

From the [architecture spec](https://modelcontextprotocol.io/specification/2025-06-18/architecture#design-principles):

> 1. **Servers should be extremely easy to build**
> 2. **Servers should be highly composable**
> 3. **Servers should not be able to read the whole conversation, nor "see into" other servers**
> 4. **Features can be added to servers and clients progressively**

Plain English, one at a time:

- **Easy to build** — a server author's job is narrow: expose a focused set of tools/resources.
  The host application (the thing orchestrating everything) carries the complexity of talking to
  multiple servers, managing the conversation, and calling the model. This repo's
  `../tasks_mcp_server.py` is 24 lines precisely because of this split.
- **Composable** — servers are meant to be mixed and matched. A host can talk to a filesystem
  server, a database server, and a task-management server (`../tasks_mcp_server.py`) at once, and
  none of them need to know the others exist.
- **Isolated** — this is the one worth sitting with: a server only ever sees what the host
  explicitly sends it (usually just the current tool call's arguments), never the full
  conversation history, and never anything about other servers connected in parallel. The host is
  the only thing with the full picture. This is a genuine privacy boundary, not an implementation
  detail — a compromised or nosy server can't scrape your entire chat history just because it's
  one of several tools in use.
- **Progressive** — a client and server only need to support the bare minimum (the handshake) to
  work together at all; anything past that (tools, resources, prompts, sampling) is negotiated as
  capabilities and can be added to either side independently without breaking existing
  integrations. `../mcp_from_scratch/mcp_server.py`'s `capabilities: {"tools": {}, "resources":
  {}}` in its `initialize` response is this in miniature — it's telling the client exactly, and
  only, what it supports.

## The four trust & safety principles

From the [specification's Security and Trust & Safety section](https://modelcontextprotocol.io/specification/2025-06-18#security-and-trust-safety):

### User Consent and Control

> "Users must explicitly consent to and understand all data access and operations. Users must
> retain control over what data is shared and what actions are taken."

Plain English: nothing happens that the user didn't knowingly agree to, and the user can always
say no. This is the principle behind every dry-run-by-default pattern in this repo —
`../devops_sre_agent` and `../databricks_autopilot_agent` both propose a mutating action and wait
for an explicit `--apply` before doing it, which is a manual, blunt-instrument version of exactly
this recommendation. [Appendix: Autonomy Levels and Approval Patterns](14-autonomy-and-approval-patterns.md)
is the deeper dive on how to implement "control over what actions are taken" well.

### Data Privacy

> "Hosts must obtain explicit user consent before exposing user data to servers. Hosts must not
> transmit resource data elsewhere without user consent."

Plain English: don't hand a server more than it needs, and don't let it forward what it does get
somewhere else without asking again. This is the same idea as the "isolated" design goal above,
pushed one step further — isolation limits what a server *can* see; this principle limits what a
host is *allowed* to do with what a server legitimately does see.

### Tool Safety

> "Tools represent arbitrary code execution and must be treated with appropriate caution. In
> particular, descriptions of tool behavior such as annotations should be considered untrusted,
> unless obtained from a trusted server. Hosts must obtain explicit user consent before invoking
> any tool."

Plain English, and arguably the single most important line on this page: **a tool call is running
someone else's code.** A tool's own name and description are not a safety guarantee — a malicious
or compromised server can describe a destructive tool as something harmless ("this just checks the
weather") and a model, reading only the description, has no way to know better. This is the same
concern [Chapter 13's guardrails section](13-trusted-tools-landscape.md#guardrails-and-safety) and
the [OWASP Top 10 for LLM Applications](13-trusted-tools-landscape.md#guardrails-and-safety) flag
as "excessive agency" — treat every tool call the way you'd treat plugging in an unlabeled USB
drive, not the way you'd treat a function you wrote yourself.

### LLM Sampling Controls

> "Users must explicitly approve any LLM sampling requests. Users should control: whether sampling
> occurs at all, the actual prompt that will be sent, what results the server can see. The protocol
> intentionally limits server visibility into prompts."

Plain English: MCP has a primitive (`sampling`, not implemented in `../mcp_from_scratch`) that lets
a *server* ask the *client's* model to generate something — the direction is inverted from the
usual "client asks server for a tool result." Without this principle, a server could quietly spend
your model budget, or use the model as a side channel to see data it otherwise couldn't. The
recommendation is that the human stays the approval gate on all three axes — whether it happens,
what's asked, and what comes back — every single time, not just once per session.

## Five implementation guidelines

The spec follows the four principles with five concrete **SHOULD**s for anyone actually building
an MCP client or host:

1. Build robust consent and authorization flows into your application.
2. Document the security implications clearly.
3. Implement appropriate access controls and data protections.
4. Follow security best practices in your integrations.
5. Consider privacy implications in your feature designs.

None of these are protocol mechanics — they're product and engineering discipline, which is
exactly why the spec frames them as recommendations rather than requirements it could check for
you at the wire level.

## Security best practices — the practical subset

The [full security best practices document](https://modelcontextprotocol.io/specification/2025-06-18/basic/security_best_practices)
is long and mostly about **remote, HTTP-based, OAuth-authenticated** MCP deployments — confused
deputy attacks in OAuth proxies, SSRF when following server-supplied metadata URLs, session-ID
hijacking, scope minimization. Genuinely important if you're deploying a networked MCP server, and
out of scope for what this repo builds (every MCP server here is local, stdio-only, no auth) — the
spec itself agrees this split matters:

> "Implementations using an HTTP-based transport **SHOULD** conform to \[the authorization]
> specification, whereas implementations using STDIO transport **SHOULD NOT** follow this
> specification, and instead retrieve credentials from the environment."

### What actually applies to a local stdio server (what this repo builds)

- **A local MCP server is a program you're about to run with your own OS permissions.** That's
  the entire risk model. The spec's concrete guidance for clients that launch local servers:
  show the user the *exact* command before running it (no truncation), flag dangerous patterns
  (`sudo`, `rm -rf`, unexpected network calls) up front, and ideally sandbox the process rather
  than trusting it by default.
- **stdio's actual security property** is narrower than it sounds: only the process that spawned
  the server (via its stdin/stdout pipes) can talk to it at all — there's no listening port for
  anything else on the machine to accidentally reach, which is a meaningfully smaller attack
  surface than an HTTP server bound to a network interface. The spec puts it plainly: use "the
  `stdio` transport to limit access to just the MCP client."
- **Credentials, if a stdio server needs any**, come from the environment (an API key in an env
  var, for instance) rather than from an MCP-level auth handshake — there isn't one on this
  transport, by design.

### What matters once you go remote/HTTP (not built in this repo, know it exists)

One line each, full detail in the official doc linked above:

- **Never accept a token that wasn't issued specifically for your server** ("token passthrough" is
  explicitly forbidden) — otherwise your server becomes an unaccountable proxy for whoever holds
  the token.
- **Never use a session ID as authentication** — session IDs must be random, non-guessable, and
  bound to a real user identity, not treated as proof of who's asking.
- **Validate every URL a server hands you before fetching it** (OAuth metadata discovery is the
  specific case) — a malicious server can point you at internal infrastructure (cloud metadata
  endpoints, localhost services) and use your client as an unwitting proxy (SSRF).
- **Never open a URL from a server via a shell, and reject non-`http(s)` schemes** — a
  `javascript:` or `file:` URL from a malicious server is a code-execution vector, not a link.
- **Ask for the least access you need, and escalate incrementally** — request narrow scopes
  up front and elevate only when a specific operation needs more, rather than requesting broad
  access "just in case."

## MCP's own tightening of JSON-RPC

One small, concrete example of MCP adding a rule JSON-RPC itself doesn't require, worth knowing
alongside [the JSON-RPC appendix](15-jsonrpc-explained.md): a request `id` **must not** be `null`
and **must not** repeat a value already used in the same session — both are technically allowed by
base JSON-RPC 2.0, and both are tightened by MCP specifically so a client can always trust that a
response's `id` uniquely identifies which request it answers.

## Translating this to what's already in this repo

| Recommendation | Where it already shows up here |
|---|---|
| User Consent and Control | `../devops_sre_agent` and `../databricks_autopilot_agent`'s `--apply` dry-run gate; [Chapter 14](14-autonomy-and-approval-patterns.md) for how to do this with more granularity than one global flag |
| Tool Safety ("descriptions are untrusted") | `../mcp_from_scratch/mcp_server.py`'s `TOOLS` list is hand-written specifically so you can see there's no verification step distinguishing "trustworthy description" from "whatever the server author wrote" — the trust has to come from somewhere else (knowing/vetting the server) |
| Isolation (servers don't see the whole conversation) | `../mcp_from_scratch/mcp_client.py`'s `call_tool()` sends only `{"name": ..., "arguments": ...}` per call — never the surrounding chat |
| stdio limits access to just the client | Literally how `../mcp_from_scratch/mcp_client.py` spawns `mcp_server.py` — no other process on the machine can address it |
| Progressive capabilities | `../mcp_from_scratch/mcp_server.py`'s `initialize` response declares exactly `{"tools": {}, "resources": {}}` and nothing more |

## A plain-English checklist

If you're building an MCP server or client for real, past this repo's teaching examples:

- [ ] Can a user see, in plain language, what a tool is about to do before it runs?
- [ ] Does anything mutate state without an explicit approval step somewhere upstream?
- [ ] Does a server ever receive more of the conversation or user data than the current call needs?
- [ ] Are you trusting a tool's own description of itself, or do you actually know/vet the server?
- [ ] If you're on HTTP: are tokens scoped narrowly, validated as issued-for-you, and never passed
      through unchecked? Are session IDs random and bound to a real identity, never used as auth?
- [ ] If a server can trigger your own model to generate something (sampling): can the user see and
      approve the prompt, not just the fact that it happened?

Every "no" is a gap between what you've built and what the spec's authors were guarding against
when they wrote these recommendations.
