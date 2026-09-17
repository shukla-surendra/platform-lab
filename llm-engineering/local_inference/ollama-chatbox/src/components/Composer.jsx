import { useEffect, useRef } from 'react'
import { ArrowUp, Square } from 'lucide-react'

export default function Composer({ value, onChange, onSend, onStop, isStreaming, disabled }) {
  const textareaRef = useRef(null)

  useEffect(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`
  }, [value])

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="composer-wrap">
      <div className="composer">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Message your local model…"
          rows={1}
          disabled={disabled}
        />
        {isStreaming ? (
          <button className="composer-btn stop" onClick={onStop} aria-label="Stop generating">
            <Square size={14} fill="currentColor" />
          </button>
        ) : (
          <button
            className="composer-btn send"
            onClick={onSend}
            disabled={!value.trim() || disabled}
            aria-label="Send message"
          >
            <ArrowUp size={18} />
          </button>
        )}
      </div>
      <div className="composer-hint">
        Runs entirely on your machine via Ollama. Models can make mistakes.
      </div>
    </div>
  )
}
