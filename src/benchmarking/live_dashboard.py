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
    # Token/word metrics
    tokens_per_response: list = None  # Token count per response
    words_per_response: list = None  # Word count per response
    
    def __post_init__(self):
        if self.token_rates is None:
            self.token_rates = []
        if self.ttft_values is None:
            self.ttft_values = []
        if self.inter_token_latencies is None:
            self.inter_token_latencies = []
        if self.response_durations is None:
            self.response_durations = []
        if self.tokens_per_response is None:
            self.tokens_per_response = []
        if self.words_per_response is None:
            self.words_per_response = []
    
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
    
    def get_avg_tokens_per_response(self) -> Optional[float]:
        """Get average tokens per response."""
        if not self.tokens_per_response:
            return None
        return sum(self.tokens_per_response) / len(self.tokens_per_response)
    
    def get_token_word_ratio(self) -> Optional[float]:
        """
        Get average token/word ratio.
        
        This shows tokenizer efficiency - different models tokenize differently.
        Lower ratio = more efficient tokenization (fewer tokens per word).
        Typical values: 1.2-1.5 for English text.
        """
        if not self.tokens_per_response or not self.words_per_response:
            return None
        if len(self.tokens_per_response) != len(self.words_per_response):
            return None
        
        # Calculate ratio for each response, then average
        ratios = []
        for tokens, words in zip(self.tokens_per_response, self.words_per_response):
            if words > 0:  # Avoid division by zero
                ratios.append(tokens / words)
        
        if not ratios:
            return None
        return sum(ratios) / len(ratios)


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
        default=2000,
        description="Characters to show in response preview"
    )
    prompt_preview_length: int = Field(
        default=100,
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
        current_response: Optional[str] = None,
        current_responses: Optional[Dict[str, str]] = None,
        current_prompts: Optional[Dict[str, str]] = None
    ) -> Layout:
        """
        Create complete dashboard layout.
        
        Supports both sequential mode (single engine) and parallel mode (all engines).
        
        Args:
            targets: List of engine/model targets
            engine_metrics: Real-time engine statistics
            start_time: Benchmark start timestamp
            total_requests: Total requests to execute
            completed_requests: Requests completed so far
            current_engine: Currently active engine (sequential mode)
            current_prompt: Current prompt being processed (sequential mode)
            current_response: Current response being generated (sequential mode)
            current_responses: Dict of engine -> current response (parallel mode)
            current_prompts: Dict of engine -> current prompt (parallel mode)
            
        Returns:
            Rich Layout with complete dashboard
        """
        # Detect parallel mode
        is_parallel_mode = current_responses is not None and any(current_responses.values())
        
        layout = Layout()
        
        # Configure layout structure based on mode
        if is_parallel_mode:
            # Parallel mode: multi-column streaming view
            layout.split_column(
                Layout(name="header", size=5),  # Progress bar
                Layout(name="engines", size=30),  # Multi-column engine panels
                Layout(name="metrics", minimum_size=12)  # Compact metrics
            )
        elif self.config.show_current_request:
            # Sequential mode: single large response area
            layout.split_column(
                Layout(name="header", size=5),  # Progress bar
                Layout(name="current", size=35),  # Large response area
                Layout(name="metrics", minimum_size=12)  # Compact metrics
            )
        else:
            # Minimal mode: just metrics
            layout.split_column(
                Layout(name="header", size=3),
                Layout(name="metrics")
            )
        
        # Build header
        layout["header"].update(
            self._create_header(start_time, total_requests, completed_requests)
        )
        
        # Build content area based on mode
        if is_parallel_mode:
            # Show multi-column parallel streaming
            layout["engines"].update(
                self._create_parallel_engines_panel(
                    targets, current_responses, current_prompts, engine_metrics
                )
            )
        elif self.config.show_current_request:
            # Show single engine panel
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
        """Create elegant header with overall progress - Jony Ive inspired."""
        elapsed = time.time() - start_time
        progress_pct = (completed_requests / total_requests * 100) if total_requests > 0 else 0
        
        # Create wider progress bar
        bar_width = 80
        filled = int(bar_width * progress_pct / 100)
        bar = "█" * filled + "░" * (bar_width - filled)
        
        header = Text()
        # Title row
        header.append(f"{self.config.title_emoji}  ", style="bold magenta")
        header.append(f"{self.config.title}", style="bold white")
        header.append(f"                    ", style="")
        header.append(f"{completed_requests}/{total_requests} requests", style="bright_cyan")
        header.append(f"  ·  ", style="bright_black")
        header.append(f"{progress_pct:.1f}%", style="bold yellow")
        header.append(f"  ·  ", style="bright_black")
        header.append(f"{self._format_time(elapsed)}", style="cyan")
        header.append("\n\n", style="")
        
        # Visual progress bar
        header.append(bar, style="cyan")
        
        return Panel(
            header,
            border_style="cyan",
            padding=(0, 1),
            box=box.HEAVY
        )
    
    def _format_time(self, seconds: float) -> str:
        """Format elapsed time elegantly."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            mins = int(seconds // 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds // 3600)
            mins = int((seconds % 3600) // 60)
            return f"{hours}h {mins}m"
    
    def _create_current_request_panel(
        self,
        current_engine: Optional[str],
        current_prompt: Optional[str],
        current_response: Optional[str]
    ) -> Panel:
        """Create elegant current request/response panel - Jony Ive inspired."""
        if not current_engine or not current_prompt:
            empty_text = Text()
            empty_text.append("\n", style="")
            empty_text.append("        Initializing", style="dim italic")
            empty_text.append("\n\n", style="")
            return Panel(
                empty_text,
                title="[dim]Streaming Response[/dim]",
                border_style="bright_black",
                box=box.SIMPLE,
                padding=(1, 2)
            )
        
        current_text = Text()
        
        # Engine - compact single line
        current_text.append(current_engine, style="bold bright_cyan")
        current_text.append("  ", style="")
        
        # Prompt - inline with good contrast
        current_text.append("→  ", style="bright_black")
        prompt_preview = (
            current_prompt[:100] + "..."
            if len(current_prompt) > 100
            else current_prompt
        )
        current_text.append(prompt_preview, style="bright_yellow")
        current_text.append("\n", style="")
        current_text.append("─" * 110, style="bright_black")
        current_text.append("\n\n", style="")
        
        if current_response:
            # Metadata line with better visibility
            if self.config.show_word_count:
                word_count = len(current_response.split())
                current_text.append(f"{word_count:,} words", style="bright_cyan")
                current_text.append(f"  ·  ", style="bright_black")
                current_text.append(f"{len(current_response):,} characters", style="bright_magenta")
                current_text.append("\n\n", style="")
            
            # Auto-scroll: show the last N characters that fit in the panel
            # If response is longer than preview limit, show the tail with scroll indicator
            if len(current_response) > self.config.response_preview_length:
                # Calculate how much we're scrolling past
                chars_hidden = len(current_response) - self.config.response_preview_length
                
                # Show scroll indicator with better visibility
                current_text.append(
                    f"▲  {chars_hidden:,} characters hidden above  ▲\n\n",
                    style="bold bright_black"
                )
                
                # Show the last N characters (scrolled to bottom)
                response_tail = current_response[-self.config.response_preview_length:]
                
                # Find a good breaking point (start of a word/sentence if possible)
                # Look for sentence breaks first, then word breaks
                for break_char in ['. ', '.\n', '! ', '?\n', ' ']:
                    break_idx = response_tail.find(break_char)
                    if break_idx > 0 and break_idx < 100:  # Within first 100 chars
                        response_tail = response_tail[break_idx + len(break_char):]
                        break
                
                current_text.append(response_tail, style="bright_green")
                current_text.append(" ▋", style="bold bright_green blink")  # Active typing indicator
            else:
                # Response fits in panel, show all
                current_text.append(current_response, style="bright_green")
                
                # Add typing indicator for short responses
                if len(current_response) < 200:
                    current_text.append(" ▋", style="bold bright_green blink")
        else:
            current_text.append(f"⏳ Sending request to model...", style="dim italic")
        
        # Panel with clear visual hierarchy
        if current_response:
            title_text = "[bold green]● [/bold green][bold white]Live Streaming[/bold white]"
            border_color = "green"
        else:
            title_text = "[dim]○ Initializing[/dim]"
            border_color = "bright_black"
        
        return Panel(
            current_text,
            title=title_text,
            border_style=border_color,
            box=box.HEAVY,
            padding=(1, 1)
        )
    
    def _create_parallel_engines_panel(
        self,
        targets: List[Dict[str, str]],
        current_responses: Dict[str, str],
        current_prompts: Dict[str, str],
        engine_metrics: Dict[str, EngineStats]
    ) -> Layout:
        """
        Create multi-column panel showing all engines streaming in parallel.
        
        Similar to the race demo, shows all engines side-by-side with live streaming.
        """
        from rich.layout import Layout
        from rich.text import Text
        
        # Create layout for engines
        engines_layout = Layout()
        
        # Create columns for each engine
        engine_names = [target["engine"] for target in targets]
        columns = []
        for i, engine_name in enumerate(engine_names):
            columns.append(Layout(name=f"engine_{i}"))
        
        # Split into columns (up to 3 engines side-by-side)
        if len(columns) > 0:
            engines_layout.split_row(*columns)
        
        # Fill each column with engine panel
        for i, target in enumerate(targets):
            engine_name = target["engine"]
            response = current_responses.get(engine_name, "")
            prompt = current_prompts.get(engine_name, "")
            stats = engine_metrics.get(engine_name)
            
            # Create panel for this engine with URL info and pod info
            panel = self._create_engine_column_panel(
                engine_name, response, prompt, stats, 
                engine_url=target.get("url"),
                engine_type=target.get("type"),
                pod_info=target.get("pod_info")
            )
            engines_layout[f"engine_{i}"].update(panel)
        
        return engines_layout
    
    def _create_engine_column_panel(
        self,
        engine_name: str,
        response: str,
        prompt: str,
        stats: Optional[EngineStats],
        engine_url: Optional[str] = None,
        engine_type: Optional[str] = None,
        pod_info: Optional[Any] = None
    ) -> Panel:
        """Create a compact panel for one engine in parallel mode with auto-scroll."""
        from rich.text import Text
        
        content = Text()
        
        # Engine info header
        if engine_url:
            content.append("🌐 ", style="dim")
            content.append(engine_url, style="bright_black italic")
            content.append("\n", style="")
        if engine_type:
            content.append("⚙️  ", style="dim")
            content.append(engine_type, style="bright_black")
            content.append("\n", style="")
        
        # Pod and resource information
        if pod_info:
            if pod_info.pod_name:
                content.append("🐳 ", style="dim")
                content.append(pod_info.pod_name, style="bright_black")
                if pod_info.namespace:
                    content.append(f" ({pod_info.namespace})", style="dim")
                content.append("\n", style="")
            
            if pod_info.resources:
                res = pod_info.resources
                
                # CPU
                if res.cpu_request or res.cpu_limit:
                    content.append("💻 ", style="dim")
                    if res.cpu_request:
                        content.append(f"{res.cpu_request}", style="cyan")
                    if res.cpu_limit:
                        content.append(f" → {res.cpu_limit}", style="bright_cyan")
                    content.append("\n", style="")
                
                # Memory
                if res.memory_request or res.memory_limit:
                    content.append("🧠 ", style="dim")
                    if res.memory_request:
                        content.append(f"{res.memory_request}", style="yellow")
                    if res.memory_limit:
                        content.append(f" → {res.memory_limit}", style="bright_yellow")
                    content.append("\n", style="")
                
                # GPU
                if res.gpu_count:
                    content.append("🎮 ", style="dim")
                    content.append(f"{res.gpu_count}x GPU", style="green")
                    if res.gpu_type:
                        gpu_display = res.gpu_type.split('/')[-1]
                        content.append(f" ({gpu_display})", style="dim")
                    content.append("\n", style="")
        
        if engine_url or engine_type or pod_info:
            content.append("─" * 40, style="bright_black")
            content.append("\n", style="")
        
        # Status line with metrics
        if stats:
            content.append(f"{stats.completed}/{stats.target}", style="cyan")
            if stats.failed > 0:
                content.append(f" ({stats.failed} failed)", style="red")
        else:
            content.append("Starting...", style="dim")
        
        content.append("\n\n", style="")
        
        # Show prompt if actively streaming
        if prompt:
            prompt_preview = prompt[:80] + "..." if len(prompt) > 80 else prompt
            content.append(prompt_preview, style="dim")
            content.append("\n", style="")
            content.append("─" * 40, style="bright_black")
            content.append("\n\n", style="")
        
        # Show response with auto-scroll
        if response:
            # Add word and character count
            word_count = len(response.split())
            char_count = len(response)
            content.append(f"{word_count:,} words", style="bright_cyan")
            content.append("  ·  ", style="bright_black")
            content.append(f"{char_count:,} chars", style="bright_magenta")
            content.append("\n\n", style="")
            
            # Auto-scroll: show last N characters for multi-column view
            max_chars = 800  # Show more text in parallel view (increased for better readability)
            
            if len(response) > max_chars:
                # Calculate how much we're scrolling past
                chars_hidden = len(response) - max_chars
                
                # Show scroll indicator
                content.append(
                    f"▲  {chars_hidden:,} characters hidden above  ▲\n\n",
                    style="bold bright_black"
                )
                
                # Show the last N characters (scrolled to bottom)
                response_tail = response[-max_chars:]
                
                # Find a good breaking point (start of a word/sentence if possible)
                for break_char in ['. ', '.\n', '! ', '?\n', ' ']:
                    break_idx = response_tail.find(break_char)
                    if break_idx > 0 and break_idx < 100:
                        response_tail = response_tail[break_idx + len(break_char):]
                        break
                
                content.append(response_tail, style="bright_green")
            else:
                # Response fits in panel, show all
                content.append(response, style="bright_green")
            
            # Add typing cursor if streaming
            content.append(" ▋", style="bold bright_green blink")
            
        elif prompt:
            # Has prompt but no response yet
            content.append("Generating...", style="dim italic")
        else:
            # Idle
            content.append("Waiting...", style="dim italic")
        
        # Panel styling based on state
        if response:
            border_style = "green"
            title_emoji = "●"
        elif prompt:
            border_style = "yellow"
            title_emoji = "○"
        else:
            border_style = "bright_black"
            title_emoji = "○"
        
        return Panel(
            content,
            title=f"[bold]{title_emoji} {engine_name}[/bold]",
            border_style=border_style,
            box=box.ROUNDED,
            padding=(1, 1)
        )
    
    def _create_metrics_table(
        self,
        targets: List[Dict[str, str]],
        engine_metrics: Dict[str, Any],
        current_engine: Optional[str]
    ) -> Table:
        """Create elegant metrics table - Jony Ive inspired clean design."""
        table = Table(
            title="[bold white]Performance Metrics[/bold white]",
            box=box.HEAVY,
            show_header=True,
            header_style="bold white",
            title_style="bold white",
            show_edge=True,
            border_style="bright_black",
            padding=(0, 2),
            expand=True
        )
        
        # Wider, cleaner columns with better spacing
        table.add_column("Engine", style="bold white", width=16)
        table.add_column("Progress", justify="center", width=9)
        table.add_column("Throughput\n(avg ± σ)", justify="right", width=15, header_style="cyan")
        table.add_column("TTFT\n(avg · p95)", justify="right", width=14, header_style="yellow")
        table.add_column("Duration\n(avg · p95)", justify="right", width=14, header_style="magenta")
        table.add_column("Inter-tok\n(avg)", justify="right", width=11, header_style="green")
        table.add_column("Tokens\n/Resp", justify="right", width=10, header_style="bright_blue")
        table.add_column("Tok/\nWord", justify="right", width=8, header_style="bright_magenta")
        table.add_column("Total", justify="right", width=9)
        table.add_column("", justify="center", width=4)  # Status
        
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
                avg_tokens_per_resp = None
                token_word_ratio = None
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
                avg_tokens_per_resp = stats.get_avg_tokens_per_response()
                token_word_ratio = stats.get_token_word_ratio()
            
            total = completed + failed
            
            # Progress
            progress_text = f"{completed}/{target_count}"
            
            # Throughput - clear avg ± variance
            if avg_tps > 0:
                if tps_variance is not None:
                    tps_text = f"{avg_tps:.1f} ± {tps_variance:.1f}"
                else:
                    tps_text = f"{avg_tps:.1f}"
                
                # Strong color for good performance
                if avg_tps >= 50:
                    tps_display = f"[bold green]{tps_text}[/bold green] [dim]tok/s[/dim]"
                elif avg_tps >= 30:
                    tps_display = f"[green]{tps_text}[/green] [dim]tok/s[/dim]"
                elif avg_tps >= 15:
                    tps_display = f"[yellow]{tps_text}[/yellow] [dim]tok/s[/dim]"
                else:
                    tps_display = f"[white]{tps_text}[/white] [dim]tok/s[/dim]"
            else:
                tps_display = "[bright_black]—[/bright_black]"
            
            # TTFT - clear avg · p95 format in milliseconds
            if avg_ttft is not None:
                ttft_ms_avg = avg_ttft * 1000
                if ttft_p95 is not None:
                    ttft_ms_p95 = ttft_p95 * 1000
                    ttft_text = f"{ttft_ms_avg:.0f} · {ttft_ms_p95:.0f}"
                else:
                    ttft_text = f"{ttft_ms_avg:.0f}"
                
                # Good latency = green/yellow, slower = white
                if avg_ttft < 0.1:
                    ttft_display = f"[bold green]{ttft_text}[/bold green] [dim]ms[/dim]"
                elif avg_ttft < 0.2:
                    ttft_display = f"[green]{ttft_text}[/green] [dim]ms[/dim]"
                elif avg_ttft < 0.4:
                    ttft_display = f"[yellow]{ttft_text}[/yellow] [dim]ms[/dim]"
                else:
                    ttft_display = f"[white]{ttft_text}[/white] [dim]ms[/dim]"
            else:
                ttft_display = "[bright_black]—[/bright_black]"
            
            # Total generation time - clear avg · p95 format
            if avg_response_duration is not None:
                if response_duration_p95 is not None:
                    gen_time_text = f"{avg_response_duration:.1f} · {response_duration_p95:.1f}"
                else:
                    gen_time_text = f"{avg_response_duration:.1f}"
                
                # Fast = magenta/purple tones
                if avg_response_duration < 5:
                    gen_time_display = f"[bold magenta]{gen_time_text}[/bold magenta] [dim]s[/dim]"
                elif avg_response_duration < 15:
                    gen_time_display = f"[magenta]{gen_time_text}[/magenta] [dim]s[/dim]"
                else:
                    gen_time_display = f"[white]{gen_time_text}[/white] [dim]s[/dim]"
            else:
                gen_time_display = "[bright_black]—[/bright_black]"
            
            # Inter-token latency - smooth = green
            if avg_inter_token is not None:
                inter_token_text = f"{avg_inter_token:.1f}"
                
                # Low latency = green (smooth streaming)
                if avg_inter_token < 20:
                    inter_token_display = f"[bold green]{inter_token_text}[/bold green] [dim]ms[/dim]"
                elif avg_inter_token < 40:
                    inter_token_display = f"[green]{inter_token_text}[/green] [dim]ms[/dim]"
                elif avg_inter_token < 80:
                    inter_token_display = f"[yellow]{inter_token_text}[/yellow] [dim]ms[/dim]"
                else:
                    inter_token_display = f"[white]{inter_token_text}[/white] [dim]ms[/dim]"
            else:
                inter_token_display = "[bright_black]—[/bright_black]"
            
            # Tokens per response - shows response size consistency
            if avg_tokens_per_resp is not None and avg_tokens_per_resp > 0:
                tokens_per_resp_text = f"{avg_tokens_per_resp:.0f}"
                tokens_per_resp_display = f"[bright_blue]{tokens_per_resp_text}[/bright_blue]"
            else:
                tokens_per_resp_display = "[bright_black]—[/bright_black]"
            
            # Token/word ratio - shows tokenizer efficiency
            if token_word_ratio is not None:
                ratio_text = f"{token_word_ratio:.2f}"
                # Color code by efficiency: lower is better
                if token_word_ratio < 1.3:
                    ratio_display = f"[bold green]{ratio_text}[/bold green]"  # Efficient
                elif token_word_ratio < 1.5:
                    ratio_display = f"[green]{ratio_text}[/green]"  # Good
                elif token_word_ratio < 1.7:
                    ratio_display = f"[yellow]{ratio_text}[/yellow]"  # Average
                else:
                    ratio_display = f"[white]{ratio_text}[/white]"  # Less efficient
            else:
                ratio_display = "[bright_black]—[/bright_black]"
            
            # Total tokens - subtle
            tokens_text = f"{total_tokens:,}" if total_tokens > 0 else "—"
            
            # Active engine gets special treatment
            engine_match = current_engine and engine_name in current_engine
            
            if engine_match:
                # ACTIVE - bright and obvious
                status = "●"
                status_style = "bold bright_green"
                engine_display = f"▶ {engine_name}"
                engine_style = "bold bright_green"
                progress_style = "bold bright_green"
            elif completed >= target_count and target_count > 0:
                # COMPLETED
                status = "✓"
                status_style = "bold green"
                engine_display = engine_name
                # Add leader star if applicable
                if engine_name == leader_engine and avg_tps > 0:
                    engine_display = f"★ {engine_name}"
                engine_style = "bright_white"
                progress_style = "green"
            elif total > 0:
                # IN PROGRESS
                status = "○"
                status_style = "bright_yellow"
                engine_display = engine_name
                engine_style = "white"
                progress_style = "bright_yellow"
            else:
                # PENDING
                status = "○"
                status_style = "bright_black"
                engine_display = engine_name
                engine_style = "dim white"
                progress_style = "dim"
            
            # Add row with dynamic styling based on state
            table.add_row(
                f"[{engine_style}]{engine_display}[/{engine_style}]",
                f"[{progress_style}]{progress_text}[/{progress_style}]",
                tps_display,
                ttft_display,
                gen_time_display,
                inter_token_display,
                tokens_per_resp_display,
                ratio_display,
                tokens_text,
                f"[{status_style}]{status}[/{status_style}]"
            )
        
        return table

