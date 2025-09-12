"""
Benchmark command - Core benchmarking functionality
Extracted from main CLI for better organization
"""

import asyncio
from typing import Optional

import click
from rich.console import Console

from ..utils.console_utils import print_status
from ..utils.async_utils import run_async_command


@click.command()
@click.option("--config", "-c", help="Configuration file path")
@click.option("--namespace", "-n", default="vllm-benchmark", help="Kubernetes namespace")
@click.option("--concurrent-users", "--users", type=int, help="Number of concurrent users")
@click.option("--duration", "-d", type=int, help="Test duration in seconds")
@click.option("--output-dir", "-o", help="Output directory for results")
@click.option("--quick", is_flag=True, help="Run quick demo test")
@click.option("--ttft-only", is_flag=True, help="Run only TTFT tests")
@click.option("--dry-run", is_flag=True, help="Show configuration and exit")
def benchmark(config: Optional[str], namespace: str, concurrent_users: Optional[int], 
              duration: Optional[int], output_dir: Optional[str], quick: bool, 
              ttft_only: bool, dry_run: bool):
    """Run benchmarking suite against deployed services"""
    
    console = Console()
    
    # Import here to avoid circular imports
    from ...config import load_config, display_config, BenchmarkConfig
    from ...service_discovery import discover_services
    from ...api_clients import create_unified_client_from_services, create_chat_request
    from ...benchmarking import TTFTBenchmark, LoadTestBenchmark
    from ...metrics import StatisticalAnalyzer
    from ...reporting import SummaryReportGenerator
    from ...results_organizer import ResultsOrganizer
    from ...visualization import BenchmarkVisualizer
    
    # Load configuration
    if quick:
        benchmark_config = load_config("config/quick-test.yaml")
    else:
        benchmark_config = load_config(config)
    
    # Apply CLI overrides
    if namespace:
        benchmark_config.services.namespace = namespace
    if concurrent_users and benchmark_config.load_tests:
        for test in benchmark_config.load_tests:
            test.concurrent_users = concurrent_users
    if duration and benchmark_config.load_tests:
        for test in benchmark_config.load_tests:
            test.duration_seconds = duration
    if output_dir:
        benchmark_config.output_dir = output_dir
    if ttft_only:
        benchmark_config.load_tests = []
    
    # Display configuration
    display_config(benchmark_config)
    
    if dry_run:
        console.print("\n[yellow]Dry run complete - configuration validated[/yellow]")
        return
    
    # Run the actual benchmark
    asyncio.run(_run_benchmark(benchmark_config, console))


async def _run_benchmark(config, console: Console):
    """Run the actual benchmarking workflow"""
    from ...service_discovery import discover_services
    from ...api_clients import create_unified_client_from_services
    from ...benchmarking import TTFTBenchmark, LoadTestBenchmark
    from ...metrics import StatisticalAnalyzer
    from ...reporting import SummaryReportGenerator
    from ...results_organizer import ResultsOrganizer
    from ...visualization import BenchmarkVisualizer
    
    console.print("\n[bold blue]🔍 Step 1: Service Discovery[/bold blue]")
    
    # Discover services
    services = await discover_services(
        namespace=config.services.namespace,
        manual_urls=config.services.manual_urls if config.services.manual_urls else None
    )
    
    # Check if we have any healthy services
    healthy_services = [name for name, info in services.items() 
                       if info.status in ["healthy", "responding"]]
    
    if len(healthy_services) < 2:
        console.print("[red]❌ Need at least 2 healthy services for comparison[/red]")
        console.print("[yellow]💡 Try running with --config config/quick-test.yaml and set manual_urls[/yellow]")
        return
    
    console.print(f"\n[green]✅ Found {len(healthy_services)} healthy services: {', '.join(healthy_services).upper()}[/green]")
    
    console.print("\n[bold blue]🚀 Step 2: API Client Setup[/bold blue]")
    
    # Create unified client
    async with create_unified_client_from_services(services) as api_client:
        
        # Health check all APIs
        health_results = await api_client.health_check_all()
        console.print(f"API Health Check: {health_results}")
        
        console.print("\n[bold blue]⚡ Step 3: TTFT Testing[/bold blue]")
        
        ttft_results = None
        if config.ttft_test.enabled:
            ttft_results = await _run_ttft_tests(api_client, config, console)
        else:
            console.print("[yellow]TTFT tests disabled in configuration[/yellow]")
        
        console.print("\n[bold blue]📊 Step 4: Load Testing[/bold blue]")
        
        load_results = None
        if config.load_tests:
            load_results = await _run_load_tests(api_client, config, console)
        else:
            console.print("[yellow]Load tests disabled or not configured[/yellow]")
        
        console.print("\n[bold blue]📈 Step 5: Results Analysis[/bold blue]")
        await _analyze_and_save_results(ttft_results, load_results, config, console)
        
        console.print("\n[bold green]🎉 Benchmarking Complete![/bold green]")
        console.print(f"[dim]Organized results available in benchmarking CLI[/dim]")


