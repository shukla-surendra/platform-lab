# Postgres queue lab

Scripts behind section 6 of [postgres_as_a_queue.html](../postgres_as_a_queue.html):
how many pods can share one jobs table without processing a job twice.

| Script | What it shows |
|---|---|
| `race_test.py` | 50 concurrent workers ("pods") claim 5,000 jobs with four claim strategies and count how many times each job was processed |
| `lease_test.py` | A pod stalls past its lease, a second pod reclaims the job, and a fencing token rejects the first pod's late write |

```bash
docker run -d --rm --name pgq-race -e POSTGRES_PASSWORD=app -e POSTGRES_USER=app \
  -p 55433:5432 postgres:17 -c max_connections=200
sleep 5
uv run --no-project --with 'psycopg[binary]' python race_test.py      # all four strategies
uv run --no-project --with 'psycopg[binary]' python race_test.py skip_locked
uv run --no-project --with 'psycopg[binary]' python lease_test.py
docker stop pgq-race
```

Each script drops and recreates its tables, so you can rerun them as often as you like.
