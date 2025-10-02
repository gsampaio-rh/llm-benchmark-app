#!/usr/bin/env python3
"""
Test script for pod info extraction.

Tests the K8s metadata extraction functionality with various URLs.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from src.utils.k8s_metadata import get_k8s_extractor, get_pod_info_for_url

console = Console()


async def test_k8s_detection():
    """Test if K8s environment is detected."""
    console.print("\n[bold cyan]🔍 Testing Kubernetes Detection[/bold cyan]\n")
    
    extractor = get_k8s_extractor()
    is_k8s = await extractor.is_k8s_available()
    
    if is_k8s:
        console.print("[green]✅ Kubernetes/OpenShift environment detected[/green]")
        namespace = await extractor.get_current_namespace()
        console.print(f"   Current namespace: [cyan]{namespace}[/cyan]")
    else:
        console.print("[yellow]⚠️  Not running in Kubernetes/OpenShift[/yellow]")
        console.print("   [dim]Pod info extraction will be skipped[/dim]")
    
    return is_k8s


async def test_pod_extraction(test_urls):
    """Test pod info extraction from various URLs."""
    console.print("\n[bold cyan]📦 Testing Pod Info Extraction[/bold cyan]\n")
    
    results = []
    
    for url in test_urls:
        console.print(f"[bold]Testing:[/bold] {url}")
        
        try:
            pod_info = await get_pod_info_for_url(url)
            
            if pod_info:
                console.print(f"  [green]✅ Found pod:[/green] {pod_info.pod_name}")
                
                # Show resources
                if pod_info.resources:
                    res = pod_info.resources
                    resource_parts = []
                    if res.cpu_limit:
                        resource_parts.append(f"CPU: {res.cpu_limit}")
                    if res.memory_limit:
                        resource_parts.append(f"RAM: {res.memory_limit}")
                    if res.gpu_count:
                        resource_parts.append(f"GPU: {res.gpu_count}x")
                    
                    if resource_parts:
                        console.print(f"     💻 {' | '.join(resource_parts)}")
                
                results.append((url, pod_info))
            else:
                console.print(f"  [yellow]⚠️  No pod found[/yellow]")
                results.append((url, None))
        
        except Exception as e:
            console.print(f"  [red]❌ Error:[/red] {e}")
            results.append((url, None))
        
        console.print()
    
    return results


def display_summary(results):
    """Display summary table of results."""
    console.print("\n[bold cyan]📊 Summary[/bold cyan]\n")
    
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold magenta")
    table.add_column("URL", style="cyan", no_wrap=False)
    table.add_column("Pod Name", style="green")
    table.add_column("Resources", style="yellow")
    
    for url, pod_info in results:
        if pod_info:
            resources_str = ""
            if pod_info.resources:
                res = pod_info.resources
                parts = []
                if res.cpu_limit:
                    parts.append(f"CPU: {res.cpu_limit}")
                if res.memory_limit:
                    parts.append(f"RAM: {res.memory_limit}")
                if res.gpu_count:
                    parts.append(f"GPU: {res.gpu_count}x")
                resources_str = "\n".join(parts) if parts else "N/A"
            
            table.add_row(
                url,
                pod_info.pod_name or "N/A",
                resources_str or "N/A"
            )
        else:
            table.add_row(url, "[dim]Not found[/dim]", "[dim]-[/dim]")
    
    console.print(table)
    console.print()


async def main():
    """Main test execution."""
    console.print(Panel(
        "[bold cyan]Pod Info Extraction Test[/bold cyan]\n\n"
        "This script tests the Kubernetes/OpenShift pod metadata extraction.\n"
        "It will attempt to extract CPU, Memory, and GPU information from pods.",
        title="🧪 Test Script",
        border_style="cyan",
        box=box.ROUNDED
    ))
    
    # Test K8s detection
    is_k8s = await test_k8s_detection()
    
    if not is_k8s:
        console.print("\n[yellow]ℹ️  Skipping pod extraction tests (not in K8s environment)[/yellow]")
        console.print("[dim]To test pod extraction, run this script in a Kubernetes/OpenShift cluster[/dim]\n")
        return
    
    # Test URLs (from your actual OpenShift routes)
    test_urls = [
        "http://ollama-test-vllm-benchmark.apps.cluster-njnqr.njnqr.sandbox1049.opentlc.com",
        "https://vllm-test-vllm-benchmark.apps.cluster-njnqr.njnqr.sandbox1049.opentlc.com",
        "http://tgi-test-vllm-benchmark.apps.cluster-njnqr.njnqr.sandbox1049.opentlc.com",
    ]
    
    console.print("[dim]Expected pods:[/dim]")
    console.print("  [dim]• ollama-test (namespace: vllm-benchmark)[/dim]")
    console.print("  [dim]• vllm-test (namespace: vllm-benchmark)[/dim]")
    console.print("  [dim]• tgi-test (namespace: vllm-benchmark)[/dim]")
    console.print()
    
    # Run extraction tests
    results = await test_pod_extraction(test_urls)
    
    # Display summary
    display_summary(results)
    
    console.print("[bold green]✅ Test complete![/bold green]\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Test interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Test failed:[/red] {e}")
        import traceback
        console.print(f"\n[dim]{traceback.format_exc()}[/dim]")
        sys.exit(1)

