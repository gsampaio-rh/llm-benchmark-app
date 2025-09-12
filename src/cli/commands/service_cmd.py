"""
Service commands - discover and test
Handles service discovery and quick testing
"""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..utils.console_utils import print_status
from ..utils.async_utils import run_async_command


@click.command()
@click.option("--namespace", "-n", default="vllm-benchmark", help="Kubernetes namespace")
@click.option("--manual-urls", help="Manual URLs in format: vllm=url1,tgi=url2,ollama=url3")
def discover(namespace: str, manual_urls: Optional[str]):
    """Discover and health check services"""
    console = Console()
    
    console.print("\n[bold blue]🔍 Service Discovery[/bold blue]")
    print_status(console, f"Discovering services in namespace: {namespace}", "info")
    
    # Parse manual URLs if provided
    manual_url_dict = None
    if manual_urls:
        manual_url_dict = {}
        for pair in manual_urls.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                manual_url_dict[key.strip()] = value.strip()
    
    async def _run_discovery():
        # Import here to avoid circular imports
        from ...service_discovery import discover_services
        
        try:
            services = await discover_services(namespace, manual_url_dict)
            
            if not services:
                console.print("[red]❌ No services found[/red]")
                return
            
            # Create services table
            table = Table(title="Discovered Services", show_header=True, header_style="bold blue")
            table.add_column("Service", style="cyan", width=12)
            table.add_column("URL", style="white")
            table.add_column("Status", style="green")
            table.add_column("Details", style="dim")
            
            healthy_count = 0
            for service_name, service_info in services.items():
                status_style = "green" if service_info.status == "healthy" else "yellow"
                
                if service_info.status == "healthy":
                    healthy_count += 1
                    status_display = f"[{status_style}]✅ {service_info.status.upper()}[/{status_style}]"
                else:
                    status_display = f"[{status_style}]⚠️ {service_info.status.upper()}[/{status_style}]"
                
                table.add_row(
                    service_name.upper(),
                    service_info.url or "Not found",
                    status_display,
                    service_info.details or ""
                )
            
            console.print(table)
            
            # Summary
            total_services = len(services)
            console.print(f"\n[bold green]📊 Summary: {healthy_count}/{total_services} services healthy[/bold green]")
            
            if healthy_count >= 2:
                print_status(console, "Ready for benchmarking! 🚀", "success")
            else:
                print_status(console, "Need at least 2 healthy services for comparison", "warning")
                console.print("[dim]💡 Try checking service logs or using manual URLs[/dim]")
                
        except Exception as e:
            console.print(f"[red]❌ Service discovery failed: {str(e)}[/red]")
    
    asyncio.run(_run_discovery())


@click.command()
@click.option("--namespace", "-n", default="vllm-benchmark", help="Kubernetes namespace")
@click.option("--prompt", "-p", default="Hello! Please respond with a simple greeting.", 
              help="Test prompt to send to services")
@click.option("--manual-urls", help="Manual URLs in format: vllm=url1,tgi=url2,ollama=url3")
def test(namespace: str, prompt: str, manual_urls: Optional[str]):
    """Quick test of all services with a simple prompt"""
    console = Console()
    
    console.print("\n[bold blue]🧪 Service Testing[/bold blue]")
    print_status(console, f"Testing services with prompt: {prompt}", "info")
    
    # Parse manual URLs if provided
    manual_url_dict = None
    if manual_urls:
        manual_url_dict = {}
        for pair in manual_urls.split(","):
            if "=" in pair:
                key, value = pair.split("=", 1)
                manual_url_dict[key.strip()] = value.strip()
    
    async def _run_test():
        # Import here to avoid circular imports
        from ...service_discovery import discover_services
        from ...api_clients import create_unified_client_from_services, create_chat_request
        
        try:
            # Discover services first
            services = await discover_services(namespace, manual_url_dict)
            
            if not services:
                console.print("[red]❌ No services found[/red]")
                return
            
            # Create unified client
            async with create_unified_client_from_services(services) as api_client:
                if not api_client.clients:
                    console.print("[red]❌ No healthy services found[/red]")
                    return
                
                print_status(console, f"Testing {len(api_client.clients)} services...", "info")
                
                # Create test request
                test_request = create_chat_request(prompt, max_tokens=100)
                
                # Run test on all services
                results = await api_client.generate_comparison(test_request)
                
                # Display results
                _display_test_results(console, results, prompt)
                
        except Exception as e:
            console.print(f"[red]❌ Service test failed: {str(e)}[/red]")
    
    asyncio.run(_run_test())


def _display_test_results(console: Console, results: dict, prompt: str):
    """Display test results in a formatted table"""
    
    console.print(f"\n[bold green]📋 Test Results for prompt: {prompt}[/bold green]")
    
    # Create results table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Service", style="cyan", width=12)
    table.add_column("Status", style="white", width=10)
    table.add_column("Response Time", style="yellow", width=15)
    table.add_column("Response Preview", style="green")
    
    successful_tests = 0
    for service_name, result in results.items():
        if result.get('success', False):
            successful_tests += 1
            status = "[green]✅ SUCCESS[/green]"
            
            # Get response time
            response_time = result.get('response_time', 0)
            time_display = f"{response_time:.2f}s"
            
            # Get response preview (first 80 chars)
            response_text = result.get('response', 'No response')
            preview = response_text[:80] + "..." if len(response_text) > 80 else response_text
            
        else:
            status = "[red]❌ FAILED[/red]"
            time_display = "N/A"
            preview = result.get('error', 'Unknown error')
        
        table.add_row(
            service_name.upper(),
            status,
            time_display,
            preview
        )
    
    console.print(table)
    
    # Summary
    total_services = len(results)
    console.print(f"\n[bold blue]📊 Test Summary: {successful_tests}/{total_services} services responded successfully[/bold blue]")
    
    if successful_tests > 0:
        print_status(console, "Services are responding! Ready for benchmarking.", "success")
        console.print("[dim]💡 Use 'python vllm_benchmark.py benchmark' to run full performance analysis[/dim]")
    else:
        print_status(console, "No services responded successfully", "warning")
        console.print("[dim]💡 Check service logs or try 'python vllm_benchmark.py discover' for more details[/dim]")
