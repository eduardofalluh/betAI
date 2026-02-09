import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import MessageBubble from './MessageBubble'
import ThemeToggle from './ThemeToggle'
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
  onSportChange,
  lastSavedAt,
  theme,
  onToggleTheme,
}) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const [showSaved, setShowSaved] = useState(false)
  const savedTimeoutRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (lastSavedAt && messages.length > 0) {
      setShowSaved(true)
      if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current)
      savedTimeoutRef.current = setTimeout(() => setShowSaved(false), 2000)
    }
    return () => { if (savedTimeoutRef.current) clearTimeout(savedTimeoutRef.current) }
  }, [lastSavedAt, messages.length])

  const handleSend = async (text = input.trim()) => {
    if (!text) return
    setInput('')
    onSendMessage('user', text)
    setLoading(true)
    try {
      const { reply } = await sendMessage(text, sport, messages)
      onSendMessage('bot', reply.replace(/\\n/g, '\n'))
    } catch (e) {
      onSendMessage('bot', `Error: ${e.message || 'Could not reach the API'}. Make sure the backend is running (port 5000) and you opened the app via npm run dev (e.g. http://localhost:3000 or 3001).`)
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
          <AnimatePresence mode="wait">
            {showSaved && (
              <motion.span
                className="saved-indicator"
                aria-live="polite"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ type: 'spring', stiffness: 400, damping: 25 }}
              >
                Saved
              </motion.span>
            )}
          </AnimatePresence>
          <ThemeToggle theme={theme} onToggle={onToggleTheme} />
          <motion.button
            type="button"
            className="btn-secondary"
            onClick={onNewChat}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
          >
            New chat
          </motion.button>
        </div>
      </header>

      <div className="messages-wrap">
        <AnimatePresence initial={false}>
          {messages.length === 0 && (
            <motion.div
              className="empty-state"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
              transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
            >
              <motion.h3
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
              >
                Your betting agent
              </motion.h3>
              <motion.p
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.15 }}
              >
                Get live odds, matchups by sport, predictions, or Milano Cortina 2026.
              </motion.p>
              <div className="quick-prompts">
                {QUICK_PROMPTS.map((prompt, idx) => (
                  <motion.button
                    key={prompt}
                    type="button"
                    className="quick-prompt"
                    onClick={() => handleSend(prompt)}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.2 + idx * 0.06, type: 'spring', stiffness: 300, damping: 24 }}
                    whileHover={{ scale: 1.03, y: -2 }}
                    whileTap={{ scale: 0.98 }}
                  >
                    {prompt}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          )}
          {messages.map((msg, i) => (
            <MessageBubble key={i} sender={msg.sender} text={msg.text} index={i} />
          ))}
          {loading && (
            <motion.div
              className="message bot typing-message"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              transition={{ type: 'spring', stiffness: 400, damping: 30 }}
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
          whileHover={{ scale: 1.03 }}
          whileTap={{ scale: 0.97 }}
          transition={{ type: 'spring', stiffness: 400, damping: 20 }}
        >
          Send
        </motion.button>
      </div>
    </motion.div>
  )
}
