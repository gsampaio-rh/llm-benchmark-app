"""
Configuration commands - config and init
Handles configuration display and initialization
"""

from typing import Optional

import click
from rich.console import Console

from ..utils.console_utils import print_status


@click.command()
@click.argument("config_file", required=False)
def config(config_file: Optional[str]):
    """Display current configuration"""
    console = Console()
    
    # Import here to avoid circular imports
    from ...config import load_config, display_config
    
    try:
        # Load configuration
        benchmark_config = load_config(config_file)
        
        console.print("\n[bold blue]📋 Configuration Display[/bold blue]")
        print_status(console, f"Loading configuration from: {config_file or 'default'}", "info")
        
        # Display the configuration
        display_config(benchmark_config)
        
        console.print("\n[green]✅ Configuration loaded successfully[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to load configuration: {str(e)}[/red]")


@click.command()
def init():
    """Initialize configuration files"""
    console = Console()
    
    # Import here to avoid circular imports  
    from ...config import create_example_configs
    
    try:
        console.print("\n[bold blue]⚙️ Configuration Initialization[/bold blue]")
        print_status(console, "Creating example configuration files...", "info")
        
        # Create example configurations
        create_example_configs()
        
        console.print("\n[green]✅ Configuration files created successfully![/green]")
        console.print("[cyan]📁 Example configurations available in config/ directory:[/cyan]")
        console.print("  • [white]config/default.yaml[/white] - Standard benchmarking")
        console.print("  • [white]config/quick-test.yaml[/white] - Quick demo test")
        console.print("  • [white]config/stress-test.yaml[/white] - Comprehensive stress test")
        
        console.print(f"\n[dim]💡 Edit these files to customize your benchmarking setup[/dim]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to initialize configuration: {str(e)}[/red]")
