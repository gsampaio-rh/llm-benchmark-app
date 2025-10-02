#!/usr/bin/env python3
"""
Quick test script to verify real streaming is working.

This script sends a single streaming request to test that tokens
are being delivered in real-time.

Usage:
    python scripts/test_streaming.py
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.text import Text

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter


console = Console()


async def test_streaming(engine_name: str, model_name: str, prompt: str) -> None:
    """
    Test streaming with a single request.
    
    Args:
        engine_name: Name of engine to test
        model_name: Model to use
        prompt: Test prompt
    """
    console.print(f"\n[bold cyan]Testing Streaming:[/bold cyan] {engine_name}")
    console.print(f"[bold]Model:[/bold] {model_name}")
    console.print(f"[bold]Prompt:[/bold] {prompt}\n")
    
    # Setup
    config_manager = ConfigManager()
    connection_manager = ConnectionManager()
    
    connection_manager.register_adapter_class("ollama", OllamaAdapter)
    connection_manager.register_adapter_class("vllm", VLLMAdapter)
    connection_manager.register_adapter_class("tgi", TGIAdapter)
    
    benchmark_config = config_manager.load_benchmark_config()
    await connection_manager.register_engines_from_config(benchmark_config)
    
    # Get adapter
    adapter = connection_manager.get_adapter(engine_name)
    if not adapter:
        console.print(f"[red]❌ Engine not found: {engine_name}[/red]")
        return
    
    # Track streaming
    accumulated_text = []
    token_count = 0
    
    # Define callback
    async def token_callback(token: str) -> None:
        nonlocal token_count
        accumulated_text.append(token)
        token_count += 1
    
    try:
        # Create live display
        with Live(console=console, refresh_per_second=10) as live:
            
            async def run_stream():
                nonlocal accumulated_text, token_count
                
                # Send streaming request
                result = await adapter.send_streaming_request(
                    prompt=prompt,
                    model=model_name,
                    token_callback=lambda token: update_display(live, token),
                    max_tokens=150,
                    temperature=0.7
                )
                
                return result
            
            def update_display(live_display, token: str) -> None:
                """Update display with new token."""
                accumulated_text.append(token)
                current_text = "".join(accumulated_text)
                
                panel = Panel(
                    Text(current_text, style="green"),
                    title=f"🔴 Streaming ({len(accumulated_text)} tokens)",
                    border_style="magenta"
                )
                live_display.update(panel)
            
            # Initialize display
            live.update(Panel(
                Text("⏳ Starting stream...", style="dim"),
                title="🎬 Live Streaming Test",
                border_style="cyan"
            ))
            
            # Run the streaming request
            result = await run_stream()
        
        # Show results
        console.print()
        if result.success:
            console.print("[bold green]✅ Streaming test successful![/bold green]")
            console.print(f"[bold]Tokens received:[/bold] {len(accumulated_text)}")
            console.print(f"[bold]Total length:[/bold] {len(result.response)} characters")
            
            if result.parsed_metrics:
                console.print(f"[bold]Response token rate:[/bold] {result.parsed_metrics.response_token_rate:.2f} tok/s")
                if result.parsed_metrics.first_token_latency:
                    console.print(f"[bold]TTFT:[/bold] {result.parsed_metrics.first_token_latency:.3f}s")
        else:
            console.print(f"[red]❌ Error:[/red] {result.error_message}")
        
    except Exception as e:
        console.print(f"[red]❌ Test failed:[/red] {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await connection_manager.close_all()


async def main() -> None:
    """Main execution."""
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]🎬 Real Streaming Test[/bold cyan]\n\n"
            "This script verifies that tokens are being delivered in real-time\n"
            "from the LLM engine, not simulated after the fact."
        ),
        border_style="cyan"
    ))
    
    # Test prompt
    test_prompt = "Write a short story about a robot learning to paint. Use vivid descriptions."
    
    # Test with Ollama (most commonly available)
    console.print("\n[bold]Available engines to test:[/bold]")
    console.print("1. Ollama (default)")
    console.print("2. vLLM")
    console.print("3. TGI")
    
    choice = input("\nSelect engine (1-3, default=1): ").strip() or "1"
    
    engine_map = {
        "1": ("ollama", "llama3.2:3b"),
        "2": ("vllm", "Qwen2.5-7B"),
        "3": ("tgi", "tgi_model")
    }
    
    engine_name, model_name = engine_map.get(choice, ("ollama", "llama3.2:3b"))
    
    await test_streaming(engine_name, model_name, test_prompt)
    
    console.print("\n[bold green]✨ Test complete![/bold green]\n")


if __name__ == "__main__":
    asyncio.run(main())

