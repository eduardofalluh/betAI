import { useState, useMemo } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const RECENT_LIMIT = 30

export default function Sidebar({
  isOpen,
  onClose,
  sports,
  chatsBySport,
  currentSport,
  currentChatId,
  loading,
  onNewChat,
  onSelectChat,
  user,
  onOpenAuth,
}) {
  const [filter, setFilter] = useState('sport') // 'sport' | 'recent'

  const sportLabel = sports.find((s) => s.key === currentSport)?.label || currentSport
  const sportIcon = sports.find((s) => s.key === currentSport)?.icon || '📋'

  const chatList = useMemo(() => {
    if (filter === 'sport') {
      const list = (chatsBySport[currentSport] || [])
        .slice()
        .sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
      return list.map((chat) => ({ ...chat, sport: currentSport, sportLabel, sportIcon }))
    }
    const flat = []
    Object.entries(chatsBySport).forEach(([sportKey, chats]) => {
      const label = sports.find((s) => s.key === sportKey)?.label || sportKey
      const icon = sports.find((s) => s.key === sportKey)?.icon || '📋'
      ;(chats || []).forEach((c) => flat.push({ ...c, sport: sportKey, sportLabel: label, sportIcon: icon }))
    })
    flat.sort((a, b) => new Date(b.createdAt || 0) - new Date(a.createdAt || 0))
    return flat.slice(0, RECENT_LIMIT)
  }, [filter, currentSport, chatsBySport, sports, sportLabel, sportIcon])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="sidebar-backdrop"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            onClick={onClose}
          />
          <motion.aside
            className="sidebar"
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            exit={{ x: '-100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 300 }}
          >
            <div className="sidebar-header">
              <h2>BetAI Advisor</h2>
              <button type="button" className="close-btn" onClick={onClose} aria-label="Close">
                ×
              </button>
            </div>
            <button type="button" className="new-chat-btn" onClick={() => onNewChat()}>
              + New chat
            </button>
            {!user && (
              <button type="button" className="sidebar-login-hint" onClick={() => { onOpenAuth?.(); onClose(); }}>
                Log in to save & load your chats
              </button>
            )}
            <div className="sidebar-filter">
              <button
                type="button"
                className={`filter-btn ${filter === 'sport' ? 'active' : ''}`}
                onClick={() => setFilter('sport')}
              >
                <span className="filter-icon">{sportIcon}</span>
                {sportLabel}
              </button>
              <button
                type="button"
                className={`filter-btn ${filter === 'recent' ? 'active' : ''}`}
                onClick={() => setFilter('recent')}
              >
                <span className="filter-icon">🕐</span>
                All recent
              </button>
            </div>
            <div className="sidebar-chat-list">
              {loading ? (
                <div className="chat-item placeholder">Loading…</div>
              ) : chatList.length === 0 ? (
                <div className="chat-item empty">
                  {filter === 'sport' ? `No ${sportLabel} chats yet` : 'No chats yet'}
                </div>
              ) : (
                <AnimatePresence initial={false}>
                  {chatList.map((chat, idx) => (
                    <motion.button
                      key={`${chat.sport}-${chat.id}`}
                      type="button"
                      className={`chat-item ${currentChatId === chat.id ? 'active' : ''}`}
                      onClick={() => onSelectChat(chat.sport, chat)}
                      layout
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -8 }}
                      transition={{ type: 'spring', stiffness: 400, damping: 30, delay: idx * 0.02 }}
                      whileTap={{ scale: 0.98 }}
                    >
                      <span className="chat-item-title" title={chat.title || 'Untitled'}>
                        {chat.title || 'Untitled'}
                      </span>
                      {filter === 'recent' && (
                        <span className="chat-item-sport" title={chat.sportLabel}>
                          {chat.sportIcon} {chat.sportLabel}
                        </span>
                      )}
                    </motion.button>
                  ))}
                </AnimatePresence>
              )}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
