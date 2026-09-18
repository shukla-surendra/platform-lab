# Ollama Chatbox

A minimal React chat UI with streaming responses and a model picker, that talks to
EITHER a local [Ollama](https://ollama.com) server OR a remote **vLLM**
OpenAI-compatible server (e.g. the GPU box from
[`cloud-practice/aws/terraform/vllm-gpu-serving/`](../../../cloud-practice/aws/terraform/vllm-gpu-serving/))
— pick via `VITE_BACKEND` in `.env.local`.

## Prerequisites

**For the `vllm` backend (default):**
- A running vLLM OpenAI-compatible server — see `cloud-practice/aws/terraform/vllm-gpu-serving/`.
- `.env.local` (gitignored — see `*.local` in `.gitignore`) with:
  ```bash
  VITE_BACKEND=vllm
  VLLM_BASE_URL=http://<instance-ip>:8000    # no VITE_ prefix — server-side only, see vite.config.js
  VLLM_API_KEY=<the vllm_api_key you set>    # omit/leave unset if the server has no --api-key
  ```

**For the `ollama` backend:**
- [Ollama](https://ollama.com) installed and running locally (`ollama serve`, or the
  desktop app running in the background), with at least one model pulled
  (e.g. `ollama pull gemma4`).
- `.env.local` with `VITE_BACKEND=ollama`.

## Running

```bash
npm install
npm run dev
```

Then open the printed URL (default `http://localhost:5173`, or the next free port).

## How it talks to each backend

Both backends have the same browser problem — no `Access-Control-Allow-Origin` header
by default — solved the same way: the Vite dev server proxies requests through to the
real server instead of the browser calling it directly (see `vite.config.js`).
`src/ollama.js` exports the same `listModels()`/`streamChat()` functions regardless of
backend, so `App.jsx` never needs to know which one is active.

**vLLM** (`VITE_BACKEND=vllm`, default): proxies `/vllm/*` to `VLLM_BASE_URL`, injecting
`Authorization: Bearer $VLLM_API_KEY` **in the proxy config itself** — the key lives in
`.env.local` and the Vite dev process only, never in client-side JS a browser's devtools
could read.
- `GET /vllm/v1/models` — OpenAI-shaped `{data: [{id, ...}]}`, mapped to `{name: id}` so
  the rest of the app doesn't care which backend it's talking to.
- `POST /vllm/v1/chat/completions` — Server-Sent Events streaming (`data: {...}` lines,
  `choices[0].delta.content` per chunk, terminated by `data: [DONE]`) — a **different
  wire format from Ollama's NDJSON**, which is why `src/ollama.js` has two separate
  parsers rather than one shared one.

**Ollama** (`VITE_BACKEND=ollama`): proxies `/ollama/*` to `http://127.0.0.1:11434`.
- `GET /ollama/api/tags` — lists locally available models.
- `POST /ollama/api/chat` — streams back the reply token-by-token as NDJSON
  (`{message: {content}, done}` per line).

If you build this app for production (`npm run build`) and serve the static files from
somewhere other than the Vite dev server, you'll need an equivalent reverse-proxy (e.g.
nginx `location /vllm/ { proxy_pass http://<instance-ip>:8000/; proxy_set_header
Authorization "Bearer <key>"; }`) — the point of proxying is the same in production:
inject the API key server-side, never ship it to the browser.
