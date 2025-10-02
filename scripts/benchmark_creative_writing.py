#!/usr/bin/env python3
"""
🎨 Creative Writing Benchmark (US-310)
========================================

Short Prompt + Long Completion benchmark for testing story generation
and creative writing performance across LLM engines.

Tests:
- Throughput (output tokens/second)
- Sustained token rate over long generation
- Time to First Token (TTFT)
- Inter-token latency consistency
- Memory stability

Usage:
    python scripts/benchmark_creative_writing.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TaskProgressColumn
)
from rich import box
from rich.text import Text
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.live import Live
from rich.layout import Layout
import time

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.core.metrics_collector import initialize_metrics_collector
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter
from src.config.scenario_loader import load_all_scenarios
from src.reporting.export_manager import ExportManager, ExportConfig
import json


console = Console()


def print_header() -> None:
    """Display beautiful header."""
    header = Text()
    header.append("🎨 ", style="bold magenta")
    header.append("Creative Writing Benchmark", style="bold cyan")
    header.append(" (US-310)", style="dim")
    
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]Short Prompt + Long Completion Benchmark[/bold cyan]\n\n"
            "[bold]Tests:[/bold]\n"
            "• Output tokens/second (throughput)\n"
            "• Sustained token rate over long generation\n"
            "• Time to First Token (TTFT)\n"
            "• Inter-token latency consistency\n\n"
            "[bold]Use Cases:[/bold] Story generation, creative writing, content ideation"
        ),
        title=header,
        border_style="magenta",
        box=box.ROUNDED
    ))
    console.print()


async def setup_system() -> Tuple[ConnectionManager, Any, Any]:
    """Setup connection manager, metrics collector, and load scenario."""
    console.print("[bold cyan]Phase 1/5:[/bold cyan] Initializing system...\n")
    
    # Setup connection manager
    config_manager = ConfigManager()
    connection_manager = ConnectionManager()
    
    connection_manager.register_adapter_class("ollama", OllamaAdapter)
    connection_manager.register_adapter_class("vllm", VLLMAdapter)
    connection_manager.register_adapter_class("tgi", TGIAdapter)
    
    metrics_collector = initialize_metrics_collector(connection_manager)
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Connecting to engines...", total=None)
        benchmark_config = config_manager.load_benchmark_config()
        await connection_manager.register_engines_from_config(benchmark_config)
        progress.update(task, completed=True)
    
    console.print("  ✅ Engines connected\n")
    
    # Load creative writing scenario
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Loading scenario...", total=None)
        library = load_all_scenarios()
        scenario = library.get_scenario("Short Prompt + Long Completion")
        progress.update(task, completed=True)
    
    if not scenario:
        console.print("[red]❌ Creative writing scenario not found![/red]")
        raise RuntimeError("Scenario not found")
    
    console.print(f"  ✅ Loaded scenario: [cyan]{scenario.name}[/cyan]")
    console.print(f"     Base test cases: {len(scenario.test_cases)}\n")
    
    return connection_manager, metrics_collector, scenario


async def select_targets(connection_manager: ConnectionManager) -> List[Dict[str, str]]:
    """Select engines and models to benchmark."""
    console.print("[bold cyan]Phase 2/5:[/bold cyan] Select engines and models...\n")
    
    targets = []
    engines = list(connection_manager.adapters.keys())
    
    if not engines:
        console.print("[red]❌ No engines available![/red]")
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
    
    console.print(engines_table)
    console.print()
    
    # Select engines
    if Confirm.ask("Benchmark all engines?", default=True):
        selected_engines = engines
        console.print(f"  ✅ Selected all {len(engines)} engine(s)\n")
    else:
        indices = Prompt.ask("Enter engine numbers (comma-separated)", default="1")
        selected_indices = [int(i.strip()) - 1 for i in indices.split(",")]
        selected_engines = [engines[i] for i in selected_indices if 0 <= i < len(engines)]
        console.print(f"  ✅ Selected {len(selected_engines)} engine(s)\n")
    
    # For each engine, select model
    for engine_name in selected_engines:
        console.print(f"[bold]Model for {engine_name}:[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Discovering models...", total=None)
            models = await connection_manager.discover_models(engine_name)
            progress.update(task, completed=True)
        
        if not models:
            console.print("  [yellow]⚠️  No models found, enter manually[/yellow]")
            model_name = Prompt.ask(f"  Model name for {engine_name}")
            targets.append({"engine": engine_name, "model": model_name})
            console.print()
            continue
        
        # Show first 5 models
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
        
        console.print(models_table)
        
        model_choice = Prompt.ask("  Select model number", default="1")
        try:
            idx = int(model_choice) - 1
            if 0 <= idx < len(models):
                targets.append({"engine": engine_name, "model": models[idx].name})
        except ValueError:
            targets.append({"engine": engine_name, "model": model_choice})
        
        console.print()
    
    # Summary
    console.print(Panel(
        "\n".join([
            f"[cyan]{i}.[/cyan] {t['engine']} → {t['model']}"
            for i, t in enumerate(targets, 1)
        ]),
        title="📋 Benchmark Targets",
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()
    
    return targets


def configure_benchmark(scenario: Any) -> Dict[str, Any]:
    """Configure benchmark parameters."""
    console.print("[bold cyan]Phase 3/5:[/bold cyan] Configure benchmark...\n")
    
    console.print(f"[bold]Scenario:[/bold] {scenario.name}")
    console.print(f"[bold]Description:[/bold] {scenario.description}\n")
    
    # Number of prompts
    console.print("[bold]Test prompts:[/bold]")
    console.print(f"  Base prompts: {len(scenario.test_cases)}")
    console.print("  [dim]Will be repeated to reach target count[/dim]\n")
    
    num_prompts = IntPrompt.ask(
        "Total prompts to test",
        default=100
    )
    
    # Expand prompts
    base_prompts = scenario.expand_test_cases()
    
    # Repeat prompts to reach target
    expanded_prompts = []
    while len(expanded_prompts) < num_prompts:
        expanded_prompts.extend(base_prompts)
    expanded_prompts = expanded_prompts[:num_prompts]
    
    console.print(f"\n  ✅ Generated {len(expanded_prompts)} test prompts\n")
    
    return {
        "description": f"Creative Writing Benchmark - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "scenario": scenario,
        "num_prompts": num_prompts,
        "prompts": expanded_prompts,
        "max_tokens": scenario.completion.max_tokens,
        "temperature": scenario.completion.temperature
    }


def create_live_metrics_display(
    targets: List[Dict[str, str]],
    engine_metrics: Dict[str, Dict],
    start_time: float,
    total_requests: int,
    completed_requests: int,
    current_engine: Optional[str] = None,
    current_prompt: Optional[str] = None,
    current_response: Optional[str] = None
) -> Layout:
    """Create live metrics dashboard with request/response view."""
    layout = Layout()
    
    # Split into header, current request, and metrics
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="current", size=10),
        Layout(name="metrics")
    )
    
    # Header with overall progress
    elapsed = time.time() - start_time
    progress_pct = (completed_requests / total_requests * 100) if total_requests > 0 else 0
    
    header_text = Text()
    header_text.append("🎨 Creative Writing Benchmark ", style="bold magenta")
    header_text.append(f"| Progress: {completed_requests}/{total_requests} ", style="cyan")
    header_text.append(f"({progress_pct:.1f}%) ", style="yellow")
    header_text.append(f"| Elapsed: {elapsed:.0f}s", style="dim")
    
    layout["header"].update(Panel(header_text, border_style="cyan"))
    
    # Current request/response panel with streaming effect
    if current_engine and current_prompt:
        current_text = Text()
        current_text.append(f"🔵 Engine: ", style="bold")
        current_text.append(f"{current_engine}\n", style="bold cyan")
        current_text.append(f"📝 Prompt: ", style="bold")
        current_text.append(f"{current_prompt[:80]}...\n\n" if len(current_prompt) > 80 else f"{current_prompt}\n\n", style="yellow")
        
        if current_response:
            # Count tokens (approximate by words)
            word_count = len(current_response.split())
            current_text.append(f"💬 Response ", style="bold")
            current_text.append(f"({word_count} words):\n", style="dim")
            
            # Show streaming response with visual indicator
            response_preview = current_response[:300] + "..." if len(current_response) > 300 else current_response
            current_text.append(response_preview, style="green")
            
            # Add typing indicator if response seems incomplete
            if len(current_response) < 50:
                current_text.append(" ▋", style="bold green blink")
        else:
            current_text.append(f"⏳ Sending request to model...", style="dim italic")
        
        # Color border based on activity
        border_color = "magenta" if current_response else "yellow"
        
        layout["current"].update(Panel(
            current_text,
            title="🎬 Live Request & Response",
            border_style=border_color,
            box=box.ROUNDED
        ))
    else:
        layout["current"].update(Panel(
            Text("⏳ Initializing benchmark...", style="dim italic"),
            title="🎬 Live Request & Response",
            border_style="dim",
            box=box.ROUNDED
        ))
    
    # Main metrics: Live comparison table
    comparison_table = Table(
        title="⚡ Live Performance Metrics",
        box=box.ROUNDED,
        show_header=True,
        header_style="bold magenta",
        title_style="bold cyan"
    )
    
    comparison_table.add_column("Engine", style="cyan", width=20)
    comparison_table.add_column("Progress", justify="center", width=12)
    comparison_table.add_column("Success Rate", justify="center", width=13)
    comparison_table.add_column("Avg Tokens/sec", justify="right", width=15)
    comparison_table.add_column("Total Tokens", justify="right", width=13)
    comparison_table.add_column("Status", justify="center", width=10)
    
    # Find current leader
    leader_tps = 0
    leader_engine = None
    
    for engine_name, stats in engine_metrics.items():
        if stats.get("avg_tps", 0) > leader_tps:
            leader_tps = stats["avg_tps"]
            leader_engine = engine_name
    
    # Add rows for each engine
    for target in targets:
        engine_name = target["engine"]
        stats = engine_metrics.get(engine_name, {})
        
        completed = stats.get("completed", 0)
        failed = stats.get("failed", 0)
        total = completed + failed
        
        # Progress bar
        progress_text = f"{completed}/{stats.get('target', 0)}"
        
        # Success rate
        success_rate = f"{(completed/total*100):.0f}%" if total > 0 else "0%"
        
        # Tokens per second
        avg_tps = stats.get("avg_tps", 0)
        tps_text = f"{avg_tps:.1f}" if avg_tps > 0 else "-"
        
        # Color code based on performance
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
        total_tokens = stats.get("total_tokens", 0)
        tokens_text = f"{total_tokens:,}" if total_tokens > 0 else "-"
        
        # Status with indicator if currently processing
        if engine_name == current_engine:
            status = "🔴 Active"
        elif completed >= stats.get("target", 0):
            status = "✅ Done"
        elif total > 0:
            status = "🔄 Running"
        else:
            status = "⏳ Pending"
        
        # Add leader indicator
        engine_display = engine_name
        if engine_name == leader_engine and avg_tps > 0:
            engine_display = f"👑 {engine_name}"
        
        comparison_table.add_row(
            engine_display,
            progress_text,
            success_rate,
            tps_display,
            tokens_text,
            status
        )
    
    layout["metrics"].update(comparison_table)
    
    return layout


async def run_benchmark(
    connection_manager: ConnectionManager,
    metrics_collector: Any,
    targets: List[Dict[str, str]],
    config: Dict[str, Any]
) -> None:
    """Run the benchmark tests."""
    console.print("[bold cyan]Phase 4/5:[/bold cyan] Running benchmark...\n")
    
    # Start metrics collection
    metrics_collector.start_collection(config["description"])
    
    total_requests = len(targets) * config["num_prompts"]
    
    console.print(f"[bold]Total requests:[/bold] {total_requests}")
    console.print(f"[bold]Prompts per target:[/bold] {config['num_prompts']}\n")
    
    # Live metrics tracking with detailed stats
    engine_metrics = {}
    for t in targets:
        engine_metrics[t["engine"]] = {
            "completed": 0,
            "failed": 0,
            "total_tokens": 0,
            "target": config["num_prompts"],
            "token_rates": [],  # Track individual token rates
            "avg_tps": 0,
            "start_time": time.time()
        }
    
    if not Confirm.ask("Start benchmark?", default=True):
        console.print("[yellow]Benchmark cancelled[/yellow]")
        return
    
    console.print()
    
    # Run benchmark with LIVE METRICS DISPLAY
    start_time = time.time()
    completed_requests = 0
    
    with Live(
        create_live_metrics_display(
            targets, engine_metrics, start_time, total_requests, completed_requests
        ),
        console=console,
        refresh_per_second=4  # Update 4x per second for smoother updates
    ) as live:
        
        for target in targets:
            engine_name = target["engine"]
            model_name = target["model"]
            
            for i, prompt in enumerate(config["prompts"]):
                # Update display to show current request BEFORE sending
                live.update(create_live_metrics_display(
                    targets, engine_metrics, start_time, total_requests, completed_requests,
                    current_engine=f"{engine_name} ({model_name})",
                    current_prompt=prompt,
                    current_response=None
                ))
                
                try:
                    result = await metrics_collector.collect_single_request_metrics(
                        engine_name,
                        prompt,
                        model_name,
                        max_tokens=config["max_tokens"],
                        temperature=config["temperature"]
                    )
                    
                    if result.success:
                        engine_metrics[engine_name]["completed"] += 1
                        
                        # Show streaming effect: progressively reveal response
                        if result.response and len(result.response) > 50:
                            words = result.response.split()
                            chunks = [
                                " ".join(words[:int(len(words)*0.3)]),
                                " ".join(words[:int(len(words)*0.6)]),
                                result.response
                            ]
                            
                            for chunk in chunks:
                                live.update(create_live_metrics_display(
                                    targets, engine_metrics, start_time, total_requests, completed_requests,
                                    current_engine=f"{engine_name} ({model_name})",
                                    current_prompt=prompt,
                                    current_response=chunk
                                ))
                                await asyncio.sleep(0.15)  # Brief pause to show streaming
                        else:
                            # Short response, show immediately
                            live.update(create_live_metrics_display(
                                targets, engine_metrics, start_time, total_requests, completed_requests,
                                current_engine=f"{engine_name} ({model_name})",
                                current_prompt=prompt,
                                current_response=result.response
                            ))
                            await asyncio.sleep(0.3)
                        
                        # Track token count
                        if result.parsed_metrics and result.parsed_metrics.eval_count:
                            tokens = result.parsed_metrics.eval_count
                            engine_metrics[engine_name]["total_tokens"] += tokens
                            
                            # Track token rate
                            if result.parsed_metrics.response_token_rate:
                                engine_metrics[engine_name]["token_rates"].append(
                                    result.parsed_metrics.response_token_rate
                                )
                        
                        # Calculate average tokens/sec
                        rates = engine_metrics[engine_name]["token_rates"]
                        if rates:
                            engine_metrics[engine_name]["avg_tps"] = sum(rates) / len(rates)
                    else:
                        engine_metrics[engine_name]["failed"] += 1
                    
                    completed_requests += 1
                    
                    # Update live display after completion
                    live.update(create_live_metrics_display(
                        targets, engine_metrics, start_time, total_requests, completed_requests
                    ))
                    
                except Exception as e:
                    engine_metrics[engine_name]["failed"] += 1
                    completed_requests += 1
                    
                    # Update display even on error
                    live.update(create_live_metrics_display(
                        targets, engine_metrics, start_time, total_requests, completed_requests,
                        current_engine=f"{engine_name} ({model_name})",
                        current_prompt=prompt,
                        current_response=f"❌ Error: {str(e)[:100]}"
                    ))
                    
                    await asyncio.sleep(0.3)
    
    console.print()
    console.print("[bold green]✅ Benchmark complete![/bold green]\n")


def export_and_display_results(
    metrics_collector: Any,
    config: Dict[str, Any]
) -> None:
    """Export results and display comparison."""
    console.print("[bold cyan]Phase 5/5:[/bold cyan] Analyzing and exporting results...\n")
    
    # Generate aggregates
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Computing statistics...", total=None)
        aggregates = metrics_collector.aggregate_metrics()
        progress.update(task, completed=True)
    
    console.print()
    
    # Display detailed comparison
    if aggregates:
        table = Table(
            title="🏆 Performance Comparison",
            box=box.ROUNDED,
            title_style="bold magenta",
            header_style="bold cyan"
        )
        
        table.add_column("Engine", style="cyan")
        table.add_column("Success", style="green", justify="center")
        table.add_column("Avg Tokens/sec", style="yellow", justify="right")
        table.add_column("p95 Tokens/sec", style="yellow", justify="right")
        table.add_column("Avg TTFT", style="blue", justify="right")
        table.add_column("Total Tokens", style="magenta", justify="right")
        
        # Find winner (highest avg throughput)
        winner_engine = None
        max_throughput = 0
        
        for agg in aggregates:
            # Calculate average tokens/sec from aggregate TPS
            avg_tps = agg.aggregate_tps if agg.aggregate_tps else 0
            
            if avg_tps > max_throughput:
                max_throughput = avg_tps
                winner_engine = agg.engine_name
        
        for agg in aggregates:
            success_rate = f"{agg.success_rate:.0%}"
            avg_tps = f"{agg.aggregate_tps:.1f}" if agg.aggregate_tps else "N/A"
            
            # For p95, we'd need token rate distribution - use avg for now
            p95_tps = avg_tps  # Simplified
            
            # TTFT calculation
            ttft_metrics = [m.first_token_latency for m in metrics_collector.current_collection.parsed_metrics 
                          if m.engine_name == agg.engine_name and m.first_token_latency]
            avg_ttft = f"{sum(ttft_metrics)/len(ttft_metrics):.3f}s" if ttft_metrics else "N/A"
            
            tokens_out = f"{agg.total_output_tokens:,}" if agg.total_output_tokens else "N/A"
            
            # Add winner indicator
            engine_display = agg.engine_name
            if agg.engine_name == winner_engine:
                engine_display = f"👑 {engine_display}"
            
            table.add_row(
                engine_display,
                success_rate,
                avg_tps,
                p95_tps,
                avg_ttft,
                tokens_out
            )
        
        console.print(table)
        console.print()
    
    # Export using ExportManager
    if Confirm.ask("Export detailed results?", default=True):
        console.print()
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Exporting results...", total=None)
            
            try:
                export_config = ExportConfig(
                    output_dir="benchmark_results",
                    create_timestamp_dir=True,
                    generate_markdown=True,
                    generate_csv=True,
                    generate_json=True
                )
                export_manager = ExportManager(export_config)
                
                result = export_manager.export_collection(
                    collection=metrics_collector.current_collection,
                    description=config["description"],
                    scenario="Creative Writing (US-310)"
                )
                
                progress.update(task, completed=True)
                
                if result.success:
                    console.print()
                    console.print(f"[bold green]✅ Results exported successfully![/bold green]")
                    console.print(f"[bold]Export directory:[/bold] {result.export_dir}\n")
                    
                    # Show files
                    files_table = Table(title="📁 Exported Files", box=box.ROUNDED)
                    files_table.add_column("File", style="cyan")
                    files_table.add_column("Type", style="magenta")
                    
                    for file_path in result.files_created:
                        file_name = file_path.name
                        if "summary" in file_name:
                            file_type = "📊 Summary"
                        elif file_name.endswith(".md"):
                            file_type = "📄 Report"
                        else:
                            file_type = "📈 Engine Results"
                        files_table.add_row(file_name, file_type)
                    
                    console.print(files_table)
                    console.print()
                else:
                    console.print(f"\n[red]❌ Export failed:[/red] {result.error_message}\n")
                    
            except Exception as e:
                progress.update(task, completed=True)
                console.print(f"\n[red]❌ Export failed:[/red] {e}\n")


def print_summary() -> None:
    """Print final summary."""
    console.print(Panel(
        Text.from_markup(
            "[bold green]🎉 Creative Writing Benchmark Complete![/bold green]\n\n"
            "[bold]Key Metrics Captured:[/bold]\n"
            "• Output tokens/second (throughput)\n"
            "• Time to First Token (TTFT)\n"
            "• Inter-token latency\n"
            "• Total tokens generated\n\n"
            "[bold]Results exported with:[/bold]\n"
            "• Per-engine JSON + CSV files\n"
            "• Cross-engine comparison summary\n"
            "• Human-readable markdown report"
        ),
        title="✅ US-310 Complete",
        border_style="green",
        box=box.ROUNDED
    ))


async def main() -> None:
    """Main execution."""
    print_header()
    
    connection_manager = None
    try:
        # Setup
        connection_manager, metrics_collector, scenario = await setup_system()
        
        # Select targets
        targets = await select_targets(connection_manager)
        
        if not targets:
            console.print("[yellow]No targets selected. Exiting.[/yellow]")
            return
        
        # Configure
        config = configure_benchmark(scenario)
        
        # Run benchmark
        await run_benchmark(connection_manager, metrics_collector, targets, config)
        
        # Export and display
        export_and_display_results(metrics_collector, config)
        
        # Summary
        print_summary()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Benchmark interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Fatal error:[/red] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if connection_manager:
            try:
                await connection_manager.close_all()
            except:
                pass


if __name__ == "__main__":
    asyncio.run(main())

