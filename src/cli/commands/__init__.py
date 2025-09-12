"""
Command handlers for the vLLM benchmarking CLI
Each command is implemented in a separate module for maintainability
"""

# Import all command handlers for easy access
from .benchmark_cmd import benchmark
from .demo_cmd import demo
from .config_cmd import config, init
from .service_cmd import discover, test
from .results_cmd import results, visualize
from .inspect_cmd import inspect

__all__ = [
    'benchmark',
    'demo', 
    'config',
    'init',
    'discover',
    'test',
    'results',
    'visualize',
    'inspect'
]
