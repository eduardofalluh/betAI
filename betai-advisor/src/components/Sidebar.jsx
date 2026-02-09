import { motion, AnimatePresence } from 'framer-motion'

export default function Sidebar({
  isOpen,
  onClose,
  sports,
  chatsBySport,
  currentSport,
  loading,
  onNewChat,
  onSelectChat,
}) {
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
            <div className="sidebar-sports">
              {sports.map((sport) => {
                const chats = chatsBySport[sport.key] || []
                const isActive = currentSport === sport.key
                return (
                  <div key={sport.key} className="sport-section">
                    <div className={`sport-heading ${isActive ? 'active' : ''}`}>
                      <span className="sport-icon">{sport.icon}</span>
                      <span className="sport-label">{sport.label}</span>
                      <span className="chat-count">{chats.length}</span>
                    </div>
                    <div className="chat-list">
                      {loading ? (
                        <div className="chat-item placeholder">Loading…</div>
                      ) : chats.length === 0 ? (
                        <button
                          type="button"
                          className="chat-item new-in-sport"
                          onClick={() => onNewChat(sport.key)}
                        >
                          Start {sport.label} chat
                        </button>
                      ) : (
                        chats.map((chat) => (
                          <button
                            key={chat.id}
                            type="button"
                            className="chat-item"
                            onClick={() => onSelectChat(sport.key, chat)}
                          >
                            {chat.title || 'Untitled'}
                          </button>
                        ))
                      )}
                    </div>
                  </div>
                )
              })}
            </div>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  )
}
