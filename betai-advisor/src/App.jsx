import { useState, useEffect, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './components/Sidebar'
import ChatPanel from './components/ChatPanel'
import { getChats, saveChat } from './lib/api'
import './App.css'

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

function generateTitle(messages) {
  const first = messages.find(m => m.sender === 'user')
  if (!first) return 'New chat'
  const text = first.text.slice(0, 40)
  return text.length < (first.text?.length || 0) ? `${text}…` : text
}

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [chatsBySport, setChatsBySport] = useState({})
  const [currentSport, setCurrentSport] = useState('basketball')
  const [currentChat, setCurrentChat] = useState(null) // { id, sport, title, messages }
  const [loading, setLoading] = useState(true)

  const loadChats = useCallback(async () => {
    try {
      const data = await getChats()
      setChatsBySport(typeof data === 'object' && !Array.isArray(data) ? data : {})
    } catch (e) {
      setChatsBySport({})
    } finally {
      setLoading(false)
    }
  }, [])

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

  const saveCurrentChat = async () => {
    if (!currentChat || currentChat.messages.length === 0) return
    const title = generateTitle(currentChat.messages)
    const id = currentChat.id || crypto.randomUUID()
    try {
      await saveChat({
        sport: currentChat.sport,
        title,
        messages: currentChat.messages,
        id,
        createdAt: new Date().toISOString(),
      })
      setCurrentChat((prev) => (prev ? { ...prev, id } : null))
      await loadChats()
    } catch (e) {
      console.error('Save chat failed', e)
    }
  }

  const appendMessage = (sender, text) => {
    setCurrentChat(prev => {
      if (!prev) return { id: null, sport: currentSport, title: 'New chat', messages: [{ sender, text }] }
      return {
        ...prev,
        messages: [...prev.messages, { sender, text }],
      }
    })
  }

  const setCurrentChatSport = (sport) => {
    setCurrentSport(sport)
    setCurrentChat(prev => prev ? { ...prev, sport } : { id: null, sport, title: 'New chat', messages: [] })
  }

  return (
    <div className="app">
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
        loading={loading}
        onNewChat={startNewChat}
        onSelectChat={loadChat}
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
            onSaveChat={saveCurrentChat}
            onSportChange={setCurrentChatSport}
            hasUnsavedMessages={currentChat?.messages?.length > 0 && !currentChat?.id}
          />
        </AnimatePresence>
      </motion.main>
    </div>
  )
}
