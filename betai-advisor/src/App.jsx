import { useState, useEffect, useCallback, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import AuthModal from './components/AuthModal'
import { useAuth } from './contexts/AuthContext'
import { getChats, saveChat } from './lib/api'
import './App.css'

const THEME_KEY = 'betai-theme'
function getStoredTheme() {
  try {
    const t = localStorage.getItem(THEME_KEY)
    if (t === 'light' || t === 'dark') return t
  } catch (_) {}
  return 'dark'
}

const SPORTS = [
  { key: 'basketball', label: 'Basketball', icon: '🏀' },
  { key: 'soccer', label: 'Soccer', icon: '⚽' },
  { key: 'american_football', label: 'American Football', icon: '🏈' },
  { key: 'baseball', label: 'Baseball', icon: '⚾' },
  { key: 'hockey', label: 'Hockey', icon: '🏒' },
  { key: 'tennis', label: 'Tennis', icon: '🎾' },
  { key: 'mma', label: 'MMA', icon: '🥊' },
  { key: 'olympics', label: 'Milano Cortina 2026', icon: '⛷️' },
  { key: 'other', label: 'Other', icon: '📋' },
]

const AUTOSAVE_DELAY_MS = 1500

function generateTitle(messages) {
  const first = messages.find(m => m.sender === 'user')
  if (!first) return 'New chat'
  const text = first.text.slice(0, 40)
  return text.length < (first.text?.length || 0) ? `${text}…` : text
}

export default function App() {
  const { user, logout, refreshUser } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatsBySport, setChatsBySport] = useState({})
  const [currentSport, setCurrentSport] = useState('basketball')
  const [currentChat, setCurrentChat] = useState(null) // { id, sport, title, messages }
  const [loading, setLoading] = useState(true)
  const [lastSavedAt, setLastSavedAt] = useState(null)
  const [theme, setTheme] = useState(getStoredTheme)
  const [authModalOpen, setAuthModalOpen] = useState(false)
  const autosaveTimerRef = useRef(null)

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    try { localStorage.setItem(THEME_KEY, theme) } catch (_) {}
  }, [theme])

  const toggleTheme = useCallback(() => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }, [])

  const loadChats = useCallback(async () => {
    if (!user) {
      setChatsBySport({})
      setLoading(false)
      return
    }
    try {
      const data = await getChats()
      setChatsBySport(typeof data === 'object' && !Array.isArray(data) ? data : {})
    } catch (e) {
      if (e?.status === 401) logout()
      setChatsBySport({})
    } finally {
      setLoading(false)
    }
  }, [user, logout])

  useEffect(() => {
    loadChats()
  }, [loadChats])

  const startNewChat = (sport = currentSport) => {
    setCurrentSport(sport)
    setCurrentChat({ id: null, sport, title: 'New chat', messages: [] })
    setSidebarOpen(false)
  }

  const loadChat = (sport, chat) => {
    setCurrentSport(sport)
    setCurrentChat({
      id: chat.id,
      sport,
      title: chat.title,
      messages: chat.messages || [],
    })
    setSidebarOpen(false)
  }

  const currentChatRef = useRef(currentChat)
  currentChatRef.current = currentChat

  const saveCurrentChat = useCallback(async () => {
    const chat = currentChatRef.current
    if (!chat || !chat.messages?.length) return Promise.resolve()
    if (!user) return Promise.resolve()
    const title = generateTitle(chat.messages)
    const id = chat.id || crypto.randomUUID()
    try {
      await saveChat({
        sport: chat.sport,
        title,
        messages: chat.messages,
        id,
        createdAt: chat.createdAt || new Date().toISOString(),
      })
      setCurrentChat((prev) => (prev ? { ...prev, id } : null))
      setLastSavedAt(Date.now())
      await loadChats()
    } catch (e) {
      if (e?.status === 401) logout()
      console.error('Autosave failed', e)
    }
  }, [user, loadChats, logout])

  // Autosave: debounce when messages change
  useEffect(() => {
    if (!currentChat?.messages?.length) return
    const timer = window.setTimeout(() => {
      const chat = currentChatRef.current
      if (!chat?.messages?.length) return
      saveCurrentChat()
    }, AUTOSAVE_DELAY_MS)
    return () => clearTimeout(timer)
  }, [currentChat?.messages, saveCurrentChat])

  const appendMessage = (sender, text) => {
    setCurrentChat(prev => {
      if (!prev) return { id: null, sport: currentSport, title: 'New chat', messages: [{ sender, text }] }
      return {
        ...prev,
        messages: [...prev.messages, { sender, text }],
      }
    })
  }

  const handleSportChange = useCallback((sport) => {
    if (sport === currentSport) return
    const chat = currentChatRef.current
    const hasMessages = chat?.messages?.length > 0
    if (hasMessages) {
      saveCurrentChat().then(() => startNewChat(sport))
    } else {
      startNewChat(sport)
    }
  }, [currentSport, saveCurrentChat])

  return (
    <div className="app" data-theme={theme}>
      <AuthModal isOpen={authModalOpen} onClose={() => setAuthModalOpen(false)} />
      <motion.button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(true)}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.98 }}
        aria-label="Open sidebar"
      >
        <span className="burger" />
        <span className="burger" />
        <span className="burger" />
      </motion.button>

      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        sports={SPORTS}
        chatsBySport={chatsBySport}
        currentSport={currentSport}
        currentChatId={currentChat?.id}
        loading={loading}
        onNewChat={startNewChat}
        onSelectChat={loadChat}
        user={user}
        onOpenAuth={() => setAuthModalOpen(true)}
      />

      <motion.main
        className={`main ${sidebarOpen ? 'sidebar-open' : ''}`}
        initial={false}
        animate={{ opacity: 1 }}
      >
        <AnimatePresence mode="wait">
          <ChatPanel
            key={currentChat?.id ?? 'new'}
            sport={currentChat?.sport ?? currentSport}
            sportLabel={SPORTS.find(s => s.key === (currentChat?.sport ?? currentSport))?.label ?? 'Sport'}
            sports={SPORTS}
            messages={currentChat?.messages ?? []}
            onSendMessage={appendMessage}
            onNewChat={() => startNewChat(currentSport)}
            onSportChange={handleSportChange}
            lastSavedAt={lastSavedAt}
            theme={theme}
            onToggleTheme={toggleTheme}
            user={user}
            onOpenAuth={() => setAuthModalOpen(true)}
            onLogout={logout}
          />
        </AnimatePresence>
      </motion.main>
    </div>
  )
}
