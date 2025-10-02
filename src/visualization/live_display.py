"""
Live streaming visualization for LLM responses.

This module provides real-time visualization of streaming LLM responses
with live metrics, performance indicators, and side-by-side comparisons.
"""

import time
from datetime import datetime
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn
from rich import box
from pydantic import BaseModel, Field


class PerformanceLevel(Enum):
    """Performance level classification."""
    EXCELLENT = "excellent"  # Green
    GOOD = "good"           # Cyan
    MODERATE = "moderate"   # Yellow
    SLOW = "slow"           # Red


@dataclass
class StreamingMetrics:
    """Real-time metrics for streaming display."""
    
    engine_name: str
    model_name: str
    start_time: float = field(default_factory=time.time)
    first_token_time: Optional[float] = None
    last_token_time: Optional[float] = None
    tokens_received: int = 0
    total_chars: int = 0
    
    # Performance metrics
    ttft: Optional[float] = None  # Time to first token
    current_token_rate: float = 0.0
    average_token_rate: float = 0.0
    inter_token_latency: float = 0.0
    
    # Status
    is_complete: bool = False
    error_message: Optional[str] = None
    
    def record_token(self, token: str, timestamp: Optional[float] = None) -> None:
        """Record a received token and update metrics."""
        if timestamp is None:
            timestamp = time.time()
        
        self.tokens_received += 1
        self.total_chars += len(token)
        
        # Record first token time
        if self.first_token_time is None:
            self.first_token_time = timestamp
            self.ttft = timestamp - self.start_time
        
        # Calculate inter-token latency
        if self.last_token_time is not None:
            self.inter_token_latency = timestamp - self.last_token_time
        
        self.last_token_time = timestamp
        
        # Calculate token rates
        elapsed = timestamp - self.start_time
        if elapsed > 0:
            self.average_token_rate = self.tokens_received / elapsed
        
        # Current rate (based on last 10 tokens worth of time)
        if self.tokens_received > 1 and self.first_token_time:
            gen_elapsed = timestamp - self.first_token_time
            if gen_elapsed > 0:
                self.current_token_rate = (self.tokens_received - 1) / gen_elapsed
    
    def get_performance_level(self) -> PerformanceLevel:
        """Determine performance level based on current metrics."""
        if self.current_token_rate == 0:
            return PerformanceLevel.MODERATE
        
        # Classification based on tokens/sec
        if self.current_token_rate >= 50:
            return PerformanceLevel.EXCELLENT
        elif self.current_token_rate >= 30:
            return PerformanceLevel.GOOD
        elif self.current_token_rate >= 15:
            return PerformanceLevel.MODERATE
        else:
            return PerformanceLevel.SLOW
    
    def get_elapsed_time(self) -> float:
        """Get total elapsed time."""
        end_time = self.last_token_time or time.time()
        return end_time - self.start_time


class StreamConfig(BaseModel):
    """Configuration for streaming display."""
    
    model_config = {"extra": "forbid"}
    
    show_tokens: bool = Field(
        default=True,
        description="Display streaming tokens"
    )
    show_metrics: bool = Field(
        default=True,
        description="Display live metrics panel"
    )
    show_progress: bool = Field(
        default=True,
        description="Display progress bar"
    )
    max_display_tokens: int = Field(
        default=500,
        description="Maximum tokens to display (for very long responses)"
    )
    update_interval: float = Field(
        default=0.1,
        description="Display update interval in seconds"
    )
    enable_syntax_highlighting: bool = Field(
        default=True,
        description="Enable syntax highlighting for code blocks"
    )
    performance_thresholds: Dict[str, float] = Field(
        default={
            "excellent": 50.0,
            "good": 30.0,
            "moderate": 15.0
        },
        description="Token/sec thresholds for performance levels"
    )


