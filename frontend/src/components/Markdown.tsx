// Minimal, safe Markdown renderer: produces React text nodes only (no innerHTML),
// because reports quote untrusted document content.
import type { ReactNode } from 'react'

function inline(text: string, key: string): ReactNode[] {
  const out: ReactNode[] = []
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g
  let last = 0
  let m: RegExpExecArray | null
  let i = 0
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(text.slice(last, m.index))
    const tok = m[0]
    out.push(tok.startsWith('**') ? <b key={`${key}-${i++}`}>{tok.slice(2, -2)}</b> : <code key={`${key}-${i++}`} className="mono">{tok.slice(1, -1)}</code>)
    last = m.index + tok.length
  }
  if (last < text.length) out.push(text.slice(last))
  return out
}

export function Markdown({ source }: { source: string }) {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: ReactNode[] = []
  let list: string[] = []
  let code: string[] | null = null
  const flushList = () => {
    if (list.length) {
      const items = list
      blocks.push(<ul key={`ul-${blocks.length}`}>{items.map((t, i) => <li key={i}>{inline(t, `li${blocks.length}-${i}`)}</li>)}</ul>)
      list = []
    }
  }
  lines.forEach((line, n) => {
    if (code) {
      if (line.startsWith('```')) {
        blocks.push(<pre key={`pre-${n}`}>{code.join('\n')}</pre>)
        code = null
      } else code.push(line)
      return
    }
    if (line.startsWith('```')) {
      flushList()
      code = []
      return
    }
    const h = /^(#{1,4})\s+(.*)$/.exec(line)
    if (h) {
      flushList()
      const level = Math.min(h[1].length, 3)
      const content = inline(h[2], `h${n}`)
      blocks.push(level === 1 ? <h1 key={n}>{content}</h1> : level === 2 ? <h2 key={n}>{content}</h2> : <h3 key={n}>{content}</h3>)
      return
    }
    const li = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line)
    if (li) {
      list.push(li[1])
      return
    }
    flushList()
    if (line.startsWith('>')) blocks.push(<blockquote key={n}>{inline(line.replace(/^>\s?/, ''), `q${n}`)}</blockquote>)
    else if (line.trim()) blocks.push(<p key={n}>{inline(line, `p${n}`)}</p>)
  })
  flushList()
  if (code) blocks.push(<pre key="pre-end">{(code as string[]).join('\n')}</pre>)
  return <div className="report-md">{blocks}</div>
}
