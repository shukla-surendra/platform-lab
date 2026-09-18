// Backend switch: 'ollama' (local, NDJSON wire format) or 'vllm' (the
// deployed GPU server in cloud-practice/aws/terraform/vllm-gpu-serving/,
// OpenAI-compatible SSE wire format). Both branches export the SAME
// listModels()/streamChat() shape, so App.jsx never needs to know which
// backend is active.
const BACKEND = import.meta.env.VITE_BACKEND || 'vllm'

// ---------------------------------------------------------------------------
// Ollama backend — GET /api/tags, POST /api/chat (NDJSON streaming)
// ---------------------------------------------------------------------------
async function listModelsOllama() {
  const res = await fetch('/ollama/api/tags')
  if (!res.ok) {
    throw new Error(`Failed to list models: ${res.status} ${res.statusText}`)
  }
  const data = await res.json()
  return data.models ?? []
}

async function streamChatOllama({ model, messages, signal, onToken }) {
  const res = await fetch('/ollama/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages, stream: true }),
    signal,
  })

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    throw new Error(`Ollama request failed: ${res.status} ${res.statusText} ${text}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let newlineIndex
    while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, newlineIndex).trim()
      buffer = buffer.slice(newlineIndex + 1)
      if (!line) continue

      const chunk = JSON.parse(line)
      if (chunk.message?.content) {
        onToken(chunk.message.content)
      }
      if (chunk.done) return
    }
  }
}

// ---------------------------------------------------------------------------
// vLLM backend — GET /v1/models, POST /v1/chat/completions (OpenAI-compatible
// Server-Sent Events streaming, NOT the same wire format as Ollama's NDJSON).
// The Authorization header is injected by the Vite dev proxy (see
// vite.config.js) — this file never sees the API key.
// ---------------------------------------------------------------------------
async function listModelsVllm() {
  const res = await fetch('/vllm/v1/models')
  if (!res.ok) {
    throw new Error(`Failed to list models: ${res.status} ${res.statusText}`)
  }
  const data = await res.json()
  // OpenAI-shaped models are {id, object, ...} — map to {name} so App.jsx's
  // `models[i].name` / `m.name` usage works unchanged regardless of backend.
  return (data.data ?? []).map((m) => ({ name: m.id }))
}

async function streamChatVllm({ model, messages, signal, onToken }) {
  const res = await fetch('/vllm/v1/chat/completions', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model, messages, stream: true }),
    signal,
  })

  if (!res.ok || !res.body) {
    const text = await res.text().catch(() => '')
    throw new Error(`vLLM request failed: ${res.status} ${res.statusText} ${text}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    let newlineIndex
    while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
      const line = buffer.slice(0, newlineIndex).trim()
      buffer = buffer.slice(newlineIndex + 1)
      if (!line.startsWith('data:')) continue

      const payload = line.slice('data:'.length).trim()
      if (payload === '[DONE]') return

      const chunk = JSON.parse(payload)
      const delta = chunk.choices?.[0]?.delta?.content
      if (delta) onToken(delta)
      if (chunk.choices?.[0]?.finish_reason) return
    }
  }
}

// ---------------------------------------------------------------------------
// Public API — dispatches to whichever backend VITE_BACKEND selects.
// ---------------------------------------------------------------------------
export async function listModels() {
  return BACKEND === 'ollama' ? listModelsOllama() : listModelsVllm()
}

export async function streamChat(args) {
  return BACKEND === 'ollama' ? streamChatOllama(args) : streamChatVllm(args)
}
