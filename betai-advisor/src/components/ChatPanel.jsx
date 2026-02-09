import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import MessageBubble from './MessageBubble'
import ThemeToggle from './ThemeToggle'
import { sendMessage } from '../lib/api'

const MAX_IMAGES = 5
const MAX_FILE_SIZE_MB = 8
const ACCEPT_IMAGES = 'image/jpeg,image/png,image/webp,image/gif'

const QUICK_PROMPTS = [
  'Show live odds',
  'What\'s on now?',
  'Show current matchups',
  'Analyze matchups — value & best bets',
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
  user,
  onOpenAuth,
  onLogout,
}) {
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [attachedImages, setAttachedImages] = useState([]) // data URLs
  const fileInputRef = useRef(null)
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

  const addImages = (files) => {
    if (!files?.length) return
    const remaining = MAX_IMAGES - attachedImages.length
    if (remaining <= 0) return
    const list = Array.from(files).slice(0, remaining)
    const maxBytes = MAX_FILE_SIZE_MB * 1024 * 1024
    list.forEach((file) => {
      if (file.size > maxBytes) return
      const reader = new FileReader()
      reader.onload = () => {
        setAttachedImages((prev) => {
          if (prev.length >= MAX_IMAGES) return prev
          return [...prev, reader.result]
        })
      }
      reader.readAsDataURL(file)
    })
  }

  const removeImage = (index) => {
    setAttachedImages((prev) => prev.filter((_, i) => i !== index))
  }

  const handlePaste = (e) => {
    const items = e.clipboardData?.items
    if (!items) return
    const files = []
    for (const item of items) {
      if (item.type.startsWith('image/')) files.push(item.getAsFile())
    }
    if (files.length) {
      e.preventDefault()
      addImages(files)
    }
  }

  const handleSend = async (text = input.trim()) => {
    const hasImages = attachedImages.length > 0
    if (!text && !hasImages) return
    const messageText = text.trim()
    setInput('')
    const imagesToSend = [...attachedImages]
    setAttachedImages([])
    onSendMessage('user', messageText, imagesToSend.length ? imagesToSend : null)
    setLoading(true)
    try {
      const { reply } = await sendMessage(messageText, sport, messages, imagesToSend)
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
          {user ? (
            <>
              <span className="auth-user-email" title={user.email}>{user.email}</span>
              <button type="button" className="btn-secondary" onClick={onLogout}>
                Log out
              </button>
            </>
          ) : (
            <button type="button" className="btn-auth" onClick={onOpenAuth}>
              Log in
            </button>
          )}
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
                Get live odds, matchups, in-depth analysis (value & possible bets), or Milano Cortina 2026.
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
            <MessageBubble key={i} sender={msg.sender} text={msg.text} images={msg.images} index={i} />
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
          ref={fileInputRef}
          type="file"
          accept={ACCEPT_IMAGES}
          multiple
          className="input-file-hidden"
          aria-hidden
          onChange={(e) => {
            addImages(e.target.files)
            e.target.value = ''
          }}
        />
        {attachedImages.length > 0 && (
          <div className="image-previews">
            {attachedImages.map((dataUrl, i) => (
              <motion.div
                key={i}
                className="image-preview-wrap"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.9 }}
              >
                <img src={dataUrl} alt="" className="image-preview" />
                <button
                  type="button"
                  className="image-preview-remove"
                  onClick={() => removeImage(i)}
                  aria-label="Remove image"
                >
                  ×
                </button>
              </motion.div>
            ))}
          </div>
        )}
        <div className="input-row">
          <button
            type="button"
            className="attach-image-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={loading || attachedImages.length >= MAX_IMAGES}
            title={attachedImages.length >= MAX_IMAGES ? 'Max 5 images' : 'Add image'}
            aria-label="Add image"
          >
            📷
          </button>
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            onPaste={handlePaste}
            placeholder={attachedImages.length ? 'Ask about this image…' : `Ask about ${sportLabel} odds or matchups…`}
            disabled={loading}
            aria-label="Message"
          />
          <motion.button
            type="button"
            className="send-btn"
            onClick={() => handleSend()}
            disabled={(!input.trim() && !attachedImages.length) || loading}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            transition={{ type: 'spring', stiffness: 400, damping: 20 }}
          >
            Send
          </motion.button>
        </div>
      </div>
    </motion.div>
  )
}
