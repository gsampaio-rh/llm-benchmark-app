"""
Main CLI entry point for the LLM Benchmarking Tool.

This module provides the command-line interface for managing engines,
running tests, and inspecting metrics.
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config.config_manager import ConfigManager, ConfigurationError
from src.core.connection_manager import ConnectionManager, ConnectionManagerError
from src.core.metrics_collector import initialize_metrics_collector, MetricsCollectionError
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter


# Initialize CLI app and console
app = typer.Typer(
    name="llm-benchmark",
    help="Universal LLM Engine Benchmarking Tool",
    add_completion=False
)
console = Console()

# Global instances
config_manager = ConfigManager()
connection_manager = ConnectionManager()
metrics_collector = initialize_metrics_collector(connection_manager)

# Register adapter classes
connection_manager.register_adapter_class("ollama", OllamaAdapter)
connection_manager.register_adapter_class("vllm", VLLMAdapter)
connection_manager.register_adapter_class("tgi", TGIAdapter)


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )


@app.command()
def engines(
    action: str = typer.Argument(..., help="Action: list, health, info"),
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="Specific engine name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
) -> None:
    """Manage engine connections."""
    setup_logging(verbose)
    
    async def _engines():
        try:
            # Load configuration and register engines
            benchmark_config = config_manager.load_benchmark_config()
            registration_results = await connection_manager.register_engines_from_config(benchmark_config)
            
            if action == "list":
                await _list_engines(registration_results)
            elif action == "health":
                await _check_health(engine)
            elif action == "info":
                await _show_engine_info(engine)
            else:
                rprint(f"[red]Unknown action: {action}[/red]")
                rprint("Available actions: list, health, info")
                raise typer.Exit(1)
                
        except ConfigurationError as e:
            rprint(f"[red]Configuration error: {e}[/red]")
            raise typer.Exit(1)
        except ConnectionManagerError as e:
            rprint(f"[red]Connection error: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected error: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()
            raise typer.Exit(1)
        finally:
            await connection_manager.close_all()
    
    asyncio.run(_engines())


async def _list_engines(registration_results: dict) -> None:
    """List all configured engines."""
    table = Table(title="Configured Engines")
    table.add_column("Name", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("URL", style="blue")
    table.add_column("Status", style="green")
    
    for engine_name, success in registration_results.items():
        adapter = connection_manager.get_adapter(engine_name)
        if adapter:
            status = "✅ Connected" if success else "❌ Failed"
            table.add_row(
                engine_name,
                adapter.config.engine_type,
                str(adapter.config.base_url),
                status
            )
        else:
            table.add_row(engine_name, "unknown", "unknown", "❌ Not registered")
    
    console.print(table)
    
    # Show summary
    total = len(registration_results)
    successful = sum(1 for success in registration_results.values() if success)
    rprint(f"\n[bold]Summary:[/bold] {successful}/{total} engines connected successfully")


async def _check_health(engine_name: Optional[str]) -> None:
    """Check health of engines."""
    if engine_name:
        # Check specific engine
        try:
            health_status = await connection_manager.health_check(engine_name, use_cache=False)
            _display_health_status(engine_name, health_status)
        except ConnectionManagerError as e:
            rprint(f"[red]Error checking {engine_name}: {e}[/red]")
    else:
        # Check all engines
        health_statuses = await connection_manager.health_check_all(use_cache=False)
        
        if not health_statuses:
            rprint("[yellow]No engines registered[/yellow]")
            return
        
        table = Table(title="Engine Health Status")
        table.add_column("Engine", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Response Time", style="blue")
        table.add_column("Version", style="magenta")
        table.add_column("Error", style="red")
        
        for engine_name, health_status in health_statuses.items():
            status_icon = "✅ Healthy" if health_status.is_healthy else "❌ Unhealthy"
            response_time = f"{health_status.response_time_ms:.1f}ms" if health_status.response_time_ms else "N/A"
            version = health_status.engine_version or "Unknown"
            error = health_status.error_message or ""
            
            table.add_row(engine_name, status_icon, response_time, version, error)
        
        console.print(table)


def _display_health_status(engine_name: str, health_status) -> None:
    """Display detailed health status for a single engine."""
    status_color = "green" if health_status.is_healthy else "red"
    status_text = "Healthy" if health_status.is_healthy else "Unhealthy"
    
    panel_content = f"""
