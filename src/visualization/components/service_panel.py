"""
ServicePanel - Individual service display component.

This component creates formatted panels for displaying service information,
including technical details, status, and response content.
"""

from typing import Optional, Dict, Any
from rich.panel import Panel
from rich.text import Text

from ...race.models import RaceParticipant, ServicePersonality, EngineInfo
from ..core.base_visualizer import BaseVisualizer


class ServicePanel(BaseVisualizer):
    """Individual service display with personality and technical info"""
    
    def __init__(self, participant: RaceParticipant):
        """Initialize the service panel
        
        Args:
            participant: The race participant to display
        """
        super().__init__()
        self.participant = participant
        
        # Service emoji mapping
        self.service_emojis = {
            "vllm": "🔵",
            "tgi": "🟢", 
            "ollama": "🟠"
        }
    
    def render(self, data: Optional[Dict[str, Any]] = None) -> Panel:
        """Render the service panel
        
        Args:
            data: Optional data containing status info
                - status: Current status text
                - status_color: Color for status text  
                - show_response: Whether to show response content
                
        Returns:
            Formatted Rich Panel
        """
        # Extract data parameters
        if data is None:
            data = {}
        
        status = data.get("status", "Ready")
        status_color = data.get("status_color", "white")
        show_response = data.get("show_response", False)
        
        return self.create_panel(status, status_color, show_response)
    
    def create_panel(self, status: str, status_color: str, show_response: bool = False) -> Panel:
        """Create formatted panel for service display
        
        Args:
            status: Current status text
            status_color: Color for the status text
            show_response: Whether to show the response content
            
        Returns:
            Styled Rich Panel with service information
        """
        personality = self.participant.personality
        personality_name, color, description = personality.value
        engine_info = self.participant.engine_info
        
        # Get service emoji
        emoji = self.service_emojis.get(self.participant.name, "⚪")
        
        # Header with service info
        header = Text()
        header.append(f"{emoji} {self.participant.name.upper()}", style=f"bold {color}")
        header.append(f"\n{description}", style="dim")
        
        # Technical Information Section
        tech_info = self.format_technical_info()
        
        # Status
        status_text = Text(f"\n\n📊 Status: {status}", style=status_color)
        
        # Build content
        content = Text()
        content.append_text(header)
        content.append_text(tech_info)
        content.append_text(status_text)
        
        # Response preview if available and requested
        if show_response and self.participant.current_response:
            response_content = self.format_response_content()
            content.append_text(response_content)
        
        return Panel(
            content,
            border_style=color,
            title=f"{emoji} {self.participant.name.upper()}",
            title_align="left"
        )
    
    def format_technical_info(self) -> Text:
        """Format engine technical information
        
        Returns:
            Formatted technical information as Rich Text
        """
        engine_info = self.participant.engine_info
        
        tech_info = Text()
        tech_info.append(f"\n🔧 Technical Info:", style="bold cyan")
        tech_info.append(f"\n• URL: {engine_info.engine_url}", style="dim")
        
        # Only show model if we have real data
        if engine_info.model_name and engine_info.model_name not in ["Unknown Model", "Config unavailable"]:
            tech_info.append(f"\n• Model: {engine_info.model_name}", style="dim")
        
        # Only show version if we have real data
        if engine_info.version and engine_info.version not in ["Unknown", "vLLM Engine", "TGI Engine", "Ollama Engine"]:
            tech_info.append(f"\n• Version: {engine_info.version}", style="dim")
        
        # Only show GPU if we have real data
        if engine_info.gpu_type and engine_info.gpu_type != "Unknown":
            if engine_info.memory_gb > 0:
                tech_info.append(f"\n• GPU: {engine_info.gpu_type} ({engine_info.memory_gb}GB)", style="dim")
            else:
                tech_info.append(f"\n• GPU: {engine_info.gpu_type}", style="dim")
        
        # Only show batch size if we have real data
        if engine_info.max_batch_size > 0:
            tech_info.append(f"\n• Batch Size: {engine_info.max_batch_size}", style="dim")
        
        # Only show context if we have real data
        if engine_info.max_context_length > 0:
            tech_info.append(f"\n• Context: {engine_info.max_context_length} tokens", style="dim")
        
        # Only show deployment if we have real data
        if engine_info.deployment and engine_info.deployment != "Unknown":
            tech_info.append(f"\n• Deploy: {engine_info.deployment}", style="dim")
        
        return tech_info
    
    def format_response_content(self, max_chars: int = 1000) -> Text:
        """Format response content with proper truncation
        
        Args:
            max_chars: Maximum characters to show
            
        Returns:
            Formatted response content as Rich Text
        """
        content = Text()
        content.append("\n\n")
        
        # Truncate response if too long
        response_text = self.participant.current_response
        if len(response_text) > max_chars:
            response_text = response_text[:max_chars-3] + "..."
        
        content.append("💬 Response:", style="bold dim")
        content.append(f"\n{response_text}", style="dim")
        
        return content
    
    def create_loading_panel(self, message: str = "Processing...") -> Panel:
        """Create a loading state panel
        
        Args:
            message: Loading message to display
            
        Returns:
            Panel showing loading state
        """
        personality_name, color, description = self.participant.personality.value
        emoji = self.service_emojis.get(self.participant.name, "⚪")
        
        content = Text()
        content.append(f"{emoji} {self.participant.name.upper()}", style=f"bold {color}")
        content.append(f"\n{description}", style="dim")
        content.append(f"\n\n{message}", style="yellow")
        content.append("\n● ● ●", style="blink")
        
        return Panel(
            content,
            border_style=color,
            title=f"{emoji} {self.participant.name.upper()}",
            title_align="left"
        )
    
    def create_error_panel(self, error_message: str) -> Panel:
        """Create an error state panel
        
        Args:
            error_message: Error message to display
            
        Returns:
            Panel showing error state
        """
        personality_name, color, description = self.participant.personality.value
        emoji = self.service_emojis.get(self.participant.name, "⚪")
        
        content = Text()
        content.append(f"{emoji} {self.participant.name.upper()}", style=f"bold {color}")
        content.append(f"\n{description}", style="dim")
        content.append(f"\n\n❌ Error: {error_message}", style="red")
        
        return Panel(
            content,
            border_style="red",
            title=f"{emoji} {self.participant.name.upper()} - ERROR",
            title_align="left"
        )
    
    def update_participant(self, participant: RaceParticipant):
        """Update the participant information
        
        Args:
            participant: New participant data
        """
        self.participant = participant
