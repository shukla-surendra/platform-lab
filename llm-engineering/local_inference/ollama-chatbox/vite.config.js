import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  // Third argument '' (not the default 'VITE_') loads EVERY env var, not just
  // VITE_-prefixed ones — VLLM_API_KEY must NOT be VITE_-prefixed, or Vite
  // would inline it into the client bundle. Reading it here, in vite.config.js,
  // keeps it server-side only: it's used below to set a proxy header, never
  // shipped to the browser.
  const env = loadEnv(mode, process.cwd(), '')

  return {
    plugins: [react()],
    server: {
      proxy: {
        // Forward /ollama/* to a local Ollama server, sidestepping its CORS
        // restrictions (Ollama doesn't send Access-Control-Allow-Origin by default).
        '/ollama': {
          target: 'http://127.0.0.1:11434',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/ollama/, ''),
        },
        // Forward /vllm/* to the deployed vLLM OpenAI-compatible server (see
        // cloud-practice/aws/terraform/vllm-gpu-serving/). Same CORS-sidestep
        // reasoning as /ollama, plus: injecting Authorization here means the
        // API key lives only in .env.local (gitignored, see *.local in
        // .gitignore) and the Vite dev process — never in client JS a browser
        // devtools tab could read.
        '/vllm': {
          target: env.VLLM_BASE_URL || 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/vllm/, ''),
          headers: env.VLLM_API_KEY ? { Authorization: `Bearer ${env.VLLM_API_KEY}` } : {},
        },
      },
    },
  }
})
