"""
Base visualizer classes and abstractions.

This module provides the foundational classes that all visualizers should inherit from,
establishing common patterns and interfaces for visualization components.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout


class BaseVisualizer(ABC):
    """Abstract base class for all visualizers"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the base visualizer
        
        Args:
            console: Rich console instance for output. If None, creates a new one.
        """
        self.console = console or Console()
    
    @abstractmethod
    def render(self, data: Any) -> Any:
        """Render the visualization with the given data
        
        Args:
            data: The data to visualize
            
        Returns:
            The rendered visualization (Panel, Layout, etc.)
        """
        pass
    
    def create_panel(self, content: Any, title: str, **kwargs) -> Panel:
        """Create a styled panel with consistent theming
        
        Args:
            content: Content to display in the panel
            title: Panel title
            **kwargs: Additional panel options
            
        Returns:
            Styled Rich Panel
        """
        default_kwargs = {
            "border_style": "blue",
            "title_align": "left",
            "padding": (1, 2)
        }
        default_kwargs.update(kwargs)
        
        return Panel(content, title=title, **default_kwargs)
    
    def print_panel(self, content: Any, title: str, **kwargs):
        """Print a panel to the console
        
        Args:
            content: Content to display
            title: Panel title
            **kwargs: Additional panel options
        """
        panel = self.create_panel(content, title, **kwargs)
        self.console.print(panel)


class LiveVisualizer(BaseVisualizer):
    """Base class for live/real-time visualizations"""
    
    def __init__(self, console: Optional[Console] = None, refresh_rate: float = 0.1):
        """Initialize the live visualizer
        
        Args:
            console: Rich console instance
            refresh_rate: How often to refresh the display (seconds)
        """
        super().__init__(console)
        self.refresh_rate = refresh_rate
        self.is_running = False
    
    @abstractmethod
    def create_layout(self) -> Layout:
        """Create the layout for live display
        
        Returns:
            Rich Layout object
        """
        pass
    
    @abstractmethod
    def update_layout(self, layout: Layout, data: Any):
        """Update the layout with new data
        
        Args:
            layout: The layout to update
            data: New data to display
        """
        pass
    
    def start_live_display(self, data_source: Any):
        """Start the live display (abstract method for subclasses)
        
        Args:
            data_source: Source of live data
        """
        self.is_running = True
    
    def stop_live_display(self):
        """Stop the live display"""
        self.is_running = False


class StaticVisualizer(BaseVisualizer):
    """Base class for static visualizations (charts, reports, etc.)"""
    
    def __init__(self, console: Optional[Console] = None, output_dir: Optional[str] = None):
        """Initialize the static visualizer
        
        Args:
            console: Rich console instance
            output_dir: Directory to save static outputs
        """
        super().__init__(console)
        self.output_dir = output_dir
    
    def save_output(self, content: Any, filename: str, format: str = "html"):
        """Save visualization output to file
        
        Args:
            content: Content to save
            filename: Output filename
            format: Output format (html, png, svg, etc.)
        """
        if not self.output_dir:
            return
        
        # Implementation will depend on content type and format
        # This is a placeholder for the pattern
        pass
