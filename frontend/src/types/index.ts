export type RoleEnum = 'youth' | 'mentor'
export type CharacterEnum = 'challenger' | 'navigator' | 'straight_shooter' | 'strategist' | 'ace' | 'nova'
export type SafeHarborEnum = 'green' | 'yellow' | 'red'
export type VibeEnum = 'solid' | 'angry' | 'guarded' | 'storm'

export interface UserProfileResponse {
  id: string
  name: string
  username: string | null
  email: string | null
  phone: string | null
  role: RoleEnum
  current_character: CharacterEnum
  current_character_name: string
  current_tier: string
  check_in_streak: number
  current_trust_score: number
  display_score: number
  intake_completed: boolean
  safe_harbor_floor: SafeHarborEnum
  age: number
  school_name: string | null
  city: string | null
  state: string | null
  user_type: string
  has_probation: boolean
  has_case_worker: boolean
  created_at: string
}

export interface RainbowTierResponse {
  key: string
  name: string
  threshold: number
  color: string
  emoji: string
  unlocked: boolean
}

export interface RainbowCircleResponse {
  current_tier: string
  current_tier_name: string
  current_tier_color: string
  current_tier_emoji: string
  score: number
  display_score: number
  min_score_in_tier: number
  max_score_in_tier: number | null
  progress_percent: number
  total_tiers: number
  tier_index: number
  all_tiers: RainbowTierResponse[]
  recent_deltas: TrustDelta[]
}

export interface SessionResponse {
  id: string
  user_id: string
  session_type: string
  character_active: CharacterEnum
  vibe_selected: VibeEnum | null
  mask_detected: boolean
  safe_harbor_level: SafeHarborEnum
  started_at: string
  is_active: boolean
  trust_score_delta: number
}

export interface VibeCheckRequest {
  session_id: string
  vibe: VibeEnum
  notes: string | null
}

export interface VibeCheckResponse {
  session_id: string
  vibe: VibeEnum
  vibe_emoji: string
  character_assigned: CharacterEnum
  character_name: string
  message: string
  safe_harbor_level: SafeHarborEnum
}

export interface TrustDelta {
  date: string
  score: number
  delta?: number
  event?: string
  event_type?: 'vouch' | 'mask' | 'tier_change' | 'check_in' | 'vibe_check' | 'tactical_action' | 'honesty_bonus'
  fullDate?: string
}

export interface TrustScoreResponse {
  user_id: string
  score: number
  display_score: number
  tier: string
  components: {
    consistency: number
    weight: number
    honesty: number
    regulation: number
    mentor_vouch: number
    penalty: number
    time_days: number
  }
  streak_days: number
  weight_multiplier: number
  masks_detected: number
  resets_completed: number
  traps_disclosed: number
  mentor_vouches: number
  days_active: number
}

export interface VouchRecord {
  id: string
  mentor_name: string
  vouch_points: number
  created_at: string
  note: string
}

export interface RewardItemResponse {
  key: string
  name: string
  icon: string
  cost: number
  can_afford: boolean
  locked: boolean
}

export interface RewardsResponse {
  current_score: number
  available_vouches: RewardItemResponse[]
  redeemed_vouches: RedeemedVouch[]
  can_redeem: boolean
  next_unlock_tier: string | null
  next_unlock_score: number | null
}

export interface RedeemedVouch {
  key: string
  name: string
  icon: string
  redeemed_at: string
  status: 'active' | 'used'
}

export interface ActivityItem {
  id: string
  type: 'check_in' | 'vibe_check' | 'flowquest' | 'document' | 'mask' | 'vouch' | 'tier_change' | 'tactical_action'
  title: string
  description: string
  timestamp: string
  delta?: number
  icon?: string
}

/* ─── Chat Types ─── */

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: string
  character?: string
  voice_url?: string
  mask_detected?: boolean
  action_item?: {
    id: string
    description: string
    status: 'pending' | 'accepted' | 'passed'
  }
  trust_delta?: number
}

export interface ChatResponse {
  message: ChatMessage
  session_id: string
}

export interface ChatHistoryResponse {
  messages: ChatMessage[]
  session_id: string
}

/* ─── Mentor / Document Types ─── */

export interface MentorNote {
  id: string
  youth_id: string
  youth_name: string
  mentor_id: string
  mentor_name: string
  note_type: 'check_in' | 'session' | 'incident' | 'milestone' | 'flag'
  content: string
  vouch_points: number
  risk_flag: boolean
  created_at: string
}

export interface DocumentItem {
  id: string
  user_id: string
  name: string
  type: 'pdf' | 'image' | 'doc' | 'txt'
  status: 'uploaded' | 'processing' | 'verified' | 'rejected'
  uploaded_at: string
  url?: string
  rag_snippets?: string[]
  document_type?: string
  mime_type?: string
  chunk_count?: number
  extracted_metadata?: Record<string, unknown>
}

