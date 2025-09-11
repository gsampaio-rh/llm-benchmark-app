#!/usr/bin/env python3
"""
vLLM Benchmarking CLI Tool
Main script for comparing vLLM, TGI, and Ollama performance
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.config import load_config, create_example_configs, display_config, BenchmarkConfig
from src.service_discovery import discover_services
from src.api_clients import create_unified_client_from_services, create_chat_request

console = Console()

def print_header():
    """Print beautiful header"""
    header_text = Text()
    header_text.append("🚀 vLLM vs TGI vs Ollama\n", style="bold blue")
    header_text.append("Low-Latency Chat Benchmarking Suite\n", style="cyan")
    header_text.append("AI Platform Team - Enterprise Performance Testing", style="dim")
    
    console.print(Panel.fit(header_text, border_style="blue"))

@click.group()
@click.version_option()
def cli():
    """vLLM Benchmarking CLI - Compare inference engines for low-latency chat"""
    print_header()

@cli.command()
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
    
    # Load configuration
    if quick:
        # Use quick test configuration
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
        benchmark_config.load_tests = []  # Skip load tests
    
    # Display configuration
    display_config(benchmark_config)
    
    if dry_run:
        console.print("\n[yellow]Dry run complete - configuration validated[/yellow]")
        return
    
    # Run the actual benchmark
    asyncio.run(_run_benchmark(benchmark_config))

async def _run_benchmark(config: BenchmarkConfig):
    """Run the actual benchmarking workflow"""
    
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
            ttft_results = await _run_ttft_tests(api_client, config)
        else:
            console.print("[yellow]TTFT tests disabled in configuration[/yellow]")
        
        console.print("\n[bold blue]📊 Step 4: Load Testing[/bold blue]")
        
        load_results = None
        if config.load_tests:
            load_results = await _run_load_tests(api_client, config)
        else:
            console.print("[yellow]Load tests disabled or not configured[/yellow]")
        
        console.print("\n[bold blue]📈 Step 5: Results Analysis[/bold blue]")
        await _analyze_and_save_results(ttft_results, load_results, config)
        
        console.print("\n[bold green]🎉 Benchmarking Complete![/bold green]")
        console.print(f"[dim]Organized results available in benchmarking CLI[/dim]")

async def _run_ttft_tests(api_client, config: BenchmarkConfig):
    """Run Time To First Token tests"""
    from src.benchmarking import TTFTBenchmark
    
    # Create and run TTFT benchmark
    ttft_benchmark = TTFTBenchmark(config.ttft_test)
    ttft_results = await ttft_benchmark.run_benchmark(api_client)
    
    return ttft_results

async def _run_load_tests(api_client, config: BenchmarkConfig):
    """Run load tests"""
    from src.benchmarking import LoadTestBenchmark
    
    load_results = {}
    
    for test_config in config.load_tests:
        load_benchmark = LoadTestBenchmark(test_config)
        test_results = await load_benchmark.run_benchmark(api_client)
        load_results[test_config.name] = test_results
    
    return load_results

async def _analyze_and_save_results(ttft_results, load_results, config: BenchmarkConfig):
    """Analyze and save benchmark results using organized structure"""
    from src.metrics import MetricsCalculator
    from src.visualization import BenchmarkVisualizer
    from src.reporting import BenchmarkReporter
    from src.results_organizer import ResultsOrganizer
    from pathlib import Path
    
    # Initialize results organizer
    organizer = ResultsOrganizer(config.output_dir)
    
    # Determine services tested
    services_tested = []
    if ttft_results:
        services_tested.extend(ttft_results.service_results.keys())
    if load_results:
        for test_results in load_results.values():
            if isinstance(test_results, dict):
                services_tested.extend(test_results.keys())
    
    # Remove duplicates and sort
    services_tested = sorted(list(set(services_tested)))
    
    # Create organized test run
    test_run = organizer.create_test_run(
        test_name=config.name,
        services_tested=services_tested
    )
    
    # Initialize metrics calculator
    calculator = MetricsCalculator()
    
    # Flatten load results if nested by test name
    flattened_load_results = {}
    if load_results:
        for test_name, test_results in load_results.items():
            if isinstance(test_results, dict):
                # test_results is a dict of service_name -> ServiceBenchmarkResult
                for service_name, service_result in test_results.items():
                    flattened_load_results[service_name] = service_result
            else:
                # Single result
                flattened_load_results[test_name] = test_results
    
    # Create comprehensive comparison
    comparison = calculator.create_comparison_report(
        ttft_results=ttft_results,
        load_results=flattened_load_results if flattened_load_results else None,
        test_name=config.name
    )
    
    # Display comprehensive results
    calculator.display_comprehensive_results(comparison)
    
    # Save organized results
    if config.save_raw_data:
        # Save main comparison results
        organizer.save_comparison_results(test_run, comparison.to_dict())
        
        # Save CSV summary
        import csv
        import io
        csv_buffer = io.StringIO()
        fieldnames = [
            'service_name', 'ttft_mean', 'ttft_p95', 'ttft_target_achieved',
            'load_p95_latency', 'load_rps', 'load_target_achieved',
            'reliability_score', 'overall_score'
        ]
        
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        
        for service_name, metrics in comparison.service_metrics.items():
            writer.writerow({
                'service_name': service_name,
                'ttft_mean': metrics.ttft_mean,
                'ttft_p95': metrics.ttft_p95,
                'ttft_target_achieved': metrics.ttft_target_achieved,
                'load_p95_latency': metrics.load_p95_latency,
                'load_rps': metrics.load_rps,
                'load_target_achieved': metrics.load_target_achieved,
                'reliability_score': metrics.reliability_score,
                'overall_score': metrics.overall_score
            })
        
        organizer.save_summary_csv(test_run, csv_buffer.getvalue())
    
    # Generate charts if configured
    charts = {}
    if config.generate_charts:
        console.print("\n[bold blue]🎨 Step 6: Generating Interactive Charts[/bold blue]")
        
        # Use temporary directory for chart generation
        temp_charts_dir = str(test_run.charts_dir)
        visualizer = BenchmarkVisualizer(temp_charts_dir)
        
        if ttft_results:
            # Full chart suite with TTFT data
            charts = visualizer.create_comprehensive_dashboard(ttft_results, comparison)
        else:
            # Load dashboard and radar chart only
            charts['load_dashboard'] = visualizer.create_load_test_dashboard(comparison)
            charts['performance_radar'] = visualizer.create_performance_radar_chart(comparison)
        
        # Save charts using organized structure
        for chart_name, fig in charts.items():
            # Save HTML version
            html_content = fig.to_html(
                include_plotlyjs='cdn',
                config={'displayModeBar': True, 'displaylogo': False}
            )
            organizer.save_chart(test_run, chart_name, html_content, 'html')
            
            # Try to save PNG version
            try:
                png_content = fig.to_image(format='png', width=1200, height=800, scale=2)
                organizer.save_chart(test_run, chart_name, png_content, 'png')
            except Exception as e:
                console.print(f"[yellow]⚠️ Could not save PNG for {chart_name}: {e}[/yellow]")
        
        console.print(f"[green]📊 Interactive charts saved to: {test_run.charts_dir}[/green]")
    
    # Generate comprehensive report if configured
    if config.generate_report:
        console.print("\n[bold blue]📋 Step 7: Generating Comprehensive Report[/bold blue]")
        
        # Create temporary reporter for generating content
        temp_reporter = BenchmarkReporter()
        
        # Convert charts to HTML for embedding
        charts_html = {}
        if charts:
            for chart_name, fig in charts.items():
                charts_html[chart_name] = fig.to_html(
                    include_plotlyjs=False,
                    div_id=f"chart_{chart_name}",
                    config={'displayModeBar': True, 'displaylogo': False}
                )
        
        # Generate executive report HTML
        executive_summary = temp_reporter.generate_executive_summary(comparison)
        technical_analysis = temp_reporter.generate_technical_analysis(comparison)
        
        # Generate detailed analysis JSON
        detailed_data = {
            "benchmark_results": comparison.to_dict(),
            "executive_summary": executive_summary,
            "technical_analysis": technical_analysis,
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Save using organized structure
        html_report = temp_reporter.generate_html_report(comparison, charts_html)
        organizer.save_executive_report(test_run, html_report)
        organizer.save_detailed_analysis(test_run, detailed_data)
        
        console.print(f"[green]📋 Executive report: {test_run.base_dir}/executive_report.html[/green]")
        console.print(f"[green]🔧 Technical data: {test_run.base_dir}/detailed_analysis.json[/green]")
    
    # Create test manifest
    organizer.create_test_manifest(test_run)
    
    console.print(f"\n[bold green]📁 All results organized in: {test_run.test_id}[/bold green]")
    console.print(f"[dim]Location: {test_run.base_dir}[/dim]")

@cli.command()
@click.option("--namespace", "-n", default="vllm-benchmark", help="Kubernetes namespace")
@click.option("--manual-urls", help="Comma-separated list: vllm=url,tgi=url,ollama=url")
def discover(namespace: str, manual_urls: Optional[str]):
    """Discover and health check services"""
    
    manual_url_dict = None
    if manual_urls:
        manual_url_dict = {}
        for pair in manual_urls.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                manual_url_dict[key.strip()] = value.strip()
    
    asyncio.run(discover_services(namespace, manual_url_dict))

@cli.command()
def init():
    """Initialize configuration files"""
    console.print("[blue]📁 Creating example configuration files...[/blue]")
    create_example_configs()
    
    console.print("\n[green]✅ Configuration files created in config/ directory[/green]")
    console.print("\n[yellow]Next steps:[/yellow]")
    console.print("1. Edit config/default.yaml to customize settings")
    console.print("2. Set manual_urls if automatic discovery fails")
    console.print("3. Run: python vllm_benchmark.py benchmark")

@cli.command()
@click.argument("config_file", required=False)
def config(config_file: Optional[str]):
    """Display current configuration"""
    
    if config_file and not Path(config_file).exists():
        console.print(f"[red]❌ Configuration file not found: {config_file}[/red]")
        return
    
    benchmark_config = load_config(config_file)
    display_config(benchmark_config)

@cli.command()
@click.argument("results_file", required=True)
@click.option("--output-dir", "-o", help="Output directory for charts and reports")
@click.option("--charts-only", is_flag=True, help="Generate only charts, skip reports")
@click.option("--reports-only", is_flag=True, help="Generate only reports, skip charts")
def visualize(results_file: str, output_dir: Optional[str], charts_only: bool, reports_only: bool):
    """Generate charts and reports from existing benchmark results"""
    
    if not Path(results_file).exists():
        console.print(f"[red]❌ Results file not found: {results_file}[/red]")
        return
    
    console.print(f"[blue]📊 Processing results from: {results_file}[/blue]")
    
    # Load results
    try:
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        # Convert to BenchmarkComparison object with proper PerformanceMetrics
        from src.metrics import BenchmarkComparison, PerformanceMetrics
        
        # Convert service_metrics from dicts to PerformanceMetrics objects
        service_metrics = {}
        for service_name, metrics_dict in data.get('service_metrics', {}).items():
            service_metrics[service_name] = PerformanceMetrics(**metrics_dict)
        
        # Create comparison object
        comparison = BenchmarkComparison(
            timestamp=data.get('timestamp', ''),
            test_name=data.get('test_name', 'Unknown Test'),
            services_tested=data.get('services_tested', []),
            service_metrics=service_metrics,
            ttft_winner=data.get('ttft_winner'),
            load_winner=data.get('load_winner'),
            overall_winner=data.get('overall_winner'),
            total_requests=data.get('total_requests', 0),
            total_test_duration=data.get('total_test_duration', 0.0)
        )
        
    except Exception as e:
        console.print(f"[red]❌ Error loading results: {e}[/red]")
        import traceback
        console.print(f"[red]Details: {traceback.format_exc()}[/red]")
        return
    
    # Set output directory
    if not output_dir:
        output_dir = Path(results_file).parent / "visualization"
    
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Generate charts if requested
    charts = {}
    if not reports_only:
        console.print("\n[bold blue]🎨 Generating Interactive Charts[/bold blue]")
        
        from src.visualization import BenchmarkVisualizer
        visualizer = BenchmarkVisualizer(str(output_path / "charts"))
        
        # Create charts (without TTFT details since we only have comparison data)
        charts['load_dashboard'] = visualizer.create_load_test_dashboard(comparison)
        charts['performance_radar'] = visualizer.create_performance_radar_chart(comparison)
        
        # Save charts
        saved_charts = visualizer.save_charts(charts, ['html', 'png'])
        
        # Generate visualization report
        viz_report = visualizer.generate_visualization_report(comparison, charts)
        console.print(f"[green]📊 Charts saved: {viz_report}[/green]")
    
    # Generate reports if requested
    if not charts_only:
        console.print("\n[bold blue]📋 Generating Comprehensive Reports[/bold blue]")
        
        from src.reporting import BenchmarkReporter
        reporter = BenchmarkReporter(str(output_path / "reports"))
        
        # Convert charts to HTML for embedding
        charts_html = {}
        if charts:
            for chart_name, fig in charts.items():
                charts_html[chart_name] = fig.to_html(
                    include_plotlyjs=False,
                    div_id=f"chart_{chart_name}",
                    config={'displayModeBar': True, 'displaylogo': False}
                )
        
        # Generate all report formats
        reports = reporter.generate_comprehensive_report(comparison, charts_html)
        
        console.print(f"[green]📋 Executive report: {reports.get('html', 'N/A')}[/green]")
        console.print(f"[green]📊 Data export: {reports.get('csv', 'N/A')}[/green]")
        console.print(f"[green]🔧 Technical data: {reports.get('json', 'N/A')}[/green]")
    
    console.print(f"\n[bold green]🎉 Visualization complete![/bold green]")
    console.print(f"[dim]Output saved to: {output_path}/[/dim]")

@cli.command()
def results():
    """Manage and view organized test results"""
    from src.results_organizer import ResultsOrganizer
    
    organizer = ResultsOrganizer()
    organizer.display_test_runs_summary()

@cli.command()
@click.option("--keep", default=10, help="Number of recent test runs to keep")
def cleanup(keep: int):
    """Clean up old test results, keeping only recent ones"""
    from src.results_organizer import ResultsOrganizer
    
    organizer = ResultsOrganizer()
    deleted = organizer.cleanup_old_tests(keep)
    
    if deleted:
        console.print(f"[green]🧹 Cleaned up {len(deleted)} old test runs[/green]")
    else:
        console.print("[blue]ℹ️ No cleanup needed[/blue]")

@cli.command()
def migrate():
    """Migrate legacy unorganized results to new structure"""
    from src.results_organizer import ResultsOrganizer, migrate_legacy_results
    
    organizer = ResultsOrganizer()
    migrated_count = migrate_legacy_results(organizer)
    
    if migrated_count > 0:
        console.print(f"\n[green]✅ Migration complete! Use 'python vllm_benchmark.py results' to view organized tests[/green]")
    else:
        console.print("[blue]ℹ️ No legacy results found to migrate[/blue]")

@cli.command()
@click.argument("test_id", required=True)
@click.option("--charts-only", is_flag=True, help="Generate only charts")
@click.option("--reports-only", is_flag=True, help="Generate only reports")
def reprocess(test_id: str, charts_only: bool, reports_only: bool):
    """Regenerate charts and reports for an existing test run"""
    from src.results_organizer import ResultsOrganizer
    from src.metrics import BenchmarkComparison, PerformanceMetrics
    from src.visualization import BenchmarkVisualizer
    from src.reporting import BenchmarkReporter
    
    organizer = ResultsOrganizer()
    test_run = organizer.get_test_run(test_id)
    
    if not test_run:
        console.print(f"[red]❌ Test run not found: {test_id}[/red]")
        console.print("[yellow]💡 Use 'python vllm_benchmark.py results' to see available test runs[/yellow]")
        return
    
    if not test_run.comparison_file or not Path(test_run.comparison_file).exists():
        console.print(f"[red]❌ Comparison results not found for test: {test_id}[/red]")
        return
    
    console.print(f"[blue]♻️ Reprocessing test run: {test_id}[/blue]")
    
    # Load comparison data
    with open(test_run.comparison_file, 'r') as f:
        data = json.load(f)
    
    # Convert to BenchmarkComparison object
    service_metrics = {}
    for service_name, metrics_dict in data.get('service_metrics', {}).items():
        service_metrics[service_name] = PerformanceMetrics(**metrics_dict)
    
    comparison = BenchmarkComparison(
        timestamp=data.get('timestamp', ''),
        test_name=data.get('test_name', 'Unknown Test'),
        services_tested=data.get('services_tested', []),
        service_metrics=service_metrics,
        ttft_winner=data.get('ttft_winner'),
        load_winner=data.get('load_winner'),
        overall_winner=data.get('overall_winner'),
        total_requests=data.get('total_requests', 0),
        total_test_duration=data.get('total_test_duration', 0.0)
    )
    
    # Regenerate charts
    if not reports_only:
        console.print("[blue]🎨 Regenerating charts...[/blue]")
        
        # Ensure charts directory exists and is set properly
        if not test_run.charts_dir:
            test_run.charts_dir = test_run.base_dir / "charts"
        test_run.charts_dir.mkdir(exist_ok=True)
        
        visualizer = BenchmarkVisualizer(str(test_run.charts_dir))
        
        charts = {}
        charts['load_dashboard'] = visualizer.create_load_test_dashboard(comparison)
        charts['performance_radar'] = visualizer.create_performance_radar_chart(comparison)
        
        # Save charts
        for chart_name, fig in charts.items():
            html_content = fig.to_html(include_plotlyjs='cdn')
            organizer.save_chart(test_run, chart_name, html_content, 'html')
            
            try:
                png_content = fig.to_image(format='png', width=1200, height=800, scale=2)
                organizer.save_chart(test_run, chart_name, png_content, 'png')
            except Exception as e:
                console.print(f"[yellow]⚠️ Could not save PNG for {chart_name}: {e}[/yellow]")
    
    # Regenerate reports
    if not charts_only:
        console.print("[blue]📋 Regenerating reports...[/blue]")
        temp_reporter = BenchmarkReporter()
        
        # Generate new reports
        html_report = temp_reporter.generate_html_report(comparison)
        organizer.save_executive_report(test_run, html_report)
        
        # Update detailed analysis
        executive_summary = temp_reporter.generate_executive_summary(comparison)
        technical_analysis = temp_reporter.generate_technical_analysis(comparison)
        
        detailed_data = {
            "benchmark_results": comparison.to_dict(),
            "executive_summary": executive_summary,
            "technical_analysis": technical_analysis,
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        organizer.save_detailed_analysis(test_run, detailed_data)
    
    # Update manifest
    organizer.create_test_manifest(test_run)
    
    console.print(f"[green]✅ Reprocessing complete: {test_run.base_dir}[/green]")

@cli.command()
@click.option("--scenario", "-s", help="Scenario number (1-5) or name")
@click.option("--prompt", "-p", type=int, default=0, help="Prompt index within scenario (0-3)")
@click.option("--services", help="Comma-separated list of services (vllm,tgi,ollama)")
@click.option("--live", is_flag=True, help="Show live conversation theater")
@click.option("--payload", is_flag=True, help="Show detailed request/response payloads")
@click.option("--mock", is_flag=True, help="Use mock responses instead of real APIs")
def demo(scenario: Optional[str], prompt: int, services: Optional[str], live: bool, payload: bool, mock: bool):
    """Interactive conversation demonstration with human-centered visualization"""
    
    from src.conversation_viz import ConversationVisualizer
    
    visualizer = ConversationVisualizer()
    
    # If no scenario specified, show menu
    if not scenario:
        visualizer.display_scenario_menu()
        return
    
    # Parse scenario
    scenario_map = {
        "1": "customer_support",
        "2": "code_review", 
        "3": "creative_writing",
        "4": "technical_docs",
        "5": "business_intelligence"
    }
    
    if scenario.isdigit() and scenario in scenario_map:
        scenario_key = scenario_map[scenario]
    elif scenario in visualizer.scenarios:
        scenario_key = scenario
    else:
        console.print(f"[red]❌ Unknown scenario: {scenario}[/red]")
        console.print("[yellow]💡 Use 'python vllm_benchmark.py demo' to see available scenarios[/yellow]")
        return
    
    # Parse services
    service_list = ["vllm", "tgi", "ollama"]
    if services:
        service_list = [s.strip() for s in services.split(",")]
    
    console.print(f"\n[bold blue]🎭 Starting Live Conversation Theater[/bold blue]")
    console.print(f"[cyan]Scenario: {visualizer.scenarios[scenario_key]['title']}[/cyan]")
    console.print(f"[cyan]Services: {', '.join(service_list).upper()}[/cyan]")
    console.print(f"[cyan]Prompt #{prompt + 1}[/cyan]")
    
    if live:
        console.print("\n[yellow]💡 Live mode - Watch the conversation unfold in real-time![/yellow]")
    if payload:
        console.print("[yellow]🔍 Payload inspection mode - Technical details will be shown[/yellow]")
    
    async def _run_demo():
        await visualizer.run_conversation_scenario(scenario_key, prompt, service_list, use_real_apis=not mock)
    
    if not mock:
        console.print("\n[green]🔗 Using REAL APIs - Connecting to deployed services[/green]")
    else:
        console.print("\n[yellow]🎭 Using DEMO mode - Mock responses for presentation[/yellow]")
    
    asyncio.run(_run_demo())

@cli.command()
@click.option("--scenario", "-s", help="Scenario number (1-5) or name")
@click.option("--services", help="Comma-separated list of services (vllm,tgi,ollama)")
@click.option("--mock", is_flag=True, help="Use mock responses instead of real APIs")
def conversation(scenario: Optional[str], services: Optional[str], mock: bool):
    """Multi-turn conversation showing context retention and memory"""
    
    from src.conversation_viz import ConversationVisualizer
    
    visualizer = ConversationVisualizer()
    
    # If no scenario specified, show menu
    if not scenario:
        console.print("[bold blue]💬 Multi-Turn Conversation Theater[/bold blue]")
        console.print("[yellow]Watch how each service handles context and conversation memory![/yellow]")
        visualizer.display_scenario_menu()
        console.print("\n[yellow]💡 Use --scenario to start a multi-turn conversation[/yellow]")
        return
    
    # Parse scenario
    scenario_map = {
        "1": "customer_support",
        "2": "code_review", 
        "3": "creative_writing",
        "4": "technical_docs",
        "5": "business_intelligence"
    }
    
    if scenario.isdigit() and scenario in scenario_map:
        scenario_key = scenario_map[scenario]
    elif scenario in visualizer.scenarios:
        scenario_key = scenario
    else:
        console.print(f"[red]❌ Unknown scenario: {scenario}[/red]")
        return
    
    # Parse services
    service_list = ["vllm", "tgi", "ollama"]
    if services:
        service_list = [s.strip() for s in services.split(",")]
    
    console.print(f"\n[bold blue]💬 Multi-Turn Conversation Analysis[/bold blue]")
    console.print(f"[cyan]Scenario: {visualizer.scenarios[scenario_key]['title']}[/cyan]")
    console.print(f"[cyan]Services: {', '.join(service_list).upper()}[/cyan]")
    console.print("\n[yellow]🧠 This demo shows how each service handles context retention across multiple conversation turns[/yellow]")
    
    async def _run_conversation():
        await visualizer.run_conversation_scenario(scenario_key, 0, service_list, multi_turn=True, use_real_apis=not mock)
    
    if not mock:
        console.print("\n[green]🔗 Using REAL APIs for multi-turn conversation[/green]")
    else:
        console.print("\n[yellow]🎭 Using DEMO mode for multi-turn conversation[/yellow]")
    
    asyncio.run(_run_conversation())

@cli.command()
@click.option("--scenario", "-s", help="Scenario number (1-5) or name")
@click.option("--prompt", "-p", type=int, default=0, help="Prompt index within scenario (0-3)")
@click.option("--services", help="Comma-separated list of services (vllm,tgi,ollama)")
def inspect(scenario: Optional[str], prompt: int, services: Optional[str]):
    """Deep technical inspection showing API payloads and token-level analysis"""
    
    from src.conversation_viz import ConversationVisualizer
    
    visualizer = ConversationVisualizer()
    
    # If no scenario specified, show menu
    if not scenario:
        console.print("[bold blue]🔍 Payload Inspector - Technical Deep Dive[/bold blue]")
        visualizer.display_scenario_menu()
        console.print("\n[yellow]💡 Use --scenario to run a conversation and see detailed API payloads[/yellow]")
        return
    
    # Parse scenario
    scenario_map = {
        "1": "customer_support",
        "2": "code_review", 
        "3": "creative_writing",
        "4": "technical_docs",
        "5": "business_intelligence"
    }
    
    if scenario.isdigit() and scenario in scenario_map:
        scenario_key = scenario_map[scenario]
    elif scenario in visualizer.scenarios:
        scenario_key = scenario
    else:
        console.print(f"[red]❌ Unknown scenario: {scenario}[/red]")
        return
    
    # Parse services
    service_list = ["vllm", "tgi", "ollama"]
    if services:
        service_list = [s.strip() for s in services.split(",")]
    
    console.print(f"\n[bold blue]🔍 Technical Payload Inspection[/bold blue]")
    console.print(f"[cyan]Scenario: {visualizer.scenarios[scenario_key]['title']}[/cyan]")
    console.print(f"[cyan]Services: {', '.join(service_list).upper()}[/cyan]")
    
    async def _run_inspection():
        from src.conversation_viz import ConversationThread, ConversationMessage
        
        # Create conversation thread
        thread = ConversationThread(
            thread_id=f"{scenario_key}_{int(time.time())}",
            title=visualizer.scenarios[scenario_key]["title"],
            scenario=scenario_key,
            user_persona=visualizer.scenarios[scenario_key]["user_persona"]
        )
        
        # Add user message
        user_message = ConversationMessage(
            role="user",
            content=visualizer.scenarios[scenario_key]["prompts"][prompt],
            timestamp=time.time()
        )
        thread.add_message(user_message)
        
        # Run conversation first
        await visualizer._run_mock_conversation(thread, service_list)
        
        console.print("\n[bold blue]📊 Technical Analysis[/bold blue]")
        
        # Show payload comparison
        payload_view = visualizer.create_payload_comparison_view(thread)
        console.print(payload_view)
        
        # Show token economics
        responses = {msg.service_name: msg for msg in thread.messages if msg.service_name}
        if responses:
            token_view = visualizer.create_token_economics_view(responses)
            console.print(token_view)
    
    asyncio.run(_run_inspection())

@cli.command()
@click.option("--namespace", "-n", default="vllm-benchmark", help="Kubernetes namespace")
@click.option("--prompt", "-p", default="Hello! How are you today?", help="Test prompt")
@click.option("--manual-urls", help="Comma-separated list: vllm=url,tgi=url,ollama=url")
def test(namespace: str, prompt: str, manual_urls: Optional[str]):
    """Quick test of all services with a simple prompt"""
    
    manual_url_dict = None
    if manual_urls:
        manual_url_dict = {}
        for pair in manual_urls.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                manual_url_dict[key.strip()] = value.strip()
    
    async def _run_test():
        services = await discover_services(namespace, manual_url_dict)
        
        async with create_unified_client_from_services(services) as api_client:
            if not api_client.clients:
                console.print("[red]❌ No healthy services found[/red]")
                return
            
            test_request = create_chat_request(prompt, max_tokens=100)
            console.print(f"\n[blue]🧪 Testing prompt: {prompt}[/blue]")
            
            results = await api_client.generate_comparison(test_request)
    
    asyncio.run(_run_test())

if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Benchmark interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        sys.exit(1)
