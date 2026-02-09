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

export default function MessageBubble({ sender, text, images, index }) {
  const lines = formatText(text)
  const hasImages = Array.isArray(images) && images.length > 0

  return (
    <motion.div
      className={`message ${sender}`}
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{
        type: 'spring',
        stiffness: 400,
        damping: 30,
        delay: index * 0.03,
      }}
    >
      <div className="message-inner">
        {text && lines.map(({ key, parts }) => (
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
        {hasImages && (
          <div className="message-images">
            {images.map((src, i) => (
              <img key={i} src={src} alt="" className="message-image" />
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
