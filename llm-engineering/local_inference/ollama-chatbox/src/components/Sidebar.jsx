import { MessageSquare, Moon, PanelLeftClose, PanelLeftOpen, Plus, Sun, Trash2 } from 'lucide-react'

export default function Sidebar({
  collapsed,
  onToggleCollapse,
  conversations,
  activeId,
  onSelect,
  onNew,
  onDelete,
  theme,
  onToggleTheme,
}) {
  if (collapsed) {
    return (
      <div className="sidebar collapsed">
        <button className="icon-btn" onClick={onToggleCollapse} aria-label="Open sidebar">
          <PanelLeftOpen size={18} />
        </button>
        <button className="icon-btn" onClick={onNew} aria-label="New chat">
          <Plus size={18} />
        </button>
      </div>
    )
  }

  return (
    <div className="sidebar">
      <div className="sidebar-top">
        <span className="brand">Ollama Chatbox</span>
        <button className="icon-btn" onClick={onToggleCollapse} aria-label="Collapse sidebar">
          <PanelLeftClose size={18} />
        </button>
      </div>

      <button className="new-chat-btn" onClick={onNew}>
        <Plus size={16} />
        New chat
      </button>

      <div className="conversation-list">
        {conversations.length === 0 && <div className="conversation-empty">No conversations yet</div>}
        {conversations.map((c) => (
          <div
            key={c.id}
            className={`conversation-item ${c.id === activeId ? 'active' : ''}`}
            onClick={() => onSelect(c.id)}
          >
            <MessageSquare size={15} className="conversation-icon" />
            <span className="conversation-title">{c.title}</span>
            <button
              className="conversation-delete"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(c.id)
              }}
              aria-label="Delete conversation"
            >
              <Trash2 size={14} />
            </button>
          </div>
        ))}
      </div>

      <button className="theme-toggle" onClick={onToggleTheme}>
        {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
        {theme === 'dark' ? 'Light mode' : 'Dark mode'}
      </button>
    </div>
  )
}
