"""
Interactive Visualization System for vLLM Benchmarking
Professional Plotly charts and dashboards for benchmark analysis
"""

import json
import time
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from .metrics import BenchmarkComparison, PerformanceMetrics
from .benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult

console = Console()

class BenchmarkVisualizer:
    """Professional visualization system for benchmark results"""
    
    # Color scheme for consistent branding
    COLORS = {
        'vllm': '#2E86AB',      # Blue - Performance leader
        'tgi': '#A23B72',       # Purple - Baseline
        'ollama': '#F18F01',    # Orange - Alternative
        'target': '#C73E1D',    # Red - Target lines
        'success': '#4CAF50',   # Green - Success
        'warning': '#FF9800',   # Orange - Warning
        'error': '#F44336'      # Red - Error
    }
    
    FONT_CONFIG = {
        'family': 'Helvetica, Arial, sans-serif',
        'size': 12,
        'color': '#2E3440'
    }
    
    def __init__(self, output_dir: str = "results/charts"):
        """Initialize visualizer with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Set default Plotly theme
        self._configure_plotly_theme()
    
    def _configure_plotly_theme(self):
        """Configure consistent Plotly styling"""
        # This will be applied to all charts
        self.layout_config = {
            'font': self.FONT_CONFIG,
            'plot_bgcolor': 'white',
            'paper_bgcolor': 'white',
            'showlegend': True,
            'legend': {
                'orientation': 'h',
                'yanchor': 'bottom',
                'y': -0.2,
                'xanchor': 'center',
                'x': 0.5
            },
            'margin': {'l': 60, 'r': 60, 't': 80, 'b': 100}
        }
    
    def create_ttft_comparison_chart(self, 
                                   ttft_results: TTFTBenchmarkResult,
                                   comparison: BenchmarkComparison) -> go.Figure:
        """
        Create comprehensive TTFT comparison with box plots and bar chart
        Shows distribution and target achievement
        """
        console.print("[blue]📊 Creating TTFT comparison charts...[/blue]")
        
        # Create subplot with secondary y-axis
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'TTFT Distribution (Box Plot)', 
                'Mean TTFT vs Target',
                'TTFT Success Rate',
                'TTFT Statistical Summary'
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"type": "table"}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        services = list(comparison.service_metrics.keys())
        
        # 1. Box Plot - TTFT Distribution
        for service_name in services:
            if service_name in ttft_results.service_results:
                ttft_values = [r.ttft_ms for r in ttft_results.service_results[service_name] 
                              if r.success and r.ttft_ms > 0]
                
                if ttft_values:
                    fig.add_trace(
                        go.Box(
                            y=ttft_values,
                            name=service_name.upper(),
                            marker_color=self.COLORS.get(service_name, '#666666'),
                            boxmean='sd'  # Show mean and standard deviation
                        ),
                        row=1, col=1
                    )
        
        # Add target line to box plot
        fig.add_hline(
            y=ttft_results.target_ms,
            line_dash="dash",
            line_color=self.COLORS['target'],
            annotation_text=f"Target: {ttft_results.target_ms}ms",
            row=1, col=1
        )
        
        # 2. Bar Chart - Mean TTFT vs Target
        mean_values = []
        target_achieved = []
        colors = []
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            mean_values.append(metrics.ttft_mean)
            target_achieved.append(metrics.ttft_target_achieved)
            colors.append(self.COLORS['success'] if metrics.ttft_target_achieved 
                         else self.COLORS.get(service_name, '#666666'))
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=mean_values,
                name='Mean TTFT',
                marker_color=colors,
                text=[f"{v:.1f}ms" for v in mean_values],
                textposition='outside'
            ),
            row=1, col=2
        )
        
        # Add target line to bar chart
        fig.add_hline(
            y=ttft_results.target_ms,
            line_dash="dash",
            line_color=self.COLORS['target'],
            annotation_text=f"Target: {ttft_results.target_ms}ms",
            row=1, col=2
        )
        
        # 3. Success Rate Chart
        success_rates = [comparison.service_metrics[s].ttft_success_rate * 100 
                        for s in services]
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=success_rates,
                name='Success Rate',
                marker_color=[self.COLORS.get(s, '#666666') for s in services],
                text=[f"{v:.1f}%" for v in success_rates],
                textposition='outside'
            ),
            row=2, col=1
        )
        
        # 4. Statistical Summary Table
        table_data = []
        headers = ['Service', 'Mean (ms)', 'P95 (ms)', 'Std Dev', 'Target Met']
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            table_data.append([
                service_name.upper(),
                f"{metrics.ttft_mean:.1f}",
                f"{metrics.ttft_p95:.1f}",
                f"{metrics.ttft_std_dev:.1f}",
                "✅" if metrics.ttft_target_achieved else "❌"
            ])
        
        # Transpose for Plotly table format
        table_values = list(map(list, zip(*table_data)))
        
        fig.add_trace(
            go.Table(
                header=dict(
                    values=headers,
                    fill_color='lightblue',
                    align='center',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=table_values,
                    fill_color='white',
                    align='center',
                    font=dict(size=11)
                )
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': f"TTFT Analysis - {comparison.test_name}",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.FONT_CONFIG['color']}
            },
            height=800,
            **self.layout_config
        )
        
        # Update axis labels
        fig.update_yaxes(title_text="TTFT (milliseconds)", row=1, col=1)
        fig.update_yaxes(title_text="TTFT (milliseconds)", row=1, col=2)
        fig.update_yaxes(title_text="Success Rate (%)", row=2, col=1)
        fig.update_xaxes(title_text="Service", row=1, col=2)
        fig.update_xaxes(title_text="Service", row=2, col=1)
        
        return fig
    
    def create_load_test_dashboard(self, 
                                 comparison: BenchmarkComparison) -> go.Figure:
        """
        Create comprehensive 4-panel load test dashboard
        Shows latency, throughput, success rates, and overall performance
        """
        console.print("[blue]📊 Creating load test dashboard...[/blue]")
        
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Latency Distribution (P95 vs Target)',
                'Throughput (Requests/Second)',
                'Success Rate & Reliability',
                'Overall Performance Score'
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}]
            ],
            vertical_spacing=0.12,
            horizontal_spacing=0.1
        )
        
        services = list(comparison.service_metrics.keys())
        
        # 1. Latency Chart (P95 vs Target)
        p95_values = []
        target_values = []
        latency_colors = []
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            p95_values.append(metrics.load_p95_latency)
            
            # Assume target is 1000ms if target_achieved is False and latency > 1000
            target_value = 1000 if not metrics.load_target_achieved and metrics.load_p95_latency > 1000 else 500
            target_values.append(target_value)
            
            latency_colors.append(self.COLORS['success'] if metrics.load_target_achieved 
                                else self.COLORS.get(service_name, '#666666'))
        
        # P95 Latency bars
        fig.add_trace(
            go.Bar(
                x=services,
                y=p95_values,
                name='P95 Latency',
                marker_color=latency_colors,
                text=[f"{v:.0f}ms" for v in p95_values],
                textposition='outside'
            ),
            row=1, col=1
        )
        
        # Add target line (use the most common target)
        common_target = max(set(target_values), key=target_values.count) if target_values else 1000
        fig.add_hline(
            y=common_target,
            line_dash="dash",
            line_color=self.COLORS['target'],
            annotation_text=f"Target: {common_target}ms",
            row=1, col=1
        )
        
        # 2. Throughput Chart
        rps_values = [comparison.service_metrics[s].load_rps for s in services]
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=rps_values,
                name='Requests/Second',
                marker_color=[self.COLORS.get(s, '#666666') for s in services],
                text=[f"{v:.2f}" for v in rps_values],
                textposition='outside'
            ),
            row=1, col=2
        )
        
        # 3. Success Rate Chart
        success_rates = [comparison.service_metrics[s].load_success_rate for s in services]
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=success_rates,
                name='Success Rate',
                marker_color=[self.COLORS['success'] if sr >= 95 else self.COLORS['warning'] 
                             for sr in success_rates],
                text=[f"{v:.1f}%" for v in success_rates],
                textposition='outside'
            ),
            row=2, col=1
        )
        
        # 4. Overall Performance Score
        overall_scores = [comparison.service_metrics[s].overall_score for s in services]
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=overall_scores,
                name='Overall Score',
                marker_color=[self.COLORS.get(s, '#666666') for s in services],
                text=[f"{v:.1f}" for v in overall_scores],
                textposition='outside'
            ),
            row=2, col=2
        )
        
        # Update layout
        fig.update_layout(
            title={
                'text': f"Load Test Dashboard - {comparison.test_name}",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.FONT_CONFIG['color']}
            },
            height=800,
            **self.layout_config
        )
        
        # Update axis labels
        fig.update_yaxes(title_text="Latency (ms)", row=1, col=1)
        fig.update_yaxes(title_text="Requests/Second", row=1, col=2)
        fig.update_yaxes(title_text="Success Rate (%)", row=2, col=1)
        fig.update_yaxes(title_text="Score", row=2, col=2)
        
        for row in [1, 2]:
            for col in [1, 2]:
                fig.update_xaxes(title_text="Service", row=row, col=col)
        
        return fig
    
    def create_performance_radar_chart(self, 
                                     comparison: BenchmarkComparison) -> go.Figure:
        """
        Create multi-dimensional performance radar chart
        Shows latency, throughput, reliability across all services
        """
        console.print("[blue]📊 Creating performance radar chart...[/blue]")
        
        fig = go.Figure()
        
        # Define dimensions (normalize to 0-100 scale)
        dimensions = ['TTFT Speed', 'Load Speed', 'Throughput', 'Reliability', 'Overall']
        
        for service_name in comparison.service_metrics:
            metrics = comparison.service_metrics[service_name]
            
            # Calculate normalized scores (0-100 scale)
            # TTFT Speed: inverse of TTFT (faster = higher score)
            ttft_score = max(0, 100 - (metrics.ttft_mean / 10)) if metrics.ttft_mean > 0 else 0
            
            # Load Speed: inverse of P95 latency
            load_speed = max(0, 100 - (metrics.load_p95_latency / 50)) if metrics.load_p95_latency > 0 else 0
            
            # Throughput: RPS scaled
            throughput = min(100, metrics.load_rps * 100) if metrics.load_rps > 0 else 0
            
            # Reliability: success rate
            reliability = metrics.reliability_score
            
            # Overall: calculated score
            overall = metrics.overall_score
            
            values = [ttft_score, load_speed, throughput, reliability, overall]
            
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],  # Close the polygon
                theta=dimensions + [dimensions[0]],  # Close the polygon
                fill='toself',
                fillcolor=self.COLORS.get(service_name, '#666666'),
                opacity=0.3,
                line=dict(color=self.COLORS.get(service_name, '#666666'), width=2),
                name=service_name.upper(),
                hovertemplate=f'<b>{service_name.upper()}</b><br>' +
                             '%{theta}: %{r:.1f}<br>' +
                             '<extra></extra>'
            ))
        
        fig.update_layout(
            title={
                'text': f"Performance Radar - {comparison.test_name}",
                'x': 0.5,
                'xanchor': 'center',
                'font': {'size': 18, 'color': self.FONT_CONFIG['color']}
            },
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticksuffix='',
                    showticklabels=True
                ),
                angularaxis=dict(
                    tickfont=dict(size=12)
                )
            ),
            **self.layout_config,
            height=600
        )
        
        return fig
    
    def create_comprehensive_dashboard(self, 
                                     ttft_results: TTFTBenchmarkResult,
                                     comparison: BenchmarkComparison) -> Dict[str, go.Figure]:
        """
        Create all visualization charts for comprehensive analysis
        Returns dictionary of chart name -> figure
        """
        console.print("[bold blue]🎨 Creating comprehensive visualization dashboard...[/bold blue]")
        
        charts = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            
            # TTFT Analysis
            task1 = progress.add_task("Creating TTFT comparison charts...", total=1)
            charts['ttft_analysis'] = self.create_ttft_comparison_chart(ttft_results, comparison)
            progress.update(task1, completed=1)
            
            # Load Test Dashboard
            task2 = progress.add_task("Creating load test dashboard...", total=1)
            charts['load_dashboard'] = self.create_load_test_dashboard(comparison)
            progress.update(task2, completed=1)
            
            # Performance Radar
            task3 = progress.add_task("Creating performance radar chart...", total=1)
            charts['performance_radar'] = self.create_performance_radar_chart(comparison)
            progress.update(task3, completed=1)
        
        console.print(f"[green]✅ Created {len(charts)} interactive charts[/green]")
        return charts
    
    def save_charts(self, 
                   charts: Dict[str, go.Figure], 
                   formats: List[str] = ['html', 'png']) -> Dict[str, List[str]]:
        """
        Save charts in multiple formats
        Returns dict of chart_name -> list of file paths
        """
        console.print("[blue]💾 Saving charts to files...[/blue]")
        
        saved_files = {}
        
        for chart_name, fig in charts.items():
            saved_files[chart_name] = []
            
            # Save in requested formats
            for fmt in formats:
                filename = f"{chart_name}_{int(time.time())}.{fmt}"
                filepath = self.output_dir / filename
                
                if fmt == 'html':
                    # Interactive HTML
                    fig.write_html(
                        str(filepath),
                        include_plotlyjs='cdn',  # Use CDN for smaller files
                        config={
                            'displayModeBar': True,
                            'displaylogo': False,
                            'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
                        }
                    )
                elif fmt == 'png':
                    # Static PNG (requires kaleido)
                    try:
                        fig.write_image(str(filepath), width=1200, height=800, scale=2)
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Could not save PNG (install kaleido): {e}[/yellow]")
                        continue
                elif fmt == 'svg':
                    # Vector SVG
                    try:
                        fig.write_image(str(filepath), format='svg')
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Could not save SVG: {e}[/yellow]")
                        continue
                
                saved_files[chart_name].append(str(filepath))
                
        console.print(f"[green]✅ Charts saved to: {self.output_dir}[/green]")
        return saved_files
    
    def generate_visualization_report(self, 
                                    comparison: BenchmarkComparison,
                                    charts: Dict[str, go.Figure]) -> str:
        """
        Generate HTML report with embedded interactive charts
        Returns path to generated report
        """
        console.print("[blue]📄 Generating visualization report...[/blue]")
        
        # HTML template
        html_template = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{comparison.test_name} - Benchmark Report</title>
            <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
            <style>
                body {{
                    font-family: 'Helvetica Neue', Arial, sans-serif;
                    margin: 0;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }}
                .header {{
                    text-align: center;
                    margin-bottom: 30px;
                    border-bottom: 2px solid #2E86AB;
                    padding-bottom: 20px;
                }}
                .chart-section {{
                    margin: 40px 0;
                    padding: 20px;
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                }}
                .summary {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 8px;
                    margin-bottom: 30px;
                }}
                .winner {{
                    color: #4CAF50;
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 {comparison.test_name}</h1>
                    <p>Generated on {comparison.timestamp}</p>
                    <p>Services tested: {', '.join(comparison.services_tested).upper()}</p>
                </div>
                
                <div class="summary">
                    <h2>📊 Executive Summary</h2>
                    <ul>
                        <li><strong>TTFT Winner:</strong> <span class="winner">{comparison.ttft_winner or 'N/A'}</span></li>
                        <li><strong>Load Test Winner:</strong> <span class="winner">{comparison.load_winner or 'N/A'}</span></li>
                        <li><strong>Overall Winner:</strong> <span class="winner">{comparison.overall_winner or 'N/A'}</span></li>
                        <li><strong>Total Requests:</strong> {comparison.total_requests}</li>
                        <li><strong>Test Duration:</strong> {comparison.total_test_duration:.1f} seconds</li>
                    </ul>
                </div>
        """
        
        # Add chart sections
        for chart_name, fig in charts.items():
            chart_div = fig.to_html(
                include_plotlyjs=False,
                div_id=f"chart_{chart_name}",
                config={
                    'displayModeBar': True,
                    'displaylogo': False,
                    'modeBarButtonsToRemove': ['pan2d', 'lasso2d']
                }
            )
            
            html_template += f"""
                <div class="chart-section">
                    <h2>📈 {chart_name.replace('_', ' ').title()}</h2>
                    {chart_div}
                </div>
            """
        
        html_template += """
            </div>
        </body>
        </html>
        """
        
        # Save report
        report_filename = f"benchmark_report_{int(time.time())}.html"
        report_path = self.output_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_template)
        
        console.print(f"[green]✅ Visualization report saved: {report_path}[/green]")
        return str(report_path)


def create_charts_from_results(results_file: str, 
                             output_dir: str = "results/charts") -> Dict[str, str]:
    """
    Convenience function to create charts from saved results file
    Returns dict of chart_name -> file_path
    """
    import time
    
    # Load results
    with open(results_file, 'r') as f:
        data = json.load(f)
    
    # Convert to BenchmarkComparison object
    comparison = BenchmarkComparison(**data)
    
    # Create visualizer
    visualizer = BenchmarkVisualizer(output_dir)
    
    # Note: For convenience function, we'll create simplified charts without TTFT details
    # since we only have the comparison data, not the raw TTFT results
    
    charts = {}
    
    # Create load dashboard and radar chart
    charts['load_dashboard'] = visualizer.create_load_test_dashboard(comparison)
    charts['performance_radar'] = visualizer.create_performance_radar_chart(comparison)
    
    # Save charts
    saved_files = visualizer.save_charts(charts, ['html', 'png'])
    
    # Generate report
    report_path = visualizer.generate_visualization_report(comparison, charts)
    
    return {
        'charts': saved_files,
        'report': report_path
    }
