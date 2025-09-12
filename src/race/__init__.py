"""
Race module for three-way performance demonstrations.

This module contains data models and logic for running performance races
between different AI inference engines (vLLM, TGI, Ollama).
"""

from .models import (
    EngineInfo,
    RaceParticipant, 
    RaceStatistics,
    ThreeWayRace,
    ServicePersonality
)

__all__ = [
    "EngineInfo",
    "RaceParticipant",
    "RaceStatistics", 
    "ThreeWayRace",
    "ServicePersonality"
]
