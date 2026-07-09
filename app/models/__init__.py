"""
Models Package
===============
Import all models here so SQLAlchemy's Base.metadata.create_all()
discovers and creates all tables.
"""

from app.models.user import User
from app.models.session import Session
from app.models.message import Message
from app.models.trust_score import TrustScore
from app.models.mentor_note import MentorNote
from app.models.school_data import SchoolData
from app.models.document_ref import DocumentRef
from app.models.api_usage import ApiUsage
from app.models.vouch import Vouch
from app.models.pattern import Pattern
from app.models.safety_event import SafetyEvent

__all__ = [
    "User", "Session", "Message", "TrustScore", "MentorNote",
    "SchoolData", "DocumentRef", "ApiUsage", "Vouch", "Pattern",
    "SafetyEvent",
]
