"""
StreamingSimulator - Token-by-token animation with service personalities.

This component simulates realistic streaming responses with word-to-token conversion,
service-specific typing speeds, and realistic response generation patterns.
"""

import asyncio
import time
import random
from typing import AsyncGenerator, Dict, List, Optional, Any
from dataclasses import dataclass

from ..conversation.models import ConversationMessage
from ..race.models import ServicePersonality


@dataclass
class ServiceTypingProfile:
    """Configuration for service typing behavior"""
    base_delay_ms: float  # Base delay per token in milliseconds
    personality: ServicePersonality
    variation: float  # Random variation factor (0.0-1.0)
    word_pause_multiplier: float  # Extra pause at word boundaries
    sentence_pause_multiplier: float  # Extra pause at sentence boundaries
    thinking_delay_ms: float  # Initial thinking delay before typing


class StreamingSimulator:
    """Simulator for realistic token-by-token streaming responses"""
    
    # Service-specific typing profiles matching original personalities
    TYPING_PROFILES = {
        "vllm": ServiceTypingProfile(
            base_delay_ms=30,  # Fast and professional
            personality=ServicePersonality.VLLM,
            variation=0.2,
            word_pause_multiplier=1.1,
            sentence_pause_multiplier=1.3,
            thinking_delay_ms=200
        ),
        "tgi": ServiceTypingProfile(
            base_delay_ms=50,  # Moderate technical speed
            personality=ServicePersonality.TGI,
            variation=0.3,
            word_pause_multiplier=1.3,
            sentence_pause_multiplier=1.5,
            thinking_delay_ms=400
        ),
        "ollama": ServiceTypingProfile(
            base_delay_ms=80,  # More deliberate and friendly
            personality=ServicePersonality.OLLAMA,
            variation=0.4,
            word_pause_multiplier=1.5,
            sentence_pause_multiplier=2.0,
            thinking_delay_ms=600
        )
    }
    
    def __init__(self):
        """Initialize the streaming simulator"""
        self.active_streams: Dict[str, Dict[str, Any]] = {}
    
    async def simulate_streaming_response(self, 
                                        message: ConversationMessage,
                                        response_text: str,
                                        service_name: str = "vllm") -> AsyncGenerator[str, None]:
        """Simulate realistic typing with word-to-token conversion
        
        Args:
            message: The original conversation message
            response_text: Full response text to stream
            service_name: Name of the service (for personality)
            
        Yields:
            Token chunks as they would be generated
        """
        profile = self.TYPING_PROFILES.get(service_name, self.TYPING_PROFILES["vllm"])
        
        # Initial thinking delay
        await asyncio.sleep(profile.thinking_delay_ms / 1000)
        
        # Convert text to realistic token chunks
        tokens = self._text_to_tokens(response_text)
        
        # Track streaming state
        stream_id = f"{service_name}_{id(message)}"
        self.active_streams[stream_id] = {
            "start_time": time.time(),
            "tokens_sent": 0,
            "total_tokens": len(tokens),
            "service": service_name
        }
        
        # Stream tokens with realistic delays
        current_text = ""
        for i, token in enumerate(tokens):
            # Calculate delay for this token
            delay = self._calculate_token_delay(token, i, tokens, profile)
            
            # Wait before sending token
            await asyncio.sleep(delay / 1000)  # Convert ms to seconds
            
            # Add token to current text
            current_text += token
            
            # Update stream state
            self.active_streams[stream_id]["tokens_sent"] = i + 1
            
            yield token
        
        # Clean up stream state
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]
    
    async def simulate_multi_service_streaming(self,
                                             message: ConversationMessage,
                                             service_responses: Dict[str, str]) -> Dict[str, AsyncGenerator[str, None]]:
        """Simulate streaming from multiple services simultaneously
        
        Args:
            message: The original conversation message
            service_responses: Dictionary of service_name -> response_text
            
        Returns:
            Dictionary of service_name -> async generator
        """
        generators = {}
        
        for service_name, response_text in service_responses.items():
            generators[service_name] = self.simulate_streaming_response(
                message, response_text, service_name
            )
        
        return generators
    
    def _text_to_tokens(self, text: str) -> List[str]:
        """Convert text to realistic token chunks
        
        Args:
            text: Full text to tokenize
            
        Returns:
            List of token strings
        """
        # Simple word-based tokenization with some subword splitting
        words = text.split()
        tokens = []
        
        for word in words:
            if len(word) <= 4:
                # Short words as single tokens
                tokens.append(word + " ")
            elif len(word) <= 8:
                # Medium words might split once
                if random.random() < 0.3:
                    mid = len(word) // 2
                    tokens.append(word[:mid])
                    tokens.append(word[mid:] + " ")
                else:
                    tokens.append(word + " ")
            else:
                # Long words split into multiple tokens
                chunk_size = random.randint(3, 6)
                for i in range(0, len(word), chunk_size):
                    chunk = word[i:i + chunk_size]
                    if i + chunk_size >= len(word):
                        chunk += " "  # Add space to last chunk
                    tokens.append(chunk)
        
        return tokens
    
    def _calculate_token_delay(self, token: str, position: int, all_tokens: List[str], profile: ServiceTypingProfile) -> float:
        """Calculate delay for a specific token
        
        Args:
            token: Current token
            position: Position in token sequence
            all_tokens: All tokens in sequence
            profile: Service typing profile
            
        Returns:
            Delay in milliseconds
        """
        base_delay = profile.base_delay_ms
        
        # Add random variation
        variation = random.uniform(-profile.variation, profile.variation)
        delay = base_delay * (1 + variation)
        
        # Word boundary pauses
        if token.endswith(" "):
            delay *= profile.word_pause_multiplier
        
        # Sentence boundary pauses
        if any(punct in token for punct in ".!?"):
            delay *= profile.sentence_pause_multiplier
        
        # Paragraph pauses
        if "\n" in token:
            delay *= 2.0
        
        # Slow down at beginning (thinking) and speed up towards end
        if position < 3:
            delay *= 1.5  # Slower start
        elif position > len(all_tokens) * 0.8:
            delay *= 0.8  # Faster finish
        
        return max(10, delay)  # Minimum 10ms delay
    
    def get_stream_status(self, service_name: str, message_id: Any) -> Optional[Dict[str, Any]]:
        """Get current status of a streaming operation
        
        Args:
            service_name: Name of the service
            message_id: ID of the message being streamed
            
        Returns:
            Stream status dictionary or None if not found
        """
        stream_id = f"{service_name}_{id(message_id)}"
        return self.active_streams.get(stream_id)
    
    def get_active_streams(self) -> Dict[str, Dict[str, Any]]:
        """Get all currently active streams
        
        Returns:
            Dictionary of stream_id -> status
        """
        return self.active_streams.copy()
    
    def stop_stream(self, service_name: str, message_id: Any):
        """Stop a streaming operation
        
        Args:
            service_name: Name of the service
            message_id: ID of the message being streamed
        """
        stream_id = f"{service_name}_{id(message_id)}"
        if stream_id in self.active_streams:
            del self.active_streams[stream_id]


