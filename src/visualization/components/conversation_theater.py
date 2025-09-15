"""
ConversationTheater - Main conversation container with chat-style layout.

This component provides the core conversation visualization experience,
including live animated dashboard, chat bubbles, and streaming updates.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.columns import Columns

from ...conversation.models import ConversationThread, ConversationMessage
from ..core.base_visualizer import LiveVisualizer
from .chat_bubble import ChatBubble
from .service_panel import ServicePanel


class ConversationTheater(LiveVisualizer):
    """Main conversation container with live animated dashboard"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the conversation theater
        
        Args:
            console: Rich console instance for output
        """
        super().__init__(console)
        self.chat_bubble = ChatBubble(console)
        self.service_panels: Dict[str, ServicePanel] = {}
        self.current_threads: Dict[str, ConversationThread] = {}
        self.live_states: Dict[str, Dict[str, Any]] = {}  # Track typing states per service
        
    def render(self, data: Dict[str, ConversationThread]) -> Layout:
        """Render the conversation theater
        
        Args:
            data: Dictionary of thread_id -> ConversationThread
            
        Returns:
            Complete conversation layout
        """
        self.current_threads = data
        return self.create_conversation_layout()
    
    def create_conversation_layout(self) -> Layout:
        """Create the main conversation layout
        
        Returns:
            Rich Layout with conversation panels
        """
        layout = Layout()
        
        if len(self.current_threads) == 1:
            # Single conversation view
            thread_id, thread = next(iter(self.current_threads.items()))
            layout.split_column(
                Layout(self.create_conversation_header(thread), name="header", size=3),
                Layout(self.create_conversation_body(thread), name="body"),
                Layout(self.create_conversation_footer(thread), name="footer", size=3)
            )
        else:
            # Multi-conversation split view
            layout.split_row(*[
                self.create_single_conversation_view(thread) 
                for thread in self.current_threads.values()
            ])
        
        return layout
    
    def create_conversation_header(self, thread: ConversationThread) -> Panel:
        """Create conversation header with scenario info
        
        Args:
            thread: The conversation thread
            
        Returns:
            Header panel with scenario information
        """
        header_text = Text()
        header_text.append(f"🎭 {thread.title or 'Conversation'}\n", style="bold blue")
        
        if hasattr(thread, 'scenario_description'):
            header_text.append(f"{thread.scenario_description}\n", style="dim")
        
        # Add participant info
        if thread.messages:
            services = set(msg.service_name for msg in thread.messages if msg.service_name)
            if services:
                header_text.append(f"Participants: {', '.join(s.upper() for s in services)}", style="cyan")
        
        return Panel(
            Align.center(header_text),
            title="Conversation Theater",
            border_style="blue",
            padding=(0, 1)
        )
    
    def create_conversation_body(self, thread: ConversationThread) -> Panel:
        """Create the main conversation body with chat bubbles
        
        Args:
            thread: The conversation thread
            
        Returns:
            Body panel with conversation messages
        """
        if not thread.messages:
            empty_text = Text("Waiting for conversation to begin...", style="dim italic")
            return Panel(
                Align.center(empty_text),
                title="Messages",
                border_style="dim",
                padding=(2, 1)
            )
        
        # Create chat bubbles for all messages, including typing indicators
        message_panels = []
        for message in thread.messages:
            if message.role == "assistant" and message.service_name:
                # Check if this service is currently typing
                service_name = message.service_name
                is_typing = self.live_states.get(service_name, {}).get("is_typing", False)
                current_text = self.live_states.get(service_name, {}).get("current_response", "")
                
                if is_typing and current_text:
                    # Show typing bubble with partial content
                    bubble = self.chat_bubble.create_typing_bubble(service_name, current_text)
                elif is_typing:
                    # Show thinking indicator
                    bubble = self.chat_bubble.create_typing_bubble(service_name)
                else:
                    # Show completed message
                    bubble = self.chat_bubble.create_response_bubble(message)
            else:
                # Regular message (user or completed assistant)
                bubble = self.chat_bubble.create_response_bubble(message)
            
            message_panels.append(bubble)
        
        # Create conversation layout with proper panel rendering
        if message_panels:
            # Use Columns to display messages vertically
            from rich.columns import Columns
            # For conversation, we want vertical stacking, so we'll create a simple layout
            conversation_layout = Layout()
            
            # Split into sections for each message
            if len(message_panels) == 1:
                conversation_layout.update(message_panels[0])
            else:
                # Create vertical layout for multiple messages
                conversation_layout.split_column(
                    *[Layout(panel, size=None) for panel in message_panels[-4:]]  # Show last 4 messages
                )
            
            return Panel(
                conversation_layout,
                title="Messages",
                border_style="green",
                padding=(0, 1)
            )
        else:
            empty_text = Text("No messages yet...", style="dim italic")
            return Panel(
                Align.center(empty_text),
                title="Messages",
                border_style="green",
                padding=(1, 1)
            )
    
    def create_conversation_footer(self, thread: ConversationThread) -> Panel:
        """Create conversation footer with typing indicators and status
        
        Args:
            thread: The conversation thread
            
        Returns:
            Footer panel with status information
        """
        footer_content = Text()
        
        # Show typing indicators for services currently responding
        typing_services = []
        for service_name in ["vllm", "tgi", "ollama"]:
            if service_name in self.live_states and self.live_states[service_name].get("is_typing", False):
                service_emoji = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}.get(service_name, "")
                typing_services.append(f"{service_emoji} {service_name.upper()}")
        
        if typing_services:
            footer_content.append("Typing: ", style="dim")
            footer_content.append(" • ".join(typing_services), style="yellow")
            footer_content.append(" ● ● ●", style="blink yellow")
        else:
            footer_content.append("Ready for input", style="dim green")
        
        # Add conversation stats
        if thread.messages:
            user_messages = len([m for m in thread.messages if m.role == "user"])
            assistant_messages = len([m for m in thread.messages if m.role == "assistant"])
            footer_content.append(f"\nMessages: {user_messages} user, {assistant_messages} assistant", style="dim cyan")
        
        return Panel(
            footer_content,
            title="Status",
            border_style="yellow",
            padding=(0, 1)
        )
    
    def create_single_conversation_view(self, thread: ConversationThread) -> Layout:
        """Create a single conversation view for split-screen layout
        
        Args:
            thread: The conversation thread
            
        Returns:
            Layout for a single conversation
        """
        layout = Layout()
        layout.split_column(
            Layout(self.create_conversation_header(thread), size=2),
            Layout(self.create_conversation_body(thread)),
            Layout(self.create_conversation_footer(thread), size=2)
        )
        return layout
    
    async def create_live_dashboard(self, threads: Dict[str, ConversationThread]) -> Layout:
        """Create live dashboard with real-time updates
        
        Args:
            threads: Dictionary of conversation threads to display
            
        Returns:
            Live dashboard layout
        """
        self.current_threads = threads
        return self.create_conversation_layout()
    
    async def run_live_conversation(self, thread: ConversationThread, services: List[str]):
        """Run a live conversation with real-time updates
        
        Args:
            thread: The conversation thread to display
            services: List of services participating
        """
        # Initialize live states for each service
        for service in services:
            self.live_states[service] = {
                "is_typing": False,
                "current_response": "",
                "typing_start_time": None
            }
        
        # Create live display
        with Live(
            self.create_live_dashboard({thread.thread_id: thread}),
            refresh_per_second=4,
            console=self.console
        ) as live:
            # Simulate conversation flow
            await self._simulate_conversation_flow(thread, services, live)
    
    async def _simulate_conversation_flow(self, thread: ConversationThread, services: List[str], live: Live):
        """Simulate the conversation flow with typing indicators
        
        Args:
            thread: The conversation thread
            services: List of participating services
            live: Rich Live instance for updates
        """
        # Show each service "thinking" and then responding
        for service in services:
            # Start typing indicator
            self.live_states[service]["is_typing"] = True
            self.live_states[service]["typing_start_time"] = time.time()
            
            # Update display to show typing
            live.update(self.create_live_dashboard({thread.thread_id: thread}))
            
            # Simulate typing delay based on service personality
            typing_delays = {"vllm": 0.8, "tgi": 1.2, "ollama": 1.8}
            await asyncio.sleep(typing_delays.get(service, 1.0))
            
            # Stop typing, service has "responded"
            self.live_states[service]["is_typing"] = False
            
            # Update display
            live.update(self.create_live_dashboard({thread.thread_id: thread}))
            
            # Small pause between services
            await asyncio.sleep(0.3)
    
    def update_typing_state(self, service_name: str, is_typing: bool, current_text: str = ""):
        """Update the typing state for a service
        
        Args:
            service_name: Name of the service
            is_typing: Whether the service is currently typing
            current_text: Current partial response text
        """
        if service_name not in self.live_states:
            self.live_states[service_name] = {}
        
        self.live_states[service_name].update({
            "is_typing": is_typing,
            "current_response": current_text,
            "typing_start_time": time.time() if is_typing else None
        })
    
    def get_current_layout(self) -> Layout:
        """Get the current conversation layout
        
        Returns:
            Current layout for the conversation theater
        """
        return self.create_conversation_layout()
    
    def create_layout(self) -> Layout:
        """Create the layout for live display (required by LiveVisualizer)
        
        Returns:
            Rich Layout with conversation panels
        """
        if self.current_threads:
            return self.create_conversation_layout()
        else:
            # Return empty layout if no threads
            layout = Layout()
            layout.split_column(
                Layout(Panel("Waiting for conversation...", title="Conversation Theater"), name="main")
            )
            return layout
    
    def update_layout(self, layout: Layout, data: Any):
        """Update the layout with new data (required by LiveVisualizer)
        
        Args:
            layout: The layout to update
            data: New conversation data
        """
        if isinstance(data, dict):
            # Update current threads
            self.current_threads = data
            # Update the layout with new conversation data
            new_layout = self.create_conversation_layout()
            # Copy the new layout structure to the existing layout
            layout.splitter = new_layout.splitter
            layout.renderable = new_layout.renderable