async def _run_ttft_tests(api_client, config, console: Console):
    """Run Time To First Token tests"""
    from ...benchmarking import TTFTBenchmark
    from ...api_clients import create_chat_request
    
    ttft_benchmark = TTFTBenchmark(api_client, console)
    
    test_request = create_chat_request(
        "Hello! Please respond with a brief explanation of artificial intelligence.",
        max_tokens=config.ttft_test.max_tokens,
        temperature=config.ttft_test.temperature
    )
    
    console.print(f"[cyan]Running {config.ttft_test.iterations} TTFT iterations with {config.ttft_test.warmup_requests} warmup requests[/cyan]")
    
    # Run TTFT benchmark
    ttft_results = await ttft_benchmark.run_benchmark(
        request=test_request,
        iterations=config.ttft_test.iterations,
        warmup_requests=config.ttft_test.warmup_requests,
        target_ms=config.ttft_test.target_ms
    )
    
    return ttft_results


async def _run_load_tests(api_client, config, console: Console):
    """Run load tests"""
    from ...benchmarking import LoadTestBenchmark
    
    load_benchmark = LoadTestBenchmark(api_client, console)
    all_load_results = {}
    
    for load_test_config in config.load_tests:
        console.print(f"\n[cyan]Running load test: {load_test_config.name}[/cyan]")
        console.print(f"[dim]Users: {load_test_config.concurrent_users}, Duration: {load_test_config.duration_seconds}s[/dim]")
        
        load_results = await load_benchmark.run_benchmark(load_test_config)
        all_load_results[load_test_config.name] = load_results
    
    return all_load_results


async def _analyze_and_save_results(ttft_results, load_results, config, console: Console):
    """Analyze results and save organized output"""
    from ...metrics import StatisticalAnalyzer
    from ...reporting import SummaryReportGenerator
    from ...results_organizer import ResultsOrganizer
    from ...visualization import BenchmarkVisualizer
    
    # Create results organizer
    organizer = ResultsOrganizer()
    test_id = organizer.create_test_run(config.name)
    
    console.print(f"[green]📁 Test ID: {test_id}[/green]")
    
    # Statistical analysis
    analyzer = StatisticalAnalyzer()
    analysis_results = {}
    
    if ttft_results:
        ttft_analysis = analyzer.analyze_ttft_results(ttft_results)
        analysis_results['ttft'] = ttft_analysis
        console.print(f"[green]⚡ TTFT Analysis: Winner is {ttft_analysis.winner}[/green]")
    
    if load_results:
        for test_name, results in load_results.items():
            load_analysis = analyzer.analyze_load_results(results)
            analysis_results[f'load_{test_name}'] = load_analysis
            console.print(f"[green]📊 Load Test '{test_name}': Winner is {load_analysis.winner}[/green]")
    
    # Save organized results
    organizer.save_comparison_results(test_id, analysis_results)
    organizer.save_summary_csv(test_id, analysis_results)
    
    # Generate visualizations
    if config.output.generate_charts:
        console.print("[cyan]📈 Generating interactive charts...[/cyan]")
        visualizer = BenchmarkVisualizer()
        
        if ttft_results:
            ttft_chart = visualizer.create_ttft_comparison(ttft_results)
            organizer.save_chart(test_id, "ttft_analysis.html", ttft_chart)
        
        if load_results:
            for test_name, results in load_results.items():
                load_chart = visualizer.create_load_dashboard(results)
                organizer.save_chart(test_id, f"load_{test_name}_dashboard.html", load_chart)
        
        # Performance radar
        if ttft_results and load_results:
            radar_chart = visualizer.create_performance_radar({
                'ttft': ttft_results,
                'load': list(load_results.values())[0]  # Use first load test
            })
            organizer.save_chart(test_id, "performance_radar.html", radar_chart)
    
    # Generate reports
    if config.output.generate_report:
        console.print("[cyan]📋 Generating executive report...[/cyan]")
        report_generator = SummaryReportGenerator()
        executive_report = report_generator.generate_executive_report(analysis_results, config)
        organizer.save_report(test_id, "executive_report.html", executive_report)
    
    # Show results path
    results_path = organizer.get_test_path(test_id)
    console.print(f"\n[bold green]📁 Results saved to: {results_path}[/bold green]")
    
    # Show quick summary
    if analysis_results:
        _display_quick_summary(analysis_results, console)


def _display_quick_summary(analysis_results, console: Console):
    """Display a quick summary of results"""
    console.print("\n[bold blue]📊 Quick Summary[/bold blue]")
    
    for test_type, analysis in analysis_results.items():
        if hasattr(analysis, 'winner') and analysis.winner:
            console.print(f"  {test_type.upper()}: [green]{analysis.winner.upper()}[/green] wins")
        
    console.print(f"\n[dim]Use 'python vllm_benchmark.py results' to view detailed analysis[/dim]")
