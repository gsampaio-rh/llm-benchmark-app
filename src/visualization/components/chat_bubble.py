"""
ChatBubble - Individual message bubble styling with service-specific themes.

This component creates chat-style bubbles for conversation messages,
with service-specific colors, metrics, and intelligent text formatting.
"""

from typing import Optional, Dict, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from ...conversation.models import ConversationMessage
from ..core.base_visualizer import BaseVisualizer


class ChatBubble(BaseVisualizer):
    """Chat bubble component with service-specific styling"""
    
    # Service-specific styling configurations
    SERVICE_STYLES = {
        "vllm": {
            "emoji": "🔵",
            "color": "blue",
            "border_style": "blue",
            "personality": "Professional",
            "description": "Fast and precise technical responses"
        },
        "tgi": {
            "emoji": "🟢", 
            "color": "green",
            "border_style": "green",
            "personality": "Technical",
            "description": "Engineering-focused systematic approach"
        },
        "ollama": {
            "emoji": "🟠",
            "color": "orange3", 
            "border_style": "yellow",
            "personality": "Friendly",
            "description": "Approachable and encouraging responses"
        }
    }
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the chat bubble component
        
        Args:
            console: Rich console instance for output
        """
        super().__init__(console)
    
    def render(self, data: ConversationMessage) -> Panel:
        """Render a conversation message as a chat bubble
        
        Args:
            data: The conversation message to render
            
        Returns:
            Styled panel representing the chat bubble
        """
        return self.create_response_bubble(data)
    
    def create_response_bubble(self, message: ConversationMessage) -> Panel:
        """Create a chat bubble for a conversation message
        
        Args:
            message: The conversation message
            
        Returns:
            Styled panel with appropriate service styling
        """
        if message.role == "user":
            return self._create_user_bubble(message)
        else:
            return self._create_assistant_bubble(message)
    
    def _create_user_bubble(self, message: ConversationMessage) -> Panel:
        """Create a user message bubble
        
        Args:
            message: User message
            
        Returns:
            User-styled panel
        """
        # Truncate user message for display (200 chars max)
        content = self._truncate_text(message.content, 200)
        
        # Create content with user styling
        bubble_content = Text()
        bubble_content.append(f"👤 User: ", style="bold white")
        bubble_content.append(content, style="white")
        
        return Panel(
            bubble_content,
            title="User Message",
            border_style="white",
            padding=(0, 1),
            title_align="left"
        )
    
    def _create_assistant_bubble(self, message: ConversationMessage) -> Panel:
        """Create an assistant message bubble with service styling
        
        Args:
            message: Assistant message from a service
            
        Returns:
            Service-styled panel
        """
        service_name = message.service_name or "unknown"
        service_style = self.SERVICE_STYLES.get(service_name, self.SERVICE_STYLES["vllm"])
        
        # Truncate assistant response for display (500 chars max)
        content = self._truncate_text(message.content, 500)
        
        # Create content with service styling
        bubble_content = Text()
        bubble_content.append(content, style=service_style["color"])
        
        # Create title with metrics
        title_parts = []
        title_parts.append(f"{service_style['emoji']} {service_name.upper()}")
        
        # Add performance metrics if available
        if message.response_time_ms:
            title_parts.append(f"({message.response_time_ms:.0f}ms")
            if message.token_count:
                title_parts.append(f", {message.token_count} tokens)")
            else:
                title_parts.append(")")
        
        title = " ".join(title_parts)
        
        return Panel(
            bubble_content,
            title=title,
            border_style=service_style["border_style"],
            padding=(0, 1),
            title_align="left"
        )
    
    def create_typing_bubble(self, service_name: str, partial_text: str = "") -> Panel:
        """Create a typing indicator bubble for a service
        
        Args:
            service_name: Name of the service that's typing
            partial_text: Partial text being typed (for streaming)
            
        Returns:
            Typing indicator panel
        """
        service_style = self.SERVICE_STYLES.get(service_name, self.SERVICE_STYLES["vllm"])
        
        # Create typing content
        bubble_content = Text()
        
        if partial_text:
            # Show partial text + typing indicator
            bubble_content.append(partial_text, style=service_style["color"])
            bubble_content.append(" ● ● ●", style="blink " + service_style["color"])
        else:
            # Just typing indicator
            bubble_content.append("[typing...] ● ● ●", style="blink " + service_style["color"])
        
        title = f"{service_style['emoji']} {service_name.upper()} - Thinking..."
        
        return Panel(
            bubble_content,
            title=title,
            border_style=service_style["border_style"],
            padding=(0, 1),
            title_align="left"
        )
    
    def create_service_info_bubble(self, service_name: str, show_details: bool = False) -> Panel:
        """Create an informational bubble about a service
        
        Args:
            service_name: Name of the service
            show_details: Whether to show detailed service information
            
        Returns:
            Service information panel
        """
        service_style = self.SERVICE_STYLES.get(service_name, self.SERVICE_STYLES["vllm"])
        
        bubble_content = Text()
        bubble_content.append(f"{service_style['emoji']} {service_name.upper()}\n", style="bold " + service_style["color"])
        bubble_content.append(f"Personality: {service_style['personality']}\n", style=service_style["color"])
        bubble_content.append(service_style['description'], style="dim " + service_style["color"])
        
        if show_details:
            # Add performance characteristics
            bubble_content.append("\n\nCharacteristics:\n", style="bold")
            
            if service_name == "vllm":
                bubble_content.append("• Speed: Very Fast (30ms/token)\n", style="green")
                bubble_content.append("• Style: Professional & Precise\n", style="dim")
                bubble_content.append("• Best for: Production workloads", style="dim")
            elif service_name == "tgi":
                bubble_content.append("• Speed: Moderate (50ms/token)\n", style="yellow")
                bubble_content.append("• Style: Technical & Systematic\n", style="dim")
                bubble_content.append("• Best for: Engineering tasks", style="dim")
            elif service_name == "ollama":
                bubble_content.append("• Speed: Thoughtful (80ms/token)\n", style="orange3")
                bubble_content.append("• Style: Friendly & Encouraging\n", style="dim")
                bubble_content.append("• Best for: Interactive exploration", style="dim")
        
        return Panel(
            bubble_content,
            title=f"Service Profile",
            border_style=service_style["border_style"],
            padding=(1, 2),
            title_align="center"
        )
    
    def create_performance_bubble(self, service_name: str, metrics: Dict[str, Any]) -> Panel:
        """Create a performance metrics bubble for a service
        
        Args:
            service_name: Name of the service
            metrics: Performance metrics dictionary
            
        Returns:
            Performance metrics panel
        """
        service_style = self.SERVICE_STYLES.get(service_name, self.SERVICE_STYLES["vllm"])
        
        bubble_content = Text()
        bubble_content.append(f"Performance Metrics\n", style="bold " + service_style["color"])
        
        # Format key metrics
        if "ttft_ms" in metrics:
            bubble_content.append(f"TTFT: {metrics['ttft_ms']:.0f}ms\n", style=service_style["color"])
        
        if "tokens_per_second" in metrics:
            bubble_content.append(f"Speed: {metrics['tokens_per_second']:.1f} tok/s\n", style=service_style["color"])
        
        if "total_tokens" in metrics:
            bubble_content.append(f"Tokens: {metrics['total_tokens']}\n", style=service_style["color"])
        
        if "response_quality" in metrics:
            bubble_content.append(f"Quality: {metrics['response_quality']}\n", style=service_style["color"])
        
        # Add performance rating
        if "overall_score" in metrics:
            score = metrics["overall_score"]
            if score >= 8:
                rating = "Excellent"
                rating_style = "bold green"
            elif score >= 6:
                rating = "Good"
                rating_style = "bold yellow"
            else:
                rating = "Fair"
                rating_style = "bold red"
            
            bubble_content.append(f"Rating: {rating} ({score:.1f}/10)", style=rating_style)
        
        title = f"{service_style['emoji']} {service_name.upper()} Performance"
        
        return Panel(
            bubble_content,
            title=title,
            border_style=service_style["border_style"],
            padding=(1, 2),
            title_align="left"
        )
    
    def _truncate_text(self, text: str, max_length: int) -> str:
        """Intelligently truncate text for display
        
        Args:
            text: Text to truncate
            max_length: Maximum length
            
        Returns:
            Truncated text with ellipsis if needed
        """
        if len(text) <= max_length:
            return text
        
        # Try to truncate at word boundary
        truncated = text[:max_length]
        last_space = truncated.rfind(' ')
        
        if last_space > max_length * 0.8:  # If we can find a reasonable word boundary
            return truncated[:last_space] + "..."
        else:
            return truncated[:-3] + "..."
    
    def get_service_style(self, service_name: str) -> Dict[str, str]:
        """Get the styling configuration for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Service styling dictionary
        """
        return self.SERVICE_STYLES.get(service_name, self.SERVICE_STYLES["vllm"])
