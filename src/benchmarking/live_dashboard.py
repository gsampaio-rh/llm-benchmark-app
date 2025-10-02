"""
Live dashboard for real-time benchmark visualization.

Provides reusable 3-panel dashboard for tracking benchmark progress
with live metrics and request/response display.
"""

import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich import box
from pydantic import BaseModel, Field


@dataclass
class EngineStats:
    """Real-time statistics for an engine."""
    completed: int = 0
    failed: int = 0
    total_tokens: int = 0
    target: int = 0
    token_rates: list = None
    avg_tps: float = 0.0
    start_time: float = 0.0
    
    def __post_init__(self):
        if self.token_rates is None:
            self.token_rates = []


class DashboardConfig(BaseModel):
    """Configuration for live dashboard."""
    
    model_config = {"extra": "forbid"}
    
    title: str = Field(
        default="Benchmark",
        description="Dashboard title"
    )
    title_emoji: str = Field(
        default="🎨",
        description="Emoji for title"
    )
    show_current_request: bool = Field(
        default=True,
        description="Show current request/response panel"
    )
    show_word_count: bool = Field(
        default=True,
        description="Show word count in response"
    )
    response_preview_length: int = Field(
        default=6000,
        description="Characters to show in response preview"
    )
    prompt_preview_length: int = Field(
        default=80,
        description="Characters to show in prompt preview"
    )


