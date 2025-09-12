"""
Console utilities for beautiful CLI output using Rich
Extracted from main CLI for reusability
"""

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn


def create_console() -> Console:
    """Create a configured Rich console instance"""
    return Console()


def print_header(console: Console) -> None:
    """Print the beautiful application header"""
    header_text = Text()
    header_text.append("🚀 vLLM vs TGI vs Ollama\n", style="bold blue")
    header_text.append("Low-Latency Chat Benchmarking Suite\n", style="cyan")
    header_text.append("AI Platform Team - Enterprise Performance Testing", style="dim")
    
    console.print(Panel.fit(header_text, border_style="blue"))


def print_status(console: Console, message: str, status: str = "info") -> None:
    """Print a status message with appropriate styling
    
    Args:
        console: Rich console instance
        message: Message to display
        status: Status type ('info', 'success', 'warning', 'error')
    """
    styles = {
        'info': '[blue]ℹ️[/blue]',
        'success': '[green]✅[/green]',
        'warning': '[yellow]⚠️[/yellow]',
        'error': '[red]❌[/red]'
    }
    
    icon = styles.get(status, '[blue]ℹ️[/blue]')
    console.print(f"{icon} {message}")


def create_status_table(console: Console, title: str) -> Table:
    """Create a standardized status table
    
    Args:
        console: Rich console instance
        title: Table title
        
    Returns:
        Configured Rich Table instance
    """
    table = Table(title=title, show_header=True, header_style="bold blue")
    return table


def show_progress_spinner(console: Console, description: str):
    """Create a progress spinner for long operations
    
    Args:
        console: Rich console instance
        description: Description of the operation
        
    Returns:
        Rich Progress context manager
    """
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    )