export interface IntakeAnswers {
  intent: 'win_freedom' | 'check_box'
  pressure_level: number
  trap: 'friends' | 'temper' | 'home' | 'boredom' | 'unknown'
  autonomy_prize: string
  collaboration: 'yes' | 'we_will_see'
}

export interface IntakeResponse {
  user_id: string
  intake_completed: boolean
  character: CharacterEnum
  character_name: string
  safe_harbor: SafeHarborEnum
  score: number
}

export interface MentorDashboardData {
  total_youth: number
  active_sessions: number
  alerts: number
  avg_trust: number
  youth_list: MentorYouthItem[]
}

export interface MentorRosterResponse {
  total_youth: number
  active_sessions: number
  alerts: number
  avg_trust: number
  youth: MentorYouthItem[]
}

export interface MentorYouthDashboard {
  user: {
    id: string
    name: string
    age: number
    city?: string | null
    state?: string | null
    school_name?: string | null
    user_type: string
    current_character: CharacterEnum
    current_character_name: string
    current_trust_score: number
    display_score: number
    current_tier: string
    check_in_streak: number
    safe_harbor_floor: SafeHarborEnum
  }
  school: {
    gpa: number | null
    attendance_rate: number | null
    classes_failing: string[]
    has_iep: boolean
  } | null
  trust_score_trend: Array<{ date: string; score: number }>
  recent_notes: Array<{
    id: string
    mentor: string | null
    type: string
    content: string
    vouch_points: number
    risk_flag_level: string | null
    date: string | null
  }>
}

export interface MentorYouthItem {
  id: string
  name: string
  avatar_url?: string
  age: number
  school_name?: string
  city?: string
  current_trust_score: number
  display_score: number
  current_tier: string
  safe_harbor_floor: SafeHarborEnum
  current_character: CharacterEnum
  current_character_name: string
  check_in_streak: number
  last_session_at?: string
  has_alert: boolean
}

/* ─── Auth Types ─── */

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: UserProfileResponse
}

export interface RegisterRequest {
  name: string
  username: string
  password: string
  age?: number
  role?: RoleEnum
  school_name?: string
  city?: string
  state?: string
  user_type?: string
  has_probation?: boolean
  has_case_worker?: boolean
}

export interface RegisterResponse {
  id: string
  name: string
  username: string
  role: RoleEnum
  message: string
}

/* ─── Character Reference (no per-persona PII) ─── */

export const CHARACTER_INFO: Record<string, { name: string; role: string; color: string; description: string }> = {
  challenger: {
    name: 'The Challenger',
    role: 'Tests boundaries, learns respect',
    color: '#DC2626',
    description: 'Fire-driven. Pushes back first. Loyal when trust is earned.',
  },
  navigator: {
    name: 'The Navigator',
    role: 'Maps paths, avoids traps',
    color: '#00A8E8',
    description: 'Ice-calm. Thinks three moves ahead. Protective of inner circle.',
  },
  straight_shooter: {
    name: 'The Straight Shooter',
    role: 'Speaks truth, builds honesty',
    color: '#10B981',
    description: 'Earth-steady. Says what others won\'t. Sometimes too blunt.',
  },
  strategist: {
    name: 'The Strategist',
    role: 'Plans wins, earns trust',
    color: '#6C5CE7',
    description: 'Shadow-wise. Seen it all. Quiet until the moment matters.',
  },
  ace: {
    name: 'The Ace',
    role: 'Performs under pressure',
    color: '#D4AF37',
    description: 'Gold-standard. Sets the pace. Expects excellence from others.',
  },
  nova: {
    name: 'The Nova',
    role: 'Ignites change, burns bright',
    color: '#FF6B35',
    description: 'Explosive energy. Transforms spaces. Needs direction to sustain.',
  },
}

export const VIBE_INFO: Record<VibeEnum, { emoji: string; label: string; color: string; advice: string }> = {
  solid: {
    emoji: '💪',
    label: 'Solid',
    color: '#00B4D8',
    advice: 'Good energy. Lock in on goals today.',
  },
  angry: {
    emoji: '🔥',
    label: 'Angry',
    color: '#FF6B35',
    advice: 'Channel the fire. Don\'t let it burn your own house.',
  },
  guarded: {
    emoji: '🧿',
    label: 'Guarded',
    color: '#64748B',
    advice: 'Walls are up. That\'s okay. What are they protecting?',
  },
  storm: {
    emoji: '⚡',
    label: 'Storm',
    color: '#7C3AED',
    advice: 'Chaos inside. Use The Dump. Don\'t let it leak into action.',
  },
}

export const SAFE_HARBOR_INFO: Record<SafeHarborEnum, { label: string; color: string; message: string }> = {
  green: {
    label: 'Safe Harbor',
    color: '#10B981',
    message: 'You\'re in a good space. Keep building.',
  },
  yellow: {
    label: 'Caution',
    color: '#F59E0B',
    message: 'Something is shifting. Pay attention.',
  },
  red: {
    label: 'Storm Watch',
    color: '#DC2626',
    message: 'High risk zone. Reach out. Use your tools.',
  },
}