class LiveStreamingOrchestrator:
    """Orchestrates live streaming across multiple services with visual updates"""
    
    def __init__(self, streaming_simulator: Optional[StreamingSimulator] = None):
        """Initialize the orchestrator
        
        Args:
            streaming_simulator: Streaming simulator instance
        """
        self.simulator = streaming_simulator or StreamingSimulator()
        self.active_conversations: Dict[str, Dict[str, Any]] = {}
    
    async def start_live_conversation_streaming(self,
                                              message: ConversationMessage,
                                              service_responses: Dict[str, str],
                                              update_callback: Optional[callable] = None) -> Dict[str, str]:
        """Start live streaming conversation with visual updates
        
        Args:
            message: Original conversation message
            service_responses: Dictionary of service -> response text
            update_callback: Optional callback for UI updates
            
        Returns:
            Dictionary of final responses
        """
        conversation_id = f"conv_{id(message)}"
        
        # Initialize conversation tracking
        self.active_conversations[conversation_id] = {
            "start_time": time.time(),
            "services": list(service_responses.keys()),
            "current_responses": {service: "" for service in service_responses.keys()},
            "completed_services": set(),
            "update_callback": update_callback
        }
        
        # Start streaming for all services
        tasks = []
        for service_name, response_text in service_responses.items():
            task = asyncio.create_task(
                self._stream_service_response(
                    conversation_id, service_name, message, response_text
                )
            )
            tasks.append(task)
        
        # Wait for all streaming to complete
        await asyncio.gather(*tasks)
        
        # Get final responses
        final_responses = self.active_conversations[conversation_id]["current_responses"]
        
        # Clean up
        del self.active_conversations[conversation_id]
        
        return final_responses
    
    async def _stream_service_response(self,
                                     conversation_id: str,
                                     service_name: str,
                                     message: ConversationMessage,
                                     response_text: str):
        """Stream response for a single service
        
        Args:
            conversation_id: ID of the conversation
            service_name: Name of the service
            message: Original message
            response_text: Full response text
        """
        current_response = ""
        
        async for token in self.simulator.simulate_streaming_response(message, response_text, service_name):
            current_response += token
            
            # Update conversation state
            self.active_conversations[conversation_id]["current_responses"][service_name] = current_response
            
            # Call update callback if provided
            update_callback = self.active_conversations[conversation_id].get("update_callback")
            if update_callback:
                await self._safe_callback(update_callback, conversation_id, service_name, current_response)
        
        # Mark service as completed
        self.active_conversations[conversation_id]["completed_services"].add(service_name)
    
    async def _safe_callback(self, callback: callable, *args):
        """Safely call update callback
        
        Args:
            callback: Callback function
            *args: Arguments to pass to callback
        """
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            # Log error but don't stop streaming
            print(f"Callback error: {e}")
    
    def get_conversation_status(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a conversation
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation status or None if not found
        """
        return self.active_conversations.get(conversation_id)
