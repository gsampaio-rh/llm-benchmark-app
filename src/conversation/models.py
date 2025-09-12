"""
Data models for conversation management.

This module contains all data structures related to managing conversations,
including messages, threads, and live conversation state.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ConversationMessage:
    """A single message in a conversation"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: float
    service_name: Optional[str] = None
    response_time_ms: Optional[float] = None
    token_count: Optional[int] = None
    streaming_tokens: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationThread:
    """A conversation thread with multiple exchanges"""
    thread_id: str
    title: str
    scenario: str
    messages: List[ConversationMessage] = field(default_factory=list)
    start_time: float = field(default_factory=time.time)
    user_persona: str = "User"
    
    def add_message(self, message: ConversationMessage):
        """Add a message to the conversation"""
        self.messages.append(message)
    
    def get_duration(self) -> float:
        """Get total conversation duration"""
        if not self.messages:
            return 0.0
        return self.messages[-1].timestamp - self.start_time
    
    def get_messages_by_service(self, service_name: str) -> List[ConversationMessage]:
        """Get all messages from a specific service"""
        return [msg for msg in self.messages if msg.service_name == service_name]
    
    def get_user_messages(self) -> List[ConversationMessage]:
        """Get all user messages"""
        return [msg for msg in self.messages if msg.role == "user"]
    
    def get_assistant_messages(self) -> List[ConversationMessage]:
        """Get all assistant messages"""
        return [msg for msg in self.messages if msg.role == "assistant"]
    
    def get_context_for_service(self, service_name: str, max_messages: int = 10) -> List[ConversationMessage]:
        """Get conversation context for a specific service, including user messages and previous responses"""
        # Get all user messages and responses from this service
        context_messages = []
        
        for msg in self.messages[-max_messages:]:
            if msg.role == "user" or msg.service_name == service_name:
                context_messages.append(msg)
        
        return context_messages


@dataclass
class LiveConversationState:
    """State for live conversation visualization"""
    active_threads: Dict[str, ConversationThread] = field(default_factory=dict)
    current_requests: Dict[str, Dict] = field(default_factory=dict)  # service -> request_info
    typing_states: Dict[str, bool] = field(default_factory=dict)  # service -> is_typing
    
    def start_typing(self, service_name: str):
        """Mark a service as typing"""
        self.typing_states[service_name] = True
    
    def stop_typing(self, service_name: str):
        """Mark a service as not typing"""
        self.typing_states[service_name] = False
    
    def is_typing(self, service_name: str) -> bool:
        """Check if a service is currently typing"""
        return self.typing_states.get(service_name, False)
    
    def add_request(self, service_name: str, request_info: Dict):
        """Track a new request for a service"""
        self.current_requests[service_name] = request_info
    
    def complete_request(self, service_name: str):
        """Mark a request as complete"""
        if service_name in self.current_requests:
            del self.current_requests[service_name]
        self.stop_typing(service_name)
    
    def get_active_requests(self) -> List[str]:
        """Get list of services with active requests"""
        return list(self.current_requests.keys())
