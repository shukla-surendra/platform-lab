# /// script
# requires-python = ">=3.11"
# dependencies = ["fastapi", "uvicorn"]
# ///
"""What happens to server-side work when the client goes away?

Run:   uv run app.py
Then hit an endpoint and kill the client after ~2s, e.g.:
       curl -m 2 localhost:8000/async      (-m 2 = give up after 2 seconds)
and watch this terminal.
"""
import asyncio
import os
import threading
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()
STEPS = 6  # each step = 1 second of "work"


def log(tag: str, msg: str) -> None:
    where = f"pid={os.getpid()} thread={threading.current_thread().name}"
    print(f"{time.strftime('%H:%M:%S')} [{tag}] {where} {msg}", flush=True)


# 1) async def, never checks the client -> does the work stop on disconnect?
@app.get("/async")
async def async_work():
    try:
        for i in range(1, STEPS + 1):
            await asyncio.sleep(1)
            log("async", f"step {i}/{STEPS}")
        log("async", "DONE - returning response (nobody may be listening)")
        return {"ok": True}
    except asyncio.CancelledError:
        log("async", "CANCELLED by server")
        raise


# 2) plain def -> runs in a threadpool thread. Threads can't be cancelled at all.
@app.get("/sync")
def sync_work():
    for i in range(1, STEPS + 1):
        time.sleep(1)
        log("sync", f"step {i}/{STEPS}")
    log("sync", "DONE - returning response (nobody may be listening)")
    return {"ok": True}


# 2b) the classic mistake: blocking call inside async def -> freezes the event loop,
#     so every other request on this worker stalls too.
@app.get("/blocking")
async def blocking_in_async():
    for i in range(1, STEPS + 1):
        time.sleep(1)  # NOT await asyncio.sleep -> blocks the only event-loop thread
        log("blocking", f"step {i}/{STEPS}")
    return {"ok": True}


@app.get("/ping")
async def ping():
    log("ping", "pong")
    return {"pong": True}


# 3) async def that cooperatively checks whether the client is still there.
@app.get("/async-check")
async def async_check(request: Request):
    for i in range(1, STEPS + 1):
        if await request.is_disconnected():
            log("check", f"client gone before step {i} -> stopping early")
            return {"ok": False}
        await asyncio.sleep(1)
        log("check", f"step {i}/{STEPS}")
    log("check", "DONE")
    return {"ok": True}


# 4) streaming response -> the server notices when it tries to write / listens for disconnect.
@app.get("/stream")
async def stream():
    async def gen():
        try:
            for i in range(1, STEPS + 1):
                await asyncio.sleep(1)
                log("stream", f"sending chunk {i}/{STEPS}")
                yield f"chunk {i}\n"
            log("stream", "DONE")
        except asyncio.CancelledError:
            log("stream", "generator CANCELLED (client disconnected)")
            raise
        finally:
            log("stream", "generator cleanup (finally)")

    return StreamingResponse(gen(), media_type="text/plain")


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
