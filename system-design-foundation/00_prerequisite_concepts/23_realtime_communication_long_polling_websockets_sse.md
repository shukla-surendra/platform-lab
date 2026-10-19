# Prerequisite Concepts, Part 23: Long-Polling, WebSockets, and Server-Sent Events — Getting the Server to Talk First

[Part 22](22_proxies_forward_and_reverse.md) covered the boxes sitting in front of and behind
a server. This part covers a constraint those boxes all still have to live with: HTTP was
built so the client always speaks first. Everything below is a different answer to the same
question — how does the server get to say something the client didn't just ask for, or keep
saying things, without breaking the request/response model it's built on top of? It assumes
[Part 3's synchronous-vs-asynchronous and push-vs-pull
vocabulary](03_communication_and_resilience.md#push-vs-pull), and reuses [Part 18's message
queue mechanics](18_message_queues_and_event_driven_semantics.md) and [Part 19's load
balancing mechanics](19_load_balancing.md) directly rather than re-deriving either.

## In Plain English

Imagine you've ordered food for delivery and want to know the instant it's ready. You could
call the restaurant every two minutes and ask "is it ready yet?" — simple, but most calls get
"no," and you can still wait up to two minutes after it's actually done before you happen to
call again. You could call once and stay on hold, with them refusing to hang up until they
actually have an answer — you hear about it the instant it's ready, but the moment you hang
up you have to call right back and start holding again. You could give them your number and
let them text you the moment it's ready, then go about your day — they reach you instantly,
but you can't use that same text thread to ask them to add napkins; that needs a separate
call. Or you could just stay on an open phone line the whole time, where either of you can
say something the moment you think of it — full attention, both directions, at the cost of
both of you tying up a line the entire time. Four real techniques map onto exactly this
spectrum: **short polling**, **long-polling**, **Server-Sent Events**, and **WebSockets**.

## The Problem, Precisely

HTTP is a **request/response, client-initiated** protocol: a client opens a connection,
sends a request, the server sends back exactly one response, and (by default) the connection
closes. The server has no mechanism to originate a message — it can only ever reply to
something the client already asked for. That's fine for a page load, but it breaks down the
moment the *server* is the one with new information (a chat message from another user, a
price update, a completed background job) and the client needs to know about it without
having to guess when to ask. Every technique in this doc is a way of working around that one
structural fact, each at a different point on the cost/latency/complexity spectrum.

## AJAX / Short Polling: The Naive Baseline

**Mechanism**: the client sends a normal HTTP request on a fixed interval — "anything new?"
every 5 seconds, say — gets a response, closes the connection, and repeats. There's no new
protocol here at all; it's plain request/response, just automated and looped from
JavaScript in the browser (the "AJAX" in the name is just "Asynchronous JavaScript and XML,"
the browser API era this pattern is named after, even though most responses are JSON today).

**Why it's expensive**: two costs compound. First, **request overhead multiplied by poll
frequency** — every single poll pays a full HTTP request's worth of overhead (a new TCP
connection unless kept alive, TLS if applicable, HTTP headers, server-side routing and auth)
regardless of whether anything actually changed. Second, most of those responses come back
**empty** — "nothing new" — because updates are rare relative to how often you're forced to
ask in order to keep latency bounded. Poll every 5 seconds to keep worst-case staleness at
5 seconds, and a service with a million idle clients is issuing 200,000 requests a second
that almost all say "no." This is exactly [Part 3's pull-vs-push trade-off named
directly](03_communication_and_resilience.md#push-vs-pull): polling has a hard latency floor
equal to the polling interval, and tightening that floor means paying for proportionally more
wasted requests — there's no way to make short polling both low-latency and cheap at the same
time.

## HTTP Long-Polling: The Hanging GET

**Mechanism**: the client sends a request exactly like a normal poll, but the server doesn't
answer immediately — it **holds the connection open** ("hangs" the request) and only writes
a response once there's actually something to say, or a timeout is reached (typically
20-60 seconds). The instant the client receives that response, it immediately opens a new
request and starts hanging again. This is the "stay on hold until they actually have an
answer" version of the analogy above.

