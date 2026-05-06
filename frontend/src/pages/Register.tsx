import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Zap, Eye, EyeOff, AlertTriangle, ChevronRight, ChevronLeft } from 'lucide-react'
import { useAuth } from '@/context/AuthContext'

export default function Register() {
  const [step, setStep] = useState(1)
  const [name, setName] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [age, setAge] = useState('')
  const [role, setRole] = useState<'youth' | 'mentor'>('youth')
  const [school, setSchool] = useState('')
  const [city, setCity] = useState('')
  const [state, setStateVal] = useState('')
  const [userType, setUserType] = useState('')
  const [probation, setProbation] = useState(false)
  const [caseWorker, setCaseWorker] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const payload: Record<string, unknown> = {
        name,
        username,
        password,
        age: age ? Number(age) : undefined,
        role,
      }
      if (role === 'youth') {
        payload.school_name = school || undefined
        payload.city = city || undefined
        payload.state = state || undefined
        payload.user_type = userType === 'juvenile_justice' || userType === 'at_risk' ? userType : 'at_risk'
        payload.has_probation = probation
        payload.has_case_worker = caseWorker
      }
      await register(payload)
      navigate('/login')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed')
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
        <div className="text-center mb-6">
          <h1 className="font-display text-4xl text-brandGold text-glow-gold mb-2">JOIN FLOWZONE</h1>
          <p className="text-textSecondary">Start your Trust Engine journey</p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="flex items-center gap-2 p-3 rounded-fz-md bg-safeRed/10 text-safeRed text-sm">
              <AlertTriangle size={16} />
              {error}
            </div>
          )}

          <AnimatePresence mode="wait">
            {step === 1 && (
              <motion.div key="s1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-4">
                <div>
                  <label className="block text-sm text-textSecondary mb-1">Full Name</label>
                  <input value={name} onChange={(e) => setName(e.target.value)} className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="Marcus Cole" />
                </div>
                <div>
                  <label className="block text-sm text-textSecondary mb-1">Username</label>
                  <input value={username} onChange={(e) => setUsername(e.target.value)} className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="marcus_c" />
                </div>
                <div>
                  <label className="block text-sm text-textSecondary mb-1">Password</label>
                  <div className="relative">
                    <input type={showPassword ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} className="w-full px-3 py-2.5 pr-10 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="••••••••" />
                    <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-3 top-1/2 -translate-y-1/2 text-textMuted hover:text-textPrimary">
                      {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                    </button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-textSecondary mb-1">Age</label>
                  <input value={age} onChange={(e) => setAge(e.target.value)} type="number" className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="17" />
                </div>
                <div>
                  <label className="block text-sm text-textSecondary mb-1">Role</label>
                  <div className="flex gap-2">
                    {(['youth', 'mentor'] as const).map((r) => (
                      <button key={r} type="button" onClick={() => setRole(r)} className={`flex-1 py-2 rounded-fz-md text-sm font-medium border transition-colors ${role === r ? 'bg-brandGold text-textInverse border-brandGold' : 'bg-bgOverlay text-textSecondary border-borderSubtle hover:border-borderActive'}`}>
                        {r === 'youth' ? 'Youth' : 'Mentor'}
                      </button>
                    ))}
                  </div>
                </div>
                <button type="button" onClick={() => setStep(2)} className="w-full flex items-center justify-center gap-2 py-2.5 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors">
                  Next <ChevronRight size={16} />
                </button>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div key="s2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="space-y-4">
                <div>
                  <label className="block text-sm text-textSecondary mb-1">School</label>
                  <input value={school} onChange={(e) => setSchool(e.target.value)} className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="Westside High" />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-sm text-textSecondary mb-1">City</label>
                    <input value={city} onChange={(e) => setCity(e.target.value)} className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="Atlanta" />
                  </div>
                  <div>
                    <label className="block text-sm text-textSecondary mb-1">State</label>
                    <input value={state} onChange={(e) => setStateVal(e.target.value)} className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="GA" />
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-textSecondary mb-1">User Type</label>
                  <input value={userType} onChange={(e) => setUserType(e.target.value)} className="w-full px-3 py-2.5 rounded-fz-md bg-bgOverlay border border-borderSubtle text-textPrimary focus:border-brandGold focus:outline-none" placeholder="diversion / probation / voluntary" />
                </div>
                <div className="flex items-center gap-3 py-1">
                  <input id="probation" type="checkbox" checked={probation} onChange={(e) => setProbation(e.target.checked)} className="w-4 h-4 accent-brandGold" />
                  <label htmlFor="probation" className="text-sm text-textSecondary">On probation</label>
                </div>
                <div className="flex items-center gap-3 py-1">
                  <input id="caseworker" type="checkbox" checked={caseWorker} onChange={(e) => setCaseWorker(e.target.checked)} className="w-4 h-4 accent-brandGold" />
                  <label htmlFor="caseworker" className="text-sm text-textSecondary">Has case worker</label>
                </div>
                <div className="flex gap-2">
                  <button type="button" onClick={() => setStep(1)} className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-fz-md border border-borderSubtle text-textSecondary hover:bg-bgHover transition-colors">
                    <ChevronLeft size={16} /> Back
                  </button>
                  <button type="submit" disabled={loading} className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-fz-md bg-brandGold text-textInverse font-semibold hover:bg-brandGoldBright transition-colors disabled:opacity-50">
                    {loading ? <div className="w-5 h-5 border-2 border-textInverse border-t-transparent rounded-full animate-spin" /> : <><Zap size={18} /> SIGN UP</>}
                  </button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </form>

        <div className="mt-6 text-center">
          <p className="text-textMuted text-sm">
            Already in?{' '}
            <Link to="/login" className="text-brandGold hover:text-brandGoldBright font-medium inline-flex items-center gap-1">
              Log in <ChevronRight size={14} />
            </Link>
          </p>
        </div>
      </motion.div>
    </div>
  )
}
