"""
Analytics module for performance analysis and business impact calculations.

This module contains metrics calculation, statistical analysis, and business
intelligence functionality.
"""

from .metrics import PerformanceMetrics
from .business_impact import BusinessImpactAnalyzer

__all__ = [
    "PerformanceMetrics",
    "BusinessImpactAnalyzer"
]
