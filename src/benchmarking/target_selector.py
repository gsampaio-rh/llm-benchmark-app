"""
Target selector for benchmark engines and models.

Provides reusable interactive selection for engines and models
to be benchmarked.
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass

from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich import box

from ..core.connection_manager import ConnectionManager
from ..utils.k8s_metadata import PodInfo


@dataclass
class BenchmarkTarget:
    """A target for benchmarking (engine + model)."""
    engine_name: str
    model_name: str
    engine_type: str = "unknown"
    base_url: Optional[str] = None
    pod_info: Optional[PodInfo] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "engine": self.engine_name,
            "model": self.model_name,
            "type": self.engine_type,
            "url": self.base_url or "unknown",
            "pod_info": self.pod_info
        }


class TargetSelector:
    """
    Interactive selector for benchmark targets.
    
    Provides reusable UI for selecting engines and models to benchmark.
    """
    
    def __init__(self, console: Optional[Console] = None):
        """
        Initialize target selector.
        
        Args:
            console: Rich console instance
        """
        self.console = console or Console()
    
    async def select_targets(
        self,
        connection_manager: ConnectionManager,
        phase_label: str = "Phase 2/5"
    ) -> List[BenchmarkTarget]:
        """
        Interactive selection of engines and models.
        
        Args:
            connection_manager: Connection manager with registered engines
            phase_label: Label for progress phase
            
        Returns:
            List of BenchmarkTarget objects
        """
        self.console.print(f"[bold cyan]{phase_label}:[/bold cyan] Select engines and models...\n")
        
        targets = []
        engines = list(connection_manager.adapters.keys())
        
        if not engines:
            self.console.print("[red]❌ No engines available![/red]")
            return targets
        
        # Display available engines
        engines_table = Table(title="🚀 Available Engines", box=box.ROUNDED)
        engines_table.add_column("#", style="cyan", justify="center")
        engines_table.add_column("Engine", style="magenta")
        engines_table.add_column("Type", style="blue")
        engines_table.add_column("Status", justify="center")
        
        for idx, engine in enumerate(engines, 1):
            adapter = connection_manager.get_adapter(engine)
            engines_table.add_row(
                str(idx),
                engine,
                adapter.config.engine_type if adapter else "unknown",
                "✅ Ready"
            )
        
        self.console.print(engines_table)
        self.console.print()
        
        # Select engines
        selected_engines = self._select_engines(engines)
        
        # For each engine, select model
        for engine_name in selected_engines:
            target = await self._select_model_for_engine(connection_manager, engine_name)
            if target:
                targets.append(target)
        
        # Display summary
        if targets:
            self._display_targets_summary(targets)
        
        return targets
    
    def _select_engines(self, engines: List[str]) -> List[str]:
        """Select which engines to benchmark."""
        if len(engines) == 1:
            self.console.print(f"  ℹ️  Auto-selected: [cyan]{engines[0]}[/cyan]\n")
            return engines
        
        if Confirm.ask("Benchmark all engines?", default=True):
            self.console.print(f"  ✅ Selected all {len(engines)} engine(s)\n")
            return engines
        else:
            indices = Prompt.ask("Enter engine numbers (comma-separated)", default="1")
            selected_indices = [int(i.strip()) - 1 for i in indices.split(",")]
            selected = [engines[i] for i in selected_indices if 0 <= i < len(engines)]
            self.console.print(f"  ✅ Selected {len(selected)} engine(s)\n")
            return selected
    
    async def _select_model_for_engine(
        self,
        connection_manager: ConnectionManager,
        engine_name: str
    ) -> Optional[BenchmarkTarget]:
        """Select model for a specific engine."""
        self.console.print(f"[bold]Model for {engine_name}:[/bold]")
        
        # Discover models
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            task = progress.add_task("Discovering models...", total=None)
            models = await connection_manager.discover_models(engine_name)
            progress.update(task, completed=True)
        
        adapter = connection_manager.get_adapter(engine_name)
        engine_type = adapter.config.engine_type if adapter else "unknown"
        base_url = str(adapter.config.base_url) if adapter else None
        
        # Fetch pod info (async) - this might take a moment
        pod_info = None
        if base_url:
            try:
                from ..utils.k8s_metadata import get_pod_info_for_url
                pod_info = await get_pod_info_for_url(base_url)
                if pod_info:
                    self.console.print(f"  [dim]📦 Found pod: {pod_info.pod_name}[/dim]")
            except Exception as e:
                self.console.print(f"  [dim]⚠️  Could not fetch pod info: {e}[/dim]")
        
        # Handle no models found
        if not models:
            self.console.print("  [yellow]⚠️  No models found, enter manually[/yellow]")
            model_name = Prompt.ask(f"  Model name for {engine_name}")
            self.console.print()
            return BenchmarkTarget(
                engine_name=engine_name,
                model_name=model_name,
                engine_type=engine_type,
                base_url=base_url,
                pod_info=pod_info
            )
        
        # Display models
        models_table = Table(box=box.SIMPLE)
        models_table.add_column("#", style="cyan", justify="center")
        models_table.add_column("Model", style="magenta")
        models_table.add_column("Size", style="blue")
        
        for idx, model in enumerate(models[:5], 1):
            models_table.add_row(
                str(idx),
                model.name,
                model.size or "Unknown"
            )
        
        if len(models) > 5:
            models_table.add_row("...", f"({len(models) - 5} more)", "")
        
        self.console.print(models_table)
        
        # Select model
        model_choice = Prompt.ask("  Select model number", default="1")
        selected_model = None
        
        try:
            idx = int(model_choice) - 1
            if 0 <= idx < len(models):
                selected_model = models[idx].name
        except ValueError:
            selected_model = model_choice
        
        self.console.print()
        
        if selected_model:
            return BenchmarkTarget(
                engine_name=engine_name,
                model_name=selected_model,
                engine_type=engine_type,
                base_url=base_url,
                pod_info=pod_info
            )
        
        return None
    
    def _display_targets_summary(self, targets: List[BenchmarkTarget]) -> None:
        """Display summary of selected targets."""
        summary_lines = []
        for i, t in enumerate(targets, 1):
            line = f"[cyan]{i}.[/cyan] {t.engine_name} → {t.model_name}"
            if t.base_url:
                line += f"\n   [dim]🌐 {t.base_url}[/dim]"
            if t.pod_info and t.pod_info.resources:
                res = t.pod_info.resources
                resource_parts = []
                if res.cpu_limit:
                    resource_parts.append(f"CPU: {res.cpu_limit}")
                if res.memory_limit:
                    resource_parts.append(f"RAM: {res.memory_limit}")
                if res.gpu_count:
                    resource_parts.append(f"GPU: {res.gpu_count}x")
                if resource_parts:
                    line += f"\n   [dim]💻 {' | '.join(resource_parts)}[/dim]"
            summary_lines.append(line)
        
        self.console.print(Panel(
            "\n".join(summary_lines),
            title="📋 Benchmark Targets",
            border_style="cyan",
            box=box.ROUNDED
        ))
        self.console.print()

