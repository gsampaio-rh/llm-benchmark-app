"""
Visualization module for real-time streaming and metrics display.

This module provides beautiful, interactive visualizations for benchmark
results including live streaming token displays and performance metrics.
"""

from .live_display import StreamingDisplay, StreamConfig, StreamingMetrics

__all__ = ["StreamingDisplay", "StreamConfig", "StreamingMetrics"]

