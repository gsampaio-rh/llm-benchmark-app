#!/usr/bin/env python3
"""
🏁 Parallel Engine Race Demo
========================================

Watch all engines answer the same question simultaneously!
Beautiful visual demonstration of parallel execution.
"""

import asyncio
import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text
from rich import box
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter

console = Console()


def print_header():
    """Print demo header."""
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold magenta]🏁 Parallel Engine Race Demo[/bold magenta]\n\n"
            "[bold]Watch 3 engines answer the same question simultaneously![/bold]\n\n"
            "This demonstrates TRUE parallel execution:\n"
            "• All engines start at the same time\n"
            "• Each streams tokens independently\n"
            "• You see them racing in real-time\n\n"
            "[dim]The fastest engine wins! 🏆[/dim]"
        ),
        box=box.DOUBLE,
        border_style="magenta",
        padding=(1, 2)
    ))
    console.print()


def create_race_display(engine_states: dict, start_time: float) -> Layout:
    """
    Create racing display showing all engines side-by-side.
    
    Args:
        engine_states: Dict with engine states
        start_time: When the race started
    """
    layout = Layout()
    
    # Title bar
    layout.split_column(
        Layout(name="header", size=5),
        Layout(name="engines")
    )
    
    # Header with elapsed time
    elapsed = time.time() - start_time
    all_done = all(s.get("completed", False) for s in engine_states.values())
    
    header_text = Text()
    header_text.append("⏱️  ", style="bold yellow")
    header_text.append(f"Elapsed: {elapsed:.1f}s", style="bold white")
    
    if all_done:
        header_text.append("  ", style="")
        header_text.append("🏁 RACE COMPLETE!", style="bold green")
        # Find winner (fastest)
        winner = min(
            [(name, s.get("completion_time", float('inf'))) for name, s in engine_states.items()],
            key=lambda x: x[1]
        )
        if winner[1] != float('inf'):
            header_text.append(f"  🏆 Winner: {winner[0]} ({winner[1]:.1f}s)", style="bold yellow")
    else:
        header_text.append("  ", style="")
        header_text.append("🏁 RACING...", style="bold yellow blink")
    
    layout["header"].update(Panel(
        header_text,
        border_style="yellow",
        box=box.HEAVY
    ))
    
    # Engine panels
    engine_names = list(engine_states.keys())
    if len(engine_names) == 0:
        layout["engines"].update(Panel("No engines"))
        return layout
    
    # Create columns for engines
    columns = []
    for i in range(len(engine_names)):
        columns.append(Layout(name=f"engine_{i}"))
    
    layout["engines"].split_row(*columns)
    
    # Fill each column
    for i, engine_name in enumerate(engine_names):
        state = engine_states[engine_name]
        panel = create_engine_panel(engine_name, state, start_time)
        layout["engines"][f"engine_{i}"].update(panel)
    
    return layout


def create_engine_panel(engine_name: str, state: dict, start_time: float) -> Panel:
    """Create a panel for one engine."""
    response = state.get("response", "")
    tokens = state.get("tokens", 0)
    completed = state.get("completed", False)
    error = state.get("error")
    completion_time = state.get("completion_time")
    
    content = Text()
    
    # Status line
    elapsed = time.time() - start_time
    if error:
        status_line = f"[red]❌ Error[/red]"
    elif completed:
        duration = completion_time if completion_time else elapsed
        status_line = f"[green]✅ Done in {duration:.1f}s[/green]"
    else:
        status_line = f"[yellow]● Racing... {elapsed:.1f}s[/yellow]"
    
    content.append(status_line, style="")
    content.append(f" · {tokens} tokens", style="bright_cyan")
    content.append("\n\n", style="")
    
    # Response text - show full response
    if response:
        content.append(response, style="bright_green")
        
        # Typing cursor if still going
        if not completed and not error:
            content.append(" ▋", style="bold bright_green blink")
    elif error:
        content.append(f"[red]{error[:200]}[/red]", style="")
    else:
        content.append("[dim italic]Waiting to start...[/dim italic]", style="")
    
    # Panel styling based on state
    if error:
        border_style = "red"
        title_emoji = "❌"
    elif completed:
        border_style = "green"
        title_emoji = "✅"
    else:
        border_style = "yellow"
        title_emoji = "🏃"
    
    return Panel(
        content,
        title=f"[bold]{title_emoji} {engine_name}[/bold]",
        border_style=border_style,
        box=box.ROUNDED,
        padding=(1, 1)
    )


