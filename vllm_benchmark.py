#!/usr/bin/env python3
"""
vLLM Benchmarking CLI Tool - Refactored Version
Main script for comparing vLLM, TGI, and Ollama performance

Phase 1.2: Streamlined CLI with modular command structure
"""

import sys
from pathlib import Path

import click

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.cli.utils.console_utils import print_header, create_console
from src.cli.commands import (
    benchmark,
    demo, 
    config,
    init,
    discover,
    test,
    results,
    visualize,
    inspect
)

# Create global console
console = create_console()


@click.group()
@click.version_option()
def cli():
    """vLLM Benchmarking CLI - Compare inference engines for low-latency chat
    
    This tool provides comprehensive performance analysis comparing vLLM, 
    TGI (Text Generation Inference), and Ollama for low-latency chat applications.
    
    Key Features:
    • Sub-100ms Time To First Token (TTFT) measurement
    • Statistical analysis with P50/P95/P99 percentiles  
    • Interactive demonstrations and live racing
    • Professional visualizations and executive reports
    • Kubernetes/OpenShift integration with service discovery
    
    Examples:
        # Quick demo test
        vllm_benchmark.py benchmark --quick
        
        # Interactive performance race
        vllm_benchmark.py demo --mode race
        
        # Service discovery
        vllm_benchmark.py discover --namespace vllm-benchmark
        
        # View results
        vllm_benchmark.py results
    """
    print_header(console)


# Add all command handlers to the CLI group
cli.add_command(benchmark)
cli.add_command(demo)
cli.add_command(config) 
cli.add_command(init)
cli.add_command(discover)
cli.add_command(test)
cli.add_command(results)
cli.add_command(visualize)
cli.add_command(inspect)


if __name__ == "__main__":
    try:
        cli()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Benchmark interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Unexpected error: {e}[/red]")
        console.print("[dim]💡 Use --help for usage information[/dim]")
        sys.exit(1)
