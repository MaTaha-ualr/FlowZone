import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Zap, Eye, EyeOff, AlertTriangle, ChevronRight } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-bgBase">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="w-full max-w-md p-6"
      >
        <div className="text-center mb-8">
          <h1 className="font-display text-4xl text-brandGold text-glow-gold mb-2">FLOWZONE</h1>
          <p className="text-textSecondary">They watch. You flex. You get vetted.</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-fz-md bg-safeRed/10 text-safeRed text-sm">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          <div>
            <label className="block text-sm text-textSecondary mb-1">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none transition-colors"
              placeholder="your_username"
            />
          </div>

          <div>
            <label className="block text-sm text-textSecondary mb-1">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full px-3 py-2.5 pr-10 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary placeholder:text-textMuted focus:border-brandGold focus:outline-none transition-colors"
                placeholder="••••••••"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-textMuted hover:text-textPrimary"
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="w-full flex items-center justify-center gap-2 py-2.5 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors disabled:opacity-50"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-textInverse border-t-transparent rounded-full animate-spin" />
            ) : (
              <>
                <Zap size={18} />
                GET IN
              </>
            )}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-textMuted text-sm">
            No account?{' '}
            <Link to="/register" className="text-brandGold hover:text-brandGoldBright font-medium inline-flex items-center gap-1">
              Join FlowZone <ChevronRight size={14} />
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
