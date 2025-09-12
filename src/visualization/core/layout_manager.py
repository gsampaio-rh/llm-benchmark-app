"""
Layout management for Rich console displays.

This module provides utilities for creating and managing Rich layouts,
including responsive layouts, column management, and consistent styling.
"""

from typing import List, Optional, Tuple, Union
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console, RenderableType


class LayoutManager:
    """Manages Rich layout creation and organization"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the layout manager
        
        Args:
            console: Rich console instance
        """
        self.console = console or Console()
    
    def create_three_column_layout(self, 
                                 left_title: str = "Left", 
                                 center_title: str = "Center", 
                                 right_title: str = "Right",
                                 ratios: Tuple[int, int, int] = (1, 1, 1)) -> Layout:
        """Create a three-column layout
        
        Args:
            left_title: Title for the left column
            center_title: Title for the center column  
            right_title: Title for the right column
            ratios: Width ratios for the columns (left, center, right)
            
        Returns:
            Configured Rich Layout
        """
        layout = Layout()
        
        # Create the main split
        layout.split_row(
            Layout(name="left", ratio=ratios[0]),
            Layout(name="center", ratio=ratios[1]),
            Layout(name="right", ratio=ratios[2])
        )
        
        # Initialize with empty panels
        layout["left"].update(Panel("", title=left_title, border_style="blue"))
        layout["center"].update(Panel("", title=center_title, border_style="green"))
        layout["right"].update(Panel("", title=right_title, border_style="orange3"))
        
        return layout
    
    def create_two_column_layout(self,
                               left_title: str = "Left",
                               right_title: str = "Right", 
                               ratio: Tuple[int, int] = (1, 1)) -> Layout:
        """Create a two-column layout
        
        Args:
            left_title: Title for the left column
            right_title: Title for the right column
            ratio: Width ratio for the columns (left, right)
            
        Returns:
            Configured Rich Layout
        """
        layout = Layout()
        
        layout.split_row(
            Layout(name="left", ratio=ratio[0]),
            Layout(name="right", ratio=ratio[1])
        )
        
        layout["left"].update(Panel("", title=left_title, border_style="blue"))
        layout["right"].update(Panel("", title=right_title, border_style="green"))
        
        return layout
    
    def create_header_body_layout(self, 
                                header_title: str = "Header",
                                body_title: str = "Content",
                                header_height: int = 3) -> Layout:
        """Create a header/body layout
        
        Args:
            header_title: Title for the header section
            body_title: Title for the body section
            header_height: Height of the header in lines
            
        Returns:
            Configured Rich Layout
        """
        layout = Layout()
        
        layout.split_column(
            Layout(name="header", size=header_height),
            Layout(name="body")
        )
        
        layout["header"].update(Panel("", title=header_title, border_style="cyan"))
        layout["body"].update(Panel("", title=body_title, border_style="blue"))
        
        return layout
    
    def update_layout_section(self, 
                            layout: Layout, 
                            section_name: str, 
                            content: RenderableType,
                            title: Optional[str] = None,
                            border_style: str = "blue"):
        """Update a specific section of a layout
        
        Args:
            layout: The layout to update
            section_name: Name of the section to update
            content: New content for the section
            title: Optional new title for the section
            border_style: Border style for the panel
        """
        if section_name in layout:
            if title:
                panel = Panel(content, title=title, border_style=border_style)
            else:
                panel = Panel(content, border_style=border_style)
            layout[section_name].update(panel)
    
    def create_grid_layout(self, 
                         rows: int, 
                         cols: int,
                         titles: Optional[List[List[str]]] = None) -> Layout:
        """Create a grid layout with specified rows and columns
        
        Args:
            rows: Number of rows
            cols: Number of columns
            titles: Optional 2D array of titles for each cell
            
        Returns:
            Configured Rich Layout
        """
        layout = Layout()
        
        # Create row layouts
        row_layouts = []
        for i in range(rows):
            row_layout = Layout()
            col_layouts = []
            
            for j in range(cols):
                col_name = f"cell_{i}_{j}"
                col_layout = Layout(name=col_name)
                
                # Set title if provided
                title = ""
                if titles and i < len(titles) and j < len(titles[i]):
                    title = titles[i][j]
                
                col_layout.update(Panel("", title=title, border_style="blue"))
                col_layouts.append(col_layout)
            
            row_layout.split_row(*col_layouts)
            row_layouts.append(row_layout)
        
        layout.split_column(*row_layouts)
        return layout
    
    def get_layout_info(self, layout: Layout) -> dict:
        """Get information about a layout structure
        
        Args:
            layout: Layout to analyze
            
        Returns:
            Dictionary with layout information
        """
        def analyze_layout(layout_node, path=""):
            info = {
                "name": getattr(layout_node, "name", "root"),
                "path": path,
                "children": []
            }
            
            if hasattr(layout_node, "_split") and layout_node._split:
                for i, child in enumerate(layout_node._split.children):
                    child_path = f"{path}/{child.name}" if path else child.name
                    child_info = analyze_layout(child, child_path)
                    info["children"].append(child_info)
            
            return info
        
        return analyze_layout(layout)
