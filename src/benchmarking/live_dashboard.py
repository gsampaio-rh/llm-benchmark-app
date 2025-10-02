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
    # Enhanced metrics
    ttft_values: list = None  # Time to First Token measurements
    inter_token_latencies: list = None  # Inter-token latency values
    response_durations: list = None  # Total response durations
    
    def __post_init__(self):
        if self.token_rates is None:
            self.token_rates = []
        if self.ttft_values is None:
            self.ttft_values = []
        if self.inter_token_latencies is None:
            self.inter_token_latencies = []
        if self.response_durations is None:
            self.response_durations = []
    
    def calculate_percentile(self, values: list, percentile: float) -> Optional[float]:
        """Calculate percentile from a list of values."""
        if not values:
            return None
        sorted_values = sorted(values)
        index = int(len(sorted_values) * percentile / 100)
        return sorted_values[min(index, len(sorted_values) - 1)]
    
    def get_ttft_p95(self) -> Optional[float]:
        """Get p95 TTFT."""
        return self.calculate_percentile(self.ttft_values, 95)
    
    def get_ttft_p99(self) -> Optional[float]:
        """Get p99 TTFT."""
        return self.calculate_percentile(self.ttft_values, 99)
    
    def get_avg_ttft(self) -> Optional[float]:
        """Get average TTFT."""
        if not self.ttft_values:
            return None
        return sum(self.ttft_values) / len(self.ttft_values)
    
    def get_token_rate_variance(self) -> Optional[float]:
        """Calculate token rate variance (std dev)."""
        if len(self.token_rates) < 2:
            return None
        mean = sum(self.token_rates) / len(self.token_rates)
        variance = sum((x - mean) ** 2 for x in self.token_rates) / len(self.token_rates)
        return variance ** 0.5  # Standard deviation
    
    def get_avg_inter_token_latency(self) -> Optional[float]:
        """Get average inter-token latency in milliseconds."""
        if not self.inter_token_latencies:
            return None
        return sum(self.inter_token_latencies) / len(self.inter_token_latencies)
    
    def get_avg_response_duration(self) -> Optional[float]:
        """Get average response duration in seconds."""
        if not self.response_durations:
            return None
        return sum(self.response_durations) / len(self.response_durations)
    
    def get_response_duration_p95(self) -> Optional[float]:
        """Get p95 response duration in seconds."""
        return self.calculate_percentile(self.response_durations, 95)


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
                Layout(name="current", size=25),
                Layout(name="metrics", size=20)
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
        """Create live metrics comparison table with enhanced statistics."""
        table = Table(
            title="⚡ Live Performance Metrics & Statistics",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta",
            title_style="bold cyan"
        )
        
        table.add_column("Engine", style="cyan", width=16)
        table.add_column("Progress", justify="center", width=9)
        table.add_column("Tokens/sec\n(avg±σ)", justify="right", width=13)
        table.add_column("TTFT\n(avg/p95)", justify="right", width=12)
        table.add_column("Gen Time\n(avg/p95)", justify="right", width=12)
        table.add_column("Inter-tok\n(avg ms)", justify="right", width=11)
        table.add_column("Tokens", justify="right", width=9)
        table.add_column("Status", justify="center", width=9)
        
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
                tps_variance = None
                avg_ttft = None
                ttft_p95 = None
                avg_response_duration = None
                response_duration_p95 = None
                avg_inter_token = None
            else:
                completed = getattr(stats, "completed", 0)
                failed = getattr(stats, "failed", 0)
                avg_tps = getattr(stats, "avg_tps", 0)
                total_tokens = getattr(stats, "total_tokens", 0)
                target_count = getattr(stats, "target", 0)
                tps_variance = stats.get_token_rate_variance()
                avg_ttft = stats.get_avg_ttft()
                ttft_p95 = stats.get_ttft_p95()
                avg_response_duration = stats.get_avg_response_duration()
                response_duration_p95 = stats.get_response_duration_p95()
                avg_inter_token = stats.get_avg_inter_token_latency()
            
            total = completed + failed
            
            # Progress
            progress_text = f"{completed}/{target_count}"
            
            # Tokens per second with variance
            if avg_tps > 0:
                if tps_variance and tps_variance > 0:
                    tps_text = f"{avg_tps:.1f}±{tps_variance:.1f}"
                else:
                    tps_text = f"{avg_tps:.1f}"
            else:
                tps_text = "-"
            
            # Color coding for TPS
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
            
            # TTFT (avg / p95)
            if avg_ttft is not None:
                if ttft_p95 is not None:
                    ttft_text = f"{avg_ttft:.3f}/{ttft_p95:.3f}s"
                else:
                    ttft_text = f"{avg_ttft:.3f}s"
                
                # Color code TTFT (lower is better)
                if avg_ttft < 0.1:
                    ttft_style = "bold green"
                elif avg_ttft < 0.3:
                    ttft_style = "bold cyan"
                elif avg_ttft < 0.5:
                    ttft_style = "bold yellow"
                else:
                    ttft_style = "bold red"
                    
                ttft_display = f"[{ttft_style}]{ttft_text}[/{ttft_style}]"
            else:
                ttft_display = "[dim]-[/dim]"
            
            # Total generation time (avg / p95)
            if avg_response_duration is not None:
                if response_duration_p95 is not None:
                    gen_time_text = f"{avg_response_duration:.2f}/{response_duration_p95:.2f}s"
                else:
                    gen_time_text = f"{avg_response_duration:.2f}s"
                
                # Color code generation time (lower is better for same quality)
                if avg_response_duration < 5:
                    gen_time_style = "bold green"
                elif avg_response_duration < 10:
                    gen_time_style = "bold cyan"
                elif avg_response_duration < 20:
                    gen_time_style = "bold yellow"
                else:
                    gen_time_style = "bold red"
                    
                gen_time_display = f"[{gen_time_style}]{gen_time_text}[/{gen_time_style}]"
            else:
                gen_time_display = "[dim]-[/dim]"
            
            # Inter-token latency
            if avg_inter_token is not None:
                inter_token_text = f"{avg_inter_token:.1f}"
                
                # Color code inter-token (lower is better)
                if avg_inter_token < 20:
                    inter_token_style = "bold green"
                elif avg_inter_token < 50:
                    inter_token_style = "bold cyan"
                elif avg_inter_token < 100:
                    inter_token_style = "bold yellow"
                else:
                    inter_token_style = "bold red"
                    
                inter_token_display = f"[{inter_token_style}]{inter_token_text}[/{inter_token_style}]"
            else:
                inter_token_display = "[dim]-[/dim]"
            
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
                tps_display,
                ttft_display,
                gen_time_display,
                inter_token_display,
                tokens_text,
                status
            )
        
        return table

