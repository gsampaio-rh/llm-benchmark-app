"""
Conversation module for multi-turn dialogue management.

This module contains data models and logic for managing conversations,
including message handling, thread management, and live conversation state.
"""

from .models import (
    ConversationMessage,
    ConversationThread,
    LiveConversationState
)

__all__ = [
    "ConversationMessage",
    "ConversationThread", 
    "LiveConversationState"
]