[bold]Engine:[/bold] {engine_name}
[bold]Status:[/bold] [{status_color}]{status_text}[/{status_color}]
[bold]Response Time:[/bold] {health_status.response_time_ms:.1f}ms
[bold]Version:[/bold] {health_status.engine_version or 'Unknown'}
"""
    
    if health_status.error_message:
        panel_content += f"[bold]Error:[/bold] [red]{health_status.error_message}[/red]\n"
    
    if health_status.additional_info:
        panel_content += f"[bold]Additional Info:[/bold] {health_status.additional_info}\n"
    
    console.print(Panel(panel_content, title=f"Health Status: {engine_name}"))


async def _show_engine_info(engine_name: Optional[str]) -> None:
    """Show detailed engine information."""
    if not engine_name:
        rprint("[red]Engine name is required for info command[/red]")
        rprint("Use: llm-benchmark engines info --engine <name>")
        raise typer.Exit(1)
    
    try:
        engine_info = await connection_manager.get_engine_info(engine_name)
        
        panel_content = f"""
[bold]Engine:[/bold] {engine_info.engine_name}
[bold]Type:[/bold] {engine_info.engine_type}
[bold]Version:[/bold] {engine_info.version or 'Unknown'}
[bold]Model Count:[/bold] {engine_info.model_count or 'Unknown'}
[bold]Supported Features:[/bold] {', '.join(engine_info.supported_features or [])}
"""
        
        if engine_info.capabilities:
            capabilities = ', '.join(f"{k}: {v}" for k, v in engine_info.capabilities.items())
            panel_content += f"[bold]Capabilities:[/bold] {capabilities}\n"
        
        console.print(Panel(panel_content, title=f"Engine Information: {engine_name}"))
        
    except ConnectionManagerError as e:
        rprint(f"[red]Error getting engine info: {e}[/red]")
        raise typer.Exit(1)


@app.command()
def models(
    action: str = typer.Argument(..., help="Action: list"),
    engine: Optional[str] = typer.Option(None, "--engine", "-e", help="Specific engine name"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
) -> None:
    """Manage and discover models."""
    setup_logging(verbose)
    
    async def _models():
        try:
            # Load configuration and register engines
            benchmark_config = config_manager.load_benchmark_config()
            await connection_manager.register_engines_from_config(benchmark_config)
            
            if action == "list":
                await _list_models(engine)
            else:
                rprint(f"[red]Unknown action: {action}[/red]")
                rprint("Available actions: list")
                raise typer.Exit(1)
                
        except (ConfigurationError, ConnectionManagerError) as e:
            rprint(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected error: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()
            raise typer.Exit(1)
        finally:
            await connection_manager.close_all()
    
    asyncio.run(_models())


async def _list_models(engine_name: Optional[str]) -> None:
    """List available models."""
    if engine_name:
        # List models for specific engine
        try:
            models = await connection_manager.discover_models(engine_name)
            _display_models_table(engine_name, models)
        except ConnectionManagerError as e:
            rprint(f"[red]Error listing models for {engine_name}: {e}[/red]")
    else:
        # List models for all engines
        all_models = await connection_manager.discover_all_models()
        
        if not all_models:
            rprint("[yellow]No engines registered or no models found[/yellow]")
            return
        
        for engine_name, models in all_models.items():
            _display_models_table(engine_name, models)
            rprint()  # Add spacing between engines


def _display_models_table(engine_name: str, models) -> None:
    """Display models in a table format."""
    if not models:
        rprint(f"[yellow]No models found for {engine_name}[/yellow]")
        return
    
    table = Table(title=f"Models for {engine_name}")
    table.add_column("Name", style="cyan")
    table.add_column("Family", style="magenta")
    table.add_column("Size", style="blue")
    table.add_column("Available", style="green")
    
    for model in models:
        available_icon = "✅" if model.is_available else "❌"
        table.add_row(
            model.name,
            model.family or "Unknown",
            model.size or "Unknown",
            available_icon
        )
    
    console.print(table)
    rprint(f"[bold]Total models:[/bold] {len(models)}")


@app.command()
def test_request(
    prompt: str = typer.Argument(..., help="Prompt to send to the engine"),
    engine: str = typer.Option(..., "--engine", "-e", help="Engine name to use"),
    model: str = typer.Option(..., "--model", "-m", help="Model name to use"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
) -> None:
    """Send a test request to an engine."""
    setup_logging(verbose)
    
    async def _test_request():
        try:
            # Load configuration and register engines
            benchmark_config = config_manager.load_benchmark_config()
            await connection_manager.register_engines_from_config(benchmark_config)
            
            # Get adapter
            adapter = connection_manager.get_adapter(engine)
            if not adapter:
                rprint(f"[red]Engine not found: {engine}[/red]")
                raise typer.Exit(1)
            
            # Start metrics collection if not already started
            if not metrics_collector.current_collection:
                collection_id = metrics_collector.start_collection("CLI test request")
                rprint(f"[dim]Started metrics collection: {collection_id}[/dim]")
            
            # Send request and collect metrics
            rprint(f"[blue]Sending request to {engine} using model {model}...[/blue]")
            result = await metrics_collector.collect_single_request_metrics(engine, prompt, model)
            
            # Display result
            _display_request_result(result)
            
        except (ConfigurationError, ConnectionManagerError) as e:
            rprint(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)
        except Exception as e:
            rprint(f"[red]Unexpected error: {e}[/red]")
            if verbose:
                import traceback
                traceback.print_exc()
            raise typer.Exit(1)
        finally:
            await connection_manager.close_all()
    
    asyncio.run(_test_request())


def _display_request_result(result) -> None:
    """Display the result of a test request."""
    if result.success:
        # Display successful result
        panel_content = f"""
