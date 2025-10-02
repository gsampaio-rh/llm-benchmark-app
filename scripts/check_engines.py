#!/usr/bin/env python3
"""
🔍 Engine Health Checker
========================

This script checks the health and connectivity of all configured LLM engines
(Ollama, vLLM, TGI). It provides detailed information about each engine's
status, response time, and capabilities.

Usage:
    python scripts/check_engines.py
"""

import asyncio
import sys
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.text import Text

from src.config.config_manager import ConfigManager, ConfigurationError
from src.core.connection_manager import ConnectionManager, ConnectionManagerError
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter


console = Console()


def print_header() -> None:
    """Display a beautiful header for the script."""
    header = Text()
    header.append("🔍 ", style="bold blue")
    header.append("LLM Engine Health Checker", style="bold cyan")
    
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]This script checks the health of all configured LLM engines.[/bold cyan]\n\n"
            "✓ Verifies connectivity\n"
            "✓ Measures response time\n"
            "✓ Retrieves engine information\n"
            "✓ Lists available models"
        ),
        title=header,
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


def print_step(step: int, total: int, message: str) -> None:
    """Print a step indicator."""
    console.print(f"[bold cyan]Step {step}/{total}:[/bold cyan] {message}")


async def load_and_register_engines() -> tuple[ConnectionManager, Dict[str, bool]]:
    """Load configuration and register all engines."""
    print_step(1, 3, "Loading engine configurations...")
    
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
            task = progress.add_task("Registering engines...", total=None)
            registration_results = await connection_manager.register_engines_from_config(benchmark_config)
            progress.update(task, completed=True)
        
        # Display registration summary
        total = len(registration_results)
        successful = sum(1 for success in registration_results.values() if success)
        
        if successful == total:
            console.print(f"  ✅ All {total} engines registered successfully\n")
        elif successful > 0:
            console.print(f"  ⚠️  {successful}/{total} engines registered successfully\n")
        else:
            console.print(f"  ❌ Failed to register any engines\n")
        
        return connection_manager, registration_results
        
    except ConfigurationError as e:
        console.print(f"[red]❌ Configuration error:[/red] {e}")
        raise
    except Exception as e:
        console.print(f"[red]❌ Unexpected error:[/red] {e}")
        raise


async def check_engine_health(connection_manager: ConnectionManager) -> None:
    """Check health of all registered engines."""
    print_step(2, 3, "Checking engine health...")
    console.print()
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Running health checks...", total=None)
        health_statuses = await connection_manager.health_check_all(use_cache=False)
        progress.update(task, completed=True)
    
    if not health_statuses:
        console.print("[yellow]⚠️  No engines to check[/yellow]\n")
        return
    
    # Create health status table
    table = Table(
        title="🏥 Engine Health Status",
        box=box.ROUNDED,
        title_style="bold cyan",
        header_style="bold magenta"
    )
    
    table.add_column("Engine", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Response Time", justify="right", style="blue")
    table.add_column("Version", style="magenta")
    table.add_column("Details", style="dim")
    
    for engine_name, health_status in health_statuses.items():
        if health_status.is_healthy:
            status = Text("✅ HEALTHY", style="bold green")
        else:
            status = Text("❌ UNHEALTHY", style="bold red")
        
        response_time = (
            f"{health_status.response_time_ms:.1f}ms" 
            if health_status.response_time_ms 
            else "N/A"
        )
        
        version = health_status.engine_version or "Unknown"
        
        details = health_status.error_message or "All systems operational"
        if len(details) > 50:
            details = details[:47] + "..."
        
        table.add_row(engine_name, status, response_time, version, details)
    
    console.print(table)
    console.print()


async def display_engine_details(connection_manager: ConnectionManager) -> None:
    """Display detailed information about each engine."""
    print_step(3, 3, "Gathering detailed engine information...")
    console.print()
    
    for engine_name in connection_manager.adapters.keys():
        try:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task(f"Querying {engine_name}...", total=None)
                engine_info = await connection_manager.get_engine_info(engine_name)
                models = await connection_manager.discover_models(engine_name)
                progress.update(task, completed=True)
            
            # Create info panel
            info_text = Text()
            info_text.append("Engine Type: ", style="bold")
            info_text.append(f"{engine_info.engine_type}\n")
            
            info_text.append("Version: ", style="bold")
            info_text.append(f"{engine_info.version or 'Unknown'}\n")
            
            info_text.append("Models Available: ", style="bold")
            info_text.append(f"{len(models) if models else 0}\n")
            
            if engine_info.supported_features:
                info_text.append("Features: ", style="bold")
                info_text.append(f"{', '.join(engine_info.supported_features)}\n")
            
            if engine_info.capabilities:
                info_text.append("Capabilities: ", style="bold")
                caps = ', '.join(f"{k}={v}" for k, v in engine_info.capabilities.items())
                info_text.append(f"{caps}\n")
            
            # Models table
            if models:
                info_text.append("\n")
                models_table = Table(box=box.SIMPLE, show_header=True, header_style="bold")
                models_table.add_column("Model Name", style="cyan")
                models_table.add_column("Family", style="magenta")
                models_table.add_column("Size", style="blue")
                models_table.add_column("Status", justify="center")
                
                for model in models[:5]:  # Show first 5 models
                    status = "✅" if model.is_available else "❌"
                    models_table.add_row(
                        model.name,
                        model.family or "Unknown",
                        model.size or "Unknown",
                        status
                    )
                
                if len(models) > 5:
                    models_table.add_row("...", "...", "...", f"({len(models) - 5} more)")
            else:
                models_table = Text("No models found", style="dim italic")
            
            console.print(Panel(
                info_text,
                title=f"🚀 {engine_name}",
                border_style="green",
                box=box.ROUNDED
            ))
            
            if models:
                console.print(models_table)
            
            console.print()
            
        except ConnectionManagerError as e:
            console.print(Panel(
                f"[red]Error querying engine:[/red] {e}",
                title=f"❌ {engine_name}",
                border_style="red",
                box=box.ROUNDED
            ))
            console.print()
        except Exception as e:
            console.print(f"[red]Unexpected error with {engine_name}:[/red] {e}\n")


def print_summary(connection_manager: ConnectionManager) -> None:
    """Print a final summary."""
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold green]✅ Health check complete![/bold green]\n\n"
            "You can now use these engines for benchmarking.\n"
            "Run other scripts to explore models, test requests, or run full benchmarks."
        ),
        title="📊 Summary",
        border_style="green",
        box=box.ROUNDED
    ))


async def main() -> None:
    """Main execution function."""
    print_header()
    
    try:
        # Load and register engines
        connection_manager, registration_results = await load_and_register_engines()
        
        # Check health
        await check_engine_health(connection_manager)
        
        # Display detailed info
        await display_engine_details(connection_manager)
        
        # Print summary
        print_summary(connection_manager)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error:[/red] {e}")
        sys.exit(1)
    finally:
        try:
            await connection_manager.close_all()
        except:
            pass


if __name__ == "__main__":
    asyncio.run(main())

