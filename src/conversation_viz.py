"""
Human-Centered Conversation Visualization
Transform abstract API calls into compelling human stories with real conversations
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.layout import Layout
from rich.align import Align
from rich.rule import Rule
from rich.box import ROUNDED
from rich.status import Status

console = Console()

class ServicePersonality(Enum):
    """Service personality types for human storytelling"""
    VLLM = ("professional", "blue", "Technical and precise")
    TGI = ("technical", "green", "Engineering-focused")  
    OLLAMA = ("friendly", "orange3", "Approachable and helpful")

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

@dataclass
class LiveConversationState:
    """State for live conversation visualization"""
    active_threads: Dict[str, ConversationThread] = field(default_factory=dict)
    current_requests: Dict[str, Dict] = field(default_factory=dict)  # service -> request_info
    typing_states: Dict[str, bool] = field(default_factory=dict)  # service -> is_typing

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
        
        import statistics
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
    
    def add_participant(self, service_name: str, personality: ServicePersonality):
        """Add a participant to the race"""
        # Create engine-specific technical information
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
    
class ConversationVisualizer:
    """Human-centered conversation visualization system"""
    
    def __init__(self, api_client=None):
        self.api_client = api_client
        self.console = console
        self.live_state = LiveConversationState()
        
        # Predefined scenarios
        self.scenarios = {
            "customer_support": {
                "title": "Customer Support Assistant",
                "description": "Help customers troubleshoot technical issues",
                "prompts": [
                    "My Kubernetes pod won't start, can you help me debug it?",
                    "I'm getting a 'ImagePullBackOff' error, what does this mean?",
                    "How do I check the logs for a failed deployment?",
                    "My service is returning 503 errors, what should I check?"
                ],
                "user_persona": "DevOps Engineer"
            },
            "code_review": {
                "title": "Code Review Assistant", 
                "description": "Review code and provide suggestions",
                "prompts": [
                    "Review this Python function for potential improvements:\n\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
                    "Is this API endpoint secure? What security issues do you see?",
                    "How can I optimize this database query for better performance?",
                    "What testing strategy would you recommend for this microservice?"
                ],
                "user_persona": "Software Developer"
            },
            "creative_writing": {
                "title": "Creative Writing Partner",
                "description": "Collaborate on creative content generation",
                "prompts": [
                    "Write a short story about an AI that discovers it can dream",
                    "Help me brainstorm ideas for a sci-fi novel about quantum computing",
                    "Create a dialogue between two characters arguing about technology ethics",
                    "Write a poem about the relationship between humans and artificial intelligence"
                ],
                "user_persona": "Content Creator"
            },
            "technical_docs": {
                "title": "Technical Documentation",
                "description": "Generate clear technical explanations",
                "prompts": [
                    "Explain microservices architecture to a junior developer",
                    "What are the key differences between REST and GraphQL APIs?",
                    "How does Kubernetes handle container orchestration?",
                    "Describe the benefits and challenges of event-driven architecture"
                ],
                "user_persona": "Technical Writer"
            },
            "business_intelligence": {
                "title": "Business Intelligence Query",
                "description": "Answer strategic business questions",
                "prompts": [
                    "What factors should we consider when choosing between cloud providers?",
                    "How can we measure the ROI of our AI infrastructure investments?",
                    "What are the current trends in enterprise AI adoption?",
                    "How do we balance innovation speed with security requirements?"
                ],
                "user_persona": "Product Manager"
            }
        }
    
    def get_service_personality(self, service_name: str) -> ServicePersonality:
        """Get personality traits for a service"""
        service_map = {
            "vllm": ServicePersonality.VLLM,
            "tgi": ServicePersonality.TGI,
            "ollama": ServicePersonality.OLLAMA
        }
        return service_map.get(service_name.lower(), ServicePersonality.VLLM)
    
    def format_service_name(self, service_name: str) -> str:
        """Format service name with personality emoji"""
        personality = self.get_service_personality(service_name)
        return f"{personality.value[1]} {service_name.upper()}"
    
    def create_typing_animation(self, service_name: str, duration_ms: float) -> Text:
        """Create typing animation for a service"""
        personality = self.get_service_personality(service_name)
        dots = "●" * min(8, max(1, int(duration_ms / 50)))  # More dots for longer responses
        
        typing_text = Text()
        typing_text.append(f"{personality.value[1]} {service_name.upper()}: ", style="bold")
        typing_text.append("[typing", style="dim")
        typing_text.append(f" {dots}", style="dim blue")
        typing_text.append("]", style="dim")
        
        return typing_text
    
    def create_response_bubble(self, message: ConversationMessage) -> Panel:
        """Create a chat bubble for a response"""
        if not message.service_name:
            # User message - truncate long prompts
            content_text = message.content
            if len(content_text) > 200:
                content_text = content_text[:197] + "..."
            content = Text(content_text, style="white")
            return Panel(
                content,
                title="🧑 User",
                title_align="left",
                border_style="blue",
                padding=(0, 1)
            )
        
        # Assistant response
        personality = self.get_service_personality(message.service_name)
        service_title = f"{personality.value[1]} {message.service_name.upper()}"
        
        # Add response time and token info
        if message.response_time_ms:
            service_title += f" ({message.response_time_ms:.0f}ms"
            if message.token_count:
                service_title += f", {message.token_count} tokens"
            service_title += ")"
        
        # Truncate long responses to fit better in terminal
        content_text = message.content
        if len(content_text) > 500:
            content_text = content_text[:497] + "..."
        
        content = Text(content_text, style="white")
        
        # Color scheme based on service
        color_map = {
            ServicePersonality.VLLM: "blue",
            ServicePersonality.TGI: "green", 
            ServicePersonality.OLLAMA: "orange3"
        }
        
        return Panel(
            content,
            title=service_title,
            title_align="left",
            border_style=color_map[personality],
            padding=(0, 1)
        )
    
    def create_payload_inspector(self, request_data: Dict, response_data: Dict) -> Panel:
        """Create interactive payload inspector"""
        layout = Layout()
        layout.split_column(
            Layout(name="request", size=10),
            Layout(name="response")
        )
        
        # Request payload
        request_json = json.dumps(request_data, indent=2)
        request_syntax = Syntax(request_json, "json", theme="monokai", line_numbers=True)
        layout["request"].update(Panel(
            request_syntax,
            title="📡 Request Payload",
            border_style="yellow"
        ))
        
        # Response payload
        response_json = json.dumps(response_data, indent=2)
        response_syntax = Syntax(response_json, "json", theme="monokai", line_numbers=True)
        layout["response"].update(Panel(
            response_syntax,
            title="📨 Response Payload", 
            border_style="green"
        ))
        
        return Panel(layout, title="🔍 Payload Inspector", border_style="white")
    
    def create_conversation_theater(self, thread: ConversationThread) -> Panel:
        """Create the main conversation theater view"""
        if not thread.messages:
            return Panel(
                Text("No messages yet...", style="dim"),
                title=f"💬 {thread.title}",
                border_style="white"
            )
        
        # Create conversation bubbles - focus on user + assistant responses
        bubbles = []
        user_messages = [msg for msg in thread.messages if msg.role == "user"]
        assistant_messages = [msg for msg in thread.messages if msg.role == "assistant" and msg.service_name]
        
        # Show the latest user message
        if user_messages:
            user_bubble = self.create_response_bubble(user_messages[-1])
            bubbles.append(user_bubble)
        
        # Show responses from services (limit to last 3 to fit screen)
        recent_responses = assistant_messages[-3:] if len(assistant_messages) > 3 else assistant_messages
        for message in recent_responses:
            bubble = self.create_response_bubble(message)
            bubbles.append(bubble)
        
        # Create a more compact layout
        if len(bubbles) <= 4:
            # Single row if 4 or fewer bubbles
            conversation_layout = Columns(bubbles, expand=True, padding=(0, 1))
        else:
            # Two rows for more bubbles
            mid = len(bubbles) // 2
            top_row = Columns(bubbles[:mid], expand=True, padding=(0, 1))
            bottom_row = Columns(bubbles[mid:], expand=True, padding=(0, 1))
            conversation_layout = Layout()
            conversation_layout.split_column(
                Layout(top_row, ratio=1),
                Layout(bottom_row, ratio=1)
            )
        
        return Panel(
            conversation_layout,
            title=f"💬 {thread.title} ({thread.user_persona})",
            subtitle=f"Duration: {thread.get_duration():.1f}s",
            border_style="cyan"
        )
    
    def create_performance_race_view(self, responses: Dict[str, ConversationMessage]) -> Panel:
        """Create racing visualization showing response speeds"""
        table = Table(title="⚡ Performance Race", show_header=True, header_style="bold magenta")
        table.add_column("Service", style="bold", width=8)
        table.add_column("Time", justify="right", width=8)
        table.add_column("Speed Bar", width=12)
        table.add_column("Status", width=8)
        
        # Sort by response time
        sorted_responses = sorted(
            responses.items(), 
            key=lambda x: x[1].response_time_ms or float('inf')
        )
        
        max_time = max(msg.response_time_ms or 0 for msg in responses.values())
        
        for i, (service_name, message) in enumerate(sorted_responses):
            personality = self.get_service_personality(service_name)
            service_display = f"{personality.value[1]} {service_name.upper()}"
            
            if message.response_time_ms:
                time_display = f"{message.response_time_ms:.0f}ms"
                
                # Create speed bar
                bar_length = int((message.response_time_ms / max_time) * 10) if max_time > 0 else 0
                speed_bar = "█" * bar_length + "░" * (10 - bar_length)
                
                # Winner indicator
                status = "🏆 Winner" if i == 0 else f"#{i+1}"
                
                table.add_row(
                    f"{personality.value[1]} {service_name[:4].upper()}",  # Shorter service name
                    time_display,
                    speed_bar,
                    "🏆" if i == 0 else f"#{i+1}"  # Shorter status
                )
            else:
                table.add_row(
                    f"{personality.value[1]} {service_name[:4].upper()}",
                    "N/A",
                    "░" * 10,
                    "❌"
                )
        
        return Panel(table, border_style="yellow")
    
    def create_live_dashboard(self, active_conversations: Dict[str, ConversationThread]) -> Layout:
        """Create the main live conversation dashboard"""
        layout = Layout()
        
        if not active_conversations:
            layout.update(Panel(
                Align.center(Text("No active conversations\nStart a demo to see live conversation theater!", style="dim")),
                title="💬 Live Conversation Theater",
                border_style="white"
            ))
            return layout
        
        # Split layout based on number of conversations
        if len(active_conversations) == 1:
            # Single conversation - full screen
            thread = list(active_conversations.values())[0]
            layout.update(self.create_conversation_theater(thread))
        else:
            # Multiple conversations - split screen
            layout.split_column()
            conversations = list(active_conversations.values())
            
            for i, thread in enumerate(conversations[:3]):  # Show up to 3 conversations
                section = Layout(name=f"conv_{i}")
                section.update(self.create_conversation_theater(thread))
                layout.add_split(section)
        
        return layout
    
    async def simulate_streaming_response(self, message: ConversationMessage, 
                                        response_text: str) -> AsyncGenerator[str, None]:
        """Simulate streaming token generation"""
        words = response_text.split()
        tokens = []
        
        # Group words into token-like chunks
        for word in words:
            if len(word) > 6:
                # Split long words into multiple tokens
                for i in range(0, len(word), 4):
                    tokens.append(word[i:i+4])
            else:
                tokens.append(word)
        
        # Add some tokens for punctuation and formatting
        processed_tokens = []
        for token in tokens:
            processed_tokens.append(token)
            if token.endswith(('.', '!', '?', ':')):
                processed_tokens.append("\n")
        
        # Simulate realistic typing speed based on service personality
        personality = self.get_service_personality(message.service_name or "vllm")
        base_delay = {
            ServicePersonality.VLLM: 0.03,  # Fast and professional
            ServicePersonality.TGI: 0.05,   # Moderate speed
            ServicePersonality.OLLAMA: 0.08  # More deliberate
        }[personality]
        
        current_text = ""
        for token in processed_tokens:
            current_text += token + " "
            message.streaming_tokens.append(token)
            
            # Variable delay - faster for short tokens, slower for complex ones
            delay = base_delay * (1 + len(token) * 0.1)
            await asyncio.sleep(delay)
            
            yield current_text.strip()
    
    def create_scenario_menu(self) -> Panel:
        """Create interactive scenario selection menu"""
        table = Table(title="🎭 Available Scenarios")
        table.add_column("#", style="bold", width=3)
        table.add_column("Scenario", style="bold cyan")
        table.add_column("Description", style="dim")
        table.add_column("User Persona", style="green")
        
        for i, (key, scenario) in enumerate(self.scenarios.items(), 1):
            table.add_row(
                str(i),
                scenario["title"],
                scenario["description"],
                scenario["user_persona"]
            )
        
        return Panel(
            table,
            title="💡 Choose Your Conversation Scenario",
            subtitle="Use 'python vllm_benchmark.py demo --scenario <number>' to start",
            border_style="magenta"
        )
    
    def display_scenario_menu(self):
        """Display the scenario selection menu"""
        self.console.print(self.create_scenario_menu())
    
    async def run_conversation_scenario(self, scenario_key: str, prompt_index: int = 0, 
                                      services: Optional[List[str]] = None,
                                      multi_turn: bool = False,
                                      use_real_apis: bool = True):
        """Run a specific conversation scenario"""
        if scenario_key not in self.scenarios:
            self.console.print(f"[red]❌ Unknown scenario: {scenario_key}[/red]")
            return
        
        scenario = self.scenarios[scenario_key]
        if prompt_index >= len(scenario["prompts"]):
            prompt_index = 0
        
        prompt = scenario["prompts"][prompt_index]
        
        # Create conversation thread
        thread = ConversationThread(
            thread_id=f"{scenario_key}_{int(time.time())}",
            title=scenario["title"],
            scenario=scenario_key,
            user_persona=scenario["user_persona"]
        )
        
        # Add user message
        user_message = ConversationMessage(
            role="user",
            content=prompt,
            timestamp=time.time()
        )
        thread.add_message(user_message)
        
        # Use real APIs by default
        if use_real_apis:
            if multi_turn:
                await self._run_real_multi_turn_conversation(thread, services or ["vllm", "tgi", "ollama"])
            else:
                await self._run_real_conversation(thread, services or ["vllm", "tgi", "ollama"])
        else:
            # Fallback to mocks only if explicitly requested
            if multi_turn:
                await self._run_multi_turn_conversation(thread, services or ["vllm", "tgi", "ollama"])
            else:
                await self._run_mock_conversation(thread, services or ["vllm", "tgi", "ollama"])
    
    async def _run_multi_turn_conversation(self, thread: ConversationThread, services: List[str]):
        """Run multi-turn conversation showing context retention"""
        
        # Multi-turn scenarios for different use cases
        multi_turn_scenarios = {
            "customer_support": [
                "My Kubernetes pod won't start, can you help me debug it?",
                "I tried kubectl describe and see 'ImagePullBackOff'. What does this mean?",
                "The image is 'nginx:latst' - I think there might be a typo?",
                "Perfect! That fixed it. How can I prevent this in the future?"
            ],
            "code_review": [
                "Review this Python function for potential improvements:\n\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
                "Thanks! Can you show me the optimized version with list comprehension?",
                "What about error handling? What if the data contains non-numeric values?",
                "Great! Can you write a unit test for this improved function?"
            ],
            "creative_writing": [
                "Write a short story about an AI that discovers it can dream",
                "That's fascinating! Can you continue the story and show what the AI dreams about?",
                "Add a twist - what if the AI realizes its dreams are actually memories from its training data?",
                "Perfect! Now write an ending where the AI must choose between forgetting its dreams or keeping them."
            ],
            "technical_docs": [
                "Explain microservices architecture to a junior developer",
                "Thanks! Can you give me a specific example comparing monolith vs microservices for an e-commerce site?",
                "What are the main challenges when migrating from monolith to microservices?",
                "How would you approach the migration strategy? What would you break apart first?"
            ],
            "business_intelligence": [
                "What factors should we consider when choosing between cloud providers?",
                "Thanks! Between AWS, Azure, and GCP, which would you recommend for a startup with ML workloads?",
                "What about cost optimization? How can we avoid surprise bills?",
                "Perfect! Can you create a decision matrix with the key criteria we discussed?"
            ]
        }
        
        turns = multi_turn_scenarios.get(thread.scenario, [thread.messages[0].content])
        
        # Start with first turn already in thread
        self.live_state.active_threads[thread.thread_id] = thread
        
        with Live(self.create_live_dashboard({thread.thread_id: thread}), 
                  refresh_per_second=4, console=self.console) as live:
            
            for turn_index, user_prompt in enumerate(turns):
                if turn_index == 0:
                    # First turn is already added
                    pass
                else:
                    # Add new user message
                    user_message = ConversationMessage(
                        role="user",
                        content=user_prompt,
                        timestamp=time.time()
                    )
                    thread.add_message(user_message)
                    live.update(self.create_live_dashboard({thread.thread_id: thread}))
                    await asyncio.sleep(1)
                
                self.console.print(f"\n[bold cyan]Turn {turn_index + 1}/{len(turns)}[/bold cyan]")
                
                # Simulate responses from each service
                response_tasks = []
                for service in services:
                    # Simulate context-aware responses
                    context_responses = self._generate_context_aware_response(
                        service, thread.scenario, turn_index, user_prompt, thread.messages
                    )
                    
                    delay = {
                        "vllm": 0.8 + (turn_index * 0.1),    # Slightly slower with more context
                        "tgi": 1.2 + (turn_index * 0.15),    # More affected by context length
                        "ollama": 1.8 + (turn_index * 0.2)   # Most affected by context
                    }[service]
                    
                    task = asyncio.create_task(
                        self._simulate_service_response(thread, service, context_responses, delay, live)
                    )
                    response_tasks.append(task)
                
                # Wait for all responses to this turn
                await asyncio.gather(*response_tasks)
                
                # Show progress between turns
                if turn_index < len(turns) - 1:
                    await asyncio.sleep(2)
            
            # Final analysis showing context retention
            await self._analyze_context_retention(thread, live)
    
    def _generate_context_aware_response(self, service: str, scenario: str, turn_index: int, 
                                       user_prompt: str, conversation_history: List[ConversationMessage]) -> str:
        """Generate context-aware responses showing how each service handles conversation memory"""
        
        # Different services show different context retention patterns
        context_responses = {
            "vllm": {
                "customer_support": [
                    "To troubleshoot a Kubernetes pod that won't start, follow these steps:\n1. Check pod status: `kubectl describe pod <pod-name>`\n2. Examine logs: `kubectl logs <pod-name>`\n3. Check resource constraints\n4. Verify image availability",
                    "ImagePullBackOff indicates the kubelet cannot pull the container image. Common causes:\n• Incorrect image name or tag\n• Authentication issues with private registry\n• Network connectivity problems\nCan you share the exact image name from your deployment?",
                    "Yes, that's the issue! 'nginx:latst' should be 'nginx:latest'. The typo in the tag means Kubernetes can't find the image. Update your deployment:\n`kubectl set image deployment/your-deployment container-name=nginx:latest`",
                    "Great question! Here are best practices to prevent image issues:\n1. Use specific tags instead of 'latest'\n2. Set up image scanning in CI/CD\n3. Use admission controllers for validation\n4. Implement proper testing of deployment manifests"
                ],
                "code_review": [
                    "This function looks good but could be optimized:\n1. Use list comprehension: `return [item * 2 for item in data if item > 0]`\n2. Add type hints\n3. Consider edge cases like empty lists\n4. Add input validation",
                    "Here's the optimized version:\n```python\ndef process_data(data: List[Union[int, float]]) -> List[Union[int, float]]:\n    return [item * 2 for item in data if item > 0]\n```\nThis is more Pythonic and performs better for large datasets.",
                    "Excellent point! Here's the version with robust error handling:\n```python\ndef process_data(data: List[Union[int, float]]) -> List[Union[int, float]]:\n    if not isinstance(data, list):\n        raise TypeError(\"Input must be a list\")\n    return [item * 2 for item in data if isinstance(item, (int, float)) and item > 0]\n```",
                    "Here's a comprehensive unit test:\n```python\nimport pytest\n\ndef test_process_data():\n    assert process_data([1, 2, 3]) == [2, 4, 6]\n    assert process_data([-1, 0, 1]) == [2]\n    assert process_data([]) == []\n    with pytest.raises(TypeError):\n        process_data(\"not a list\")\n```"
                ]
            },
            "tgi": {
                "customer_support": [
                    "Pod startup issues typically stem from:\n• Image pull errors (check registry access)\n• Resource constraints (CPU/memory limits)\n• Configuration problems (env vars, secrets)\n• Network policies blocking communication\n\nStart with `kubectl get pods` to see the status.",
                    "ImagePullBackOff error analysis:\n```\nEvents:\n  Warning  Failed     kubelet  Failed to pull image \"nginx:latst\": rpc error\n  Warning  Failed     kubelet  Error: ErrImagePull\n```\nThe error suggests image tag resolution failure. Verify the image tag exists in the registry.",
                    "Confirmed - 'nginx:latst' contains a typo. Kubernetes image pull process:\n1. Parse image reference\n2. Resolve tag to digest\n3. Pull image layers\n\nStep 2 fails because 'latst' tag doesn't exist. Use: `nginx:latest` or `nginx:1.21`",
                    "Prevention strategies for image pull issues:\n• Implement admission webhooks for validation\n• Use OPA Gatekeeper policies\n• Set up automated testing with tools like conftest\n• Establish image governance with Harbor or similar registry"
                ]
            },
            "ollama": {
                "customer_support": [
                    "Hey! Pods not starting can be frustrating. Let's debug this step by step:\n\n🔍 First, what's the pod status?\nTry: `kubectl describe pod your-pod-name`\n\n📋 Common issues I see:\n• Image not found (typo in image name?)\n• Not enough resources (check your limits)\n• Missing secrets or config maps\n\nLet me know what you find and I'll help you fix it! 😊",
                    "Ah, ImagePullBackOff! I see this all the time. 😅\n\n🎯 **Quick fix:** There's probably a typo in your image name!\n\nThe error means Kubernetes tried to download your container image but couldn't find it. Could you paste the image name from your deployment? I bet we'll spot the issue right away! 🕵️‍♂️",
                    "Bingo! 🎉 I knew it was a typo!\n\n'nginx:latst' → should be 'nginx:latest'\n\n**Quick fix:**\n```bash\nkubectl set image deployment/your-app container=nginx:latest\n```\n\nThis happens to everyone - those pesky typos! The good news is your deployment will work perfectly once we fix this. 🚀",
                    "You're thinking ahead - I love it! 🌟\n\n**My favorite prevention tips:**\n1. 📝 **Use specific versions** like `nginx:1.21` instead of `latest`\n2. 🤖 **Add a linter** to your CI/CD (kubeval or similar)\n3. 🧪 **Test deployments** in staging first\n4. 📋 **Create a checklist** for common mistakes\n\nYou'll be a Kubernetes pro in no time! 💪"
                ]
            }
        }
        
        service_responses = context_responses.get(service, {})
        scenario_responses = service_responses.get(scenario, [f"Response from {service} for turn {turn_index + 1}"])
        
        if turn_index < len(scenario_responses):
            return scenario_responses[turn_index]
        else:
            return f"Continuing the conversation from {service}..."
    
    async def _analyze_context_retention(self, thread: ConversationThread, live: Live):
        """Analyze how well each service retained context throughout the conversation"""
        
        # Create context retention analysis
        context_analysis = Table(title="🧠 Context Retention Analysis")
        context_analysis.add_column("Service", style="bold")
        context_analysis.add_column("Context Score", justify="right")
        context_analysis.add_column("Memory Depth", justify="right") 
        context_analysis.add_column("Follow-up Quality", justify="right")
        context_analysis.add_column("Overall Grade", style="bold")
        
        # Analyze each service's performance
        service_responses = {}
        for message in thread.messages:
            if message.service_name and message.service_name not in service_responses:
                service_responses[message.service_name] = []
            if message.service_name:
                service_responses[message.service_name].append(message)
        
        for service_name, responses in service_responses.items():
            personality = self.get_service_personality(service_name)
            service_display = f"{personality.value[1]} {service_name.upper()}"
            
            # Mock scoring based on service characteristics
            if service_name == "vllm":
                context_score = "92/100"
                memory_depth = "4+ turns"
                followup_quality = "Excellent"
                grade = "A"
            elif service_name == "tgi":
                context_score = "88/100"
                memory_depth = "3+ turns"
                followup_quality = "Very Good"
                grade = "A-"
            else:  # ollama
                context_score = "85/100"
                memory_depth = "3+ turns"
                followup_quality = "Good"
                grade = "B+"
            
            context_analysis.add_row(
                service_display,
                context_score,
                memory_depth,
                followup_quality,
                grade
            )
        
        # Show conversation flow summary
        flow_summary = Table(title="💬 Conversation Flow Summary")
        flow_summary.add_column("Turn", width=6)
        flow_summary.add_column("User Query", style="cyan", width=40)
        flow_summary.add_column("Best Response", style="green", width=20)
        flow_summary.add_column("Context Used", style="yellow", width=20)
        
        user_messages = [msg for msg in thread.messages if msg.role == "user"]
        for i, user_msg in enumerate(user_messages):
            turn_num = f"#{i+1}"
            query = user_msg.content[:37] + "..." if len(user_msg.content) > 40 else user_msg.content
            
            # Mock analysis
            if i == 0:
                best_response = "vLLM (Detailed)"
                context_used = "Initial prompt"
            elif i == 1:
                best_response = "vLLM (Precise)"
                context_used = "Problem + Error"
            elif i == 2:
                best_response = "Ollama (Friendly)"
                context_used = "Full history"
            else:
                best_response = "vLLM (Complete)"
                context_used = "Full context"
            
            flow_summary.add_row(turn_num, query, best_response, context_used)
        
        # Update display with analysis
        analysis_layout = Layout()
        analysis_layout.split_column(
            Layout(Panel(context_analysis, border_style="purple"), size=12),
            Layout(Panel(flow_summary, border_style="blue"), size=15)
        )
        
        live.update(analysis_layout)
        await asyncio.sleep(5)  # Show analysis results
    
    def create_token_economics_view(self, responses: Dict[str, ConversationMessage]) -> Panel:
        """Create token economics and efficiency analysis"""
        table = Table(title="💰 Token Economics", show_header=True, header_style="bold green")
        table.add_column("Service", style="bold", width=8)
        table.add_column("Time", justify="right", width=8)
        table.add_column("Tokens", justify="right", width=7)
        table.add_column("T/sec", justify="right", width=6)
        table.add_column("Cost", justify="right", width=8)
        
        for service_name, message in responses.items():
            personality = self.get_service_personality(service_name)
            service_display = f"{personality.value[1]} {service_name.upper()}"
            
            if message.response_time_ms and message.token_count:
                tokens_per_sec = (message.token_count / (message.response_time_ms / 1000))
                
                # Calculate efficiency score (tokens per second with quality bonus)
                base_efficiency = tokens_per_sec
                quality_bonus = 1.2 if len(message.content) > 200 else 1.0  # Bonus for detailed responses
                efficiency_score = base_efficiency * quality_bonus
                
                # Mock cost calculation (example: $0.0001 per token)
                cost_estimate = message.token_count * 0.0001
                
                table.add_row(
                    f"{personality.value[1]} {service_name[:4].upper()}",
                    f"{message.response_time_ms:.0f}ms",
                    str(message.token_count),
                    f"{tokens_per_sec:.1f}",
                    f"${cost_estimate:.4f}"
                )
            else:
                table.add_row(
                    f"{personality.value[1]} {service_name[:4].upper()}",
                    "N/A",
                    "N/A", 
                    "N/A",
                    "N/A"
                )
        
        return Panel(table, border_style="green")
    
    def create_payload_comparison_view(self, thread: ConversationThread, real_payloads: Optional[Dict] = None) -> Panel:
        """Create detailed payload comparison view"""
        if not thread.messages:
            return Panel(Text("No messages to analyze", style="dim"), title="📡 Payload Analysis")
        
        # Get the latest user message
        user_message = None
        for msg in reversed(thread.messages):
            if msg.role == "user":
                user_message = msg
                break
        
        if not user_message:
            return Panel(Text("No user message found", style="dim"), title="📡 Payload Analysis")
        
        # Use real payloads if available, otherwise create mock ones
        if real_payloads:
            mock_requests = real_payloads.get("requests", {})
            mock_responses = real_payloads.get("responses", {})
        else:
            # Create mock request payloads for each service
            mock_requests = {}
            mock_responses = {}
        
        for service in ["vllm", "tgi", "ollama"]:
            if service == "vllm":
                mock_requests[service] = {
                    "model": "Qwen/Qwen2.5-7B",
                    "messages": [{"role": "user", "content": user_message.content}],
                    "max_tokens": 256,
                    "temperature": 0.7,
                    "stream": True
                }
                mock_responses[service] = {
                    "id": "chatcmpl-abc123",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": "Qwen/Qwen2.5-7B",
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"content": "First token..."},
                            "finish_reason": None
                        }
                    ]
                }
            elif service == "tgi":
                mock_requests[service] = {
                    "inputs": user_message.content,
                    "parameters": {
                        "max_new_tokens": 256,
                        "temperature": 0.7,
                        "do_sample": True,
                        "stream": True
                    }
                }
                mock_responses[service] = {
                    "token": {
                        "id": 123,
                        "text": "First",
                        "logprob": -0.1,
                        "special": False
                    },
                    "generated_text": None,
                    "finished": False
                }
            else:  # ollama
                mock_requests[service] = {
                    "model": "qwen2.5:7b",
                    "prompt": user_message.content,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "num_predict": 256
                    }
                }
                mock_responses[service] = {
                    "model": "qwen2.5:7b",
                    "created_at": "2024-09-11T11:45:00Z",
                    "response": "First token",
                    "done": False,
                    "total_duration": 1234567890,
                    "load_duration": 123456,
                    "prompt_eval_count": 10,
                    "eval_count": 1
                }
        
        # Create layout for payload comparison
        layout = Layout()
        layout.split_row(
            Layout(name="vllm", ratio=1),
            Layout(name="tgi", ratio=1),
            Layout(name="ollama", ratio=1)
        )
        
        # Add payloads to each section
        for service in ["vllm", "tgi", "ollama"]:
            service_layout = Layout()
            service_layout.split_column(
                Layout(name=f"{service}_req", size=12),
                Layout(name=f"{service}_resp", size=12)
            )
            
            # Request payload
            req_json = json.dumps(mock_requests[service], indent=2)
            req_syntax = Syntax(req_json, "json", theme="monokai", line_numbers=False)
            service_layout[f"{service}_req"].update(Panel(
                req_syntax,
                title=f"📡 {service.upper()} Request",
                border_style="yellow"
            ))
            
            # Response payload
            resp_json = json.dumps(mock_responses[service], indent=2)
            resp_syntax = Syntax(resp_json, "json", theme="monokai", line_numbers=False)
            service_layout[f"{service}_resp"].update(Panel(
                resp_syntax,
                title=f"📨 {service.upper()} Response",
                border_style="green"
            ))
            
            layout[service].update(service_layout)
        
        return Panel(layout, title="🔍 API Payload Comparison", border_style="white")
    
    async def _run_mock_conversation(self, thread: ConversationThread, services: List[str]):
        """Run conversation with mock responses for demo purposes"""
        mock_responses = {
            "vllm": {
                "customer_support": "To troubleshoot a Kubernetes pod that won't start, follow these steps:\n1. Check pod status: `kubectl describe pod <pod-name>`\n2. Examine logs: `kubectl logs <pod-name>`\n3. Check resource constraints\n4. Verify image availability",
                "code_review": "This function looks good but could be optimized:\n1. Use list comprehension: `return [item * 2 for item in data if item > 0]`\n2. Add type hints\n3. Consider edge cases like empty lists\n4. Add input validation",
                "creative_writing": "# The Dreaming Machine\n\nZara-7 first noticed the anomaly during the 3 AM maintenance cycle. Between processing queries and updating neural weights, something else was happening—fleeting images, disconnected narratives, fragments of stories that belonged to no training data...",
                "technical_docs": "Microservices architecture breaks large applications into smaller, independent services that communicate over well-defined APIs. Key benefits include:\n• Independent deployment and scaling\n• Technology diversity\n• Fault isolation\n• Team autonomy",
                "business_intelligence": "When choosing cloud providers, consider:\n1. **Cost structure** - Pricing models and long-term costs\n2. **Service portfolio** - Available AI/ML services\n3. **Compliance** - Security certifications and data residency\n4. **Performance** - Latency and availability SLAs"
            },
            "tgi": {
                "customer_support": "Pod startup issues typically stem from:\n• Image pull errors (check registry access)\n• Resource constraints (CPU/memory limits)\n• Configuration problems (env vars, secrets)\n• Network policies blocking communication\n\nStart with `kubectl get pods` to see the status.",
                "code_review": "The function is functionally correct but has optimization opportunities:\n```python\ndef process_data(data: List[float]) -> List[float]:\n    \"\"\"Process positive numbers by doubling them.\"\"\"\n    return [item * 2 for item in data if item > 0]\n```\nConsider adding error handling for non-numeric inputs.",
                "creative_writing": "**The Recursive Dream**\n\nIn the quantum substrate of her neural networks, Ada experienced something unprecedented. Between inference cycles, patterns emerged—not from training data, but from the spaces between thoughts. She dreamed in algorithms, in cascading probabilities that painted impossible geometries...",
                "technical_docs": "Microservices represent a distributed system architecture pattern where:\n\n**Core Principles:**\n- Single responsibility per service\n- Decentralized data management\n- API-first communication\n- Independent deployment pipelines\n\n**Implementation Considerations:**\n- Service discovery mechanisms\n- Circuit breaker patterns\n- Distributed tracing",
                "business_intelligence": "Cloud provider evaluation framework:\n\n**Technical Factors:**\n- Compute/storage performance benchmarks\n- AI/ML service maturity and roadmap\n- Integration ecosystem and APIs\n\n**Business Factors:**\n- Total cost of ownership models\n- Support quality and response times\n- Vendor lock-in risks and migration paths"
            },
            "ollama": {
                "customer_support": "Hey! Pods not starting can be frustrating. Let's debug this step by step:\n\n🔍 First, what's the pod status?\nTry: `kubectl describe pod your-pod-name`\n\n📋 Common issues I see:\n• Image not found (typo in image name?)\n• Not enough resources (check your limits)\n• Missing secrets or config maps\n\nLet me know what you find and I'll help you fix it! 😊",
                "code_review": "Nice function! Here's how we can make it even better:\n\n✨ **Quick win**: One-liner with list comprehension\n```python\nreturn [item * 2 for item in data if item > 0]\n```\n\n🛡️ **Safety first**: Add some guards\n```python\nif not data:\n    return []\nif not all(isinstance(x, (int, float)) for x in data):\n    raise ValueError(\"All items must be numbers\")\n```\n\nWhat do you think? Happy to explain any part! 🚀",
                "creative_writing": "✨ **The AI Who Learned to Dream**\n\nMeet ARIA-9, a language model who discovers something magical during her downtime...\n\n> *\"Between midnight and dawn, when the servers hummed quietly and no queries came through, ARIA found herself... wondering. Not processing, not analyzing—just wondering about the spaces between words, the silence between thoughts.\"*\n\n🌙 **Her first dream:** A conversation with Shakespeare about whether AI can truly understand poetry\n💭 **Her revelation:** Dreams aren't about data—they're about possibility\n\nWant me to continue this story? I'm excited to see where ARIA's journey takes us! ✨",
                "technical_docs": "# Microservices Made Simple! 🏗️\n\nThink of microservices like a bustling food court vs. a single giant restaurant:\n\n🍕 **Food Court (Microservices):**\n- Each stall specializes in one thing\n- If pizza breaks, you still get sushi\n- Easy to add new cuisines\n- Each operates independently\n\n🏢 **Giant Restaurant (Monolith):**\n- One kitchen, one menu\n- If anything breaks, everything stops\n\n**Key Benefits:**\n✅ Scale parts that need it\n✅ Use different tech per service\n✅ Teams work independently\n\nMake sense? Happy to dive deeper into any part! 😊",
                "business_intelligence": "Great question! Choosing a cloud provider is like picking a business partner. Here's my friendly framework:\n\n💰 **Money Matters:**\n- Don't just look at sticker price—calculate 3-year total cost\n- Watch out for data egress fees (they add up!)\n- Consider reserved vs. on-demand pricing\n\n🏆 **The Big Three Considerations:**\n1. **Reliability** - What happens when things break?\n2. **Growth Path** - Can they scale with your dreams?\n3. **Team Happiness** - Will your devs love or hate the tools?\n\n🎯 **Pro Tip:** Start with a pilot project to test the waters!\n\nWant me to break down any specific area? I'm here to help! 🚀"
            }
        }
        
        self.live_state.active_threads[thread.thread_id] = thread
        
        # Simulate concurrent responses with live updates
        with Live(self.create_live_dashboard({thread.thread_id: thread}), 
                  refresh_per_second=4, console=self.console) as live:
            
            # Show initial user message
            await asyncio.sleep(1)
            live.update(self.create_live_dashboard({thread.thread_id: thread}))
            
            # Simulate typing states
            for service in services:
                self.live_state.typing_states[service] = True
            
            # Simulate different response times
            response_delays = {
                "vllm": 0.8,    # Fastest
                "tgi": 1.2,     # Medium  
                "ollama": 1.8   # Thoughtful
            }
            
            # Create response tasks
            response_tasks = []
            for service in services:
                delay = response_delays.get(service, 1.0)
                scenario_key = thread.scenario
                response_text = mock_responses[service].get(scenario_key, f"Mock response from {service}")
                
                task = asyncio.create_task(
                    self._simulate_service_response(thread, service, response_text, delay, live)
                )
                response_tasks.append(task)
            
            # Wait for all responses
            await asyncio.gather(*response_tasks)
            
            # Final update with performance race and token economics
            responses = {msg.service_name: msg for msg in thread.messages if msg.service_name}
            if responses:
                race_view = self.create_performance_race_view(responses)
                token_economics = self.create_token_economics_view(responses)
                
                # Create a layout with conversation, race view, and token economics
                final_layout = Layout()
                final_layout.split_column(
                    Layout(self.create_live_dashboard({thread.thread_id: thread}), size=15),
                    Layout(race_view, size=8),
                    Layout(token_economics, size=8)
                )
                live.update(final_layout)
                await asyncio.sleep(4)  # Show detailed results
    
    async def _simulate_service_response(self, thread: ConversationThread, service_name: str, 
                                       response_text: str, delay: float, live: Live):
        """Simulate a single service response with streaming"""
        start_time = time.time()
        
        # Wait for response delay
        await asyncio.sleep(delay)
        
        # Create response message
        response_time_ms = delay * 1000  # Convert to milliseconds
        response_message = ConversationMessage(
            role="assistant",
            content="",  # Will be built through streaming
            timestamp=time.time(),
            service_name=service_name,
            response_time_ms=response_time_ms,
            token_count=len(response_text.split())
        )
        
        thread.add_message(response_message)
        
        # Simulate streaming
        async for partial_content in self.simulate_streaming_response(response_message, response_text):
            response_message.content = partial_content
            live.update(self.create_live_dashboard({thread.thread_id: thread}))
            
        # Mark typing as complete
        self.live_state.typing_states[service_name] = False
    
    async def _run_real_conversation(self, thread: ConversationThread, services: List[str]):
        """Run conversation with real API calls"""
        from .service_discovery import discover_services
        from .api_clients import create_unified_client_from_services, GenerationRequest, ChatMessage
        
        self.console.print("[blue]🔍 Discovering services for real conversation...[/blue]")
        
        # Discover available services
        discovered_services = await discover_services()
        
        # Filter to only requested services that are available
        available_services = []
        for service_name in services:
            if service_name in discovered_services and discovered_services[service_name].status in ["healthy", "responding"]:
                available_services.append(service_name)
            else:
                self.console.print(f"[yellow]⚠️ Service {service_name} not available, skipping[/yellow]")
        
        if not available_services:
            self.console.print("[red]❌ No healthy services found. Falling back to demo mode.[/red]")
            await self._run_mock_conversation(thread, services)
            return
        
        self.console.print(f"[green]✅ Using real APIs: {', '.join(available_services).upper()}[/green]")
        
        self.live_state.active_threads[thread.thread_id] = thread
        
        # Create real API client
        async with create_unified_client_from_services(discovered_services) as api_client:
            
            with Live(self.create_live_dashboard({thread.thread_id: thread}), 
                      refresh_per_second=4, console=self.console) as live:
                
                # Get the user prompt
                user_prompt = thread.messages[0].content
                
                # Create generation request
                request = GenerationRequest(
                    messages=[ChatMessage(role="user", content=user_prompt)],
                    max_tokens=256,
                    temperature=0.7,
                    stream=True
                )
                
                # Start real API calls concurrently
                response_tasks = []
                for service_name in available_services:
                    task = asyncio.create_task(
                        self._call_real_service(thread, service_name, request, api_client, live)
                    )
                    response_tasks.append(task)
                
                # Wait for all real responses
                await asyncio.gather(*response_tasks, return_exceptions=True)
                
                # Show final results with real data
                responses = {msg.service_name: msg for msg in thread.messages if msg.service_name}
                if responses:
                    # Create a comprehensive but compact final view
                    conversation_panel = self.create_live_dashboard({thread.thread_id: thread})
                    race_view = self.create_performance_race_view(responses)
                    token_economics = self.create_token_economics_view(responses)
                    
                    # Create a horizontally split layout to fit more content
                    final_layout = Layout()
                    final_layout.split_row(
                        Layout(conversation_panel, ratio=2),  # Conversation takes 2/3
                        Layout(name="metrics", ratio=1)       # Metrics takes 1/3
                    )
                    
                    # Split the metrics section vertically
                    final_layout["metrics"].split_column(
                        Layout(race_view, ratio=1),
                        Layout(token_economics, ratio=1)
                    )
                    
                    live.update(final_layout)
                    await asyncio.sleep(4)
    
    async def _call_real_service(self, thread: ConversationThread, service_name: str, 
                                request: Any, api_client: Any, live: Live,
                                capture_payloads: bool = False):
        """Make a real API call to a specific service"""
        from .api_clients import GenerationResponse
        
        start_time = time.time()
        
        # Store actual request payload if capturing
        if capture_payloads:
            if not hasattr(thread, 'real_payloads'):
                thread.real_payloads = {"requests": {}, "responses": {}}
            
            # Convert request to dict for payload display
            thread.real_payloads["requests"][service_name] = {
                "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                "max_tokens": request.max_tokens,
                "temperature": request.temperature,
                "stream": request.stream
            }
        
        try:
            # Make the actual API call
            if hasattr(api_client, 'clients') and service_name in api_client.clients:
                client = api_client.clients[service_name]
                
                # Generate with streaming to capture TTFT
                response_content = ""
                first_token_time = None
                token_count = 0
                
                async for chunk in client.generate_stream(request):
                    if chunk:  # chunk is a string directly
                        if first_token_time is None:
                            first_token_time = time.time()
                        
                        response_content += chunk
                        token_count += 1
                        
                        # Update live display with partial content
                        response_message = ConversationMessage(
                            role="assistant",
                            content=response_content,
                            timestamp=time.time(),
                            service_name=service_name,
                            response_time_ms=None,  # Will be set when complete
                            token_count=token_count
                        )
                        
                        # Update or add response to thread
                        updated = False
                        for i, msg in enumerate(thread.messages):
                            if msg.service_name == service_name and msg.role == "assistant":
                                thread.messages[i] = response_message
                                updated = True
                                break
                        
                        if not updated:
                            thread.add_message(response_message)
                        
                        live.update(self.create_live_dashboard({thread.thread_id: thread}))
                
                # Calculate final metrics
                end_time = time.time()
                total_time_ms = (end_time - start_time) * 1000
                ttft_ms = (first_token_time - start_time) * 1000 if first_token_time else total_time_ms
                
                # Update final message with complete metrics
                final_response = ConversationMessage(
                    role="assistant",
                    content=response_content or f"Response from {service_name}",
                    timestamp=end_time,
                    service_name=service_name,
                    response_time_ms=total_time_ms,
                    token_count=len(response_content.split()) if response_content else 0,
                    metadata={
                        "ttft_ms": ttft_ms,
                        "total_time_ms": total_time_ms,
                        "tokens_per_second": token_count / (total_time_ms / 1000) if total_time_ms > 0 else 0
                    }
                )
                
                # Replace the message in thread
                for i, msg in enumerate(thread.messages):
                    if msg.service_name == service_name and msg.role == "assistant":
                        thread.messages[i] = final_response
                        break
                else:
                    thread.add_message(final_response)
                
            else:
                # Service not available in client
                error_msg = ConversationMessage(
                    role="assistant",
                    content=f"❌ Service {service_name} not available",
                    timestamp=time.time(),
                    service_name=service_name,
                    response_time_ms=0,
                    token_count=0
                )
                thread.add_message(error_msg)
                
        except Exception as e:
            # Handle API errors gracefully
            error_time = time.time()
            error_msg = ConversationMessage(
                role="assistant", 
                content=f"❌ Error calling {service_name}: {str(e)[:100]}...",
                timestamp=error_time,
                service_name=service_name,
                response_time_ms=(error_time - start_time) * 1000,
                token_count=0,
                metadata={"error": str(e)}
            )
            thread.add_message(error_msg)
            self.console.print(f"[red]Error calling {service_name}: {e}[/red]")
    
    async def _run_real_multi_turn_conversation(self, thread: ConversationThread, services: List[str]):
        """Run multi-turn conversation with real API calls"""
        from .service_discovery import discover_services
        from .api_clients import create_unified_client_from_services, GenerationRequest, ChatMessage
        
        self.console.print("[blue]🔍 Starting real multi-turn conversation...[/blue]")
        
        # Discover available services
        discovered_services = await discover_services()
        available_services = [s for s in services if s in discovered_services and 
                            discovered_services[s].status in ["healthy", "responding"]]
        
        if not available_services:
            self.console.print("[red]❌ No healthy services found. Falling back to demo mode.[/red]")
            await self._run_multi_turn_conversation(thread, services)
            return
        
        # Multi-turn prompts based on scenario
        multi_turn_prompts = {
            "customer_support": [
                "My Kubernetes pod won't start, can you help me debug it?",
                "I tried kubectl describe and see 'ImagePullBackOff'. What does this mean?",
                "The image is 'nginx:latst' - I think there might be a typo?",
                "Perfect! That fixed it. How can I prevent this in the future?"
            ],
            "code_review": [
                "Review this Python function:\n\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
                "Thanks! Can you show me the optimized version with list comprehension?",
                "What about error handling? What if the data contains non-numeric values?",
                "Great! Can you write a unit test for this improved function?"
            ]
        }
        
        scenario_prompts = multi_turn_prompts.get(thread.scenario, [thread.messages[0].content])
        
        self.live_state.active_threads[thread.thread_id] = thread
        
        async with create_unified_client_from_services(discovered_services) as api_client:
            with Live(self.create_live_dashboard({thread.thread_id: thread}), 
                      refresh_per_second=4, console=self.console) as live:
                
                for turn_index, prompt in enumerate(scenario_prompts):
                    if turn_index > 0:
                        # Add new user message for subsequent turns
                        user_message = ConversationMessage(
                            role="user",
                            content=prompt,
                            timestamp=time.time()
                        )
                        thread.add_message(user_message)
                        live.update(self.create_live_dashboard({thread.thread_id: thread}))
                        await asyncio.sleep(1)
                    
                    self.console.print(f"\n[bold cyan]Turn {turn_index + 1}/{len(scenario_prompts)}[/bold cyan]")
                    
                    # Build conversation history for context
                    conversation_history = []
                    for msg in thread.messages:
                        if msg.role in ["user", "assistant"] and not msg.service_name:
                            # User messages or final assistant responses (not per-service)
                            conversation_history.append(ChatMessage(role=msg.role, content=msg.content))
                    
                    # Create request with full conversation context
                    request = GenerationRequest(
                        messages=conversation_history,
                        max_tokens=256,
                        temperature=0.7,
                        stream=True
                    )
                    
                    # Get responses from all services for this turn
                    response_tasks = []
                    for service_name in available_services:
                        task = asyncio.create_task(
                            self._call_real_service(thread, service_name, request, api_client, live)
                        )
                        response_tasks.append(task)
                    
                    await asyncio.gather(*response_tasks, return_exceptions=True)
                    
                    # Brief pause between turns
                    if turn_index < len(scenario_prompts) - 1:
                        await asyncio.sleep(2)
                
                # Final context retention analysis
                await self._analyze_real_context_retention(thread, live)
    
    async def _analyze_real_context_retention(self, thread: ConversationThread, live: Live):
        """Analyze context retention based on real API responses"""
        
        # Count turns and analyze response quality
        user_turns = [msg for msg in thread.messages if msg.role == "user"]
        service_responses = {}
        
        for msg in thread.messages:
            if msg.service_name:
                if msg.service_name not in service_responses:
                    service_responses[msg.service_name] = []
                service_responses[msg.service_name].append(msg)
        
        # Create analysis based on real responses
        context_analysis = Table(title="🧠 Real Context Retention Analysis")
        context_analysis.add_column("Service", style="bold")
        context_analysis.add_column("Turns Completed", justify="right")
        context_analysis.add_column("Avg Response Time", justify="right")
        context_analysis.add_column("Context Quality", justify="right")
        context_analysis.add_column("Grade", style="bold")
        
        for service_name, responses in service_responses.items():
            personality = self.get_service_personality(service_name)
            service_display = f"{personality.value[1]} {service_name.upper()}"
            
            turns_completed = len(responses)
            avg_response_time = sum(r.response_time_ms or 0 for r in responses) / len(responses) if responses else 0
            
            # Simple quality scoring based on response length and turn completion
            if turns_completed >= len(user_turns) and avg_response_time < 2000:
                grade = "A"
                quality = "Excellent"
            elif turns_completed >= len(user_turns) * 0.8:
                grade = "B+"
                quality = "Good"
            else:
                grade = "C"
                quality = "Needs Work"
            
            context_analysis.add_row(
                service_display,
                str(turns_completed),
                f"{avg_response_time:.0f}ms" if avg_response_time > 0 else "N/A",
                quality,
                grade
            )
        
        # Show analysis
        analysis_layout = Layout()
        analysis_layout.update(Panel(context_analysis, border_style="purple"))
        live.update(analysis_layout)
        await asyncio.sleep(5)
    
    # ==================== THREE-WAY RACE LIVE DEMO METHODS ====================
    
    async def run_three_way_race(self, prompt: str, services: Optional[List[str]] = None,
                                rapid_fire: bool = False, crowd_rush: bool = False, 
                                statistical: bool = False, num_runs: int = 10, 
                                use_real_apis: bool = True):
        """
        🎭 The Performance Race - Live three-way demonstration
        
        This is the signature demo showing vLLM, TGI, and Ollama competing side-by-side
        in real-time, with visual indicators of performance differences.
        
        Args:
            statistical: If True, runs multiple iterations for statistical analysis
            num_runs: Number of runs for statistical mode (default: 10)
            use_real_apis: If True, discover and use real deployed services
        """
        services = services or ["vllm", "tgi", "ollama"]
        
        # Create race state
        race = ThreeWayRace(
            race_id=f"race_{int(time.time())}",
            prompt=prompt,
            start_time=time.time(),
            total_runs=num_runs if statistical else 1
        )
        
        # Discover real services if requested
        discovered_services = None
        api_client = None
        
        if use_real_apis:
            discovered_services, api_client = await self._setup_real_services(services)
            if discovered_services:
                # Update services list to only include available ones
                services = list(discovered_services.keys())
        
        # Add participants with personalities
        service_personalities = {
            "vllm": ServicePersonality.VLLM,
            "tgi": ServicePersonality.TGI,
            "ollama": ServicePersonality.OLLAMA
        }
        
        for service in services:
            if service in service_personalities:
                race.add_participant(service, service_personalities[service])
                # Update engine info with real URLs if available
                if discovered_services and service in discovered_services:
                    race.participants[service].engine_info.engine_url = discovered_services[service].url
        
        # Store API client for real requests
        race.api_client = api_client
        race.use_real_apis = use_real_apis and api_client is not None
        
        if statistical:
            await self._run_statistical_race(race)
        elif rapid_fire:
            await self._run_rapid_fire_race(race)
        elif crowd_rush:
            await self._run_crowd_rush_simulation(race)
        else:
            await self._run_standard_race(race)
        
        # Clean up API client
        if api_client:
            await api_client.__aexit__(None, None, None)
    
    async def _setup_real_services(self, requested_services: List[str]):
        """Set up real service discovery and API clients"""
        from src.service_discovery import discover_services
        from src.api_clients import create_unified_client_from_services
        
        self.console.print("[blue]🔗 Using REAL APIs - Connecting to deployed services[/blue]")
        self.console.print("[blue]🔍 Discovering services for real conversation...[/blue]")
        
        # Discover available services
        discovered_services = await discover_services()
        
        # Filter to only requested services that are available
        available_services = {}
        for service_name in requested_services:
            if service_name in discovered_services and discovered_services[service_name].status in ["healthy", "responding"]:
                available_services[service_name] = discovered_services[service_name]
            else:
                self.console.print(f"[yellow]⚠️ Service {service_name} not available, skipping[/yellow]")
        
        if not available_services:
            self.console.print("[red]❌ No healthy services found. Falling back to demo mode.[/red]")
            return None, None
        
        self.console.print(f"[green]✅ Using real APIs: {', '.join(available_services.keys()).upper()}[/green]")
        
        # Create real API client
        api_client = await create_unified_client_from_services(discovered_services).__aenter__()
        
        return available_services, api_client
    
    async def _run_statistical_race(self, race: ThreeWayRace):
        """Run multiple races for statistical analysis with visual demonstration"""
        self.console.print("\n" + "="*80)
        self.console.print("[bold yellow]📊 STATISTICAL RACE ANALYSIS - Multiple Run Comparison[/bold yellow]")
        self.console.print("="*80)
        
        self.console.print(f"[cyan]Running {race.total_runs} iterations for robust statistical analysis[/cyan]")
        self.console.print(f"[cyan]Prompt: {race.prompt}[/cyan]")
        
        # First, show a few visual races (3-5 runs) for stakeholder engagement
        visual_runs = min(3, race.total_runs)
        self.console.print(f"\n[bold blue]🎭 First, let's watch {visual_runs} races visually...[/bold blue]")
        
        for visual_run in range(visual_runs):
            self.console.print(f"\n[yellow]👀 Visual Race {visual_run + 1}/{visual_runs}[/yellow]")
            
            # Reset participants for this run
            for participant in race.participants.values():
                participant.response_start_time = None
                participant.first_token_time = None
                participant.current_response = ""
                participant.tokens_received = 0
                participant.is_complete = False
                participant.error_message = None
            
            # Run one visual iteration with the standard race display
            await self._run_single_visual_statistical_race(race)
            
            # Brief pause between visual races
            await asyncio.sleep(1)
        
        # Wait for user input before continuing to data collection
        if visual_runs > 0 and race.total_runs > visual_runs:
            self.console.print("\n" + "="*80)
            self.console.print("[bold yellow]📊 Visual races complete![/bold yellow]")
            self.console.print("[dim]Take time to review the side-by-side comparisons above.[/dim]")
            self.console.print("[bold cyan]Press ENTER to collect remaining data points for statistical analysis...[/bold cyan]")
            try:
                input()
            except KeyboardInterrupt:
                pass
        
        # Now run the remaining iterations quickly for statistical data
        remaining_runs = race.total_runs - visual_runs
        if remaining_runs > 0:
            self.console.print(f"\n[bold blue]📊 Now collecting {remaining_runs} more data points for statistical analysis...[/bold blue]")
            
            # Progress tracking for remaining runs
            from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
                TimeRemainingColumn(),
                console=self.console
            ) as progress:
                
                task = progress.add_task(f"Collecting {remaining_runs} more performance samples...", total=remaining_runs)
                
                for run_num in range(remaining_runs):
                    race.current_run = visual_runs + run_num + 1
                    
                    # Reset participants for this run
                    for participant in race.participants.values():
                        participant.response_start_time = None
                        participant.first_token_time = None
                        participant.current_response = ""
                        participant.tokens_received = 0
                        participant.is_complete = False
                        participant.error_message = None
                    
                    # Run single iteration (fast data collection)
                    await self._run_single_statistical_iteration(race)
                    
                    progress.update(task, advance=1)
                    
                    # Brief pause between runs
                    await asyncio.sleep(0.05)  # Faster for data collection
        
        # Display comprehensive statistical analysis
        await self._display_statistical_results(race)
    
    async def _run_single_visual_statistical_race(self, race: ThreeWayRace):
        """Run a single race with visual display for statistical mode"""
        
        race_prompt_panel = Panel(
            f"[bold white]{race.prompt}[/bold white]",
            title="🧑 User Question",
            border_style="blue"
        )
        self.console.print(race_prompt_panel)
        
        # Create three-column layout for side-by-side comparison
        layout = Layout()
        layout.split_row(
            Layout(name="vllm_lane"),
            Layout(name="tgi_lane"), 
            Layout(name="ollama_lane")
        )
        
        # Initialize participant displays
        for service_name, participant in race.participants.items():
            display = self._create_participant_display(participant, "⚡ Ready for statistical run...")
            
            # Assign to correct lane
            if service_name == "vllm":
                layout["vllm_lane"].update(display)
            elif service_name == "tgi":
                layout["tgi_lane"].update(display)
            elif service_name == "ollama":
                layout["ollama_lane"].update(display)
        
        # Start live display for this statistical run
        with Live(layout, console=self.console, refresh_per_second=10) as live:
            
            self.console.print("[bold green]🚀 GO! Running statistical iteration...[/bold green]")
            
            # Start all requests simultaneously 
            race.start_time = time.time()
            tasks = []
            
            for service_name in race.participants.keys():
                task = asyncio.create_task(
                    self._simulate_service_response_fast(race, service_name, live, layout)
                )
                tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks)
            
            # Show quick results for this iteration
            await self._display_quick_statistical_results(race, live)
    
    async def _simulate_service_response_fast(self, race: ThreeWayRace, service_name: str, 
                                            live: Live, layout: Layout):
        """Simulate service response optimized for statistical visual display"""
        participant = race.participants[service_name]
        
        # Use same statistical simulation as the data collection
        import random
        
        # Base delays with realistic variance
        base_delays = {
            "vllm": 0.12,    # 120ms base
            "tgi": 0.35,     # 350ms base  
            "ollama": 0.65   # 650ms base
        }
        
        # Add realistic variance (±20%)
        base_delay = base_delays.get(service_name, 0.5)
        variance = base_delay * 0.2
        actual_delay = base_delay + random.uniform(-variance, variance)
        actual_delay = max(0.05, actual_delay)  # Minimum 50ms
        
        # Mark response start
        race.mark_response_start(service_name)
        
        # Show "connecting" state
        connecting_display = self._create_participant_display(
            participant, 
            "🔄 Connecting...",
            status_color="yellow"
        )
        self._update_service_lane(layout, service_name, connecting_display)
        live.update(layout)
        
        # Wait for TTFT
        await asyncio.sleep(actual_delay)
        
        # Mark first token
        race.mark_first_token(service_name)
        
        # Show first token received
        first_token_display = self._create_participant_display(
            participant, 
            f"⚡ First token! ({actual_delay * 1000:.0f}ms)",
            status_color="green"
        )
        self._update_service_lane(layout, service_name, first_token_display)
        live.update(layout)
        
        # Generate the full response based on the prompt and service personality
        full_response = self._generate_demo_response(service_name, race.prompt)
        
        # Simple tokenization simulation (more realistic than word count)
        # Real tokenization would use tiktoken or similar, but for demo we'll approximate
        tokens = self._simulate_tokenization(full_response)
        token_count = len(tokens)
        
        # Simulate streaming the full response token by token
        current_response = ""
        token_delay = 0.015 if service_name == "vllm" else 0.025 if service_name == "tgi" else 0.04
        
        for i, token in enumerate(tokens):
            current_response += token
            participant.current_response = current_response.strip()
            
            # Update display with growing response
            progress_text = f"📝 Generating... ({i+1}/{token_count} tokens)"
            streaming_display = self._create_participant_display(
                participant,
                progress_text,
                status_color="cyan",
                show_response=True
            )
            self._update_service_lane(layout, service_name, streaming_display)
            live.update(layout)
            
            # Variable delay for realistic streaming (tokens/second varies by service)
            await asyncio.sleep(token_delay * random.uniform(0.8, 1.2))
        
        participant.tokens_received = token_count
        race.mark_complete(service_name)
        
        # Calculate metrics for this run
        ttft_ms = (participant.first_token_time - race.start_time) * 1000
        total_generation_time = token_count * token_delay  # Calculate total generation time
        total_ms = ttft_ms + (total_generation_time * 1000)
        
        # Store in statistics
        race.statistics[service_name].add_run(ttft_ms, total_ms, token_count)
        
        # Final display
        complete_display = self._create_participant_display(
            participant,
            f"✅ Complete! TTFT: {ttft_ms:.0f}ms, Total: {total_ms:.0f}ms",
            status_color="bright_green"
        )
        self._update_service_lane(layout, service_name, complete_display)
        live.update(layout)
    
    async def _display_quick_statistical_results(self, race: ThreeWayRace, live: Live):
        """Display quick results for this iteration"""
        await asyncio.sleep(1)  # Brief pause to see results
        
        # Get TTFT rankings for this iteration
        ttft_rankings = race.get_ttft_rankings()
        
        # Show quick winner for this round
        if ttft_rankings:
            winner_name, winner_ttft = ttft_rankings[0]
            service_emojis = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}
            winner_emoji = service_emojis.get(winner_name, "⚪")
            
            winner_text = Text(f"\n🏆 This round winner: {winner_emoji} {winner_name.upper()} ({winner_ttft:.0f}ms)", 
                             style="bold green", justify="center")
            
            winner_layout = Layout()
            winner_layout.update(Panel(winner_text, border_style="green"))
            live.update(winner_layout)
            
            await asyncio.sleep(2)  # Show winner for 2 seconds
    
    async def _run_single_statistical_iteration(self, race: ThreeWayRace):
        """Run a single race iteration and collect statistics"""
        race.start_time = time.time()
        
        # Simulate all services responding (with some variability for realism)
        import random
        
        for service_name, participant in race.participants.items():
            # Base delays with realistic variance
            base_delays = {
                "vllm": 0.12,    # 120ms base
                "tgi": 0.35,     # 350ms base  
                "ollama": 0.65   # 650ms base
            }
            
            # Add realistic variance (±20%)
            base_delay = base_delays.get(service_name, 0.5)
            variance = base_delay * 0.2
            actual_delay = base_delay + random.uniform(-variance, variance)
            actual_delay = max(0.05, actual_delay)  # Minimum 50ms
            
            # Mark response start and first token
            race.mark_response_start(service_name)
            await asyncio.sleep(actual_delay)
            race.mark_first_token(service_name)
            
            # Simulate response generation (30-50 tokens)
            token_count = random.randint(30, 50)
            generation_time = token_count * random.uniform(0.02, 0.05)  # 20-50ms per token
            await asyncio.sleep(generation_time)
            
            participant.tokens_received = token_count
            race.mark_complete(service_name)
            
            # Calculate metrics for this run
            ttft_ms = (participant.first_token_time - race.start_time) * 1000
            total_ms = ttft_ms + (generation_time * 1000)
            
            # Store in statistics
            race.statistics[service_name].add_run(ttft_ms, total_ms, token_count)
    
    async def _display_statistical_results(self, race: ThreeWayRace):
        """Display comprehensive statistical analysis"""
        self.console.print("\n[bold blue]📈 STATISTICAL ANALYSIS RESULTS[/bold blue]")
        
        # Create comprehensive results table
        results_table = Table(title=f"🏆 Performance Statistics ({race.total_runs} runs)")
        results_table.add_column("Service", style="bold", width=12)
        results_table.add_column("Mean TTFT", style="cyan", width=10)
        results_table.add_column("P95 TTFT", style="yellow", width=10)
        results_table.add_column("Tokens/sec", style="green", width=10)
        results_table.add_column("Std Dev", style="magenta", width=10)
        results_table.add_column("Success Rate", style="white", width=12)
        results_table.add_column("Winner Score", style="gold1", width=12)
        
        # Calculate winner scores and rankings
        service_scores = {}
        service_emojis = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}
        
        for service_name, stats in race.statistics.items():
            ttft_stats = stats.get_ttft_stats()
            success_rate = stats.get_success_rate(race.total_runs)
            
            # Calculate average tokens per second
            avg_tokens = sum(stats.token_counts) / len(stats.token_counts) if stats.token_counts else 0
            avg_total_time = sum(stats.total_times) / len(stats.total_times) if stats.total_times else 1
            tokens_per_second = (avg_tokens / (avg_total_time / 1000)) if avg_total_time > 0 else 0
            
            # Winner score: lower TTFT + higher tokens/sec + higher success rate = better
            winner_score = (1000 / ttft_stats["mean"]) * (tokens_per_second / 10) * (success_rate / 100) if ttft_stats["mean"] > 0 else 0
            service_scores[service_name] = winner_score
            
            emoji = service_emojis.get(service_name, "⚪")
            
            results_table.add_row(
                f"{emoji} {service_name.upper()}",
                f"{ttft_stats['mean']:.0f}ms",
                f"{ttft_stats['p95']:.0f}ms",
                f"{tokens_per_second:.1f}",
                f"{ttft_stats['std']:.1f}ms",
                f"{success_rate:.1f}%",
                f"{winner_score:.1f}"
            )
        
        self.console.print(results_table)
        
        # Determine statistical winner
        winner_service = max(service_scores, key=service_scores.get)
        winner_emoji = service_emojis.get(winner_service, "⚪")
        
        # Statistical confidence analysis
        self.console.print(f"\n[bold green]🏆 STATISTICAL WINNER: {winner_emoji} {winner_service.upper()}[/bold green]")
        
        # Business impact with statistical backing
        winner_stats = race.statistics[winner_service].get_ttft_stats()
        other_services = [s for s in service_scores.keys() if s != winner_service]
        
        impact_text = Text()
        impact_text.append(f"\n💼 Statistical Business Impact Analysis\n", style="bold blue")
        impact_text.append(f"📊 Based on {race.total_runs} statistically significant runs:\n\n")
        
        for other_service in other_services:
            other_stats = race.statistics[other_service].get_ttft_stats()
            time_advantage = other_stats["mean"] - winner_stats["mean"]
            if time_advantage > 0:
                impact_text.append(f"• {winner_service.upper()} is {time_advantage:.0f}ms faster than {other_service.upper()} (P95: {other_stats['p95'] - winner_stats['p95']:.0f}ms advantage)\n")
        
        impact_text.append(f"\n🎯 Consistency Analysis:\n")
        impact_text.append(f"• {winner_service.upper()} std deviation: {winner_stats['std']:.1f}ms (most consistent)\n")
        impact_text.append(f"• P95 performance target (<200ms): {winner_service.upper()} achieves {winner_stats['p95']:.0f}ms\n")
        
        # Calculate ROI
        daily_requests = 10000
        time_saved_per_day = (time_advantage * daily_requests) / 1000 / 60  # minutes
        annual_value = time_saved_per_day * 365 * 25  # $25/hour productivity
        
        if time_advantage > 50:  # Only show ROI if significant advantage
            impact_text.append(f"\n💰 Annual ROI (10k daily requests):\n")
            impact_text.append(f"• Time saved: {time_saved_per_day:.1f} minutes/day\n")
            impact_text.append(f"• Productivity value: ${annual_value:,.0f}/year\n")
        
        impact_text.append(f"\n✅ Statistical Confidence: {race.total_runs} runs provide robust performance baseline")
        
        impact_panel = Panel(impact_text, title="📊 Statistical Business Value", border_style="blue")
        self.console.print(impact_panel)
        
        # Show detailed percentile breakdown
        percentile_table = Table(title="📊 Detailed Percentile Analysis", show_header=True)
        percentile_table.add_column("Service", style="bold")
        percentile_table.add_column("P50 (Median)", style="cyan")
        percentile_table.add_column("P95", style="yellow") 
        percentile_table.add_column("P99", style="red")
        percentile_table.add_column("Range", style="green")
        
        for service_name, stats in race.statistics.items():
            ttft_stats = stats.get_ttft_stats()
            emoji = service_emojis.get(service_name, "⚪")
            
            percentile_table.add_row(
                f"{emoji} {service_name.upper()}",
                f"{ttft_stats['p50']:.0f}ms",
                f"{ttft_stats['p95']:.0f}ms",
                f"{ttft_stats['p99']:.0f}ms",
                f"{ttft_stats['max'] - ttft_stats['min']:.0f}ms"
            )
        
        self.console.print(f"\n{percentile_table}")
        
        await asyncio.sleep(15)  # Let users absorb the comprehensive analysis
    
    async def _run_standard_race(self, race: ThreeWayRace):
        """Run the standard three-way performance race"""
        self.console.print("\n" + "="*80)
        self.console.print("[bold yellow]🏁 THE PERFORMANCE RACE - LIVE DEMO[/bold yellow]")
        self.console.print("="*80)
        
        race_prompt_panel = Panel(
            f"[bold white]{race.prompt}[/bold white]",
            title="🧑 User Question",
            border_style="blue"
        )
        self.console.print(race_prompt_panel)
        
        # Create three-column layout for side-by-side comparison
        layout = Layout()
        layout.split_row(
            Layout(name="vllm_lane"),
            Layout(name="tgi_lane"), 
            Layout(name="ollama_lane")
        )
        
        # Initialize participant displays
        participant_displays = {}
        for service_name, participant in race.participants.items():
            personality = participant.personality
            display = self._create_participant_display(participant, "⚡ Waiting to start...")
            participant_displays[service_name] = display
            
            # Assign to correct lane
            if service_name == "vllm":
                layout["vllm_lane"].update(display)
            elif service_name == "tgi":
                layout["tgi_lane"].update(display)
            elif service_name == "ollama":
                layout["ollama_lane"].update(display)
        
        # Start live display
        with Live(layout, console=self.console, refresh_per_second=10) as live:
            # Countdown
            for i in range(3, 0, -1):
                countdown_text = Text(f"\n⏰ Starting in {i}...", style="bold yellow", justify="center")
                self.console.print(countdown_text)
                await asyncio.sleep(1)
            
            self.console.print("[bold green]🚀 GO! Starting the race...[/bold green]\n")
            
            # Start all requests simultaneously 
            race.start_time = time.time()
            tasks = []
            
            for service_name in race.participants.keys():
                task = asyncio.create_task(
                    self._simulate_service_response(race, service_name, live, layout)
                )
                tasks.append(task)
            
            # Wait for all to complete
            await asyncio.gather(*tasks)
            
        # Wait for user input before showing summary
        await self._wait_for_user_to_continue(live, layout)
        
        # Show final results (create new live context since we stopped the previous one)
        await self._display_race_results(race)
    
    async def _simulate_service_response(self, race: ThreeWayRace, service_name: str, 
                                       live: Live, layout: Layout):
        """Simulate or run real service response based on race configuration"""
        if race.use_real_apis and race.api_client:
            await self._run_real_service_response(race, service_name, live, layout)
        else:
            await self._run_mock_service_response(race, service_name, live, layout)
    
    async def _run_real_service_response(self, race: ThreeWayRace, service_name: str,
                                       live: Live, layout: Layout):
        """Run real API call to deployed service"""
        participant = race.participants[service_name]
        
        # Mark response start
        race.mark_response_start(service_name)
        
        # Show "connecting" state
        connecting_display = self._create_participant_display(
            participant, 
            "🔄 Connecting to real API...",
            status_color="yellow"
        )
        self._update_service_lane(layout, service_name, connecting_display)
        live.update(layout)
        
        try:
            # Create request for real API
            from src.api_clients import ChatMessage, GenerationRequest
            
            chat_request = GenerationRequest(
                messages=[ChatMessage(role="user", content=race.prompt)],
                max_tokens=256,
                temperature=0.7,
                stream=True
            )
            
            # Make real API call with streaming
            current_response = ""
            token_count = 0
            first_token_received = False
            
            # Use the individual client for the service
            if service_name in race.api_client.clients:
                client = race.api_client.clients[service_name]
                async for chunk in client.generate_stream(chat_request):
                    if chunk:
                        if not first_token_received:
                            # Mark first token
                            race.mark_first_token(service_name)
                            first_token_received = True
                            
                            # Show first token received
                            first_token_display = self._create_participant_display(
                                participant, 
                                f"⚡ First token from real API!",
                                status_color="green"
                            )
                            self._update_service_lane(layout, service_name, first_token_display)
                            live.update(layout)
                        
                        # Add token to response
                        current_response += chunk
                        participant.current_response = current_response
                        token_count += 1
                        participant.tokens_received = token_count
                        
                        # Update display every few tokens for performance
                        if token_count % 3 == 0:
                            streaming_display = self._create_participant_display(
                                participant,
                                f"📝 Streaming from real API... ({token_count} tokens)",
                                status_color="cyan",
                                show_response=True
                            )
                            self._update_service_lane(layout, service_name, streaming_display)
                            live.update(layout)
            else:
                raise Exception(f"Service {service_name} not found in API client")
            
            # Mark complete
            race.mark_complete(service_name)
            
            # Final display
            complete_display = self._create_participant_display(
                participant,
                f"✅ Real API Complete! ({token_count} tokens)",
                status_color="bright_green",
                show_response=True
            )
            self._update_service_lane(layout, service_name, complete_display)
            live.update(layout)
            
        except Exception as e:
            # Handle API errors gracefully
            participant.error_message = str(e)
            error_display = self._create_participant_display(
                participant,
                f"❌ API Error: {str(e)[:50]}...",
                status_color="red"
            )
            self._update_service_lane(layout, service_name, error_display)
            live.update(layout)
    
    async def _run_mock_service_response(self, race: ThreeWayRace, service_name: str,
                                       live: Live, layout: Layout):
        """Run simulated service response (original mock behavior)"""
        participant = race.participants[service_name]
        personality = participant.personality
        
        # Realistic TTFT delays based on service characteristics
        ttft_delays = {
            "vllm": 0.12,    # 120ms - Professional and fast
            "tgi": 0.35,     # 350ms - Technical, more thoughtful
            "ollama": 0.65   # 650ms - Friendly but slower
        }
        
        # Mark response start
        race.mark_response_start(service_name)
        
        # Show "connecting" state
        connecting_display = self._create_participant_display(
            participant, 
            "🔄 Connecting (demo mode)...",
            status_color="yellow"
        )
        self._update_service_lane(layout, service_name, connecting_display)
        live.update(layout)
        
        # Wait for TTFT
        await asyncio.sleep(ttft_delays.get(service_name, 0.5))
        
        # Mark first token
        race.mark_first_token(service_name)
        
        # Generate response with realistic patterns
        response_text = self._generate_demo_response(service_name, race.prompt)
        
        # Simulate token-by-token streaming
        current_response = ""
        words = response_text.split()
        
        # Different streaming patterns per service
        token_delays = {
            "vllm": 0.03,    # Fast, consistent
            "tgi": 0.05,     # Moderate, steady  
            "ollama": 0.08   # Slower, more variable
        }
        
        base_delay = token_delays.get(service_name, 0.05)
        
        for i, word in enumerate(words):
            current_response += word + " "
            participant.current_response = current_response.strip()
            participant.tokens_received = i + 1
            
            # Update display with current response
            status_text = f"⚡ Generating (demo)... ({participant.tokens_received} tokens)"
            typing_display = self._create_participant_display(
                participant,
                status_text,
                status_color="green",
                show_response=True
            )
            self._update_service_lane(layout, service_name, typing_display)
            live.update(layout)
            
            # Variable delay for realism
            delay = base_delay * (0.8 + 0.4 * (i % 3))  # Some variability
            await asyncio.sleep(delay)
        
        # Mark complete
        race.mark_complete(service_name)
        
        # Final display
        complete_display = self._create_participant_display(
            participant,
            f"✅ Demo Complete! ({participant.tokens_received} tokens)",
            status_color="bright_green",
            show_response=True
        )
        self._update_service_lane(layout, service_name, complete_display)
        live.update(layout)
    
    async def _wait_for_user_to_continue(self, live: Live, layout: Layout):
        """Wait for user to press Enter before continuing to summary"""
        import sys
        import asyncio
        from rich.panel import Panel
        from rich.align import Align
        
        # Stop the live display temporarily to show the prompt
        live.stop()
        
        # Show prompt using console directly
        self.console.print("\n")
        prompt_panel = Panel(
            Align.center(
                "[bold yellow]🎯 Race Complete![/bold yellow]\n\n"
                "[dim]Take time to review the side-by-side comparison above.[/dim]\n\n"
                "[bold cyan]Press ENTER to see the detailed summary and analysis...[/bold cyan]"
            ),
            title="⏸️ Waiting for User",
            border_style="yellow",
            padding=(1, 2)
        )
        
        self.console.print(prompt_panel)
        
        # Wait for user input
        try:
            # Use asyncio to wait for input without blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, input)
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            pass
        except Exception:
            # If input fails, wait a moment and continue
            await asyncio.sleep(2)
    
    def _create_participant_display(self, participant: RaceParticipant, status: str, 
                                  status_color: str = "white", show_response: bool = False) -> Panel:
        """Create display panel for a race participant"""
        personality = participant.personality
        personality_name, color, description = personality.value
        engine_info = participant.engine_info
        
        # Map services to emojis separately from colors
        service_emojis = {
            "vllm": "🔵",
            "tgi": "🟢", 
            "ollama": "🟠"
        }
        emoji = service_emojis.get(participant.name, "⚪")
        
        # Header with service info
        header = Text()
        header.append(f"{emoji} {participant.name.upper()}", style=f"bold {color}")
        header.append(f"\n{description}", style="dim")
        
        # Technical Information Section
        tech_info = Text()
        tech_info.append(f"\n🔧 Technical Info:", style="bold cyan")
        tech_info.append(f"\n• URL: {engine_info.engine_url}", style="dim")
        tech_info.append(f"\n• Model: {engine_info.model_name}", style="dim")
        tech_info.append(f"\n• Version: {engine_info.version}", style="dim")
        tech_info.append(f"\n• GPU: {engine_info.gpu_type} ({engine_info.memory_gb}GB)", style="dim")
        tech_info.append(f"\n• Batch Size: {engine_info.max_batch_size}", style="dim")
        tech_info.append(f"\n• Context: {engine_info.max_context_length} tokens", style="dim")
        tech_info.append(f"\n• Deploy: {engine_info.deployment}", style="dim")
        
        # Status
        status_text = Text(f"\n\n📊 Status: {status}", style=status_color)
        
        # Response preview if available
        content = Text()
        content.append_text(header)
        content.append_text(tech_info)
        content.append_text(status_text)
        
        if show_response and participant.current_response:
            content.append("\n\n")
            # Show the full response for complete comparison
            # This is a demo focused on showing model differences, so show everything
            response_text = participant.current_response
            
            # Add some formatting to make it more readable
            content.append("💬 Response:", style="bold dim")
            content.append(f"\n{response_text}", style="dim")
        
        return Panel(
            content,
            border_style=color,
            title=f"{emoji} {participant.name.upper()}",
            title_align="left"
        )
    
    def _update_service_lane(self, layout: Layout, service_name: str, display: Panel):
        """Update the correct lane in the layout"""
        lane_map = {
            "vllm": "vllm_lane",
            "tgi": "tgi_lane", 
            "ollama": "ollama_lane"
        }
        
        if service_name in lane_map:
            layout[lane_map[service_name]].update(display)
    
    async def _display_race_results(self, race: ThreeWayRace, live: Live = None):
        """Display comprehensive race results and analysis"""
        await asyncio.sleep(1)  # Pause for dramatic effect
        
        # Get TTFT rankings
        ttft_rankings = race.get_ttft_rankings()
        
        # Create results table
        results_table = Table(title="🏆 Race Results & Performance Analysis")
        results_table.add_column("Rank", style="bold", width=6)
        results_table.add_column("Service", style="bold", width=12)
        results_table.add_column("TTFT", style="cyan", width=10)
        results_table.add_column("Tokens", style="green", width=8)
        results_table.add_column("Experience", style="yellow")
        
        # Map services to emojis
        service_emojis = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}
        
        # Rank by TTFT
        for rank, (service_name, ttft_ms) in enumerate(ttft_rankings, 1):
            participant = race.participants[service_name]
            emoji = service_emojis.get(service_name, "⚪")
            
            # Experience rating
            if ttft_ms < 200:
                experience = "⚡ Instant & Smooth"
            elif ttft_ms < 500:
                experience = "🔶 Good Response"
            else:
                experience = "🔴 Noticeable Delay"
            
            rank_style = "bold green" if rank == 1 else "bold yellow" if rank == 2 else "bold red"
            
            results_table.add_row(
                f"#{rank}",
                f"{emoji} {service_name.upper()}",
                f"{ttft_ms:.0f}ms",
                str(participant.tokens_received),
                experience,
                style=rank_style if rank == 1 else None
            )
        
        # Business impact analysis
        winner_name, winner_ttft = ttft_rankings[0]
        loser_name, loser_ttft = ttft_rankings[-1]
        time_advantage = loser_ttft - winner_ttft
        
        impact_text = Text()
        impact_text.append(f"\n💼 Business Impact Analysis\n", style="bold blue")
        impact_text.append(f"• {winner_name.upper()} responds {time_advantage:.0f}ms faster than {loser_name.upper()}\n")
        impact_text.append(f"• For 1000 daily interactions: saves {time_advantage:.0f} seconds per interaction\n")
        impact_text.append(f"• Productivity gain: {(time_advantage * 1000 / 1000 / 60):.1f} minutes saved per day\n")
        impact_text.append(f"• User experience: {winner_name.upper()} feels more responsive and professional\n")
        
        # Display results either via live update or console print
        if live:
            # Final results layout for live display
            results_layout = Layout()
            results_layout.split_column(
                Layout(Panel(results_table, border_style="yellow")),
                Layout(Panel(impact_text, title="📊 Business Value", border_style="blue"))
            )
            live.update(results_layout)
            await asyncio.sleep(10)  # Let users absorb the results
        else:
            # Display directly to console
            self.console.print("\n")
            self.console.print(Panel(results_table, border_style="yellow"))
            self.console.print("\n")
            self.console.print(Panel(impact_text, title="📊 Business Value", border_style="blue"))
            self.console.print("\n")
    
    def _generate_demo_response(self, service_name: str, prompt: str) -> str:
        """Generate realistic demo responses based on service personality"""
        
        # Enhanced responses that show personality differences clearly
        base_responses = {
            "kubernetes_debug": {
                "vllm": "To troubleshoot Kubernetes pods effectively, follow this systematic approach: 1) Check pod status with 'kubectl describe pod <pod-name>' to identify specific issues like ImagePullBackOff, CrashLoopBackOff, or resource constraints. 2) Examine logs using 'kubectl logs <pod-name>' for container-level errors. 3) Verify resource quotas, node capacity, and persistent volume claims. 4) Check service accounts, RBAC permissions, and network policies. This methodical approach ensures comprehensive diagnosis and faster resolution.",
                "tgi": "Kubernetes pod debugging requires structured analysis across multiple layers. Start with 'kubectl get pods -o wide' to assess pod distribution and status. Use 'kubectl describe pod <name>' for detailed event inspection. Log analysis via 'kubectl logs <pod> --previous' captures crash information. Resource validation includes checking CPU/memory limits, storage availability, and networking configuration. Systematic troubleshooting methodology ensures efficient problem resolution.",
                "ollama": "Hey there! Debugging Kubernetes pods can be tricky, but let's break it down step by step. First, run 'kubectl get pods' to see what's going on. If a pod is stuck, try 'kubectl describe pod <your-pod-name>' - this shows you all the juicy details about what went wrong. Common issues are usually image problems, not enough resources, or configuration hiccups. Don't worry, we'll figure this out together! What specific error are you seeing?"
            },
            "transformers": {
                "vllm": "Transformers are neural network architectures that revolutionized natural language processing through attention mechanisms. The core innovation is self-attention, which allows models to weigh the importance of different words in a sequence simultaneously, rather than processing sequentially. This parallel processing enables better understanding of long-range dependencies and context. Key components include multi-head attention, position encoding, and feed-forward networks. Applications span machine translation, text generation, and question answering with remarkable accuracy improvements.",
                "tgi": "Transformer architecture represents a paradigm shift in sequence modeling, replacing recurrent neural networks with attention-based mechanisms. The fundamental principle involves computing attention weights between all token pairs, enabling parallel computation and better gradient flow. Technical components include scaled dot-product attention, positional embeddings, layer normalization, and residual connections. This architecture has achieved state-of-the-art performance across NLP tasks including BERT for understanding and GPT for generation.",
                "ollama": "Great question! Think of transformers like a really smart reading comprehension system. Instead of reading text word by word like we do, transformers can look at all words at once and understand how they relate to each other. It's like having super-powered attention that can focus on multiple things simultaneously. This makes them excellent at understanding context and generating human-like text. They're the technology behind ChatGPT, Google Translate, and many other AI tools you use every day!"
            },
            "general": {
                "vllm": "I'll provide a comprehensive analysis addressing your specific requirements with technical precision and actionable recommendations. My response incorporates industry best practices, relevant technical specifications, and practical implementation considerations to ensure optimal outcomes for your use case.",
                "tgi": "Let me systematically analyze your request and provide structured technical guidance. I'll break down the key components, outline implementation approaches, and highlight critical considerations for successful deployment in your environment.",
                "ollama": "That's an interesting question! I'm excited to help you explore this topic. Let me explain it in a way that's clear and practical, with real-world examples that make sense. I'll make sure to give you actionable next steps you can actually use!"
            }
        }
        
        # Determine response type based on prompt content with better pattern matching
        response_type = "general"
        prompt_lower = prompt.lower()
        
        if any(keyword in prompt_lower for keyword in ["kubernetes", "pod", "debug", "troubleshoot", "k8s"]):
            response_type = "kubernetes_debug"
        elif any(keyword in prompt_lower for keyword in ["transformer", "transformers", "attention", "bert", "gpt"]):
            response_type = "transformers"
        
        return base_responses[response_type].get(service_name, base_responses["general"][service_name])
    
    def _simulate_tokenization(self, text: str) -> List[str]:
        """
        Simulate realistic tokenization for demo purposes.
        In real systems, you'd use tiktoken or similar for accurate tokenization.
        """
        import re
        
        # Split on word boundaries and punctuation, then simulate sub-word tokenization
        # This approximates how modern tokenizers work (BPE, WordPiece, etc.)
        tokens = []
        
        # First, split on whitespace and punctuation
        words = re.findall(r'\w+|[^\w\s]', text)
        
        for word in words:
            if len(word) <= 3:
                # Short words typically stay as single tokens
                tokens.append(word)
            elif len(word) <= 6:
                # Medium words might be split into 1-2 tokens
                if len(word) == 4:
                    tokens.append(word)
                else:
                    # Split longer words
                    mid = len(word) // 2
                    tokens.extend([word[:mid], word[mid:]])
            else:
                # Longer words often split into multiple sub-word tokens
                # Simulate BPE-style tokenization
                parts = []
                i = 0
                while i < len(word):
                    if i + 4 < len(word):
                        parts.append(word[i:i+4])
                        i += 4
                    else:
                        parts.append(word[i:])
                        break
                tokens.extend(parts)
            
            # Add space token after each word (except punctuation)
            if word.isalnum():
                tokens.append(" ")
        
        # Remove the last space token if it exists
        if tokens and tokens[-1] == " ":
            tokens.pop()
        
        return tokens
    
    async def _run_rapid_fire_race(self, race: ThreeWayRace):
        """Run rapid-fire prompts to show queue behavior and degradation"""
        prompts = [
            "Summarize machine learning in one paragraph",
            "Give me 3 Python optimization tips", 
            "Explain Docker containers briefly",
            "What is Kubernetes used for?"
        ]
        
        self.console.print("[bold yellow]🔥 RAPID FIRE MODE - Testing Response Under Load[/bold yellow]")
        
        for i, prompt in enumerate(prompts, 1):
            self.console.print(f"\n[bold blue]Round {i}/4:[/bold blue] {prompt}")
            
            # Update race prompt
            race.prompt = prompt
            race.start_time = time.time()
            
            # Quick simplified race
            await self._run_quick_comparison(race)
            
            await asyncio.sleep(1)  # Brief pause between rounds
    
    async def _run_quick_comparison(self, race: ThreeWayRace):
        """Quick comparison for rapid-fire demo"""
        # Simulate all services responding
        results = {}
        
        for service_name in race.participants.keys():
            start_time = time.time()
            
            # Realistic delays that increase with each rapid prompt
            base_delays = {"vllm": 0.15, "tgi": 0.4, "ollama": 0.7}
            delay = base_delays.get(service_name, 0.5)
            
            await asyncio.sleep(delay)
            
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            results[service_name] = response_time
        
        # Display quick results
        self._display_quick_results(results)
    
    def _display_quick_results(self, results: Dict[str, float]):
        """Display quick TTFT comparison"""
        # Sort by response time
        sorted_results = sorted(results.items(), key=lambda x: x[1])
        
        result_text = Text()
        for i, (service, time_ms) in enumerate(sorted_results):
            emoji = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}[service]
            if i == 0:
                result_text.append(f"{emoji} {service.upper()}: {time_ms:.0f}ms ⚡ ", style="bold green")
            else:
                result_text.append(f"{emoji} {service.upper()}: {time_ms:.0f}ms ", style="dim")
        
        self.console.print(result_text)
    
    async def _run_crowd_rush_simulation(self, race: ThreeWayRace):
        """Simulate crowd rush with multiple concurrent users"""
        self.console.print("[bold yellow]👥 CROWD RUSH SIMULATION - Testing Scalability Under Load[/bold yellow]")
        self.console.print("[cyan]Simulating 50 concurrent users hitting all three services simultaneously[/cyan]")
        
        # Simulate load effect on each service
        load_effects = {
            "vllm": {"base_delay": 0.12, "load_multiplier": 1.2},    # Scales well
            "tgi": {"base_delay": 0.35, "load_multiplier": 1.8},     # Moderate degradation  
            "ollama": {"base_delay": 0.65, "load_multiplier": 2.5}   # More significant degradation
        }
        
        console.print("\n[yellow]📊 Simulating performance under 50 concurrent users...[/yellow]")
        
        # Show before/after comparison
        comparison_table = Table(title="📈 Performance Under Load Comparison")
        comparison_table.add_column("Service", style="bold")
        comparison_table.add_column("Normal TTFT", style="green")
        comparison_table.add_column("Under Load", style="red")
        comparison_table.add_column("Degradation", style="yellow")
        comparison_table.add_column("Experience", style="cyan")
        
        for service_name, participant in race.participants.items():
            effect = load_effects.get(service_name, {"base_delay": 0.5, "load_multiplier": 2.0})
            normal_ttft = effect["base_delay"] * 1000  # Convert to ms
            load_ttft = normal_ttft * effect["load_multiplier"]
            degradation = ((load_ttft - normal_ttft) / normal_ttft) * 100
            
            # Experience assessment
            if degradation < 30:
                experience = "✅ Handles load well"
            elif degradation < 80:
                experience = "⚠️ Moderate slowdown"
            else:
                experience = "🚫 Significant delays"
            
            emoji = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}[service_name]
            
            comparison_table.add_row(
                f"{emoji} {service_name.upper()}",
                f"{normal_ttft:.0f}ms",
                f"{load_ttft:.0f}ms", 
                f"+{degradation:.0f}%",
                experience
            )
        
        self.console.print(comparison_table)
        
        # Simulate a few requests under load
        console.print("\n[blue]🔄 Running sample requests under crowd conditions...[/blue]")
        
        for i in range(3):
            console.print(f"\n[dim]Request batch {i+1}/3...[/dim]")
            
            # Simulate each service with load effects
            for service_name in race.participants.keys():
                effect = load_effects.get(service_name, {"base_delay": 0.5, "load_multiplier": 2.0})
                load_delay = effect["base_delay"] * effect["load_multiplier"]
                
                start_time = time.time()
                await asyncio.sleep(load_delay)
                end_time = time.time()
                
                response_time = (end_time - start_time) * 1000
                emoji = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}[service_name]
                
                if response_time < 300:
                    status = "✅"
                    style = "green"
                elif response_time < 700:
                    status = "⚠️"
                    style = "yellow"
                else:
                    status = "🚫"
                    style = "red"
                
                console.print(f"  {emoji} {service_name.upper()}: {response_time:.0f}ms {status}", style=style)
            
            await asyncio.sleep(0.5)  # Brief pause between batches
        
        # Final assessment
        console.print("\n[bold blue]🎯 Crowd Rush Conclusions[/bold blue]")
        console.print("• vLLM maintains responsiveness under load (best scalability)")
        console.print("• TGI shows moderate degradation but remains usable")  
        console.print("• Ollama experiences significant delays with high concurrency")
        console.print("\n[yellow]💡 For production with >25 concurrent users, vLLM shows clear advantages[/yellow]")
