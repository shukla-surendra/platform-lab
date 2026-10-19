# http_connection

A small lesson: a browser page (`client.html`) calls a FastAPI endpoint (`app.py`) with `fetch`,
and you learn why the browser blocks it at first (CORS) and how to allow it.

## Files

| File | What it does |
|------|--------------|
| `app.py` | FastAPI app with one route, `GET /request`, that returns `{"message": "Hello, World!"}`. Adds `CORSMiddleware` so the browser page can read the response. |
| `client.html` | Plain HTML page that calls `http://localhost:8000/request` with `fetch` and logs the JSON to the browser console. |
| `pyproject.toml` | Dependencies (`fastapi[standard]`, which includes uvicorn). A member of the repo-root uv workspace. |

## Run it

```bash
cd fastapi_practice/http_connection
uv run uvicorn app:app --reload
```

- `app:app` means "in `app.py`, use the object named `app`".
- `--reload` restarts the server when you save a file.

Check it from the terminal:

```bash
curl http://127.0.0.1:8000/request
# {"message":"Hello, World!"}
```

FastAPI also generates interactive docs at http://127.0.0.1:8000/docs.

Then open `client.html` in a browser (double-click it), open DevTools → Console, and you should see
`{message: 'Hello, World!'}`.

## What CORS is and why it showed up

The browser follows the **same-origin policy**: a script on one origin (scheme + host + port) can
send a request to another origin, but it can't **read the response** unless that server explicitly
allows it.

Here the two sides are on different origins:

- The page is opened from disk (`file://`), so the browser sends `Origin: null`.
- The API is at `http://localhost:8000`.

Without CORS, the console shows:

```
Access to fetch at 'http://localhost:8000/request' from origin 'null' has been blocked by CORS policy:
No 'Access-Control-Allow-Origin' header is present on the requested resource.
GET http://localhost:8000/request net::ERR_FAILED 200 (OK)
```

Notice the `200 (OK)`: **the server did answer.** The browser received the response and then
refused to hand it to your JavaScript. CORS is enforced by the browser, not the server. That's why
`curl` always worked.

### The fix

The server has to say which origins may read its responses. In `app.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["null", "http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

- `"null"` covers `client.html` opened straight from disk.
- `localhost:5500` covers serving the page with VS Code Live Server.
- `allow_origins=["*"]` (any origin) also works for practice, but listing the origins you actually
  use is the habit to keep for real apps.

Now the response includes the header the browser was looking for. You can see it with curl:

```bash
curl -si -H 'Origin: null' http://127.0.0.1:8000/request | grep -i access-control
# access-control-allow-origin: null
```

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `uvicorn: command not found` | Run it through uv (`uv run uvicorn ...`), or activate the repo-root `.venv`. |
| `Expected a Python module at: src/http_connection/__init__.py` | The project was set up as an installable package. It's a single script, so `pyproject.toml` uses `[tool.uv] package = false` and has no `[build-system]`. |
| uv warning: `VIRTUAL_ENV=... does not match the project environment` | Another project's venv is active. Run `deactivate`, or open a fresh terminal. |
| Still getting the CORS error after editing `app.py` | The server is running old code. Restart it, or start it with `--reload`. |
| `Address already in use` | Something is already on port 8000. Find it with `lsof -iTCP:8000 -sTCP:LISTEN` and stop it, or use `--port 8001` (and update the URL in `client.html`). |
| Pylance: `Import "fastapi..." could not be resolved` | VS Code is using the wrong interpreter. Choose "Python: Select Interpreter" and pick `platform-lab/.venv`. |
