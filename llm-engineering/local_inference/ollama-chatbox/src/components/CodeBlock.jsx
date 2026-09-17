import { useState } from 'react'
import { Check, Copy } from 'lucide-react'

function getTextContent(node) {
  if (typeof node === 'string' || typeof node === 'number') return String(node)
  if (Array.isArray(node)) return node.map(getTextContent).join('')
  if (node?.props?.children != null) return getTextContent(node.props.children)
  return ''
}

// Overrides the <pre> tag react-markdown renders for fenced code blocks, so we can
// add a language label + copy button. `children` here is the <code> element produced
// by rehype-highlight (its children are the syntax-highlighted spans).
export default function CodeBlock({ children }) {
  const [copied, setCopied] = useState(false)
  const codeElement = Array.isArray(children) ? children[0] : children
  const className = codeElement?.props?.className || ''
  const language = /language-(\w+)/.exec(className)?.[1] || 'text'
  const codeText = getTextContent(codeElement?.props?.children)

  async function handleCopy() {
    await navigator.clipboard.writeText(codeText)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span className="code-lang">{language}</span>
        <button className="code-copy" onClick={handleCopy}>
          {copied ? <Check size={13} /> : <Copy size={13} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
      <pre>{children}</pre>
    </div>
  )
}
