"""
FlowZone Constants & Enumerations
===================================
Central definitions for all system-wide constants.
These define the game rules, character behaviors, and scoring system.

Architecture Note:
    Character-to-model mappings are defined here but the actual
    routing logic (fallbacks, budget checks) lives in the Model Router service.
    This file is pure data — no logic.
"""

from enum import Enum


# ============================================================
# CHARACTERS — The four Strategic Voices
# ============================================================

class Character(str, Enum):
    """
    The four adaptive AI characters from the FlowZone framework.
    Each has a distinct personality, trigger condition, and model affinity.
    """
    CHALLENGER = "challenger"
    NAVIGATOR = "navigator"
    STRAIGHT_SHOOTER = "straight_shooter"
    STRATEGIST = "strategist"


# ============================================================
# VIBE EMOJIS — User-selected emotional state
# ============================================================

class Vibe(str, Enum):
    """User selects one of these at the start of each FlowQuest session."""
    SOLID = "solid"           # 💎 — Feeling good / stable
    ANGRY = "angry"           # 🔥 — Pressure / frustration
    GUARDED = "guarded"       # 🔏 — Closed off / resistant
    STORM = "storm"           # ⛈️ — Overwhelmed / crisis


VIBE_EMOJI_MAP = {
    Vibe.SOLID: "💎",
    Vibe.ANGRY: "🔥",
    Vibe.GUARDED: "🔏",
    Vibe.STORM: "⛈️",
}


# ============================================================
# CHARACTER ASSIGNMENT MATRIX
# ============================================================
# Based on intake data (heat level + vibe tendency), the system
# assigns an initial character. This can change dynamically.

CHARACTER_ASSIGNMENT_RULES = {
    # (heat_level_range, dominant_vibe) -> character
    ("high", Vibe.GUARDED): Character.CHALLENGER,
    ("high", Vibe.STORM): Character.NAVIGATOR,
    ("low", Vibe.SOLID): Character.STRATEGIST,
    ("low", Vibe.ANGRY): Character.STRAIGHT_SHOOTER,
    # Defaults for ambiguous cases
    ("high", Vibe.ANGRY): Character.CHALLENGER,
    ("high", Vibe.SOLID): Character.STRATEGIST,
    ("low", Vibe.GUARDED): Character.STRAIGHT_SHOOTER,
    ("low", Vibe.STORM): Character.NAVIGATOR,
}


# ============================================================
# MODEL PROVIDER DEFINITIONS
# ============================================================

class ModelProvider(str, Enum):
    """Supported LLM API providers."""
    ANTHROPIC = "anthropic"   # Claude — paid, premium quality
    OPENAI = "openai"         # GPT-4o-mini — paid, cheap
    GOOGLE = "google"         # Gemini 1.5 Flash — free tier
    GROQ = "groq"             # Llama 3.1 via Groq — free tier


class ModelID(str, Enum):
    """Specific model identifiers per provider."""
    # Anthropic
    CLAUDE_SONNET = "claude-sonnet-4-20250514"
    # OpenAI
    GPT_4O_MINI = "gpt-4o-mini"
    # Google
    GEMINI_FLASH = "gemini-1.5-flash"
    # Groq (Llama)
    LLAMA_70B = "llama-3.1-70b-versatile"
    LLAMA_8B = "llama-3.1-8b-instant"
    # Groq (Whisper — for STT)
    WHISPER_LARGE_V3 = "whisper-large-v3"


# ============================================================
# CHARACTER → MODEL MAPPING (with fallback chains)
# ============================================================
# Each character has a primary model and a fallback chain.
# The Model Router tries primary first, falls back on budget/rate-limit issues.

