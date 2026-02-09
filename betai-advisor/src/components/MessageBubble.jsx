import { motion } from 'framer-motion'

function formatText(text) {
  if (!text || typeof text !== 'string') return []
  return text.split('\n').map((line, i) => {
    const parts = []
    let rest = line
    while (rest.includes('**')) {
      const i1 = rest.indexOf('**')
      const i2 = rest.indexOf('**', i1 + 2)
      if (i2 === -1) break
      parts.push({ type: 'text', value: rest.slice(0, i1) })
      parts.push({ type: 'bold', value: rest.slice(i1 + 2, i2) })
      rest = rest.slice(i2 + 2)
    }
    if (rest) parts.push({ type: 'text', value: rest })
    return { key: i, parts: parts.length ? parts : [{ type: 'text', value: line }] }
  })
}

export default function MessageBubble({ sender, text, index }) {
  const lines = formatText(text)
  const isUser = sender === 'user'

  return (
    <motion.div
      className={`message ${sender}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, delay: index * 0.04 }}
    >
      <div className="message-inner">
        {lines.map(({ key, parts }) => (
          <div key={key} className="message-line">
            {parts.map((p, i) =>
              p.type === 'bold' ? (
                <strong key={i}>{p.value}</strong>
              ) : (
                <span key={i}>{p.value}</span>
              )
            )}
          </div>
        ))}
      </div>
    </motion.div>
  )
}
