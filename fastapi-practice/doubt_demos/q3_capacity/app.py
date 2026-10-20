import asyncio, os, time
from concurrent.futures import ProcessPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI

def burn(seconds: float) -> int:
    """Pure CPU work: spin for `seconds`."""
    end, n = time.perf_counter() + seconds, 0
    while time.perf_counter() < end:
        n += 1
    return n

pool: ProcessPoolExecutor | None = None

@asynccontextmanager
async def lifespan(app):
    global pool
    pool = ProcessPoolExecutor(max_workers=4)
    yield
    pool.shutdown()

app = FastAPI(lifespan=lifespan)

@app.get("/hello")
async def hello():
    return {"ok": True}

@app.get("/io")            # waits 0.5s, but awaits -> loop is free
async def io():
    await asyncio.sleep(0.5); return {"pid": os.getpid()}

@app.get("/sync-io")       # waits 0.5s in a threadpool thread (40 max)
def sync_io():
    time.sleep(0.5); return {"pid": os.getpid()}

@app.get("/cpu")           # 0.3s of CPU on the event loop -> blocks the worker
async def cpu():
    burn(0.3); return {"pid": os.getpid()}

@app.get("/cpu-offload")   # same CPU work, sent to a separate process
async def cpu_offload():
    await asyncio.get_running_loop().run_in_executor(pool, burn, 0.3)
    return {"pid": os.getpid()}

@app.get("/ping")
async def ping():
    return {"pid": os.getpid()}
