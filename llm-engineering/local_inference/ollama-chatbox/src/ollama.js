const BASE_URL = '/ollama'

// GET /api/tags -> list of locally pulled models
export async function listModels() {
  const res = await fetch(`${BASE_URL}/api/tags`)
  if (!res.ok) {
    throw new Error(`Failed to list models: ${res.status} ${res.statusText}`)
  }
  const data = await res.json()
  return data.models ?? []
}

// POST /api/chat with streaming NDJSON response.
// Calls onToken(text) for each chunk of assistant content as it arrives.
// Returns once the stream is done. Supports cancellation via AbortSignal.
export async function streamChat({ model, messages, signal, onToken }) {
  const res = await fetch(`${BASE_URL}/api/chat`, {
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
