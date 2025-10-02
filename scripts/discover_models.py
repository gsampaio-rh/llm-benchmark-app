#!/usr/bin/env python3
"""
🔎 Model Discovery Explorer
===========================

This script explores and displays all available models across your configured
LLM engines. It provides detailed information about model families, sizes,
and availability status.

Usage:
    python scripts/discover_models.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, List

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.text import Text
from rich.columns import Columns
from rich.tree import Tree

from src.config.config_manager import ConfigManager, ConfigurationError
from src.core.connection_manager import ConnectionManager, ConnectionManagerError
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter
from src.models.engine_config import ModelInfo


console = Console()


def print_header() -> None:
    """Display a beautiful header for the script."""
    header = Text()
    header.append("🔎 ", style="bold blue")
    header.append("Model Discovery Explorer", style="bold cyan")
    
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]Discover and explore available models across all engines.[/bold cyan]\n\n"
            "✓ Lists all available models\n"
            "✓ Shows model families and sizes\n"
            "✓ Displays availability status\n"
            "✓ Provides model metadata"
        ),
        title=header,
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


async def setup_connection_manager() -> ConnectionManager:
    """Setup and initialize the connection manager."""
    console.print("[bold cyan]Step 1/2:[/bold cyan] Initializing engines...\n")
    
    config_manager = ConfigManager()
    connection_manager = ConnectionManager()
    
    # Register adapter classes
    connection_manager.register_adapter_class("ollama", OllamaAdapter)
    connection_manager.register_adapter_class("vllm", VLLMAdapter)
    connection_manager.register_adapter_class("tgi", TGIAdapter)
    
    try:
        benchmark_config = config_manager.load_benchmark_config()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Connecting to engines...", total=None)
            await connection_manager.register_engines_from_config(benchmark_config)
            progress.update(task, completed=True)
        
        console.print("  ✅ Engines connected\n")
        return connection_manager
        
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration error:[/red] {e}")
        raise


async def discover_all_models(connection_manager: ConnectionManager) -> Dict[str, List[ModelInfo]]:
    """Discover models from all engines."""
    console.print("[bold cyan]Step 2/2:[/bold cyan] Discovering models...\n")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Scanning all engines...", total=None)
        all_models = await connection_manager.discover_all_models()
        progress.update(task, completed=True)
    
    console.print()
    return all_models


def display_models_summary(all_models: Dict[str, List[ModelInfo]]) -> None:
    """Display a summary of discovered models."""
    if not all_models:
        console.print("[yellow]⚠️  No models found[/yellow]")
        return
    
    # Calculate totals
    total_engines = len(all_models)
    total_models = sum(len(models) for models in all_models.values())
    available_models = sum(
        sum(1 for m in models if m.is_available) 
        for models in all_models.values()
    )
    
    # Create summary panel
    summary_text = Text()
    summary_text.append(f"Engines Scanned: ", style="bold")
    summary_text.append(f"{total_engines}\n")
    summary_text.append(f"Total Models: ", style="bold")
    summary_text.append(f"{total_models}\n")
    summary_text.append(f"Available: ", style="bold green")
    summary_text.append(f"{available_models}\n")
    summary_text.append(f"Unavailable: ", style="bold red")
    summary_text.append(f"{total_models - available_models}\n")
    
    console.print(Panel(
        summary_text,
        title="📊 Discovery Summary",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


def display_models_by_engine(all_models: Dict[str, List[ModelInfo]]) -> None:
    """Display detailed models for each engine."""
    for engine_name, models in all_models.items():
        if not models:
            console.print(Panel(
                "[dim italic]No models found[/dim italic]",
                title=f"🚀 {engine_name}",
                border_style="yellow",
                box=box.ROUNDED
            ))
            console.print()
            continue
        
        # Create models table
        table = Table(
            title=f"🚀 {engine_name} - {len(models)} model(s)",
            box=box.ROUNDED,
            title_style="bold cyan",
            header_style="bold magenta"
        )
        
        table.add_column("Model Name", style="cyan", no_wrap=True)
        table.add_column("Family", style="magenta")
        table.add_column("Size", style="blue", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Details", style="dim")
        
        for model in models:
            # Status with color
            if model.is_available:
                status = Text("✅ Available", style="bold green")
            else:
                status = Text("❌ Unavailable", style="bold red")
            
            # Details
            details_parts = []
            if model.context_length:
                details_parts.append(f"Context: {model.context_length:,}")
            if model.additional_info:
                # Try to extract useful info
                info = model.additional_info
                if isinstance(info, dict):
                    if 'modified_at' in info:
                        details_parts.append(f"Updated: {info['modified_at']}")
                    if 'parameter_size' in info:
                        details_parts.append(f"Size: {info['parameter_size']}")
            details = " | ".join(details_parts) if details_parts else "—"
            
            table.add_row(
                model.name,
                model.family or "Unknown",
                model.size or "Unknown",
                status,
                details
            )
        
        console.print(table)
        console.print()


def display_model_families_tree(all_models: Dict[str, List[ModelInfo]]) -> None:
    """Display models organized by family in a tree view."""
    console.print(Panel(
        "[bold cyan]Model Families Overview[/bold cyan]",
        box=box.ROUNDED,
        border_style="cyan"
    ))
    console.print()
    
    # Group models by family across all engines
    families: Dict[str, List[tuple[str, ModelInfo]]] = {}
    
    for engine_name, models in all_models.items():
        for model in models:
            family = model.family or "Unknown"
            if family not in families:
                families[family] = []
            families[family].append((engine_name, model))
    
    # Create tree for each family
    for family_name, models in sorted(families.items()):
        tree = Tree(
            f"[bold cyan]{family_name}[/bold cyan] ({len(models)} model(s))",
            guide_style="dim"
        )
        
        # Group by engine
        by_engine: Dict[str, List[ModelInfo]] = {}
        for engine_name, model in models:
            if engine_name not in by_engine:
                by_engine[engine_name] = []
            by_engine[engine_name].append(model)
        
        for engine_name, engine_models in sorted(by_engine.items()):
            engine_branch = tree.add(f"[magenta]{engine_name}[/magenta]")
            for model in engine_models:
                status = "✅" if model.is_available else "❌"
                size = f" ({model.size})" if model.size else ""
                engine_branch.add(f"{status} {model.name}{size}")
        
        console.print(tree)
        console.print()


def print_next_steps() -> None:
    """Print next steps for the user."""
    console.print(Panel(
        Text.from_markup(
            "[bold green]✅ Model discovery complete![/bold green]\n\n"
            "[bold]Next steps:[/bold]\n"
            "1. Test a model: [cyan]python scripts/test_request.py[/cyan]\n"
            "2. Run benchmark: [cyan]python scripts/run_benchmark.py[/cyan]\n"
            "3. Check engine health: [cyan]python scripts/check_engines.py[/cyan]"
        ),
        title="🎯 What's Next?",
        border_style="green",
        box=box.ROUNDED
    ))


async def main() -> None:
    """Main execution function."""
    print_header()
    
    connection_manager = None
    try:
        # Setup connection manager
        connection_manager = await setup_connection_manager()
        
        # Discover models
        all_models = await discover_all_models(connection_manager)
        
        # Display results
        display_models_summary(all_models)
        display_models_by_engine(all_models)
        display_model_families_tree(all_models)
        
        # Print next steps
        print_next_steps()
        
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

