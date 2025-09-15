"""
Results commands - results and visualize  
Handles results management and visualization generation
"""

from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from ..utils.console_utils import print_status


@click.command()
@click.option("--test-id", help="Show details for specific test ID")
@click.option("--limit", default=10, help="Number of recent tests to show")
def results(test_id: Optional[str], limit: int):
    """Manage and view organized test results"""
    console = Console()
    
    # Import here to avoid circular imports
    from ...results_organizer import ResultsOrganizer
    
    try:
        organizer = ResultsOrganizer()
        
        if test_id:
            _show_test_details(console, organizer, test_id)
        else:
            _show_test_list(console, organizer, limit)
            
    except Exception as e:
        console.print(f"[red]❌ Failed to load results: {str(e)}[/red]")


@click.command()
@click.argument("results_file")
@click.option("--output-dir", "-o", help="Output directory for charts")
@click.option("--format", default="html", help="Output format (html, png, svg)")
def visualize(results_file: str, output_dir: Optional[str], format: str):
    """Generate charts and reports from existing benchmark results"""
    console = Console()
    
    console.print("\n[bold blue]📈 Visualization Generation[/bold blue]")
    print_status(console, f"Processing results file: {results_file}", "info")
    
    try:
        # Import here to avoid circular imports
        from ...visualization import BenchmarkVisualizer
        from ...reporting import BenchmarkReporter
        import json
        from pathlib import Path
        
        # Load results file
        results_path = Path(results_file)
        if not results_path.exists():
            console.print(f"[red]❌ Results file not found: {results_file}[/red]")
            return
        
        with open(results_path, 'r') as f:
            results_data = json.load(f)
        
        # Set output directory
        if not output_dir:
            output_dir = results_path.parent / "charts"
        
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        print_status(console, f"Generating visualizations in: {output_path}", "info")
        
        # Create visualizer
        visualizer = BenchmarkVisualizer()
        
        # Generate charts based on available data
        charts_generated = 0
        
        # TTFT charts
        if 'ttft' in results_data:
            console.print("[cyan]📊 Generating TTFT analysis chart...[/cyan]")
            ttft_chart = visualizer.create_ttft_comparison(results_data['ttft'])
            chart_file = output_path / f"ttft_analysis.{format}"
            
            if format == 'html':
                ttft_chart.write_html(str(chart_file))
            else:
                ttft_chart.write_image(str(chart_file))
            
            charts_generated += 1
            print_status(console, f"TTFT chart saved: {chart_file}", "success")
        
        # Load test charts
        load_tests = [key for key in results_data.keys() if key.startswith('load_')]
        for load_test_key in load_tests:
            console.print(f"[cyan]📊 Generating {load_test_key} dashboard...[/cyan]")
            load_chart = visualizer.create_load_dashboard(results_data[load_test_key])
            chart_file = output_path / f"{load_test_key}_dashboard.{format}"
            
            if format == 'html':
                load_chart.write_html(str(chart_file))
            else:
                load_chart.write_image(str(chart_file))
            
            charts_generated += 1
            print_status(console, f"Load test chart saved: {chart_file}", "success")
        
        # Performance radar
        if 'ttft' in results_data and load_tests:
            console.print("[cyan]📊 Generating performance radar chart...[/cyan]")
            radar_data = {
                'ttft': results_data['ttft'],
                'load': results_data[load_tests[0]]  # Use first load test
            }
            radar_chart = visualizer.create_performance_radar(radar_data)
            chart_file = output_path / f"performance_radar.{format}"
            
            if format == 'html':
                radar_chart.write_html(str(chart_file))
            else:
                radar_chart.write_image(str(chart_file))
            
            charts_generated += 1
            print_status(console, f"Performance radar saved: {chart_file}", "success")
        
        # Generate report
        console.print("[cyan]📋 Generating summary report...[/cyan]")
        report_generator = BenchmarkReporter()
        report_html = report_generator.generate_executive_report(results_data, None)
        
        report_file = output_path / "executive_report.html"
        with open(report_file, 'w') as f:
            f.write(report_html)
        
        print_status(console, f"Executive report saved: {report_file}", "success")
        
        # Summary
        console.print(f"\n[bold green]🎉 Visualization Complete![/bold green]")
        console.print(f"[green]📊 Generated {charts_generated} charts and 1 report[/green]")
        console.print(f"[cyan]📁 Output directory: {output_path}[/cyan]")
        
    except Exception as e:
        console.print(f"[red]❌ Visualization generation failed: {str(e)}[/red]")


def _show_test_list(console: Console, organizer, limit: int):
    """Show list of available test runs"""
    console.print("\n[bold blue]📊 Test Results Overview[/bold blue]")
    
    # Get recent test runs
    test_runs = organizer.list_test_runs(limit=limit)
    
    if not test_runs:
        console.print("[yellow]No test results found.[/yellow]")
        console.print("[dim]💡 Run 'python vllm_benchmark.py benchmark' to create test results[/dim]")
        return
    
    # Create table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Test ID", style="cyan")
    table.add_column("Date", style="white")
    table.add_column("Name", style="green")
    table.add_column("Services", style="yellow")
    table.add_column("Status", style="white")
    
    for test_run in test_runs:
        table.add_row(
            test_run.get('test_id', 'Unknown'),
            test_run.get('date', 'Unknown'),
            test_run.get('name', 'Unknown'),
            test_run.get('services', 'Unknown'),
            "[green]✅ Complete[/green]" if test_run.get('complete') else "[yellow]⚠️ Partial[/yellow]"
        )
    
    console.print(table)
    
    console.print(f"\n[dim]💡 Use --test-id to view details for a specific test[/dim]")
    console.print(f"[dim]💡 Use 'python vllm_benchmark.py visualize' to generate charts[/dim]")


def _show_test_details(console: Console, organizer, test_id: str):
    """Show detailed information for a specific test"""
    console.print(f"\n[bold blue]📋 Test Details: {test_id}[/bold blue]")
    
    try:
        # Get test details
        test_details = organizer.get_test_details(test_id)
        
        if not test_details:
            console.print(f"[red]❌ Test not found: {test_id}[/red]")
            return
        
        # Basic info
        console.print(f"[cyan]📅 Date:[/cyan] {test_details.get('date', 'Unknown')}")
        console.print(f"[cyan]📝 Name:[/cyan] {test_details.get('name', 'Unknown')}")
        console.print(f"[cyan]🎯 Services:[/cyan] {test_details.get('services', 'Unknown')}")
        
        # Files
        test_path = organizer.get_test_path(test_id)
        console.print(f"\n[bold blue]📁 Files:[/bold blue]")
        console.print(f"[cyan]📍 Location:[/cyan] {test_path}")
        
        # List files in test directory
        if test_path.exists():
            files = list(test_path.iterdir())
            for file_path in sorted(files):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    size_str = f"{file_size:,} bytes"
                    console.print(f"  📄 {file_path.name} ({size_str})")
                elif file_path.is_dir():
                    console.print(f"  📂 {file_path.name}/")
        
        # Results summary
        comparison_file = test_path / "comparison.json"
        if comparison_file.exists():
            console.print(f"\n[bold blue]🏆 Results Summary:[/bold blue]")
            import json
            with open(comparison_file, 'r') as f:
                comparison_data = json.load(f)
            
            for test_type, results in comparison_data.items():
                if hasattr(results, 'get') and results.get('winner'):
                    console.print(f"  {test_type.upper()}: [green]{results['winner'].upper()}[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Failed to load test details: {str(e)}[/red]")
