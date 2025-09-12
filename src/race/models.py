"""
Data models for three-way performance races.

This module contains all data structures related to racing AI inference engines,
including participant information, statistics tracking, and race state management.
"""

import time
import statistics
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class ServicePersonality(Enum):
    """Service personality types for human storytelling"""
    VLLM = ("professional", "blue", "Technical and precise")
    TGI = ("technical", "green", "Engineering-focused")  
    OLLAMA = ("friendly", "orange3", "Approachable and helpful")


@dataclass
class EngineInfo:
    """Technical information about an inference engine"""
    engine_url: str = "auto-discovered"
    model_name: str = "Qwen/Qwen2.5-7B"
    version: str = "latest"
    gpu_type: str = "NVIDIA H100"
    memory_gb: int = 80
    max_batch_size: int = 32
    max_context_length: int = 4096
    deployment: str = "Kubernetes"


@dataclass
class RaceParticipant:
    """A service participating in the three-way race"""
    name: str
    personality: ServicePersonality
    engine_info: EngineInfo = field(default_factory=EngineInfo)
    response_start_time: Optional[float] = None
    first_token_time: Optional[float] = None
    current_response: str = ""
    tokens_received: int = 0
    total_tokens: Optional[int] = None
    is_complete: bool = False
    error_message: Optional[str] = None
    

@dataclass
class RaceStatistics:
    """Statistical data across multiple race runs"""
    service_name: str
    ttft_times: List[float] = field(default_factory=list)
    total_times: List[float] = field(default_factory=list)
    token_counts: List[int] = field(default_factory=list)
    errors: int = 0
    
    def add_run(self, ttft_ms: float, total_ms: float, tokens: int):
        """Add data from a single run"""
        self.ttft_times.append(ttft_ms)
        self.total_times.append(total_ms)
        self.token_counts.append(tokens)
    
    def get_ttft_stats(self) -> Dict[str, float]:
        """Get TTFT statistical summary"""
        if not self.ttft_times:
            return {"mean": 0, "p50": 0, "p95": 0, "p99": 0, "min": 0, "max": 0}
        
        sorted_times = sorted(self.ttft_times)
        n = len(sorted_times)
        
        return {
            "mean": statistics.mean(sorted_times),
            "p50": sorted_times[int(n * 0.5)],
            "p95": sorted_times[int(n * 0.95)] if n >= 20 else sorted_times[-1],
            "p99": sorted_times[int(n * 0.99)] if n >= 100 else sorted_times[-1],
            "min": min(sorted_times),
            "max": max(sorted_times),
            "std": statistics.stdev(sorted_times) if n > 1 else 0
        }
    
    def get_success_rate(self, total_runs: int) -> float:
        """Get success rate percentage"""
        successful_runs = len(self.ttft_times)
        return (successful_runs / total_runs) * 100 if total_runs > 0 else 0