**Why it's still, fundamentally, request/response underneath**: nothing about the HTTP
protocol has changed — this is a plain request that the server is simply slow, on purpose, to
answer. There's no persistent bidirectional channel, no new wire format, nothing a
network intermediary needs to understand differently; a corporate proxy or an ancient load
balancer that only knows plain HTTP handles a hanging GET without any special support at
all, which is exactly why long-polling was the practical way to approximate real-time push
for years before WebSockets had universal support.

**The real production cost**: holding a request open ties up server-side resources —
historically a thread or worker process per open connection in a synchronous server model —
for the entire hold duration, not just the brief moment of actual work. A server that can
comfortably handle 10,000 quick request/response cycles a second can be brought to its knees
by 10,000 *concurrently open* long-polls, because each one is occupying a worker for tens of
seconds instead of milliseconds. This is **worker/thread exhaustion**, and it's the specific
reason long-polling at real scale requires an async, non-blocking server model (Node.js,
Netty, an event-loop-based framework) rather than a traditional thread-per-request one — the
resource being exhausted is concurrent open connections, not CPU. There's also a structural
churn cost that never goes away regardless of server model: every single delivered message
still costs a full connection teardown and a brand-new connection setup immediately after,
which is exactly the overhead the next technique eliminates by keeping one connection open
for the whole conversation.

## WebSockets: One Connection, Both Directions, No More Polling

**Mechanism, precisely**: a WebSocket connection starts life as a completely normal HTTP
request, with a few extra headers that ask the server to change what the connection *is*: an
`Upgrade: websocket` header (plus `Connection: Upgrade` and a `Sec-WebSocket-Key`). If the
server agrees, it replies with HTTP status **`101 Switching Protocols`** instead of a normal
`200` — and from that exact moment on, the underlying TCP connection stops speaking HTTP
entirely and becomes a raw, persistent, bidirectional channel with a lightweight **WebSocket
framing protocol** (RFC 6455) layered directly on top of TCP: small frames carrying an
opcode, a payload length, and the data itself, with none of HTTP's per-message header
overhead. Nothing about this is a second protocol built from scratch — it's one HTTP
handshake used purely as a socially-agreed-upon door into a different mode, which is exactly
why it reuses HTTP's existing ports (80/443) and generally survives infrastructure that
already expects to see an HTTP request on those ports.

**Full-duplex, defined precisely**: both sides can send a frame at any moment, independent of
whether the other side is currently sending — the "open phone line" from the analogy, where
either party can start talking without waiting for a turn. This is worth contrasting with
**half-duplex**, where both directions are technically possible but only one can be active
at a time (a walkie-talkie: you can't hear their reply while you're still holding the
button). Long-polling and SSE are both effectively half-duplex-or-worse in one direction —
the client asks, the server eventually answers — while a WebSocket connection genuinely has
neither side waiting on the other's turn.

**Why this matters, and its real cost**: because the connection is genuinely persistent
(often minutes to hours, not the tens-of-seconds a long-poll hangs for), messages in either
direction cost only the frame itself — no repeated handshake, no repeated headers, dramatically
lower per-message latency and overhead than either polling technique. But that same
persistence is exactly what makes WebSockets structurally different to operate: **the server
holding a connection open is now stateful**. A normal HTTP server is trivially horizontally
scalable — any request can go to any server, because no server remembers anything about the
last request from that client. A WebSocket-holding server can't be treated the same way: the
specific server instance a client's connection landed on is the *only* server that can push a
message to that client, because that's the only place the open TCP socket actually exists.
This single fact is what forces **sticky sessions** (or a connection-aware load balancer)
into the picture the moment WebSockets enter a horizontally-scaled system — covered in full
in the scaling section below.

## Server-Sent Events (SSE): Server Push, Kept Deliberately Simple

**Mechanism, precisely**: the client makes one plain HTTP `GET` request, exactly like any
other — no `Upgrade` header, no protocol switch, no `101`. The server responds with the MIME
type **`text/event-stream`** and, critically, never closes the response — it keeps writing
new lines to the same open response body indefinitely, each new update sent as a
`data: <payload>` line (or several) followed by a blank line to mark the end of that event. A
browser consuming this doesn't need custom networking code at all: the built-in
**`EventSource`** API opens the connection, parses that wire format automatically, fires a
JavaScript event per `data:` block, and — genuinely useful in production — **automatically
reconnects** if the connection drops, resuming from the last event it saw via a `Last-Event-ID`
header the browser tracks for you, no reconnect logic to hand-write.

