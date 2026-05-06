import { HashRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from '@/context/AuthContext'
import Layout from '@/components/Layout'

import Home from '@/pages/Home'
import Login from '@/pages/Login'
import Register from '@/pages/Register'
import Intake from '@/pages/Intake'
import Dashboard from '@/pages/Dashboard'
import VibeCheck from '@/pages/VibeCheck'
import FlowQuest from '@/pages/FlowQuest'
import SessionHistory from '@/pages/SessionHistory'
import Profile from '@/pages/Profile'
import TrustDetail from '@/pages/TrustDetail'
import Rewards from '@/pages/Rewards'
import Documents from '@/pages/Documents'
import Voice from '@/pages/Voice'
import MentorDashboard from '@/pages/MentorDashboard'
import MentorNotes from '@/pages/MentorNotes'

function ProtectedRoute({ children, mentorOnly = false }: { children: React.ReactNode; mentorOnly?: boolean }) {
  const { isAuthenticated, isLoading, role } = useAuth()
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-screen bg-bgBase">
        <div className="w-8 h-8 border-2 border-brandGold border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }
  if (!isAuthenticated) return <Navigate to="/login" replace />
  if (mentorOnly && role !== 'mentor') return <Navigate to="/dashboard" replace />
  return <>{children}</>
}

function AppRoutes() {
  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/intake" element={<ProtectedRoute><Intake /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
        <Route path="/vibe-check" element={<ProtectedRoute><VibeCheck /></ProtectedRoute>} />
        <Route path="/flowquest/:sessionId?" element={<ProtectedRoute><FlowQuest /></ProtectedRoute>} />
        <Route path="/sessions" element={<ProtectedRoute><SessionHistory /></ProtectedRoute>} />
        <Route path="/profile" element={<ProtectedRoute><Profile /></ProtectedRoute>} />
        <Route path="/trust" element={<ProtectedRoute><TrustDetail /></ProtectedRoute>} />
        <Route path="/rewards" element={<ProtectedRoute><Rewards /></ProtectedRoute>} />
        <Route path="/documents" element={<ProtectedRoute><Documents /></ProtectedRoute>} />
        <Route path="/voice" element={<ProtectedRoute><Voice /></ProtectedRoute>} />
        <Route path="/mentor/dashboard" element={<ProtectedRoute mentorOnly><MentorDashboard /></ProtectedRoute>} />
        <Route path="/mentor/notes/:userId" element={<ProtectedRoute mentorOnly><MentorNotes /></ProtectedRoute>} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <HashRouter>
        <AppRoutes />
      </HashRouter>
    </AuthProvider>
  )
}
