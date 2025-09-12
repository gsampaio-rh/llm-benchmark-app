"""
Async utilities for CLI command execution
Handles async operations in Click commands consistently
"""

import asyncio
import functools
from typing import Callable, Any
from rich.console import Console


def run_async_command(async_func: Callable) -> Callable:
    """Decorator to run async functions in Click commands
    
    This decorator handles the asyncio.run() boilerplate for CLI commands
    that need to call async functions.
    
    Args:
        async_func: The async function to wrap
        
    Returns:
        Synchronous wrapper function
    """
    @functools.wraps(async_func)
    def wrapper(*args, **kwargs):
        return asyncio.run(async_func(*args, **kwargs))
    return wrapper


async def safe_async_execute(console: Console, coro, error_message: str = "Operation failed"):
    """Safely execute an async operation with error handling
    
    Args:
        console: Rich console for output
        coro: Coroutine to execute
        error_message: Message to display on error
        
    Returns:
        Result of the coroutine or None on error
    """
    try:
        return await coro
    except Exception as e:
        console.print(f"[red]❌ {error_message}: {str(e)}[/red]")
        return None


def create_async_context(console: Console):
    """Create a context manager for async operations in CLI commands
    
    Args:
        console: Rich console for output
        
    Returns:
        AsyncContextManager for handling async operations
    """
    class AsyncContext:
        def __init__(self, console: Console):
            self.console = console
            
        async def __aenter__(self):
            return self
            
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            if exc_type:
                self.console.print(f"[red]❌ Async operation failed: {exc_val}[/red]")
                
        async def execute(self, coro, error_message: str = "Operation failed"):
            """Execute coroutine with error handling"""
            return await safe_async_execute(self.console, coro, error_message)
    
    return AsyncContext(console)