**Why it's genuinely simpler than a WebSocket, precisely**: SSE never leaves HTTP. There's no
protocol upgrade, no new framing format for a proxy, firewall, or load balancer to understand
— to every piece of infrastructure between client and server, it still looks like an
ordinary (if unusually long-lived) HTTP response. That's exactly why it survives environments
that are hostile to the WebSocket handshake — some corporate proxies and older
network appliances only understand plain request/response HTTP and will drop or refuse an
`Upgrade: websocket` request outright, while a plain `GET` returning `text/event-stream`
sails through unmodified.

**The one thing it genuinely can't do**: SSE is one-directional by construction — server to
client only, on that channel. There's no mechanism for the client to send data back over the
same open connection at all; a client that needs to send something (a chat reply, a command)
has to issue a completely separate, ordinary HTTP request to do it. This makes SSE the wrong
choice the moment a use case needs low-latency messages in *both* directions, and the right
one whenever it genuinely doesn't — this is precisely the wire format underneath most modern
LLM API token streaming today (Anthropic's and OpenAI's own streaming completions are
delivered as `text/event-stream`, one `data:` line per token/chunk), because a model
generating a response is a textbook one-directional push: the server has an unbounded stream
of new tokens, and the client has nothing further to say until generation finishes.

**A principal-level nuance worth naming**: a held-open SSE (or long-poll) connection occupies
one of a browser's small per-origin connection budget under HTTP/1.1 (historically around six
per host) — leaving one open indefinitely quietly reduces how many *other* requests to that
origin can run in parallel, a client-side form of **head-of-line blocking** with nothing to
do with the server at all. HTTP/2's **connection multiplexing** (many logical streams over
one physical connection) removes this ceiling, one more reason HTTP/2 matters for any design
leaning on long-lived connections at scale.

## Choosing Between Them

The decision is driven by three questions: does the client ever need to send data on the
same channel, how frequent are updates, and how hostile is the network path in between.

| Requirement | Best fit | Why |
|---|---|---|
| Frequent, low-latency, genuinely bidirectional (chat, multiplayer state, collaborative editing) | WebSockets | full-duplex, one connection, no per-message handshake cost |
| Server push only, client rarely/never talks back (live scores, notifications, LLM token streaming, stock tickers) | Server-Sent Events | simpler than a WebSocket, plain HTTP, built-in auto-reconnect |
| Infrequent updates, or an environment that can't reliably sustain a persistent connection | Long-polling | still ordinary HTTP underneath, the most infrastructure-compatible fallback |
| Very infrequent updates, or simplicity matters more than freshness | Short polling | trivial to implement and debug; not appropriate for real-time |

In production, these aren't always a one-time either/or choice: **Socket.IO** (a library
layered on top of the native WebSocket API) deliberately starts a new connection as
long-polling, then transparently upgrades to a real WebSocket the moment it confirms one will
work end-to-end — treating long-polling as a *fallback*, not a competing choice, for exactly
the networks described above where the WebSocket handshake itself gets blocked. **Slack** and
**Discord** both use WebSocket-based gateways as their primary real-time transport for
message delivery and presence, precisely because their core product is bidirectional and
latency-sensitive; a notification-only feed inside either product is a better fit for a
push-style channel like SSE if it were being built standalone.

## Scaling WebSockets in Production

The stateful-connection cost named above isn't just theoretical — it's the single hardest
operational problem WebSockets introduce, and it shows up in two distinct places.

