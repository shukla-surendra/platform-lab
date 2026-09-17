import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import rehypeHighlight from 'rehype-highlight'
import { Bot, User } from 'lucide-react'
import CodeBlock from './CodeBlock'

const markdownComponents = {
  pre: CodeBlock,
}

export default function ChatMessage({ role, content, modelName, pending }) {
  const isUser = role === 'user'

  return (
    <div className={`chat-message ${role}`}>
      <div className="avatar">{isUser ? <User size={16} /> : <Bot size={16} />}</div>
      <div className="message-body">
        <div className="message-author">{isUser ? 'You' : modelName}</div>
        {pending ? (
          <div className="typing-dots">
            <span />
            <span />
            <span />
          </div>
        ) : isUser ? (
          <div className="message-text plain">{content}</div>
        ) : (
          <div className="message-text markdown">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              rehypePlugins={[rehypeHighlight]}
              components={markdownComponents}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}
      </div>
    </div>
  )
}
