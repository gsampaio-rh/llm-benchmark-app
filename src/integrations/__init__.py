"""
Integrations module for external service adapters and interfaces.

This module provides clean abstractions and adapters for external dependencies,
including API clients, service discovery, and configuration management.
"""

from .api_adapter import APIAdapter
from .service_adapter import ServiceAdapter
from .config_manager import ConfigurationManager

__all__ = [
    "APIAdapter",
    "ServiceAdapter", 
    "ConfigurationManager"
]