**Getting a client's connection to land on, and stay on, the right server** is the first
problem, and it's exactly [Part 19's load-balancing
mechanism](19_load_balancing.md#algorithms-how-the-routing-decision-actually-gets-made) —
**session affinity**, whether via consistent hashing or an [L7 sticky-session
cookie](19_load_balancing.md#l4-vs-l7-the-mechanism-itself) — applied to a connection that,
unlike a normal stateless HTTP request, genuinely cannot be handled by *any* server behind
the load balancer, only the one it originally connected to. Without it, a load balancer
routing a client's next request to a different backend simply has no open socket to that
client at all.

**Getting a message from the server holding User A's connection to the server holding User
B's connection** is the second, structurally different problem — this is a **fan-out**
problem, the same shape [Part 3 already named for a
celebrity post](03_communication_and_resilience.md#fan-out-push-applied-to-one-write-many-readers),
just between server processes instead of between a write and its readers. If a chat room's
ten members happen to be spread across four different WebSocket-gateway instances, one
member's message has to somehow reach the other three gateways, not just the one that
received it. The standard fix is a **publish/subscribe (pub/sub) broadcast**: every gateway
subscribes to a channel per room/topic, and when any gateway receives a message from one of
its own locally-connected clients, it *publishes* that message to the channel instead of
trying to push it to remote sockets directly — every subscribed gateway (including the
sender's own) receives the published message and forwards it only to whichever of its local
connections belong to that room. **Redis pub/sub** is the common lightweight choice for this
specifically because it's already in most stacks as a cache (see [Part
15](15_caching.md)) and its `PUBLISH`/`SUBSCRIBE` primitives require no extra
infrastructure; Socket.IO ships an official Redis adapter that implements exactly this
pattern. It's worth being precise about what Redis pub/sub does *not* give you here, by
direct contrast with [Part 18's delivery
guarantees](18_message_queues_and_event_driven_semantics.md#delivery-guarantees-what-sent-actually-promises):
a plain Redis pub/sub channel has no persistence and no replay — a gateway that's briefly
disconnected simply misses whatever was published while it was down, with nothing to catch up
on afterward. Systems needing a durable, replayable guarantee behind this fan-out reach for
[an actual broker or log instead — Kafka, RabbitMQ, or a managed
equivalent](18_message_queues_and_event_driven_semantics.md#real-tools-modern-defaults), at
the cost of more moving parts than a bare pub/sub channel.

[The chat system case
study](../../system_design_practice/03_design_chat_system/tutorial.md#deep-dive-connection-management-at-scale)
and [the collaborative document editor case
study](../../system_design_practice/14_design_collaborative_doc_editor/tutorial.md#deep-dive-two-real-approaches-to-merging-concurrent-edits)
are both exactly this mechanism applied at staff-interview depth — a presence service mapping
user to gateway in the chat case, a single-owner document server per document in the editor
case. Fully managed alternatives also exist — **AWS API Gateway WebSocket APIs**, **Pusher**,
**Ably** — handling both connection-affinity and fan-out as a managed service, trading
operational control for not having to build either piece yourself.

## Designing and Operating From First Principles

1. Does this feature genuinely need the client to send data on the same channel as server
   push, or am I reaching for a WebSocket when SSE (or even long-polling) would cover the
   actual requirement at lower operational cost?
2. If I've chosen WebSockets, have I actually planned for the stateful-connection problem —
   sticky sessions or a connection-aware load balancer — or am I assuming any server in the
   fleet can serve any client's next message?
3. If connections are spread across multiple server instances, how does a message from a
   client on server A reach a client on server B — is there an actual pub/sub or broker layer
   doing that fan-out, or does this only work in my local testing with one server instance?
4. Have I named what happens to an in-flight message if the pub/sub layer itself briefly
   drops a subscriber — is silent loss acceptable here, or does this specific feature need a
   durable, replayable guarantee instead of bare pub/sub?
5. Have I checked whether the network this client sits behind can even complete a WebSocket
   `Upgrade` handshake — or should the design fall back to long-polling/SSE for exactly the
   restrictive-proxy case that breaks it?

## Key Takeaways

- **Every technique in this doc is a workaround for the same fact**: HTTP is
  request/response and client-initiated, and none of these techniques change that at the
  protocol-origin level — they each just decide differently how to make the server *look*
  like it can speak first.
- **Short polling trades latency for wasted requests; long-polling trades connection churn
  and worker exhaustion for lower latency** — both are still, underneath, plain HTTP
  request/response, just tuned differently.
- **A WebSocket is one HTTP-initiated handshake (`Upgrade` → `101 Switching Protocols`) into
  a genuinely different, full-duplex, persistent connection** — and that persistence is
  exactly what makes the server holding it stateful, unlike a normal HTTP server.
- **SSE is deliberately simpler than a WebSocket because it never leaves HTTP** — no upgrade,
  no new framing, built-in reconnect via `EventSource` — at the fixed cost of being
  one-directional by construction.
- **Scaling WebSockets is two separate problems, not one**: getting a client's traffic to
  stick to the server holding its connection (session affinity), and getting a message from
  one server's connections to another's (fan-out via pub/sub) — solving one without the other
  still breaks the system.

## Quick Self-Check

- Explain precisely why long-polling is still "just HTTP" even though it feels real-time from
  the client's perspective — what hasn't actually changed about the protocol?
- Walk through the WebSocket handshake step by step: what does the client send, what status
  code does the server reply with, and what happens to the underlying TCP connection
  immediately afterward?
- Why can't a load balancer route a WebSocket client's next message to a different backend
  server the way it freely could for a normal stateless HTTP request?
- Given a chat room whose ten members are connected to four different WebSocket-gateway
  instances, explain exactly how a message from one member reaches the other nine.
- Why is Server-Sent Events, not WebSockets, the better fit for streaming an LLM's response
  token by token — name the specific property of that use case that makes it one-directional
  by nature, not just by convenient choice?

## Articulate It: Interview Framing & Vocabulary

### Three Ways to Explain This

- **Constraint-first framing (the default for 'how would you push data to a client'
  questions):** "I'd start from the fact that HTTP is client-initiated request/response —
  every real-time technique is a different way of working around that, and I'd pick between
  them based on whether the client genuinely needs to talk back on the same channel, not by
  reaching for whichever sounds most modern."
- **Stateful-cost framing (good for a 'how does this scale' follow-up on WebSockets):** "I'd
  name the stateful-connection cost explicitly before drawing anything else — a WebSocket
  server can't be load-balanced like a normal stateless one, so I need session affinity to
  get traffic to the right server and a pub/sub fan-out layer to get messages between
  servers, and those are two separate problems, not one."
- **Simplicity-as-a-feature framing (good for justifying SSE over WebSockets when asked 'why
  not just use WebSockets everywhere'):** "I'd push back gently — SSE staying inside plain
  HTTP isn't a limitation, it's the reason it survives infrastructure that would otherwise
  block a WebSocket's upgrade handshake, and I wouldn't pay for bidirectional complexity a
  one-directional feed never needed."

### Vocabulary Builder

**Technical shorthand — use these instead of over-explaining the concept every time:**

- **hanging GET** (n. phrase) — the long-polling mechanism: a request the server deliberately
  delays answering until it has something to say, or a timeout is reached.
- **`101 Switching Protocols`** (HTTP status code) — the server's reply that turns an HTTP
  connection into a raw WebSocket connection, in response to an `Upgrade: websocket` request.
- **full-duplex / half-duplex** (adj. phrases) — both sides can send at any moment
  independent of the other (a WebSocket) versus only one direction being active at a time
  (long-polling and SSE, each in their own way).
- **`text/event-stream`** (MIME type) — SSE's wire format: an HTTP response that never
  closes, sending `data:` lines the browser's `EventSource` API parses automatically.
- **connection multiplexing** (n. phrase) — HTTP/2's ability to run many logical streams over
  one physical connection, removing the per-origin connection-count ceiling that makes a
  long-lived HTTP/1.1 connection quietly block other requests.
- **session affinity / sticky sessions** (n. phrases) — routing a client's traffic to the
  same backend server every time, required for WebSockets because only that one server holds
  the open socket.
- **fan-out via pub/sub** (n. phrase) — broadcasting one server's incoming message to every
  other server holding connections for the same logical room/channel, typically via Redis
  pub/sub or a message broker.

**Expressive phrases — for stating a trade-off fluently instead of listing pros/cons:**

- **"…the server is just slow to answer, on purpose"** — a precise, plain-language way to
  describe why long-polling is still fundamentally request/response underneath.
- **"…one handshake into a different mode, not a second protocol from scratch"** — a fluent
  way to correct the common misconception that WebSockets are unrelated to HTTP.
- **"…simple because it never left HTTP"** — a compact way to justify choosing SSE over
  WebSockets when bidirectional capability was never actually needed.

---

**Previous:** [Part 22: Proxies — Forward, Reverse, and Why "Reverse Proxy vs. Load Balancer" Is a Trick Question](22_proxies_forward_and_reverse.md)  |  **Next:** [Part 24: Cardinality — One Word, Five Meanings, One Underlying Idea](24_cardinality.md)
