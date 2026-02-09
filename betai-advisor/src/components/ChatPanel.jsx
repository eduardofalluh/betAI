import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import MessageBubble from './MessageBubble'
import { sendMessage } from '../lib/api'

const QUICK_PROMPTS = [
  'Show live odds',
  'What\'s on now?',
  'Show current matchups',
  'Milano Cortina 2026 odds',
]

export default function ChatPanel({
  sport,
  sportLabel,
  sports,
  messages,
  onSendMessage,
  onNewChat,
  onSaveChat,
  onSportChange,
  hasUnsavedMessages,
}) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (text = input.trim()) => {
    if (!text) return
    setInput('')
    onSendMessage('user', text)
    setLoading(true)
    try {
      const { reply } = await sendMessage(text, sport, messages)
      onSendMessage('bot', reply.replace(/\\n/g, '\n'))
    } catch (e) {
      onSendMessage('bot', `Error: ${e.message}. Is the backend running on port 5000?`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      className="chat-panel"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.25 }}
    >
      <header className="chat-header">
        <div className="chat-header-left">
          <span className="sport-badge">{sportLabel}</span>
          <select
            className="sport-select"
            value={sport}
            onChange={(e) => onSportChange(e.target.value)}
            aria-label="Change sport"
          >
            {sports.map((s) => (
              <option key={s.key} value={s.key}>
                {s.icon} {s.label}
              </option>
            ))}
          </select>
          <button
            type="button"
            className="live-odds-chip"
            onClick={() => handleSend('Show live odds')}
            disabled={loading}
            title="Get live and upcoming odds across all sports"
          >
            🔴 Live odds
          </button>
        </div>
        <div className="chat-header-actions">
          {hasUnsavedMessages && (
            <button type="button" className="btn-secondary" onClick={onSaveChat}>
              Save chat
            </button>
          )}
          <button type="button" className="btn-secondary" onClick={onNewChat}>
            New chat
          </button>
        </div>
      </header>

      <div className="messages-wrap">
        <AnimatePresence initial={false}>
          {messages.length === 0 && (
            <motion.div
              className="empty-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <h3>Your betting agent</h3>
              <p>Get live odds, matchups by sport, predictions, or Milano Cortina 2026.</p>
              <div className="quick-prompts">
                {QUICK_PROMPTS.map((prompt) => (
                  <button
                    key={prompt}
                    type="button"
                    className="quick-prompt"
                    onClick={() => handleSend(prompt)}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </motion.div>
          )}
          {messages.map((msg, i) => (
            <MessageBubble key={i} sender={msg.sender} text={msg.text} index={i} />
          ))}
          {loading && (
            <motion.div
              className="message bot"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
            >
              <span className="typing-dots">
                <span>.</span><span>.</span><span>.</span>
              </span>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      <div className="input-wrap">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
          placeholder={`Ask about ${sportLabel} odds or matchups…`}
          disabled={loading}
          aria-label="Message"
        />
        <motion.button
          type="button"
          className="send-btn"
          onClick={() => handleSend()}
          disabled={!input.trim() || loading}
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
        >
          Send
        </motion.button>
      </div>
    </motion.div>
  )
}