class StreamingDisplay:
    """
    Real-time streaming visualization for LLM responses.
    
    Provides beautiful live display of streaming tokens with metrics,
    performance indicators, and comparison capabilities.
    """
    
    def __init__(self, config: Optional[StreamConfig] = None, console: Optional[Console] = None):
        """
        Initialize streaming display.
        
        Args:
            config: Stream configuration (uses defaults if None)
            console: Rich console instance (creates new if None)
        """
        self.config = config or StreamConfig()
        self.console = console or Console()
        
        # Active streams
        self.active_streams: Dict[str, StreamingMetrics] = {}
        self.stream_content: Dict[str, List[str]] = {}
        
        # Display state
        self.is_paused: bool = False
        self.live_display: Optional[Live] = None
    
    def start_stream(
        self,
        engine_name: str,
        model_name: str,
        prompt: str
    ) -> StreamingMetrics:
        """
        Start a new streaming session.
        
        Args:
            engine_name: Name of the engine
            model_name: Name of the model
            prompt: The prompt being processed
            
        Returns:
            StreamingMetrics instance for this stream
        """
        stream_id = f"{engine_name}:{model_name}"
        
        metrics = StreamingMetrics(
            engine_name=engine_name,
            model_name=model_name
        )
        
        self.active_streams[stream_id] = metrics
        self.stream_content[stream_id] = []
        
        return metrics
    
    def add_token(self, engine_name: str, model_name: str, token: str) -> None:
        """
        Add a token to the stream display.
        
        Args:
            engine_name: Name of the engine
            model_name: Name of the model
            token: The token to add
        """
        stream_id = f"{engine_name}:{model_name}"
        
        if stream_id not in self.active_streams:
            return
        
        # Update metrics
        self.active_streams[stream_id].record_token(token)
        
        # Store content
        self.stream_content[stream_id].append(token)
    
    def complete_stream(self, engine_name: str, model_name: str) -> None:
        """Mark a stream as complete."""
        stream_id = f"{engine_name}:{model_name}"
        
        if stream_id in self.active_streams:
            self.active_streams[stream_id].is_complete = True
    
    def error_stream(self, engine_name: str, model_name: str, error: str) -> None:
        """Mark a stream as errored."""
        stream_id = f"{engine_name}:{model_name}"
        
        if stream_id in self.active_streams:
            self.active_streams[stream_id].is_complete = True
            self.active_streams[stream_id].error_message = error
    
    def _create_token_panel(self, stream_id: str) -> Panel:
        """Create the token streaming panel."""
        metrics = self.active_streams[stream_id]
        content = self.stream_content[stream_id]
        
        # Build display text
        display_text = "".join(content)
        
        # Truncate if too long
        if len(content) > self.config.max_display_tokens:
            display_text = "".join(content[-self.config.max_display_tokens:])
            display_text = f"[dim]... (showing last {self.config.max_display_tokens} tokens)[/dim]\n\n" + display_text
        
        # Create styled text
        text = Text(display_text)
        
        # Add progress bar
        if not metrics.is_complete:
            text.append(f"\n\n{'━' * 40} {metrics.tokens_received} tokens")
        
        # Status indicator
        status_icon = "🔴" if not metrics.is_complete else "✅"
        status_text = "STREAMING" if not metrics.is_complete else "COMPLETE"
        
        if metrics.error_message:
            status_icon = "❌"
            status_text = "ERROR"
        
        title = f"{status_icon} {status_text} | {metrics.engine_name} | {metrics.model_name}"
        
        return Panel(
            text,
            title=title,
            border_style="cyan" if not metrics.is_complete else "green",
            box=box.ROUNDED
        )
    
    def _create_metrics_panel(self, stream_id: str) -> Panel:
        """Create the live metrics panel."""
        metrics = self.active_streams[stream_id]
        perf_level = metrics.get_performance_level()
        
        # Performance color coding
        perf_colors = {
            PerformanceLevel.EXCELLENT: "green",
            PerformanceLevel.GOOD: "cyan",
            PerformanceLevel.MODERATE: "yellow",
            PerformanceLevel.SLOW: "red"
        }
        perf_color = perf_colors[perf_level]
        
        # Build metrics text
        metrics_text = Text()
        
        # Tokens per second
        metrics_text.append("⚡ ", style="bold yellow")
        metrics_text.append(f"{metrics.current_token_rate:.1f} tokens/sec", style=f"bold {perf_color}")
        
        # Time to first token
        if metrics.ttft is not None:
            metrics_text.append(" | ⏱️  ", style="bold")
            metrics_text.append(f"TTFT: {metrics.ttft:.3f}s", style="bold blue")
        
        # Elapsed time
        elapsed = metrics.get_elapsed_time()
        metrics_text.append(" | ⏲️  ", style="bold")
        metrics_text.append(f"{elapsed:.1f}s", style="dim")
        
        # Token count
        metrics_text.append(" | 📊 ", style="bold")
        metrics_text.append(f"{metrics.tokens_received} tokens", style="bold magenta")
        
        # Status
        if metrics.is_complete:
            if metrics.error_message:
                metrics_text.append(" | ❌ ", style="bold red")
                metrics_text.append(f"Error: {metrics.error_message[:50]}", style="red")
            else:
                metrics_text.append(" | ✅ ", style="bold green")
                metrics_text.append("Complete", style="green")
        else:
            metrics_text.append(" | 🔄 ", style="bold")
            metrics_text.append("Running", style="cyan")
        
        return Panel(
            metrics_text,
            title="📈 Live Metrics",
            border_style=perf_color,
            box=box.ROUNDED
        )
    
    def _create_comparison_table(self) -> Table:
        """Create side-by-side comparison table."""
        table = Table(
            title="🏁 Engine Comparison",
            box=box.ROUNDED,
            header_style="bold magenta"
        )
        
        table.add_column("Engine", style="cyan")
        table.add_column("Model", style="blue")
        table.add_column("Tokens", style="magenta", justify="right")
        table.add_column("Rate", style="yellow", justify="right")
        table.add_column("TTFT", style="blue", justify="right")
        table.add_column("Status", justify="center")
        
        for stream_id, metrics in self.active_streams.items():
            perf_level = metrics.get_performance_level()
            perf_colors = {
                PerformanceLevel.EXCELLENT: "green",
                PerformanceLevel.GOOD: "cyan",
                PerformanceLevel.MODERATE: "yellow",
                PerformanceLevel.SLOW: "red"
            }
            rate_color = perf_colors[perf_level]
            
            status = "✅" if metrics.is_complete else "🔄"
            if metrics.error_message:
                status = "❌"
            
            ttft_str = f"{metrics.ttft:.3f}s" if metrics.ttft else "..."
            
            table.add_row(
                metrics.engine_name,
                metrics.model_name,
                str(metrics.tokens_received),
                f"[{rate_color}]{metrics.current_token_rate:.1f}[/{rate_color}]",
                ttft_str,
                status
            )
        
        return table
    
    def display_single_stream(
        self,
        engine_name: str,
        model_name: str,
        stream_callback: Callable[[], None],
        show_metrics: bool = True
    ) -> None:
        """
        Display a single stream with live updates.
        
        Args:
            engine_name: Name of the engine
            model_name: Name of the model
            stream_callback: Callback function that processes the stream
            show_metrics: Whether to show metrics panel
        """
        stream_id = f"{engine_name}:{model_name}"
        
        with Live(
            self._create_layout(stream_id, show_metrics),
            console=self.console,
            refresh_per_second=int(1 / self.config.update_interval)
        ) as live:
            self.live_display = live
            
            # Run the streaming callback
            stream_callback()
            
            # Update one final time
            live.update(self._create_layout(stream_id, show_metrics))
    
    def _create_layout(self, stream_id: str, show_metrics: bool = True) -> Layout:
        """Create the display layout."""
        layout = Layout()
        
        if show_metrics:
            layout.split_column(
                Layout(name="tokens", ratio=3),
                Layout(name="metrics", size=3)
            )
            layout["tokens"].update(self._create_token_panel(stream_id))
            layout["metrics"].update(self._create_metrics_panel(stream_id))
        else:
            layout.update(self._create_token_panel(stream_id))
        
        return layout
    
    def display_comparison(
        self,
        stream_callbacks: List[Callable[[], None]]
    ) -> None:
        """
        Display multiple streams for comparison.
        
        Args:
            stream_callbacks: List of callback functions for each stream
        """
        # TODO: Implement multi-stream comparison
        # This would show side-by-side streaming from multiple engines
        pass
    
    def pause(self) -> None:
        """Pause the display updates."""
        self.is_paused = True
    
    def resume(self) -> None:
        """Resume the display updates."""
        self.is_paused = False
    
    def get_final_metrics(self, engine_name: str, model_name: str) -> Optional[StreamingMetrics]:
        """Get final metrics for a completed stream."""
        stream_id = f"{engine_name}:{model_name}"
        return self.active_streams.get(stream_id)
    
    def clear(self) -> None:
        """Clear all active streams."""
        self.active_streams.clear()
        self.stream_content.clear()

