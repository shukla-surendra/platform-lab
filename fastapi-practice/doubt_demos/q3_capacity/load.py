import asyncio, sys, time, collections, httpx
URL = "http://127.0.0.1:8766"

async def burst(path, n):
    async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=n)) as c:
        t0 = time.perf_counter()
        rs = await asyncio.gather(*[c.get(URL + path) for _ in range(n)])
        dt = time.perf_counter() - t0
    pids = collections.Counter(r.json().get("pid") for r in rs)
    print(f"{n:>4} x {path:<13} -> all done in {dt:5.2f}s   pids={dict(pids)}")

async def ping_during(path, n):
    async with httpx.AsyncClient(timeout=60, limits=httpx.Limits(max_connections=n+1)) as c:
        load = asyncio.gather(*[c.get(URL + path) for _ in range(n)])
        await asyncio.sleep(0.1)
        t0 = time.perf_counter(); await c.get(URL + "/ping"); dt = time.perf_counter() - t0
        await load
    print(f"/ping while {n} x {path:<12} running -> {dt*1000:7.0f} ms")

async def main():
    for arg in sys.argv[1:]:
        kind, path, n = arg.split(":"); n = int(n)
        await (burst if kind == "burst" else ping_during)(path, n)
asyncio.run(main())
