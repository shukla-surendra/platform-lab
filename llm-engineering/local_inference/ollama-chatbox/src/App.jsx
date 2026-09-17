import { useEffect, useRef, useState } from 'react'
import { ChevronDown } from 'lucide-react'
import { listModels, streamChat } from './ollama'
import { useConversations } from './useConversations'
import { useTheme } from './useTheme'
import Sidebar from './components/Sidebar'
import ChatMessage from './components/ChatMessage'
import Composer from './components/Composer'
import './App.css'

const SUGGESTIONS = [
  'Explain how transformers work, simply',
  'Write a Python function to reverse a linked list',
  'Give me 5 ideas for a weekend side project',
  'Summarize the plot of Dune in 3 sentences',
]

export default function App() {
  const { theme, toggle: toggleTheme } = useTheme()
  const [models, setModels] = useState([])
  const [modelsError, setModelsError] = useState('')
  const [collapsed, setCollapsed] = useState(false)
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [chatError, setChatError] = useState('')
  const [modelMenuOpen, setModelMenuOpen] = useState(false)

  const {
    conversations,
    activeConversation,
    activeId,
    setActiveId,
    createConversation,
    deleteConversation,
    setMessages,
    setModel,
  } = useConversations('')

  const abortRef = useRef(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    listModels()
      .then((list) => setModels(list))
      .catch((err) => setModelsError(err.message))
  }, [])

  useEffect(() => {
    if (!activeId && conversations.length === 0 && models.length > 0) {
      createConversation(models[0].name)
    }
  }, [activeId, conversations.length, models, createConversation])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [activeConversation?.messages])

  const currentModel = activeConversation?.model || models[0]?.name || ''
  const messages = activeConversation?.messages || []

  function handleNewChat() {
    createConversation(currentModel)
    setInput('')
    setChatError('')
  }

  function handleSelect(id) {
    setActiveId(id)
    setChatError('')
  }

  async function sendMessage() {
    const text = input.trim()
    if (!text || isStreaming || !currentModel) return

    let convoId = activeId
    if (!convoId) convoId = createConversation(currentModel)

    const priorMessages = activeConversation?.messages || []
    const nextMessages = [...priorMessages, { role: 'user', content: text }]
    setMessages(convoId, [...nextMessages, { role: 'assistant', content: '' }])
    setInput('')
    setIsStreaming(true)
    setChatError('')

    const controller = new AbortController()
    abortRef.current = controller

    let assistantText = ''
    try {
      await streamChat({
        model: currentModel,
        messages: nextMessages,
        signal: controller.signal,
        onToken: (token) => {
          assistantText += token
          setMessages(convoId, [...nextMessages, { role: 'assistant', content: assistantText }])
        },
      })
    } catch (err) {
      if (err.name !== 'AbortError') setChatError(err.message)
    } finally {
      setIsStreaming(false)
      abortRef.current = null
    }
  }

  function stopStreaming() {
    abortRef.current?.abort()
  }

  function handleModelChange(name) {
    if (activeId) setModel(activeId, name)
    setModelMenuOpen(false)
  }

  return (
    <div className="shell">
      <Sidebar
        collapsed={collapsed}
        onToggleCollapse={() => setCollapsed((v) => !v)}
        conversations={conversations}
        activeId={activeId}
        onSelect={handleSelect}
        onNew={handleNewChat}
        onDelete={deleteConversation}
        theme={theme}
        onToggleTheme={toggleTheme}
      />

      <div className="main">
        <header className="topbar">
          <div className="model-picker">
            <button className="model-picker-btn" onClick={() => setModelMenuOpen((v) => !v)}>
              {currentModel || 'No models found'}
              <ChevronDown size={14} />
            </button>
            {modelMenuOpen && (
              <div className="model-menu">
                {models.map((m) => (
                  <div
                    key={m.name}
                    className={`model-menu-item ${m.name === currentModel ? 'active' : ''}`}
                    onClick={() => handleModelChange(m.name)}
                  >
                    {m.name}
                  </div>
                ))}
              </div>
            )}
          </div>
        </header>

        {(modelsError || chatError) && (
          <div className="error-banner">{modelsError || chatError}</div>
        )}

        <main className="messages">
          {messages.length === 0 ? (
            <div className="empty-state">
              <h2>What can I help with?</h2>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} className="suggestion-chip" onClick={() => setInput(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="messages-inner">
              {messages.map((m, i) => (
                <ChatMessage
                  key={i}
                  role={m.role}
                  content={m.content}
                  modelName={currentModel}
                  pending={isStreaming && i === messages.length - 1 && !m.content}
                />
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </main>

        <Composer
          value={input}
          onChange={setInput}
          onSend={sendMessage}
          onStop={stopStreaming}
          isStreaming={isStreaming}
          disabled={!currentModel}
        />
      </div>
    </div>
  )
}
