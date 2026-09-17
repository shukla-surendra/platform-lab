import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'ollama-chatbox:conversations'
const ACTIVE_KEY = 'ollama-chatbox:active-id'

function makeId() {
  return crypto.randomUUID ? crypto.randomUUID() : `${Date.now()}-${Math.random()}`
}

function titleFromMessage(text) {
  const clean = text.trim().replace(/\s+/g, ' ')
  return clean.length > 42 ? `${clean.slice(0, 42)}…` : clean || 'New chat'
}

function loadConversations() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    const parsed = raw ? JSON.parse(raw) : []
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

export function useConversations(defaultModel) {
  const [conversations, setConversations] = useState(loadConversations)
  const [activeId, setActiveId] = useState(() => localStorage.getItem(ACTIVE_KEY) || null)

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations))
  }, [conversations])

  useEffect(() => {
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId)
  }, [activeId])

  const createConversation = useCallback(
    (model) => {
      const conversation = {
        id: makeId(),
        title: 'New chat',
        model: model || defaultModel,
        messages: [],
        createdAt: Date.now(),
      }
      setConversations((prev) => [conversation, ...prev])
      setActiveId(conversation.id)
      return conversation.id
    },
    [defaultModel],
  )

  const deleteConversation = useCallback(
    (id) => {
      setConversations((prev) => prev.filter((c) => c.id !== id))
      setActiveId((current) => (current === id ? null : current))
    },
    [],
  )

  const updateConversation = useCallback((id, updater) => {
    setConversations((prev) =>
      prev.map((c) => (c.id === id ? { ...c, ...updater(c) } : c)),
    )
  }, [])

  const setMessages = useCallback(
    (id, messages) => {
      updateConversation(id, (c) => {
        const next = { messages }
        if (c.title === 'New chat' && messages[0]?.role === 'user') {
          next.title = titleFromMessage(messages[0].content)
        }
        return next
      })
    },
    [updateConversation],
  )

  const setModel = useCallback(
    (id, model) => updateConversation(id, () => ({ model })),
    [updateConversation],
  )

  const activeConversation = conversations.find((c) => c.id === activeId) || null

  return {
    conversations,
    activeConversation,
    activeId,
    setActiveId,
    createConversation,
    deleteConversation,
    setMessages,
    setModel,
  }
}
