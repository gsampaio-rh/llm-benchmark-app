#!/usr/bin/env python3
"""
🏃 Benchmark Runner
==================

This script runs comprehensive benchmarks across multiple engines and models,
collecting detailed performance metrics for analysis and comparison.

Usage:
    python scripts/run_benchmark.py
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

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

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.core.metrics_collector import initialize_metrics_collector
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter


console = Console()


def print_header() -> None:
    """Display a beautiful header for the script."""
    header = Text()
    header.append("🏃 ", style="bold blue")
    header.append("Benchmark Runner", style="bold cyan")
    
    console.print()
    console.print(Panel(
        Text.from_markup(
            "[bold cyan]Run comprehensive benchmarks across LLM engines.[/bold cyan]\n\n"
            "✓ Test multiple engines and models\n"
            "✓ Configure request parameters\n"
            "✓ Collect detailed performance metrics\n"
            "✓ Generate comparison reports"
        ),
        title=header,
        border_style="cyan",
        box=box.ROUNDED
    ))
    console.print()


async def setup_connection_manager() -> tuple[ConnectionManager, object]:
    """Setup and initialize the connection manager and metrics collector."""
    console.print("[bold cyan]Phase 1/5:[/bold cyan] Initializing benchmark system...\n")
    
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
        registration_results = await connection_manager.register_engines_from_config(benchmark_config)
        progress.update(task, completed=True)
    
    successful = sum(1 for success in registration_results.values() if success)
    total = len(registration_results)
    
    if successful == 0:
        console.print("[red]❌ No engines available for benchmarking[/red]")
        raise RuntimeError("No engines connected")
    
    console.print(f"  ✅ Connected to {successful}/{total} engine(s)\n")
    return connection_manager, metrics_collector


def configure_benchmark() -> Dict[str, Any]:
    """Interactive benchmark configuration."""
    console.print("[bold cyan]Phase 2/5:[/bold cyan] Configure benchmark parameters...\n")
    
    # Benchmark description
    description = Prompt.ask(
        "Benchmark description",
        default=f"Benchmark run {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    
    console.print()
    
    # Number of requests
    console.print("[bold]Number of test requests per model:[/bold]")
    console.print("[dim]Recommended: 5-10 for quick tests, 50+ for production benchmarks[/dim]\n")
    
    num_requests = IntPrompt.ask(
        "Number of requests",
        default=10
    )
    
    console.print()
    
    # Test prompts
    console.print("[bold]Choose test prompt strategy:[/bold]\n")
    
    prompt_table = Table(box=box.SIMPLE)
    prompt_table.add_column("#", style="cyan", justify="center")
    prompt_table.add_column("Strategy", style="magenta")
    prompt_table.add_column("Description", style="dim")
    
    prompt_table.add_row("1", "Short prompts", "10-20 words, fast responses")
    prompt_table.add_row("2", "Medium prompts", "30-50 words, balanced")
    prompt_table.add_row("3", "Long prompts", "100+ words, stress testing")
    prompt_table.add_row("4", "Mixed", "Variety of lengths")
    
    console.print(prompt_table)
    console.print()
    
    prompt_choice = Prompt.ask(
        "Select prompt strategy",
        choices=["1", "2", "3", "4"],
        default="2"
    )
    
    # Generate test prompts based on choice
    test_prompts = generate_test_prompts(prompt_choice, num_requests)
    
    console.print(f"  ✅ Generated {len(test_prompts)} test prompts\n")
    
    return {
        "description": description,
        "num_requests": num_requests,
        "prompt_strategy": prompt_choice,
        "test_prompts": test_prompts
    }


def generate_test_prompts(strategy: str, count: int) -> List[str]:
    """Generate test prompts based on strategy."""
    short_prompts = [
        "Explain quantum computing briefly",
        "What is machine learning?",
        "Define artificial intelligence",
        "Describe cloud computing",
        "What are microservices?",
        "Explain REST APIs",
        "What is Kubernetes?",
        "Define DevOps practices",
        "What is containerization?",
        "Explain serverless computing"
    ]
    
    medium_prompts = [
        "Explain the key differences between supervised and unsupervised machine learning, and provide examples of when each approach is most effective.",
        "Describe how containers differ from virtual machines in terms of resource usage, isolation, and deployment workflows.",
        "What are the main benefits and challenges of adopting a microservices architecture compared to a monolithic application design?",
        "Explain how OAuth 2.0 authentication works and why it's considered more secure than traditional username/password authentication.",
        "Describe the CAP theorem in distributed systems and explain how different databases handle the trade-offs between consistency, availability, and partition tolerance."
    ]
    
    long_prompts = [
        "Provide a comprehensive explanation of how Large Language Models (LLMs) are trained, including the pre-training and fine-tuning phases. Discuss the role of transformer architecture, attention mechanisms, tokenization, and the computational resources required. Also explain common challenges like catastrophic forgetting, hallucinations, and bias in outputs.",
        "Explain the complete process of deploying a machine learning model to production, starting from model training and validation, through containerization, API development, monitoring setup, and continuous integration/deployment. Include best practices for versioning, A/B testing, and handling model drift over time.",
        "Describe the evolution of cloud computing from traditional data centers to modern cloud-native architectures. Include discussions of Infrastructure as a Service (IaaS), Platform as a Service (PaaS), Software as a Service (SaaS), serverless computing, and edge computing. Explain the benefits and trade-offs of each approach."
    ]
    
    if strategy == "1":  # Short
        base_prompts = short_prompts
    elif strategy == "2":  # Medium
        base_prompts = medium_prompts
    elif strategy == "3":  # Long
        base_prompts = long_prompts
    else:  # Mixed
        base_prompts = short_prompts[:3] + medium_prompts[:2] + long_prompts[:1]
    
    # Repeat prompts to reach desired count
    prompts = []
    for i in range(count):
        prompts.append(base_prompts[i % len(base_prompts)])
    
    return prompts


async def select_targets(connection_manager: ConnectionManager) -> List[Dict[str, str]]:
    """Select engines and models to benchmark."""
    console.print("[bold cyan]Phase 3/5:[/bold cyan] Select benchmark targets...\n")
    
    targets = []
    
    # Get available engines
    engines = list(connection_manager.adapters.keys())
    
    if not engines:
        console.print("[red]❌ No engines available[/red]")
        return targets
    
    # Display engines
    engines_table = Table(title="🚀 Available Engines", box=box.ROUNDED)
    engines_table.add_column("#", style="cyan", justify="center")
    engines_table.add_column("Engine", style="magenta")
    engines_table.add_column("Type", style="blue")
    
    for idx, engine in enumerate(engines, 1):
        adapter = connection_manager.get_adapter(engine)
        engines_table.add_row(
            str(idx),
            engine,
            adapter.config.engine_type if adapter else "unknown"
        )
    
    console.print(engines_table)
    console.print()
    
    # Select engines
    if len(engines) == 1:
        selected_engines = engines
        console.print(f"  ℹ️  Auto-selected: [cyan]{engines[0]}[/cyan]\n")
    else:
        if Confirm.ask("Benchmark all engines?", default=True):
            selected_engines = engines
            console.print(f"  ✅ Selected all {len(engines)} engine(s)\n")
        else:
            # Manual selection
            indices = Prompt.ask(
                "Enter engine numbers (comma-separated)",
                default="1"
            )
            selected_indices = [int(i.strip()) - 1 for i in indices.split(",")]
            selected_engines = [engines[i] for i in selected_indices if 0 <= i < len(engines)]
            console.print(f"  ✅ Selected {len(selected_engines)} engine(s)\n")
    
    # For each engine, select models
    for engine_name in selected_engines:
        console.print(f"[bold]Models for {engine_name}:[/bold]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task(f"Discovering models...", total=None)
            models = await connection_manager.discover_models(engine_name)
            progress.update(task, completed=True)
        
        if not models:
            console.print("  [yellow]⚠️  No models found, enter manually[/yellow]")
            model_name = Prompt.ask(f"  Model name for {engine_name}")
            targets.append({"engine": engine_name, "model": model_name})
            console.print()
            continue
        
        # Display models
        models_table = Table(box=box.SIMPLE)
        models_table.add_column("#", style="cyan", justify="center")
        models_table.add_column("Model", style="magenta")
        models_table.add_column("Size", style="blue")
        models_table.add_column("Status", justify="center")
        
        for idx, model in enumerate(models[:10], 1):
            status = "✅" if model.is_available else "❌"
            models_table.add_row(
                str(idx),
                model.name,
                model.size or "Unknown",
                status
            )
        
        if len(models) > 10:
            models_table.add_row("...", f"({len(models) - 10} more)", "", "")
        
        console.print(models_table)
        
        # Select model(s)
        if Confirm.ask(f"  Test all available models on {engine_name}?", default=False):
            for model in models:
                if model.is_available:
                    targets.append({"engine": engine_name, "model": model.name})
        else:
            model_choice = Prompt.ask("  Select model number", default="1")
            try:
                idx = int(model_choice) - 1
                if 0 <= idx < len(models):
                    targets.append({"engine": engine_name, "model": models[idx].name})
            except ValueError:
                # Assume it's a model name
                targets.append({"engine": engine_name, "model": model_choice})
        
        console.print()
    
    console.print(f"[bold green]✅ Configured {len(targets)} target(s) for benchmarking[/bold green]\n")
    
    # Display targets summary
    summary_table = Table(title="📋 Benchmark Targets", box=box.ROUNDED)
    summary_table.add_column("#", style="cyan", justify="center")
    summary_table.add_column("Engine", style="magenta")
    summary_table.add_column("Model", style="blue")
    
    for idx, target in enumerate(targets, 1):
        summary_table.add_row(str(idx), target["engine"], target["model"])
    
    console.print(summary_table)
    console.print()
    
    return targets


async def run_benchmark_tests(
    connection_manager: ConnectionManager,
    metrics_collector: object,
    targets: List[Dict[str, str]],
    config: Dict[str, Any]
) -> None:
    """Run the benchmark tests."""
    console.print("[bold cyan]Phase 4/5:[/bold cyan] Running benchmark tests...\n")
    
    # Start metrics collection
    metrics_collector.start_collection(config["description"])
    
    # Calculate total requests
    total_requests = len(targets) * config["num_requests"]
    test_prompts = config["test_prompts"]
    
    console.print(f"[bold]Total requests to execute:[/bold] {total_requests}")
    console.print(f"[bold]Prompts per target:[/bold] {config['num_requests']}\n")
    
    if not Confirm.ask("Start benchmark?", default=True):
        console.print("[yellow]Benchmark cancelled[/yellow]")
        return
    
    console.print()
    
    # Run tests with progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("•"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        overall_task = progress.add_task(
            "[cyan]Overall Progress",
            total=total_requests
        )
        
        completed = 0
        failed = 0
        
        for target in targets:
            engine_name = target["engine"]
            model_name = target["model"]
            
            target_task = progress.add_task(
                f"[magenta]{engine_name}/{model_name}",
                total=config["num_requests"]
            )
            
            for i in range(config["num_requests"]):
                prompt = test_prompts[i]
                
                try:
                    result = await metrics_collector.collect_single_request_metrics(
                        engine_name, prompt, model_name
                    )
                    
                    if result.success:
                        completed += 1
                    else:
                        failed += 1
                    
                except Exception as e:
                    failed += 1
                    console.print(f"[dim red]Request failed: {str(e)[:50]}...[/dim red]")
                
                progress.update(target_task, advance=1)
                progress.update(overall_task, advance=1)
            
            progress.remove_task(target_task)
    
    console.print()
    console.print(f"[bold green]✅ Benchmark complete![/bold green]")
    console.print(f"[bold]Success:[/bold] {completed}/{total_requests}")
    console.print(f"[bold]Failed:[/bold] {failed}/{total_requests}")
    console.print(f"[bold]Success Rate:[/bold] {completed/total_requests:.1%}\n")


def display_results(metrics_collector: object) -> None:
    """Display benchmark results."""
    console.print("[bold cyan]Phase 5/5:[/bold cyan] Analyzing results...\n")
    
    # Generate aggregates
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        task = progress.add_task("Computing aggregate metrics...", total=None)
        aggregates = metrics_collector.aggregate_metrics()
        progress.update(task, completed=True)
    
    console.print()
    
    # Display comparison table
    if aggregates:
        table = Table(
            title="📊 Benchmark Results Comparison",
            box=box.ROUNDED,
            title_style="bold cyan",
            header_style="bold magenta"
        )
        
        table.add_column("Engine/Model", style="cyan")
        table.add_column("Success", style="green", justify="center")
        table.add_column("Avg Latency", style="blue", justify="right")
        table.add_column("p95 Latency", style="blue", justify="right")
        table.add_column("TPS", style="yellow", justify="right")
        table.add_column("Tokens In", style="dim", justify="right")
        table.add_column("Tokens Out", style="dim", justify="right")
        
        for agg in aggregates:
            success_rate = f"{agg.success_rate:.0%}"
            avg_lat = f"{agg.latency_mean:.2f}s" if agg.latency_mean else "N/A"
            p95_lat = f"{agg.latency_p95:.2f}s" if agg.latency_p95 else "N/A"
            tps = f"{agg.aggregate_tps:.1f}" if agg.aggregate_tps else "N/A"
            tokens_in = f"{agg.total_input_tokens:,}" if agg.total_input_tokens else "N/A"
            tokens_out = f"{agg.total_output_tokens:,}" if agg.total_output_tokens else "N/A"
            
            table.add_row(
                agg.engine_name,
                success_rate,
                avg_lat,
                p95_lat,
                tps,
                tokens_in,
                tokens_out
            )
        
        console.print(table)
        console.print()
    
    # Export results
    if Confirm.ask("Export results to file?", default=True):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_path = f"benchmark_results/benchmark_{timestamp}.json"
        
        output_path = Prompt.ask("Output file path", default=default_path)
        
        try:
            exported_file = metrics_collector.export_metrics(output_path, "json")
            console.print(f"\n[bold green]✅ Results exported to:[/bold green] {exported_file}\n")
        except Exception as e:
            console.print(f"\n[red]❌ Export failed:[/red] {e}\n")


def print_summary() -> None:
    """Print final summary and next steps."""
    console.print(Panel(
        Text.from_markup(
            "[bold green]🎉 Benchmark complete![/bold green]\n\n"
            "[bold]Next steps:[/bold]\n"
            "1. View detailed metrics: [cyan]python scripts/view_metrics.py[/cyan]\n"
            "2. Run another benchmark: [cyan]python scripts/run_benchmark.py[/cyan]\n"
            "3. Check engine health: [cyan]python scripts/check_engines.py[/cyan]"
        ),
        title="✅ Summary",
        border_style="green",
        box=box.ROUNDED
    ))


async def main() -> None:
    """Main execution function."""
    print_header()
    
    connection_manager = None
    try:
        # Setup
        connection_manager, metrics_collector = await setup_connection_manager()
        
        # Configure benchmark
        config = configure_benchmark()
        
        # Select targets
        targets = await select_targets(connection_manager)
        
        if not targets:
            console.print("[yellow]No targets selected. Exiting.[/yellow]")
            return
        
        # Run benchmark
        await run_benchmark_tests(connection_manager, metrics_collector, targets, config)
        
        # Display results
        display_results(metrics_collector)
        
        # Print summary
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

