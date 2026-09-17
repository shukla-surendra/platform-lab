# Ollama Chatbox

A minimal React chat UI that talks to a local [Ollama](https://ollama.com) server, with
streaming responses and a model picker populated from whatever models you have pulled
(e.g. `gemma4`, `llama3.1`, `qwen3.5`, ...).

## Prerequisites

- [Ollama](https://ollama.com) installed and running locally (`ollama serve`, or the
  desktop app running in the background).
- At least one model pulled, e.g. `ollama pull gemma4`.

## Running

```bash
npm install
npm run dev
```

Then open the printed URL (default `http://localhost:5173`).

## How it talks to Ollama

Ollama's REST API listens on `http://127.0.0.1:11434` but doesn't send CORS headers by
default, so a browser page can't `fetch()` it directly. Instead of requiring you to set
`OLLAMA_ORIGINS`, this app's Vite dev server proxies any request to `/ollama/*` through to
Ollama (see `vite.config.js`). The frontend code (`src/ollama.js`) only ever talks to
`/ollama/...`.

- `GET /ollama/api/tags` — lists locally available models (powers the model dropdown).
- `POST /ollama/api/chat` — sends the conversation and streams back the assistant's
  reply token-by-token (NDJSON streaming).

If you build this app for production (`npm run build`) and serve the static files from
somewhere other than the Vite dev server, you'll need an equivalent proxy (e.g. nginx
`location /ollama/ { proxy_pass http://127.0.0.1:11434/; }`) or set
`OLLAMA_ORIGINS=<your-origin>` before starting Ollama and point `src/ollama.js` directly
at `http://localhost:11434`.