class LiveDashboard:
    """
    Live dashboard for real-time benchmark visualization.
    
    Provides a 3-panel layout:
    1. Header - Overall progress
    2. Current Request - What's happening now
    3. Metrics Table - Side-by-side comparison
    """
    
    def __init__(self, config: Optional[DashboardConfig] = None, console: Optional[Console] = None):
        """
        Initialize live dashboard.
        
        Args:
            config: Dashboard configuration
            console: Rich console instance
        """
        self.config = config or DashboardConfig()
        self.console = console or Console()
    
    def create_display(
        self,
        targets: List[Dict[str, str]],
        engine_metrics: Dict[str, EngineStats],
        start_time: float,
        total_requests: int,
        completed_requests: int,
        current_engine: Optional[str] = None,
        current_prompt: Optional[str] = None,
        current_response: Optional[str] = None
    ) -> Layout:
        """
        Create complete dashboard layout.
        
        Args:
            targets: List of engine/model targets
            engine_metrics: Real-time engine statistics
            start_time: Benchmark start timestamp
            total_requests: Total requests to execute
            completed_requests: Requests completed so far
            current_engine: Currently active engine
            current_prompt: Current prompt being processed
            current_response: Current response being generated
            
        Returns:
            Rich Layout with complete dashboard
        """
        layout = Layout()
        
        # Configure layout structure
        if self.config.show_current_request:
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="current", size=40),
                Layout(name="metrics")
            )
        else:
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="metrics")
            )
        
        # Build header
        layout["header"].update(
            self._create_header(start_time, total_requests, completed_requests)
        )
        
        # Build current request panel
        if self.config.show_current_request:
            layout["current"].update(
                self._create_current_request_panel(
                    current_engine, current_prompt, current_response
                )
            )
        
        # Build metrics table
        layout["metrics"].update(
            self._create_metrics_table(targets, engine_metrics, current_engine)
        )
        
        return layout
    
    def _create_header(
        self,
        start_time: float,
        total_requests: int,
        completed_requests: int
    ) -> Panel:
        """Create header panel with overall progress."""
        elapsed = time.time() - start_time
        progress_pct = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        header_text = Text()
        header_text.append(f"{self.config.title_emoji} {self.config.title} ", style="bold magenta")
        header_text.append(f"| Progress: {completed_requests}/{total_requests} ", style="cyan")
        header_text.append(f"({progress_pct:.1f}%) ", style="yellow")
        header_text.append(f"| Elapsed: {elapsed:.0f}s", style="dim")
        
        return Panel(header_text, border_style="cyan")
    
    def _create_current_request_panel(
        self,
        current_engine: Optional[str],
        current_prompt: Optional[str],
        current_response: Optional[str]
    ) -> Panel:
        """Create current request/response panel."""
        if not current_engine or not current_prompt:
            return Panel(
                Text("⏳ Initializing benchmark...", style="dim italic"),
                title="🎬 Live Request & Response",
                border_style="dim",
                box=box.ROUNDED
            )
        
        current_text = Text()
        current_text.append(f"🔵 Engine: ", style="bold")
        current_text.append(f"{current_engine}\n", style="bold cyan")
        current_text.append(f"📝 Prompt: ", style="bold")
        
        # Preview prompt
        prompt_preview = (
            current_prompt[:self.config.prompt_preview_length] + "..."
            if len(current_prompt) > self.config.prompt_preview_length
            else current_prompt
        )
        current_text.append(f"{prompt_preview}\n\n", style="yellow")
        
        if current_response:
            # Show word count if enabled
            if self.config.show_word_count:
                word_count = len(current_response.split())
                current_text.append(f"💬 Response ", style="bold")
                current_text.append(f"({word_count} words):\n", style="dim")
            else:
                current_text.append(f"💬 Response:\n", style="bold")
            
            # Show response preview
            response_preview = (
                current_response[:self.config.response_preview_length] + "..."
                if len(current_response) > self.config.response_preview_length
                else current_response
            )
            current_text.append(response_preview, style="green")
            
            # Add typing indicator for short responses
            if len(current_response) < 50:
                current_text.append(" ▋", style="bold green blink")
        else:
            current_text.append(f"⏳ Sending request to model...", style="dim italic")
        
        # Dynamic border color
        border_color = "magenta" if current_response else "yellow"
        
        return Panel(
            current_text,
            title="🎬 Live Request & Response",
            border_style=border_color,
            box=box.ROUNDED
        )
    
    def _create_metrics_table(
        self,
        targets: List[Dict[str, str]],
        engine_metrics: Dict[str, Any],
        current_engine: Optional[str]
    ) -> Table:
        """Create live metrics comparison table."""
        table = Table(
            title="⚡ Live Performance Metrics",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan"
        )
        
        table.add_column("Engine", style="cyan", width=20)
        table.add_column("Progress", justify="center", width=12)
        table.add_column("Success Rate", justify="center", width=13)
        table.add_column("Avg Tokens/sec", justify="right", width=15)
        table.add_column("Total Tokens", justify="right", width=13)
        table.add_column("Status", justify="center", width=10)
        
        # Find current leader
        leader_tps = 0
        leader_engine = None
        
        for engine_name, stats in engine_metrics.items():
            avg_tps = stats.get("avg_tps", 0) if isinstance(stats, dict) else getattr(stats, "avg_tps", 0)
            if avg_tps > leader_tps:
                leader_tps = avg_tps
                leader_engine = engine_name
        
        # Add rows for each engine
        for target in targets:
            engine_name = target["engine"]
            stats = engine_metrics.get(engine_name, {})
            
            if isinstance(stats, dict):
                completed = stats.get("completed", 0)
                failed = stats.get("failed", 0)
                avg_tps = stats.get("avg_tps", 0)
                total_tokens = stats.get("total_tokens", 0)
                target_count = stats.get("target", 0)
            else:
                completed = getattr(stats, "completed", 0)
                failed = getattr(stats, "failed", 0)
                avg_tps = getattr(stats, "avg_tps", 0)
                total_tokens = getattr(stats, "total_tokens", 0)
                target_count = getattr(stats, "target", 0)
            
            total = completed + failed
            
            # Progress
            progress_text = f"{completed}/{target_count}"
            
            # Success rate
            success_rate = f"{(completed/total*100):.0f}%" if total > 0 else "0%"
            
            # Tokens per second with color coding
            tps_text = f"{avg_tps:.1f}" if avg_tps > 0 else "-"
            
            if avg_tps >= 50:
                tps_style = "bold green"
            elif avg_tps >= 30:
                tps_style = "bold cyan"
            elif avg_tps >= 15:
                tps_style = "bold yellow"
            elif avg_tps > 0:
                tps_style = "bold red"
            else:
                tps_style = "dim"
            
            tps_display = f"[{tps_style}]{tps_text}[/{tps_style}]"
            
            # Total tokens
            tokens_text = f"{total_tokens:,}" if total_tokens > 0 else "-"
            
            # Status with active indicator
            engine_match = current_engine and engine_name in current_engine
            if engine_match:
                status = "🔴 Active"
            elif completed >= target_count and target_count > 0:
                status = "✅ Done"
            elif total > 0:
                status = "🔄 Running"
            else:
                status = "⏳ Pending"
            
            # Add leader crown
            engine_display = engine_name
            if engine_name == leader_engine and avg_tps > 0:
                engine_display = f"👑 {engine_name}"
            
            table.add_row(
                engine_display,
                progress_text,
                success_rate,
                tps_display,
                tokens_text,
                status
            )
        
        return table

