"""
Visualization module for creating interactive charts and displays.

This module contains visualization components, including core abstractions,
reusable UI components, and modern chart generation functionality.
"""

# Core abstractions
from .core import BaseVisualizer, LayoutManager, DisplayComponents

# Modern chart generation - replaces legacy BenchmarkVisualizer
from .charts import ChartFactory

# Legacy compatibility alias - drop-in replacement
BenchmarkVisualizer = ChartFactory

__all__ = [
    "BaseVisualizer",
    "LayoutManager", 
    "DisplayComponents",
    "ChartFactory",
    "BenchmarkVisualizer"  # Legacy compatibility (alias to ChartFactory)
]