@dataclass
class ThreeWayRace:
    """State for three-way performance race demonstration"""
    race_id: str
    prompt: str
    start_time: float
    participants: Dict[str, RaceParticipant] = field(default_factory=dict)
    winner: Optional[str] = None
    race_complete: bool = False
    # Statistical tracking across multiple runs
    statistics: Dict[str, RaceStatistics] = field(default_factory=dict)
    current_run: int = 0
    total_runs: int = 1
    # Real API integration
    api_client: Optional[Any] = None
    use_real_apis: bool = False
    
    def add_participant(self, service_name: str, personality: ServicePersonality, engine_info: Optional[EngineInfo] = None):
        """Add a participant to the race"""
        # Use provided engine info or create default
        if engine_info is None:
            engine_info = self._create_engine_info(service_name)
        
        self.participants[service_name] = RaceParticipant(
            name=service_name,
            personality=personality,
            engine_info=engine_info
        )
        # Initialize statistics tracking
        self.statistics[service_name] = RaceStatistics(service_name=service_name)
    
    def _create_engine_info(self, service_name: str) -> EngineInfo:
        """Create realistic engine information for each service"""
        engine_configs = {
            "vllm": EngineInfo(
                engine_url="https://vllm-route.apps.cluster.com",
                model_name="Qwen/Qwen2.5-7B-Instruct",
                version="v0.5.4",
                gpu_type="NVIDIA H100",
                memory_gb=80,
                max_batch_size=64,
                max_context_length=8192,
                deployment="OpenShift Pod"
            ),
            "tgi": EngineInfo(
                engine_url="https://tgi-route.apps.cluster.com",
                model_name="Qwen/Qwen2.5-7B-Instruct",
                version="v2.0.1",
                gpu_type="NVIDIA A100",
                memory_gb=40,
                max_batch_size=32,
                max_context_length=4096,
                deployment="Kubernetes Pod"
            ),
            "ollama": EngineInfo(
                engine_url="https://ollama-route.apps.cluster.com",
                model_name="qwen2.5:7b-instruct",
                version="v0.3.6",
                gpu_type="NVIDIA RTX 4090",
                memory_gb=24,
                max_batch_size=16,
                max_context_length=4096,
                deployment="Docker Container"
            )
        }
        
        return engine_configs.get(service_name, EngineInfo())
    
    def reset_for_next_run(self):
        """Reset race state for the next iteration"""
        self.current_run += 1
        self.race_complete = False
        self.winner = None
        
        # Reset participant states
        for participant in self.participants.values():
            participant.response_start_time = None
            participant.first_token_time = None
            participant.current_response = ""
            participant.tokens_received = 0
            participant.total_tokens = None
            participant.is_complete = False
            participant.error_message = None
    
    def determine_winner(self) -> Optional[str]:
        """Determine the race winner based on first token time"""
        valid_participants = {
            name: participant for name, participant in self.participants.items()
            if participant.first_token_time is not None and participant.error_message is None
        }
        
        if not valid_participants:
            return None
        
        # Winner is whoever had the fastest first token
        winner_name = min(valid_participants.keys(), 
                         key=lambda x: valid_participants[x].first_token_time)
        
        self.winner = winner_name
        return winner_name
    
    def mark_response_start(self, service_name: str):
        """Mark when a service starts responding"""
        if service_name in self.participants:
            self.participants[service_name].response_start_time = time.time()
    
    def mark_first_token(self, service_name: str):
        """Mark when first token arrives"""
        if service_name in self.participants:
            participant = self.participants[service_name]
            participant.first_token_time = time.time()
    
    def add_token(self, service_name: str, token: str):
        """Add a token to service response"""
        if service_name in self.participants:
            participant = self.participants[service_name]
            participant.current_response += token
            participant.tokens_received += 1
    
    def mark_complete(self, service_name: str):
        """Mark service as complete"""
        if service_name in self.participants:
            self.participants[service_name].is_complete = True
            # Check if we have a winner (first to complete)
            if not self.winner:
                self.winner = service_name
    
    def get_ttft_rankings(self) -> List[tuple]:
        """Get TTFT rankings (service_name, ttft_ms)"""
        rankings = []
        for name, participant in self.participants.items():
            if participant.first_token_time:
                ttft_ms = (participant.first_token_time - self.start_time) * 1000
                rankings.append((name, ttft_ms))
        return sorted(rankings, key=lambda x: x[1])
    
    def is_race_complete(self) -> bool:
        """Check if all participants are done"""
        return all(p.is_complete for p in self.participants.values())

    def update_statistics(self):
        """Update statistics with data from current run"""
        for name, participant in self.participants.items():
            if participant.first_token_time and participant.response_start_time:
                ttft_ms = (participant.first_token_time - participant.response_start_time) * 1000
                total_ms = (time.time() - participant.response_start_time) * 1000
                tokens = participant.tokens_received
                
                self.statistics[name].add_run(ttft_ms, total_ms, tokens)
            else:
                # Count as an error
                self.statistics[name].errors += 1
