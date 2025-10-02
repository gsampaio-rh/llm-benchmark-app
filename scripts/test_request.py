#!/usr/bin/env python3
"""
🧪 Single Request Tester
========================

This script sends a test request to a specific LLM engine and model, measuring
performance metrics and displaying the results. Perfect for testing individual
model configurations before running full benchmarks.

Usage:
    python scripts/test_request.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich import box
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.syntax import Syntax

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.core.metrics_collector import initialize_metrics_collector
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter


console = Console()


def print_header() -> None:
    """Display a beautiful header for the script."""
    header = Text()
    header.append("🧪 ", style="bold blue")
    header.append("Single Request Tester", style="bold cyan")
    
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]Test a single request to any LLM engine and model.[/bold cyan]\n\n"
            "✓ Measures end-to-end latency\n"
            "✓ Tracks token generation rates\n"
            "✓ Displays detailed metrics\n"
            "✓ Shows the model's response"
        ),
        title=header,
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


async def setup_connection_manager() -> tuple[ConnectionManager, object]:
    """Setup and initialize the connection manager and metrics collector."""
    console.print("[bold cyan]Step 1/4:[/bold cyan] Initializing system...\n")
    
    config_manager = ConfigManager()
    connection_manager = ConnectionManager()
    
    # Register adapter classes
    connection_manager.register_adapter_class("ollama", OllamaAdapter)
    connection_manager.register_adapter_class("vllm", VLLMAdapter)
    connection_manager.register_adapter_class("tgi", TGIAdapter)
    
    # Initialize metrics collector
    metrics_collector = initialize_metrics_collector(connection_manager)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Connecting to engines...", total=None)
        benchmark_config = config_manager.load_benchmark_config()
        await connection_manager.register_engines_from_config(benchmark_config)
        progress.update(task, completed=True)
    
    console.print("  ✅ System initialized\n")
    return connection_manager, metrics_collector


async def select_engine_and_model(connection_manager: ConnectionManager) -> tuple[str, str, str]:
    """Interactive selection of engine and model."""
    console.print("[bold cyan]Step 2/4:[/bold cyan] Select engine and model...\n")
    
    # Get available engines
    engines = list(connection_manager.adapters.keys())
    
    if not engines:
        console.print("[red]❌ No engines available![/red]")
        raise RuntimeError("No engines configured")
    
    # Display available engines
    engines_table = Table(title="🚀 Available Engines", box=box.ROUNDED, title_style="bold cyan")
    engines_table.add_column("#", style="cyan", justify="center")
    engines_table.add_column("Engine Name", style="magenta")
    engines_table.add_column("Type", style="blue")
    engines_table.add_column("Status", justify="center")
    
    for idx, engine_name in enumerate(engines, 1):
        adapter = connection_manager.get_adapter(engine_name)
        engines_table.add_row(
            str(idx),
            engine_name,
            adapter.config.engine_type if adapter else "unknown",
            "✅ Ready"
        )
    
    console.print(engines_table)
    console.print()
    
    # Select engine
    while True:
        engine_choice = Prompt.ask(
            "Select engine by number or name",
            default="1"
        )
        
        # Try numeric selection
        try:
            idx = int(engine_choice) - 1
            if 0 <= idx < len(engines):
                selected_engine = engines[idx]
                break
        except ValueError:
            pass
        
        # Try name selection
        if engine_choice in engines:
            selected_engine = engine_choice
            break
        
        console.print("[red]Invalid selection. Please try again.[/red]")
    
    console.print(f"  ✅ Selected: [bold cyan]{selected_engine}[/bold cyan]\n")
    
    # Get available models
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task(f"Discovering models on {selected_engine}...", total=None)
        models = await connection_manager.discover_models(selected_engine)
        progress.update(task, completed=True)
    
    console.print()
    
    if not models:
        console.print("[yellow]⚠️  No models found. You can still enter a model name manually.[/yellow]\n")
        model_name = Prompt.ask("Enter model name")
        return selected_engine, model_name, "manual"
    
    # Display available models
    models_table = Table(title=f"📦 Models on {selected_engine}", box=box.ROUNDED, title_style="bold cyan")
    models_table.add_column("#", style="cyan", justify="center")
    models_table.add_column("Model Name", style="magenta")
    models_table.add_column("Family", style="blue")
    models_table.add_column("Size", style="green")
    models_table.add_column("Status", justify="center")
    
    for idx, model in enumerate(models[:10], 1):  # Show first 10
        status = "✅" if model.is_available else "❌"
        models_table.add_row(
            str(idx),
            model.name,
            model.family or "Unknown",
            model.size or "Unknown",
            status
        )
    
    if len(models) > 10:
        models_table.add_row("...", f"({len(models) - 10} more)", "", "", "")
    
    console.print(models_table)
    console.print()
    
    # Select model
    while True:
        model_choice = Prompt.ask(
            "Select model by number or name",
            default="1"
        )
        
        # Try numeric selection
        try:
            idx = int(model_choice) - 1
            if 0 <= idx < len(models):
                selected_model = models[idx].name
                model_family = models[idx].family or "Unknown"
                break
        except ValueError:
            pass
        
        # Try name selection
        matching_models = [m for m in models if m.name == model_choice]
        if matching_models:
            selected_model = model_choice
            model_family = matching_models[0].family or "Unknown"
            break
        
        console.print("[red]Invalid selection. Please try again.[/red]")
    
    console.print(f"  ✅ Selected: [bold cyan]{selected_model}[/bold cyan] ({model_family})\n")
    
    return selected_engine, selected_model, model_family


def get_prompt() -> str:
    """Get the prompt from user."""
    console.print("[bold cyan]Step 3/4:[/bold cyan] Enter your prompt...\n")
    
    # Show example prompts
    examples = Panel(
        Text.from_markup(
            "[dim]Example prompts:[/dim]\n"
            "• Explain quantum computing in simple terms\n"
            "• Write a Python function to calculate fibonacci\n"
            "• What are the benefits of async programming?"
        ),
        title="💡 Suggestions",
        border_style="dim",
        box=box.ROUNDED
    )
    console.print(examples)
    console.print()
    
    prompt = Prompt.ask(
        "Enter your prompt",
        default="Explain what an LLM is in one sentence"
    )
    
    console.print()
    return prompt


async def send_request_and_display_results(
    connection_manager: ConnectionManager,
    metrics_collector: object,
    engine_name: str,
    model_name: str,
    prompt: str
) -> None:
    """Send the request and display results."""
    console.print("[bold cyan]Step 4/4:[/bold cyan] Sending request...\n")
    
    # Start metrics collection
    if not metrics_collector.current_collection:
        metrics_collector.start_collection("Single request test")
    
    # Send request with progress indicator
    start_time = datetime.now()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console
    ) as progress:
        task = progress.add_task(
            f"Sending request to {engine_name}...",
            total=100
        )
        
        # Simulate progress updates (since we can't track real progress easily)
        async def update_progress():
            for i in range(0, 95, 5):
                await asyncio.sleep(0.1)
                progress.update(task, completed=i)
        
        progress_task = asyncio.create_task(update_progress())
        
        try:
            result = await metrics_collector.collect_single_request_metrics(
                engine_name, prompt, model_name
            )
            progress_task.cancel()
            progress.update(task, completed=100)
        except Exception:
            progress_task.cancel()
            raise
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    console.print()
    
    # Display results
    if result.success:
        # Response panel
        response_text = result.response
        if len(response_text) > 500:
            response_text = response_text[:497] + "..."
        
        console.print(Panel(
            Syntax(response_text, "text", theme="monokai", word_wrap=True),
            title="💬 Model Response",
            border_style="green",
            box=box.ROUNDED
        ))
        console.print()
        
        # Metrics table
        if result.parsed_metrics:
            metrics = result.parsed_metrics
            
            metrics_table = Table(
                title="📊 Performance Metrics",
                box=box.ROUNDED,
                title_style="bold cyan",
                show_header=True,
                header_style="bold magenta"
            )
            
            metrics_table.add_column("Metric", style="cyan")
            metrics_table.add_column("Value", style="green", justify="right")
            metrics_table.add_column("Details", style="dim")
            
            # Add metrics rows
            metrics_table.add_row(
                "Total Duration",
                f"{metrics.total_duration:.3f}s",
                "End-to-end request time"
            )
            
            if metrics.load_duration:
                metrics_table.add_row(
                    "Load Duration",
                    f"{metrics.load_duration:.3f}s",
                    "Model setup time"
                )
            
            if metrics.prompt_eval_count:
                metrics_table.add_row(
                    "Input Tokens",
                    f"{metrics.prompt_eval_count}",
                    "Tokens in prompt"
                )
            
            if metrics.prompt_eval_duration:
                metrics_table.add_row(
                    "Prompt Processing Time",
                    f"{metrics.prompt_eval_duration:.3f}s",
                    "Time to process input"
                )
            
            if metrics.prompt_token_rate:
                metrics_table.add_row(
                    "Prompt Token Rate",
                    f"{metrics.prompt_token_rate:.1f} tok/s",
                    "Input processing speed"
                )
            
            if metrics.eval_count:
                metrics_table.add_row(
                    "Output Tokens",
                    f"{metrics.eval_count}",
                    "Tokens in response"
                )
            
            if metrics.eval_duration:
                metrics_table.add_row(
                    "Generation Time",
                    f"{metrics.eval_duration:.3f}s",
                    "Time to generate output"
                )
            
            if metrics.response_token_rate:
                metrics_table.add_row(
                    "Response Token Rate",
                    f"{metrics.response_token_rate:.1f} tok/s",
                    "Output generation speed"
                )
            
            if metrics.first_token_latency:
                metrics_table.add_row(
                    "First Token Latency",
                    f"{metrics.first_token_latency:.3f}s",
                    "Time to first output token"
                )
            
            if metrics.inter_token_latency:
                metrics_table.add_row(
                    "Inter-token Latency",
                    f"{metrics.inter_token_latency:.4f}s",
                    "Average time per token"
                )
            
            console.print(metrics_table)
        
        # Success summary
        console.print()
        console.print(Panel(
            Text.from_markup(
                f"[bold green]✅ Request completed successfully![/bold green]\n\n"
                f"[bold]Engine:[/bold] {engine_name}\n"
                f"[bold]Model:[/bold] {model_name}\n"
                f"[bold]Actual Duration:[/bold] {duration:.2f}s"
            ),
            title="🎉 Success",
            border_style="green",
            box=box.ROUNDED
        ))
        
    else:
        # Error display
        console.print(Panel(
            Text.from_markup(
                f"[bold red]❌ Request failed[/bold red]\n\n"
                f"[bold]Engine:[/bold] {engine_name}\n"
                f"[bold]Model:[/bold] {model_name}\n"
                f"[bold]Error:[/bold] {result.error_message}"
            ),
            title="❌ Error",
            border_style="red",
            box=box.ROUNDED
        ))


def print_next_steps(export_path: str) -> None:
    """Print next steps for the user."""
    console.print()
    console.print(Panel(
        Text.from_markup(
            f"[bold]Metrics exported to:[/bold]\n"
            f"[cyan]{export_path}[/cyan]\n\n"
            "[bold]What's next?[/bold]\n\n"
            "1. Run another test: [cyan]python scripts/test_request.py[/cyan]\n"
            "2. Run full benchmark: [cyan]python scripts/run_benchmark.py[/cyan]\n"
            "3. Check engine health: [cyan]python scripts/check_engines.py[/cyan]"
        ),
        title="🎯 Next Steps",
        border_style="cyan",
        box=box.ROUNDED
    ))


async def main() -> None:
    """Main execution function."""
    print_header()
    
    connection_manager = None
    try:
        # Setup
        connection_manager, metrics_collector = await setup_connection_manager()
        
        # Select engine and model
        engine_name, model_name, model_family = await select_engine_and_model(connection_manager)
        
        # Get prompt
        prompt = get_prompt()
        
        # Send request and display results
        await send_request_and_display_results(
            connection_manager, metrics_collector, engine_name, model_name, prompt
        )
        
        # Auto-export metrics
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_path = f"benchmark_results/test_request_{timestamp}.json"
        try:
            exported_file = metrics_collector.export_metrics(export_path, "json")
            export_path = str(exported_file)
        except Exception as e:
            console.print(f"\n[yellow]⚠️  Could not export metrics: {e}[/yellow]")
            export_path = "Not exported"
        
        # Print next steps
        print_next_steps(export_path)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error:[/red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection_manager:
            try:
                await connection_manager.close_all()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())

