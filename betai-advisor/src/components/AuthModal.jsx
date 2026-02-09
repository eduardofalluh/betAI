import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '../contexts/AuthContext'

export default function AuthModal({ isOpen, onClose }) {
  const { login, signup } = useAuth()
  const [mode, setMode] = useState('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      if (mode === 'login') {
        await login(email, password)
      } else {
        await signup(email, password)
      }
      onClose()
      setEmail('')
      setPassword('')
    } catch (err) {
      setError(err.message || 'Something went wrong')
    } finally {
      setSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        className="auth-backdrop"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        onClick={onClose}
      />
      <motion.div
        className="auth-modal"
        role="dialog"
        aria-labelledby="auth-title"
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.96 }}
        transition={{ type: 'spring', damping: 25, stiffness: 300 }}
      >
        <div className="auth-modal-header">
          <h2 id="auth-title">{mode === 'login' ? 'Log in' : 'Sign up'}</h2>
          <button type="button" className="auth-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>
        <p className="auth-hint">
          {mode === 'login'
            ? 'Log in to load and save your chats across devices.'
            : 'Create an account to save your chats and access them later.'}
        </p>
        <form onSubmit={handleSubmit} className="auth-form">
          <label htmlFor="auth-email">Email</label>
          <input
            id="auth-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@example.com"
            required
          />
          <label htmlFor="auth-password">Password</label>
          <input
            id="auth-password"
            type="password"
            autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder={mode === 'login' ? '••••••••' : 'Min 6 characters'}
            minLength={mode === 'signup' ? 6 : undefined}
            required
          />
          {error && <p className="auth-error">{error}</p>}
          <button type="submit" className="auth-submit" disabled={submitting}>
            {submitting ? '…' : mode === 'login' ? 'Log in' : 'Sign up'}
          </button>
        </form>
        <button
          type="button"
          className="auth-switch"
          onClick={() => { setMode(mode === 'login' ? 'signup' : 'login'); setError(''); }}
        >
          {mode === 'login' ? "Don't have an account? Sign up" : 'Already have an account? Log in'}
        </button>
      </motion.div>
    </AnimatePresence>
  )
}
