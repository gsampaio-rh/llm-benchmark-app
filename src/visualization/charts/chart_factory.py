"""
Chart Factory - Modern Replacement for Legacy BenchmarkVisualizer

This module provides a drop-in replacement for the legacy BenchmarkVisualizer
class, using the new modular chart generation architecture.
"""

import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from rich.console import Console

from .ttft_charts import TTFTChartGenerator
from .load_charts import LoadChartGenerator  
from .radar_charts import RadarChartGenerator

# Import data models
try:
    from ...metrics import BenchmarkComparison, PerformanceMetrics
    from ...benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult
except ImportError:
    # Fallback for testing or different import contexts
    from src.metrics import BenchmarkComparison, PerformanceMetrics
    from src.benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult


class ChartFactory:
    """
    Modern replacement for legacy BenchmarkVisualizer
    
    Provides the exact same interface as the legacy BenchmarkVisualizer
    but uses the new modular chart generation architecture underneath.
    This ensures drop-in compatibility with existing CLI commands.
    """
    
    def __init__(self, output_dir: str = "results/charts"):
        """Initialize chart factory with output directory
        
        Args:
            output_dir: Directory for saving chart files (maintains legacy compatibility)
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.console = Console()
        
        # Initialize focused chart generators
        self.ttft_generator = TTFTChartGenerator(self.console)
        self.load_generator = LoadChartGenerator(self.console)
        self.radar_generator = RadarChartGenerator(self.console)
        
        self.console.print("[blue]🎨 Modern chart factory initialized[/blue]")
    
    # Legacy compatibility methods - exact same interface as BenchmarkVisualizer
    
    def create_ttft_comparison(self, ttft_results: TTFTBenchmarkResult,
                              comparison: Optional[BenchmarkComparison] = None) -> go.Figure:
        """
        Create TTFT comparison chart (legacy compatibility method)
        
        Args:
            ttft_results: TTFT benchmark results
            comparison: Optional benchmark comparison for additional metrics
            
        Returns:
            Plotly figure with TTFT analysis
        """
        return self.ttft_generator.create_comparison_chart(ttft_results, comparison)
    
    def create_load_dashboard(self, 
                             comparison_or_results: Union[BenchmarkComparison, Any]) -> go.Figure:
        """
        Create load test dashboard (legacy compatibility method)
        
        Args:
            comparison_or_results: BenchmarkComparison object or legacy results format
            
        Returns:
            Plotly figure with load test dashboard
        """
        # Handle different input formats for backward compatibility
        if isinstance(comparison_or_results, BenchmarkComparison):
            return self.load_generator.create_dashboard(comparison_or_results)
        else:
            # Try to handle legacy format - may need conversion
            self.console.print("[yellow]⚠️ Legacy load results format detected, attempting conversion[/yellow]")
            # For now, pass through and let the load generator handle it
            return self.load_generator.create_dashboard(comparison_or_results)
    
    def create_performance_radar(self, 
                                metrics_data: Union[BenchmarkComparison, Dict[str, Any]]) -> go.Figure:
        """
        Create performance radar chart (legacy compatibility method)
        
        Args:
            metrics_data: BenchmarkComparison object or legacy metrics dictionary
            
        Returns:
            Plotly figure with performance radar chart
        """
        return self.radar_generator.create_radar_chart(metrics_data)
    
    # Additional legacy compatibility methods
    
    def create_ttft_comparison_chart(self, ttft_results: TTFTBenchmarkResult,
                                   comparison: BenchmarkComparison) -> go.Figure:
        """Legacy method name compatibility"""
        return self.create_ttft_comparison(ttft_results, comparison)
    
    def create_load_test_dashboard(self, comparison: BenchmarkComparison) -> go.Figure:
        """Legacy method name compatibility"""
        return self.create_load_dashboard(comparison)
    
    def create_performance_radar_chart(self, comparison: BenchmarkComparison) -> go.Figure:
        """Legacy method name compatibility"""
        return self.create_performance_radar(comparison)
    
    # Enhanced modern methods (optional, for new functionality)
    
    def create_comprehensive_dashboard(self, 
                                     ttft_results: TTFTBenchmarkResult,
                                     comparison: BenchmarkComparison) -> Dict[str, go.Figure]:
        """
        Create all visualization charts for comprehensive analysis
        
        Returns dictionary of chart name -> figure (legacy compatibility)
        """
        self.console.print("[bold blue]🎨 Creating comprehensive visualization dashboard...[/bold blue]")
        
        charts = {}
        
        # TTFT Analysis
        self.console.print("[cyan]📊 Generating TTFT comparison charts...[/cyan]")
        charts['ttft_analysis'] = self.create_ttft_comparison(ttft_results, comparison)
        
        # Load Test Dashboard  
        self.console.print("[cyan]📈 Generating load test dashboard...[/cyan]")
        charts['load_dashboard'] = self.create_load_dashboard(comparison)
        
        # Performance Radar
        self.console.print("[cyan]🌟 Generating performance radar chart...[/cyan]")
        charts['performance_radar'] = self.create_performance_radar(comparison)
        
        self.console.print(f"[green]✅ Created {len(charts)} interactive charts[/green]")
        return charts
    
    def save_charts(self, 
                   charts: Dict[str, go.Figure], 
                   formats: List[str] = ['html', 'png']) -> Dict[str, List[str]]:
        """
        Save charts to files (legacy compatibility)
        
        Args:
            charts: Dictionary of chart_name -> figure
            formats: List of formats to save ['html', 'png', 'svg']
            
        Returns:
            Dictionary of chart_name -> list of saved file paths
        """
        self.console.print(f"[cyan]💾 Saving {len(charts)} charts in {formats} format(s)...[/cyan]")
        
        saved_files = {}
        
        for chart_name, figure in charts.items():
            file_paths = []
            
            for fmt in formats:
                if fmt.lower() == 'html':
                    file_path = self.output_dir / f"{chart_name}.html"
                    figure.write_html(str(file_path))
                    file_paths.append(str(file_path))
                    
                elif fmt.lower() in ['png', 'jpg', 'jpeg', 'svg', 'pdf']:
                    file_path = self.output_dir / f"{chart_name}.{fmt.lower()}"
                    try:
                        figure.write_image(str(file_path))
                        file_paths.append(str(file_path))
                    except Exception as e:
                        self.console.print(f"[yellow]⚠️ Could not save {fmt} format: {e}[/yellow]")
            
            saved_files[chart_name] = file_paths
            self.console.print(f"[green]✅ Saved {chart_name}: {len(file_paths)} files[/green]")
        
        return saved_files
    
    def generate_visualization_report(self, 
                                    comparison: BenchmarkComparison,
                                    charts: Dict[str, go.Figure]) -> str:
        """
        Generate comprehensive HTML report with embedded charts (legacy compatibility)
        
        Args:
            comparison: Benchmark comparison data
            charts: Dictionary of chart figures
            
        Returns:
            Path to generated HTML report
        """
        self.console.print("[cyan]📋 Generating comprehensive visualization report...[/cyan]")
        
        # Get chart HTML
        chart_htmls = {}
        for chart_name, figure in charts.items():
            chart_htmls[chart_name] = figure.to_html(
                include_plotlyjs='cdn',
                div_id=f"chart_{chart_name}",
                config={'displayModeBar': True, 'displaylogo': False}
            )
        
        # Generate modern HTML report
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>vLLM Benchmarking Report - {comparison.test_name}</title>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f8f9fa;
                    color: #2E3440;
                }}
                .header {{
                    text-align: center;
                    background: linear-gradient(135deg, #2E86AB, #A23B72);
                    color: white;
                    padding: 30px;
                    border-radius: 10px;
                    margin-bottom: 30px;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 300;
                }}
                .header p {{
                    margin: 10px 0 0 0;
                    font-size: 1.2em;
                    opacity: 0.9;
                }}
                .chart-container {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin-bottom: 30px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .chart-title {{
                    font-size: 1.5em;
                    font-weight: 600;
                    margin-bottom: 15px;
                    color: #2E3440;
                    border-left: 4px solid #2E86AB;
                    padding-left: 15px;
                }}
                .footer {{
                    text-align: center;
                    color: #666;
                    font-size: 0.9em;
                    margin-top: 40px;
                    padding: 20px;
                    border-top: 1px solid #ddd;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>🚀 vLLM Benchmarking Report</h1>
                <p>{comparison.test_name} - Generated on {comparison.timestamp}</p>
            </div>
            
            <div class="chart-container">
                <div class="chart-title">📊 TTFT Performance Analysis</div>
                {chart_htmls.get('ttft_analysis', '<p>TTFT chart not available</p>')}
            </div>
            
            <div class="chart-container">
                <div class="chart-title">📈 Load Test Dashboard</div>
                {chart_htmls.get('load_dashboard', '<p>Load dashboard not available</p>')}
            </div>
            
            <div class="chart-container">
                <div class="chart-title">🌟 Performance Radar</div>
                {chart_htmls.get('performance_radar', '<p>Radar chart not available</p>')}
            </div>
            
            <div class="footer">
                <p>Generated by vLLM Benchmarking Suite - Modern Chart Generation Engine</p>
                <p>Services tested: {', '.join(comparison.services_tested)}</p>
            </div>
        </body>
        </html>
        """
        
        # Save report
        report_path = self.output_dir / f"benchmark_report_{comparison.timestamp.replace(' ', '_').replace(':', '-')}.html"
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        self.console.print(f"[green]✅ Visualization report saved: {report_path}[/green]")
        return str(report_path)


# Legacy compatibility alias
BenchmarkVisualizer = ChartFactory
