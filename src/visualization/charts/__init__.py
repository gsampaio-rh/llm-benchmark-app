"""
Modern Chart Generation Module

Replaces the legacy BenchmarkVisualizer with focused, modular chart generators.
Each chart type has its own dedicated module for better maintainability.
"""

from .chart_factory import ChartFactory

# Export the main interface - ChartFactory acts as the new BenchmarkVisualizer
__all__ = [
    "ChartFactory"
]
