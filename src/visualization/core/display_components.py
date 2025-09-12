"""
Reusable display components for Rich console output.

This module provides common UI components that can be reused across different
visualization contexts, including progress indicators, status displays, and tables.
"""

from typing import List, Dict, Optional, Any, Union
from rich.console import Console, RenderableType
from rich.panel import Panel  
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, SpinnerColumn
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED
from rich.status import Status


class DisplayComponents:
    """Collection of reusable display components"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize display components
        
        Args:
            console: Rich console instance
        """
        self.console = console or Console()
    
    def create_service_status_table(self, services: Dict[str, Any], title: str = "Service Status") -> Table:
        """Create a table showing service status information
        
        Args:
            services: Dictionary of service_name -> service_info
            title: Title for the table
            
        Returns:
            Rich Table with service status
        """
        table = Table(title=title, box=ROUNDED)
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", justify="center")
        table.add_column("URL", style="blue")
        table.add_column("Response Time", justify="right")
        
        for service_name, info in services.items():
            # Extract status information
            status = getattr(info, 'status', 'unknown')
            url = getattr(info, 'url', 'N/A')
            response_time = getattr(info, 'response_time_ms', 0)
            
            # Style status based on health
            if status == "healthy":
                status_text = "✅ Healthy"
                status_style = "green"
            elif status == "responding":
                status_text = "⚠️ Responding"
                status_style = "yellow"
            else:
                status_text = "❌ Unhealthy"
                status_style = "red"
            
            table.add_row(
                service_name.upper(),
                Text(status_text, style=status_style),
                url,
                f"{response_time:.1f}ms" if response_time > 0 else "N/A"
            )
        
        return table
    
    def create_metrics_table(self, metrics: Dict[str, Dict[str, float]], title: str = "Performance Metrics") -> Table:
        """Create a table showing performance metrics
        
        Args:
            metrics: Dictionary of service_name -> metrics_dict
            title: Title for the table
            
        Returns:
            Rich Table with metrics
        """
        table = Table(title=title, box=ROUNDED)
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("TTFT (ms)", justify="right")
        table.add_column("P95 Latency", justify="right") 
        table.add_column("Success Rate", justify="right")
        table.add_column("Score", justify="center")
        
        for service_name, service_metrics in metrics.items():
            ttft = service_metrics.get('ttft_mean', 0)
            p95 = service_metrics.get('load_p95_latency', 0)
            success_rate = service_metrics.get('reliability_score', 0)
            overall_score = service_metrics.get('overall_score', 0)
            
            # Style based on performance
            score_style = "green" if overall_score >= 0.8 else "yellow" if overall_score >= 0.6 else "red"
            
            table.add_row(
                service_name.upper(),
                f"{ttft:.1f}" if ttft > 0 else "N/A",
                f"{p95:.1f}ms" if p95 > 0 else "N/A",
                f"{success_rate*100:.1f}%" if success_rate > 0 else "N/A",
                Text(f"{overall_score:.2f}", style=score_style)
            )
        
        return table
    
    def create_progress_display(self, description: str = "Processing") -> Progress:
        """Create a progress display for long-running operations
        
        Args:
            description: Description of the operation
            
        Returns:
            Rich Progress instance
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console
        )
    
    def create_status_panel(self, status: str, details: str = "", color: str = "blue") -> Panel:
        """Create a status panel with consistent styling
        
        Args:
            status: Main status message
            details: Additional details
            color: Border color
            
        Returns:
            Rich Panel with status information
        """
        content = Text(status, style=f"bold {color}")
        if details:
            content.append(f"\n{details}", style="dim")
        
        return Panel(
            Align.center(content),
            border_style=color,
            padding=(1, 2)
        )
    
    def create_comparison_table(self, 
                              data: List[Dict[str, Any]], 
                              columns: List[str],
                              title: str = "Comparison") -> Table:
        """Create a generic comparison table
        
        Args:
            data: List of dictionaries with data to display
            columns: List of column names to include
            title: Table title
            
        Returns:
            Rich Table with comparison data
        """
        table = Table(title=title, box=ROUNDED)
        
        # Add columns
        for col in columns:
            table.add_column(col.replace("_", " ").title(), justify="center")
        
        # Add rows
        for row_data in data:
            row_values = []
            for col in columns:
                value = row_data.get(col, "N/A")
                if isinstance(value, float):
                    row_values.append(f"{value:.2f}")
                else:
                    row_values.append(str(value))
            table.add_row(*row_values)
        
        return table
    
    def create_winner_announcement(self, winner: str, metrics: Dict[str, float]) -> Panel:
        """Create a winner announcement panel
        
        Args:
            winner: Name of the winning service
            metrics: Key metrics that led to the win
            
        Returns:
            Rich Panel announcing the winner
        """
        content = Text()
        content.append("🏆 WINNER: ", style="bold yellow")
        content.append(f"{winner.upper()}", style="bold green")
        content.append("\n")
        
        for metric_name, value in metrics.items():
            content.append(f"\n• {metric_name}: ", style="cyan")
            content.append(f"{value:.1f}", style="bold white")
            if "ms" in metric_name.lower():
                content.append("ms", style="dim")
            elif "rate" in metric_name.lower():
                content.append("%", style="dim")
        
        return Panel(
            Align.center(content),
            title="🎉 Performance Champion",
            border_style="gold1",
            padding=(1, 2)
        )
    
    def create_loading_status(self, message: str) -> Status:
        """Create a loading status indicator
        
        Args:
            message: Loading message to display
            
        Returns:
            Rich Status object
        """
        return Status(message, console=self.console, spinner="dots")
    
    def format_duration(self, seconds: float) -> str:
        """Format a duration in seconds to human-readable format
        
        Args:
            seconds: Duration in seconds
            
        Returns:
            Formatted duration string
        """
        if seconds < 1:
            return f"{seconds*1000:.0f}ms"
        elif seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds // 60
            remaining_seconds = seconds % 60
            return f"{minutes:.0f}m {remaining_seconds:.0f}s"
        else:
            hours = seconds // 3600
            remaining_minutes = (seconds % 3600) // 60
            return f"{hours:.0f}h {remaining_minutes:.0f}m"
    
    def format_number(self, value: Union[int, float], unit: str = "", decimal_places: int = 1) -> str:
        """Format a number with appropriate unit and decimal places
        
        Args:
            value: Numeric value to format
            unit: Unit to append (e.g., "ms", "%", "MB")
            decimal_places: Number of decimal places
            
        Returns:
            Formatted number string
        """
        if isinstance(value, float):
            formatted = f"{value:.{decimal_places}f}"
        else:
            formatted = str(value)
        
        return f"{formatted}{unit}" if unit else formatted