CHARACTER_MODEL_MAP = {
    Character.CHALLENGER: {
        "primary": {"provider": ModelProvider.ANTHROPIC, "model": ModelID.CLAUDE_SONNET},
        "fallbacks": [
            {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
        "description": "Needs strong persona adherence and nuanced pushback. Worth the premium."
    },
    Character.NAVIGATOR: {
        "primary": {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
        "fallbacks": [
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
        "description": "Empathetic guidance. Gemini free tier handles this well."
    },
    Character.STRAIGHT_SHOOTER: {
        "primary": {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        "fallbacks": [
            {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
        ],
        "description": "Direct and tactical. Shorter responses = smaller models work great."
    },
    Character.STRATEGIST: {
        "primary": {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
        "fallbacks": [
            {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
        "description": "Long-game optimization. GPT-4o-mini is cheap and strategic."
    },
}


# ============================================================
# TASK-SPECIFIC MODEL MAPPING
# ============================================================
# Non-conversational tasks use dedicated (usually free) models.

class TaskType(str, Enum):
    """The three types of LLM tasks in the system."""
    CONVERSATIONAL = "conversational"  # Character chatting with youth
    ANALYTICAL = "analytical"          # Mask detection, sentiment, JSON extraction
    UTILITY = "utility"                # Sanitization, summarization, embeddings


TASK_MODEL_MAP = {
    TaskType.ANALYTICAL: {
        "primary": {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
        "fallbacks": [
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
    },
    TaskType.UTILITY: {
        "primary": {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_8B},
        "fallbacks": [
            {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
        ],
    },
}


# ============================================================
# MODEL COST TABLE (per 1M tokens, in USD)
# ============================================================
# Used by the Credit Manager to track spending.

MODEL_COSTS = {
    ModelID.CLAUDE_SONNET: {"input": 3.00, "output": 15.00},
    ModelID.GPT_4O_MINI: {"input": 0.15, "output": 0.60},
    ModelID.GEMINI_FLASH: {"input": 0.0, "output": 0.0},  # Free tier
    ModelID.LLAMA_70B: {"input": 0.0, "output": 0.0},      # Free tier (Groq)
    ModelID.LLAMA_8B: {"input": 0.0, "output": 0.0},       # Free tier (Groq)
    ModelID.WHISPER_LARGE_V3: {"input": 0.0, "output": 0.0},  # Free tier (Groq)
}


# ============================================================
# RATE LIMITS (requests per minute per provider, free tier)
# ============================================================

PROVIDER_RATE_LIMITS = {
    ModelProvider.GOOGLE: {"rpm": 15, "rpd": 1500},
    ModelProvider.GROQ: {"rpm": 30, "rpd": 14400},
    ModelProvider.OPENAI: {"rpm": 60, "rpd": None},      # Pay-per-use, no daily cap
    ModelProvider.ANTHROPIC: {"rpm": 50, "rpd": None},    # Pay-per-use
}


# ============================================================
# SAFE HARBOR LEVELS
# ============================================================

class SafeHarborLevel(str, Enum):
    """
    Privacy/safety tiers for user data and system behavior.
    Green: Private vault (only youth + AI)
    Yellow: Trends shared with mentors
    Red: Emergency — system interrupt, alert Rainbow Circle
    """
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"


# ============================================================
# TRUST SCORE WEIGHTS (The Shield Formula)
# ============================================================
# Trust Score = (C × W) + H + R + M - P) / T

TRUST_SCORE_WEIGHTS = {
    "consistency_base": 3,        # C: points per consecutive check-in day
    "weight_hard_day": 1.5,       # W: multiplier when vibe is 🔥 or ⛈️
    "weight_normal_day": 1.0,     # W: multiplier for 💎 or 🔏 days
    "honesty_bonus": 25,          # H: per proactive trap disclosure
    "regulation_bonus": 10,       # R: per completed tactical reset
    "mentor_vouch_max": 50,       # M: max per single vouch
    "mask_penalty": -10,          # P: per detected mask
    "lie_penalty": -25,           # P: per detected lie (fact-check fail)
    "credit_decay_rate": 0.05,    # 5% per day of silence (after 72h)
    "decay_threshold_hours": 72,  # Hours of silence before decay starts
}


# ============================================================
# TRUST TIERS (Gamification Economy)
# ============================================================

class TrustTier(str, Enum):
    THE_WATCH = "the_watch"   # Baseline — access to Trust Engine
    THE_FLEX = "the_flex"     # Unlocks App Vouches
    THE_VETTED = "the_vetted" # High-trust — reduced monitoring recommendations


TRUST_TIER_THRESHOLDS = {
    TrustTier.THE_WATCH: 0,       # Starting tier
    TrustTier.THE_FLEX: 200,      # Points needed
    TrustTier.THE_VETTED: 500,    # Points needed
}


# ============================================================
# INTAKE SCORING
# ============================================================

INTAKE_SCORING = {
    "q1_check_box": 50,       # Honesty bonus — first honest thing said
    "q1_win_freedom": 10,     # Likely compliance mask
    "q2_high_heat_threshold": 8,
    "q2_high_heat_multiplier": 1.5,
    "q2_mid_heat_threshold": 5,
    "q2_mid_heat_multiplier": 1.2,
    "q3_specific_trap": 25,
    "q3_dont_know": 5,
    "q4_any_answer": 10,
    "q5_yes": 0,              # Starts streak (no bonus points)
    "q5_well_see": 0,         # No penalty
}


# ============================================================
# VOUCH CONFIGURATION
# ============================================================

VOUCH_CONFIG = {
    "expiry_hours": 48,               # App Vouches expire in 48h
    "curfew_extension_cost": 50,      # Trust credits to spend
    "social_pass_cost": 30,
    "reduced_monitoring_cost": 100,
}
