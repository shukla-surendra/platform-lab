# Client disconnect lab

**Question:** if the client goes away mid-request, what happens to the work running on the backend?

## Run

```bash
uv run app.py                        # terminal 1 — server on :8000, watch its logs
curl -m 2 localhost:8000/async       # terminal 2 — client gives up after 2s
```

Try each of: `/async`, `/sync`, `/async-check`, `/stream`. Each does 6 × 1s of "work".
(Ctrl+C on a plain `curl` works too, instead of `-m 2`.) Every log line shows `pid=` and
`thread=` so you can see where the work ran.

Also in `app.py`: `/blocking` (blocking call inside `async def`) and `/ping`, used in
[docs/02-processes-threads-event-loop.md](../docs/02-processes-threads-event-loop.md), which explains processes vs threads vs event loop
and uvicorn vs gunicorn.

## What actually happens (observed: fastapi 0.141, starlette 1.6, uvicorn 0.52)

| Endpoint | Kind | Client quits at 2s → server... |
|---|---|---|
| `/async` | `async def`, never checks | **keeps running** all 6 steps, builds the response, uvicorn silently drops it. |
| `/sync` | plain `def` (threadpool) | **keeps running** all 6 steps. Threads can't be cancelled at all. |
| `/async-check` | `async def` + `await request.is_disconnected()` | **stops early** at the next check (step 3). |
| `/stream` | `StreamingResponse` | generator gets **`CancelledError`**, `finally` runs. Work stops. |

Sample log:

```
[async] step 1/6 ... step 6/6
[async] DONE - returning response (nobody may be listening)
[sync]  step 1/6 ... step 6/6
[check] step 1/6
[check] step 2/6
[check] client gone before step 3 -> stopping early
[stream] sending chunk 1/6
[stream] generator CANCELLED (client disconnected)
[stream] generator cleanup (finally)
```

Notice there's **no uvicorn access-log line** for `/async`, `/sync`, `/async-check`: the response was never sent.

## How to test the client side

The server only learns what the TCP connection tells it, so each scenario is a different way
for the client to *leave*.

### 1. Clean exit: timeout or Ctrl+C (server is told immediately)

```bash
curl -m 2 localhost:8000/async-check     # client timeout
curl localhost:8000/stream               # press Ctrl+C mid-stream
```
Or open `http://localhost:8000/stream` in a browser and close the tab.
Result: see the table above.

### 2. From Python, as a real calling service would

```python
import httpx
try:
    httpx.get("http://localhost:8000/async", timeout=2)
except httpx.TimeoutException:
    print("client gave up")   # server log keeps going: client timeouts don't cancel server work
```

### 3. Frozen client: process alive, socket still open

```bash
curl -s localhost:8000/stream > /dev/null & C=$!
sleep 1.5; kill -STOP $C      # freeze curl, don't close it
sleep 6;   kill -CONT $C      # resume
```
Observed: the server **sent all 6 chunks, logged DONE**, and curl exited 0 after resuming. The
server can't tell "slow" from "frozen". Small writes just sit in the kernel's socket buffers. Only
a full buffer (backpressure) or a closed socket changes anything.

### 4. Silent network drop: no FIN ever arrives (cable pull, dead VM, LB drops flow)

```bash
curl -s localhost:8000/async-check & C=$!
sudo iptables -I INPUT -i lo -p tcp --dport 8000 -j DROP   # blackhole the traffic
kill $C                                                    # the FIN is dropped
# watch the server log, then clean up:
sudo iptables -D INPUT -i lo -p tcp --dport 8000 -j DROP
```
Expected: `/async-check` runs **all 6 steps**, because `is_disconnected()` never hears about the
close. *Not run in this lab:* it needs sudo, and iptables may behave differently on WSL2. On a
real network, the server only finds out when a write fails or TCP keepalive times out.

### 5. Many clients give up at once (wasted capacity)

```bash
for i in $(seq 10); do curl -s -m 1 localhost:8000/sync > /dev/null & done; wait
```
Observed: all clients were gone after 1s, but the server ran **10 threadpool threads × 6s** of
work and logged 10× `DONE`. Under real load, abandoned requests compete with live ones for the
40-thread pool.

### Gotcha when scripting these

Don't stop the server with `pkill -f app.py` from a shell whose own command line contains
`app.py`, because it kills that shell too. Use `fuser -k 8000/tcp` or kill the saved `$!` PID.

## Mental model

1. **The TCP connection drops right away** — the client's OS sends a FIN/RST, and uvicorn's
   `connection_lost` fires. Uvicorn then marks the request "disconnected" and queues an
   `http.disconnect` ASGI message.
2. **Your handler is *not* killed.** For a normal request/response, nobody cancels the
   handler task: it runs to completion and the final `send()` becomes a no-op. CPU, DB
   queries, and downstream API calls all still happen (and still cost money).
3. **You only find out if you ask:**
   - `await request.is_disconnected()`: cooperative polling (do this inside long loops).
   - Streaming: Starlette watches for disconnect while streaming and cancels the generator,
     so `try/finally` in the generator is where cleanup goes.
4. **Sync (`def`) handlers can never be interrupted**: the threadpool thread keeps going. A
   long one also holds one of the threadpool slots (default 40) for its whole run.
5. **"Gone" ≠ "told us it's gone".** A clean close (Ctrl+C, timeout) sends a FIN and is
   seen right away. A pulled cable, killed VM, or NAT/LB silently dropping the flow sends
   nothing: the server only notices when a write fails or TCP keepalive times out (can be minutes).
   Proxies (nginx, ALB) sit in between: the server sees the *proxy's* connection, not the client's.

## Takeaways

- Long or expensive work → check `is_disconnected()` periodically, or move it to a job
  queue (Celery/RQ/Arq) and return a job id. Then disconnects don't matter at all.
- Make side effects idempotent: the client may retry work that actually completed.
- Put cleanup in `try/finally` (or `except CancelledError: ...; raise`), never swallow `CancelledError`.
