#!/usr/bin/env python3
"""
vLLM Benchmarking CLI Tool
Main script for comparing vLLM, TGI, and Ollama performance
"""

import asyncio
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
        console.print(f"[dim]Results saved to: {config.output_dir}/[/dim]")

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
    """Analyze and save benchmark results"""
    from src.metrics import MetricsCalculator
    from pathlib import Path
    
    # Create output directory
    output_dir = Path(config.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
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
    
    # Save results if configured
    if config.save_raw_data:
        # Save JSON results
        json_path = output_dir / f"benchmark_results_{int(time.time())}.json"
        comparison.save_to_file(str(json_path))
        
        # Save CSV metrics
        from src.metrics import export_metrics_csv
        csv_path = output_dir / f"metrics_{int(time.time())}.csv"
        export_metrics_csv(comparison, str(csv_path))

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
