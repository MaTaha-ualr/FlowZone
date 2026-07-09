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


CHARACTER_DISPLAY_NAMES = {
    Character.NAVIGATOR: "Yogi",
    Character.CHALLENGER: "Vex",
    Character.STRAIGHT_SHOOTER: "Ace",
    Character.STRATEGIST: "Nova",
}


VIBE_CHARACTER_MAP = {
    Vibe.SOLID: Character.NAVIGATOR,
    Vibe.ANGRY: Character.CHALLENGER,
    Vibe.GUARDED: Character.STRAIGHT_SHOOTER,
    Vibe.STORM: Character.NAVIGATOR,
}


VIBE_MESSAGE_TEMPLATES = {
    Vibe.SOLID: "{character_name} is here to help you keep the momentum steady.",
    Vibe.ANGRY: "You're feeling angry. {character_name} is here to help you cool down.",
    Vibe.GUARDED: "You're feeling guarded. {character_name} will keep it direct and low-pressure.",
    Vibe.STORM: "You're in storm mode. {character_name} is here to help you slow things down.",
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
            {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
        "description": "Needs strong persona adherence and nuanced pushback. Claude is worth the premium."
    },
    Character.NAVIGATOR: {
        "primary": {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
        "fallbacks": [
            {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
        "description": "Empathetic guidance. Gemini Flash is free and fast, GPT-4o-mini as quality fallback."
    },
    Character.STRAIGHT_SHOOTER: {
        "primary": {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        "fallbacks": [
            {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
        ],
        "description": "Direct and tactical. Llama-70B on Groq is fast and free, GPT-4o-mini as backup."
    },
    Character.STRATEGIST: {
        "primary": {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
        "fallbacks": [
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
            {"provider": ModelProvider.GOOGLE, "model": ModelID.GEMINI_FLASH},
        ],
        "description": "Long-game optimization. GPT-4o-mini handles planning well, free models backstop budget pressure."
    },
}


# ============================================================
# PER-CHARACTER GENERATION PARAMETERS
# ============================================================
# Tuned to make each character sound like itself rather than the same model
# voice in different costumes.
#   - temperature: higher = looser, more conversational; lower = focused/tactical
#   - max_tokens:  caps reply length, reinforces the brevity baked into prompts
#   - top_p:       slight nucleus narrowing for the more disciplined characters
#   - frequency_penalty: discourages the "I hear you / it sounds like" loop

CHARACTER_GEN_PARAMS = {
    Character.CHALLENGER: {
        "temperature": 0.85,   # spontaneous, edgier; less canned
        "max_tokens": 400,
        "top_p": 0.95,
        "frequency_penalty": 0.4,
        "presence_penalty": 0.3,
    },
    Character.NAVIGATOR: {
        "temperature": 0.6,    # steady, deliberate, low-key
        "max_tokens": 380,
        "top_p": 0.9,
        "frequency_penalty": 0.5,
        "presence_penalty": 0.2,
    },
    Character.STRAIGHT_SHOOTER: {
        "temperature": 0.5,    # tactical, low variance, get-to-the-point
        "max_tokens": 320,
        "top_p": 0.85,
        "frequency_penalty": 0.4,
        "presence_penalty": 0.2,
    },
    Character.STRATEGIST: {
        "temperature": 0.7,    # balanced, long-form when needed
        "max_tokens": 600,
        "top_p": 0.92,
        "frequency_penalty": 0.3,
        "presence_penalty": 0.2,
    },
}


def get_gen_params(character: Character) -> dict:
    """Return generation params for a character with sane fallbacks."""
    return CHARACTER_GEN_PARAMS.get(
        character,
        CHARACTER_GEN_PARAMS[Character.NAVIGATOR],
    )


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
    # Analytical: mask detection, sentiment, JSON extraction.
    # Needs reliable structured output — GPT-4o-mini is fast/cheap and handles JSON well.
    TaskType.ANALYTICAL: {
        "primary": {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
        "fallbacks": [
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
        ],
    },
    # Utility: sanitization, summarization. Llama-8B on Groq is plenty for these.
    TaskType.UTILITY: {
        "primary": {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_8B},
        "fallbacks": [
            {"provider": ModelProvider.GROQ, "model": ModelID.LLAMA_70B},
            {"provider": ModelProvider.OPENAI, "model": ModelID.GPT_4O_MINI},
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


TRUST_TIER_DISPLAY = {
    TrustTier.THE_WATCH: {
        "name": "The Watch",
        "color": "#9E9E9E",
        "emoji": "\U0001f441\ufe0f",
    },
    TrustTier.THE_FLEX: {
        "name": "The Flex",
        "color": "#4CAF50",
        "emoji": "\U0001f4aa",
    },
    TrustTier.THE_VETTED: {
        "name": "The Vetted",
        "color": "#7E57C2",
        "emoji": "\u2b50",
    },
}


VOUCH_DISPLAY = {
    "curfew_extension": {
        "name": "Curfew Extension",
        "icon": "\U0001f319",
    },
    "social_pass": {
        "name": "Social Pass",
        "icon": "\U0001f389",
    },
    "reduced_monitoring": {
        "name": "Reduced Monitoring",
        "icon": "\U0001f513",
    },
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
