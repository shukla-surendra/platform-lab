# Q3 capacity demo

```bash
cd fastapi-practice/doubt_demos/q3_capacity
uv venv -q .venv && uv pip install --python .venv/bin/python 'uvicorn[standard]' fastapi httpx

# terminal 1: try --workers 1, then --workers 4
.venv/bin/uvicorn app:app --port 8766 --workers 1 --log-level warning

# terminal 2
ab -k -n 20000 -c 100 http://127.0.0.1:8766/hello            # raw throughput
ab -n 1000 -c 1000 http://127.0.0.1:8766/io                  # 1000 waiting requests at once
.venv/bin/python load.py burst:/sync-io:100 burst:/cpu:8 ping:/cpu:8 burst:/cpu-offload:8 ping:/cpu-offload:8
```

`load.py` args are `burst:<path>:<n>` (fire n at once, time them) or `ping:<path>:<n>`
(fire n, then time one `/ping` while they run).