[bold]Prompt:[/bold] {result.prompt}
[bold]Response:[/bold] {result.response}
[bold]Engine:[/bold] {result.engine_name}
[bold]Model:[/bold] {result.model_name}
"""
        
        if result.parsed_metrics:
            metrics = result.parsed_metrics
            panel_content += f"""
[bold]Metrics:[/bold]
  • Total Duration: {metrics.total_duration:.3f}s
  • Prompt Tokens: {metrics.prompt_eval_count or 'N/A'}
  • Response Tokens: {metrics.eval_count or 'N/A'}
  • Response Rate: {metrics.response_token_rate:.1f} tokens/s
"""
        
        console.print(Panel(panel_content, title="✅ Request Successful", border_style="green"))
    else:
        # Display error result
        panel_content = f"""
[bold]Prompt:[/bold] {result.prompt}
[bold]Engine:[/bold] {result.engine_name}
[bold]Model:[/bold] {result.model_name}
[bold]Error:[/bold] [red]{result.error_message}[/red]
"""
        
        console.print(Panel(panel_content, title="❌ Request Failed", border_style="red"))


@app.command()
def metrics(
    action: str = typer.Argument(..., help="Action: show, export, clear"),
    format: str = typer.Option("json", "--format", "-f", help="Export format (json, csv)"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging")
) -> None:
    """Manage collected metrics."""
    setup_logging(verbose)
    
    try:
        if action == "show":
            _show_metrics()
        elif action == "export":
            if not output:
                rprint("[red]Output file path is required for export[/red]")
                raise typer.Exit(1)
            _export_metrics(output, format)
        elif action == "clear":
            _clear_metrics()
        else:
            rprint(f"[red]Unknown action: {action}[/red]")
            rprint("Available actions: show, export, clear")
            raise typer.Exit(1)
    except Exception as e:
        rprint(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback
            traceback.print_exc()
        raise typer.Exit(1)


def _show_metrics() -> None:
    """Show current metrics collection summary."""
    try:
        summary = metrics_collector.get_collection_summary()
        
        panel_content = f"""
[bold]Collection ID:[/bold] {summary['collection_id']}
[bold]Created:[/bold] {summary['created_at']}
[bold]Description:[/bold] {summary.get('description', 'No description')}
[bold]Total Raw Metrics:[/bold] {summary['total_raw_metrics']}
[bold]Total Parsed Metrics:[/bold] {summary['total_parsed_metrics']}
[bold]Total Aggregate Metrics:[/bold] {summary['total_aggregate_metrics']}
[bold]Engines:[/bold] {', '.join(summary['engines']) if summary['engines'] else 'None'}
[bold]Models:[/bold] {', '.join(summary['models']) if summary['models'] else 'None'}
[bold]Success Rate:[/bold] {summary['success_rate']:.1%}
"""
        
        console.print(Panel(panel_content, title="📊 Metrics Collection Summary"))
        
    except MetricsCollectionError as e:
        rprint(f"[yellow]No active metrics collection: {e}[/yellow]")
        rprint("Use 'test-request' command to start collecting metrics")


def _export_metrics(output_path: str, format: str) -> None:
    """Export metrics to file."""
    try:
        exported_file = metrics_collector.export_metrics(output_path, format)
        rprint(f"[green]✅ Metrics exported to: {exported_file}[/green]")
    except MetricsCollectionError as e:
        rprint(f"[yellow]No metrics to export: {e}[/yellow]")


def _clear_metrics() -> None:
    """Clear current metrics collection."""
    metrics_collector.clear_collection()
    rprint("[green]✅ Metrics collection cleared[/green]")


@app.command()
def version() -> None:
    """Show version information."""
    from src import __version__, __author__
    rprint(f"[bold]LLM Benchmark Tool[/bold] v{__version__}")
    rprint(f"Author: {__author__}")


if __name__ == "__main__":
    app()