async def run_race(connection_manager):
    """Run the parallel race demo."""
    console.print("[bold cyan]🏁 Starting The Race![/bold cyan]\n")
    
    # Get available engines
    available = connection_manager.list_engines()
    if not available:
        console.print("[red]No engines available![/red]")
        return
    
    # Limit to 3 engines
    test_engines = available[:min(3, len(available))]
    console.print(f"[bold]Racers:[/bold]")
    for i, engine in enumerate(test_engines, 1):
        console.print(f"  {i}. [cyan]{engine}[/cyan]")
    console.print()
    
    # Get models
    engine_models = {}
    for engine_name in test_engines:
        adapter = connection_manager.get_adapter(engine_name)
        models = await adapter.list_models()
        if models:
            engine_models[engine_name] = models[0].name
            console.print(f"  ✅ {engine_name}: {models[0].name}")
        else:
            console.print(f"  [yellow]⚠️  {engine_name}: No models, skipping[/yellow]")
    
    if not engine_models:
        console.print("[red]No engines with models![/red]")
        return
    
    console.print()
    
    # The question - something that generates a longer, interesting response
    question = "Write a short story (3 paragraphs) about a robot who discovers the meaning of friendship."
    
    console.print(Panel(
        Text.from_markup(
            f"[bold]The Question:[/bold]\n\n"
            f"[cyan]{question}[/cyan]"
        ),
        title="🎯 Challenge",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()
    console.print("[yellow]Starting race in 2 seconds...[/yellow]\n")
    await asyncio.sleep(2)
    
    # Initialize state
    engine_states = {
        engine: {
            "response": "",
            "tokens": 0,
            "completed": False,
            "error": None,
            "completion_time": None
        }
        for engine in engine_models.keys()
    }
    
    start_time = time.time()
    
    async def race_engine(engine_name: str) -> None:
        """One engine racing."""
        try:
            adapter = connection_manager.get_adapter(engine_name)
            model_name = engine_models[engine_name]
            
            # Token callback
            async def token_callback(token: str) -> None:
                engine_states[engine_name]["response"] += token
                engine_states[engine_name]["tokens"] += 1
            
            # Race!
            result = await adapter.send_streaming_request(
                prompt=question,
                model=model_name,
                token_callback=token_callback,
                max_tokens=1000,
                temperature=0.8
            )
            
            # Mark completion time
            engine_states[engine_name]["completion_time"] = time.time() - start_time
            engine_states[engine_name]["completed"] = True
            
            if not result.success:
                engine_states[engine_name]["error"] = result.error_message
                
        except Exception as e:
            engine_states[engine_name]["error"] = str(e)
            engine_states[engine_name]["completion_time"] = time.time() - start_time
            engine_states[engine_name]["completed"] = True
    
    # Create tasks FIRST (this starts them immediately)
    tasks = [asyncio.create_task(race_engine(engine)) for engine in engine_models.keys()]
    
    # Give them a moment to start
    await asyncio.sleep(0.1)
    
    # NOW show the live display (engines are already running!)
    with Live(
        create_race_display(engine_states, start_time),
        console=console,
        refresh_per_second=10
    ) as live:
        # Keep updating the display while any task is running
        while not all(task.done() for task in tasks):
            live.update(create_race_display(engine_states, start_time))
            await asyncio.sleep(0.1)  # Update every 100ms
        
        # Final update to show completion
        live.update(create_race_display(engine_states, start_time))
        await asyncio.sleep(2)
    
    # Results
    console.print()
    console.print("[bold green]═" * 80 + "[/bold green]")
    console.print()
    console.print("[bold magenta]🏆 Race Results[/bold magenta]\n")
    
    # Sort by completion time
    results = [
        (name, state["completion_time"], state["tokens"], state.get("error"))
        for name, state in engine_states.items()
    ]
    results.sort(key=lambda x: x[1] if x[1] is not None else float('inf'))
    
    medals = ["🥇", "🥈", "🥉"]
    for i, (name, duration, tokens, error) in enumerate(results):
        medal = medals[i] if i < len(medals) else "  "
        if error:
            console.print(f"{medal} [red]{name}[/red]: ❌ Error")
        else:
            console.print(f"{medal} [cyan]{name}[/cyan]: {duration:.2f}s · {tokens} tokens")
    
    console.print()
    
    # Show full responses
    console.print("[bold cyan]📝 Full Responses[/bold cyan]\n")
    
    for name, state in engine_states.items():
        response = state.get("response", "")
        error = state.get("error")
        
        if error:
            console.print(Panel(
                f"[red]Error: {error}[/red]",
                title=f"[bold red]❌ {name}[/bold red]",
                border_style="red",
                box=box.ROUNDED
            ))
        else:
            console.print(Panel(
                Text(response, style="green"),
                title=f"[bold green]✅ {name}[/bold green]",
                border_style="green",
                box=box.ROUNDED,
                padding=(1, 2)
            ))
        console.print()
    
    console.print("[bold green]✅ Parallel execution demonstrated![/bold green]")
    console.print("[green]All engines ran simultaneously and independently![/green]")
    console.print()


async def main():
    """Run the demo."""
    print_header()
    
    connection_manager = None
    
    try:
        # Setup
        console.print("[bold yellow]⚙️  Setting up engines...[/bold yellow]\n")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to engines...", total=None)
            
            config_manager = ConfigManager()
            connection_manager = ConnectionManager()
            
            connection_manager.register_adapter_class("ollama", OllamaAdapter)
            connection_manager.register_adapter_class("vllm", VLLMAdapter)
            connection_manager.register_adapter_class("tgi", TGIAdapter)
            
            benchmark_config = config_manager.load_benchmark_config()
            await connection_manager.register_engines_from_config(benchmark_config)
            
            progress.update(task, completed=True)
        
        available = connection_manager.list_engines()
        console.print(f"\n[green]✅ {len(available)} engines ready![/green]\n")
        
        # Run the race!
        await run_race(connection_manager)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Race cancelled[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error:[/red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection_manager:
            try:
                console.print("[dim]Closing connections...[/dim]")
                await connection_manager.close_all()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())

