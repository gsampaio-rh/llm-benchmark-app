"""
ThreeWayPanel - Reusable three-column layout component.

This component provides a consistent three-column layout that can be used for
any comparison use case, not just AI service comparisons.
"""

from typing import Optional, Tuple, Literal
from rich.layout import Layout
from rich.panel import Panel
from rich.console import RenderableType
from rich.text import Text

from ..core.base_visualizer import BaseVisualizer


class ThreeWayPanel(BaseVisualizer):
    """🎯 REUSABLE: Three-column layout for any comparison use case"""
    
    def __init__(self, 
                 left_title: str = "Left", 
                 center_title: str = "Center", 
                 right_title: str = "Right",
                 ratios: Tuple[int, int, int] = (1, 1, 1),
                 border_styles: Tuple[str, str, str] = ("blue", "green", "orange3")):
        """Initialize the three-way panel
        
        Args:
            left_title: Title for the left column
            center_title: Title for the center column
            right_title: Title for the right column
            ratios: Width ratios for the columns (left, center, right)
            border_styles: Border colors for each column
        """
        super().__init__()
        self.left_title = left_title
        self.center_title = center_title
        self.right_title = right_title
        self.ratios = ratios
        self.border_styles = border_styles
        self.layout = self._create_layout()
    
    def _create_layout(self) -> Layout:
        """Create the three-column layout"""
        layout = Layout()
        
        # Create the main split
        layout.split_row(
            Layout(name="left", ratio=self.ratios[0]),
            Layout(name="center", ratio=self.ratios[1]),
            Layout(name="right", ratio=self.ratios[2])
        )
        
        # Initialize with empty panels
        layout["left"].update(Panel("", title=self.left_title, border_style=self.border_styles[0]))
        layout["center"].update(Panel("", title=self.center_title, border_style=self.border_styles[1]))
        layout["right"].update(Panel("", title=self.right_title, border_style=self.border_styles[2]))
        
        return layout
    
    def render(self, data=None) -> Layout:
        """Render the three-way panel layout
        
        Args:
            data: Optional data (not used in base implementation)
            
        Returns:
            The Rich layout for display
        """
        return self.layout
    
    def update_column(self, position: Literal["left", "center", "right"], content: RenderableType, title: Optional[str] = None):
        """Update specific column content
        
        Args:
            position: Which column to update
            content: New content for the column
            title: Optional new title for the column
        """
        if position not in ["left", "center", "right"]:
            raise ValueError(f"Invalid position: {position}. Must be 'left', 'center', or 'right'")
        
        # Determine border style
        style_map = {
            "left": self.border_styles[0],
            "center": self.border_styles[1], 
            "right": self.border_styles[2]
        }
        
        # Determine title
        if title is None:
            title_map = {
                "left": self.left_title,
                "center": self.center_title,
                "right": self.right_title
            }
            title = title_map[position]
        
        # Update the column
        panel = Panel(content, title=title, border_style=style_map[position])
        self.layout[position].update(panel)
    
    def update_all_columns(self, 
                          left_content: RenderableType,
                          center_content: RenderableType, 
                          right_content: RenderableType,
                          left_title: Optional[str] = None,
                          center_title: Optional[str] = None,
                          right_title: Optional[str] = None):
        """Update all three columns at once
        
        Args:
            left_content: Content for left column
            center_content: Content for center column
            right_content: Content for right column
            left_title: Optional title for left column
            center_title: Optional title for center column
            right_title: Optional title for right column
        """
        self.update_column("left", left_content, left_title)
        self.update_column("center", center_content, center_title)
        self.update_column("right", right_content, right_title)
    
    def get_layout(self) -> Layout:
        """Get the Rich layout for live display
        
        Returns:
            The Rich layout object
        """
        return self.layout
    
    def reset_columns(self):
        """Reset all columns to empty state"""
        self.update_column("left", "")
        self.update_column("center", "")
        self.update_column("right", "")
    
    def set_loading_state(self, position: Literal["left", "center", "right"], message: str = "Loading..."):
        """Set a column to loading state
        
        Args:
            position: Which column to set to loading
            message: Loading message to display
        """
        loading_text = Text(message, style="dim")
        loading_text.append("\n● ● ●", style="blink")
        self.update_column(position, loading_text)
