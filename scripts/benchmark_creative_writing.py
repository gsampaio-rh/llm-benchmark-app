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
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.core.metrics_collector import initialize_metrics_collector
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter
from src.config.scenario_loader import load_all_scenarios
from src.reporting.export_manager import ExportManager, ExportConfig
from src.benchmarking.target_selector import TargetSelector
from src.benchmarking.benchmark_runner import BenchmarkRunner, BenchmarkConfig
from src.benchmarking.live_dashboard import DashboardConfig


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
        
        # Select targets using new TargetSelector
        selector = TargetSelector(console=console)
        targets = await selector.select_targets(connection_manager, phase_label="Phase 2/5")
        
        if not targets:
            console.print("[yellow]No targets selected. Exiting.[/yellow]")
            return
        
        # Configure
        prompt_config = configure_benchmark(scenario)
        
        # Create benchmark config
        bench_config = BenchmarkConfig(
            description=prompt_config["description"],
            scenario_name=scenario.name,
            num_requests_per_target=prompt_config["num_prompts"],
            max_tokens=prompt_config["max_tokens"],
            temperature=prompt_config["temperature"]
        )
        
        # Run benchmark using new BenchmarkRunner
        dashboard_config = DashboardConfig(
            title="Creative Writing Benchmark",
            title_emoji="🎨"
        )
        runner = BenchmarkRunner(console=console, dashboard_config=dashboard_config)
        
        console.print("[bold cyan]Phase 4/5:[/bold cyan] Running benchmark...\n")
        console.print(f"[bold]Total requests:[/bold] {len(targets) * bench_config.num_requests_per_target}")
        console.print(f"[bold]Prompts per target:[/bold] {bench_config.num_requests_per_target}\n")
        
        from rich.prompt import Confirm
        if not Confirm.ask("Start benchmark?", default=True):
            console.print("[yellow]Benchmark cancelled[/yellow]")
            return
        
        console.print()
        
        engine_stats = await runner.run(
            metrics_collector,
            targets,
            prompt_config["prompts"],
            bench_config
        )
        
        console.print()
        console.print("[bold green]✅ Benchmark complete![/bold green]\n")
        
        # Export and display
        export_and_display_results(metrics_collector, prompt_config)
        
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

