#!/usr/bin/env python3
"""
Test script to debug vLLM streaming issues.

This script tests vLLM streaming with verbose logging to identify
why tokens aren't being received in the dashboard.

Usage:
    python scripts/test_vllm_streaming.py
"""

import asyncio
import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.adapters.vllm_adapter import VLLMAdapter

# Enable verbose logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

console = Console()


async def test_vllm_streaming():
    """Test vLLM streaming with debug output."""
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]🔍 vLLM Streaming Debug Test[/bold cyan]\n\n"
            "This script will test vLLM streaming with verbose logging."
        ),
        border_style="cyan"
    ))
    
    # Setup
    config_manager = ConfigManager()
    connection_manager = ConnectionManager()
    
    connection_manager.register_adapter_class("vllm", VLLMAdapter)
    
    benchmark_config = config_manager.load_benchmark_config()
    await connection_manager.register_engines_from_config(benchmark_config)
    
    # Get vLLM adapter
    adapter = connection_manager.get_adapter("vllm")
    if not adapter:
        console.print("[red]❌ vLLM engine not found![/red]")
        return
    
    console.print("[green]✅ vLLM adapter initialized[/green]\n")
    
    # Test prompt
    test_prompt = "Write a short story about a robot."
    model = "Qwen/Qwen2.5-7B"
    
    console.print(f"[bold]Testing with:[/bold]")
    console.print(f"  Model: {model}")
    console.print(f"  Prompt: {test_prompt}")
    console.print()
    
    # Track tokens
    tokens_received = []
    
    async def token_callback(token: str):
        """Callback for each token."""
        tokens_received.append(token)
        console.print(f"[green]Token #{len(tokens_received)}:[/green] {repr(token[:50])}")
    
    try:
        console.print("[yellow]🔴 Starting streaming request...[/yellow]\n")
        
        result = await adapter.send_streaming_request(
            prompt=test_prompt,
            model=model,
            token_callback=token_callback,
            max_tokens=100,
            temperature=0.7
        )
        
        console.print()
        if result.success:
            console.print("[bold green]✅ Streaming completed successfully![/bold green]")
            console.print(f"[bold]Tokens received:[/bold] {len(tokens_received)}")
            console.print(f"[bold]Total response length:[/bold] {len(result.response)} chars")
            console.print()
            console.print("[bold]Full response:[/bold]")
            console.print(Panel(result.response, border_style="green"))
            
            if result.parsed_metrics:
                console.print()
                console.print("[bold]Metrics:[/bold]")
                console.print(f"  TTFT: {result.parsed_metrics.first_token_latency:.3f}s" if result.parsed_metrics.first_token_latency else "  TTFT: N/A")
                console.print(f"  Token rate: {result.parsed_metrics.response_token_rate:.2f} tok/s" if result.parsed_metrics.response_token_rate else "  Token rate: N/A")
                console.print(f"  Total duration: {result.parsed_metrics.total_duration:.2f}s" if result.parsed_metrics.total_duration else "  Total duration: N/A")
        else:
            console.print(f"[red]❌ Error:[/red] {result.error_message}")
        
        # Summary
        console.print()
        console.print("[bold cyan]📊 Summary:[/bold cyan]")
        console.print(f"  Tokens via callback: {len(tokens_received)}")
        console.print(f"  Response length: {len(result.response) if result.response else 0} chars")
        console.print(f"  Success: {result.success}")
        
        if len(tokens_received) == 0 and result.success:
            console.print()
            console.print("[bold yellow]⚠️  WARNING:[/bold yellow] No tokens received via callback!")
            console.print("  This indicates the streaming callback is not being called.")
            console.print("  Check the debug logs above for details.")
        
    except Exception as e:
        console.print(f"[red]❌ Exception:[/red] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await connection_manager.close_all()


async def main():
    """Main execution."""
    try:
        await test_vllm_streaming()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error:[/red] {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    console.print()
    console.print("[dim]Logging level: DEBUG (verbose output enabled)[/dim]")
    console.print()
    asyncio.run(main())

