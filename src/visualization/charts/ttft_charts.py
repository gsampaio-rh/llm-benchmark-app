"""
TTFT Chart Generation Module

Modern, focused implementation for Time To First Token analysis charts.
Replaces the TTFT chart functionality from legacy BenchmarkVisualizer.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
from rich.console import Console

# Import data models - using relative imports to match the legacy structure
try:
    from ...metrics import BenchmarkComparison, PerformanceMetrics
    from ...benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult
except ImportError:
    # Fallback for testing or different import contexts
    from src.metrics import BenchmarkComparison, PerformanceMetrics
    from src.benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult


class TTFTChartGenerator:
    """Focused chart generator for TTFT analysis visualizations"""
    
    # Consistent color scheme matching legacy
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
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the TTFT chart generator
        
        Args:
            console: Rich console for progress messages. Creates new one if None.
        """
        self.console = console or Console()
    
    def create_comparison_chart(self, 
                               ttft_results: TTFTBenchmarkResult,
                               comparison: Optional[BenchmarkComparison] = None) -> go.Figure:
        """
        Create comprehensive TTFT comparison chart with modern, clean design
        
        Features:
        - Box plots showing TTFT distribution  
        - Bar chart with mean TTFT vs target
        - Success rate visualization
        - Statistical summary table
        
        Args:
            ttft_results: TTFT benchmark results
            comparison: Optional benchmark comparison for additional metrics
            
        Returns:
            Plotly figure with comprehensive TTFT analysis
        """
        self.console.print("[blue]📊 Creating modern TTFT comparison charts...[/blue]")
        
        # Create sophisticated subplot layout
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '🔍 TTFT Distribution Analysis', 
                '📊 Mean Performance vs Target',
                '✅ Success Rate Analysis',
                '📋 Statistical Summary'
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"type": "table"}]
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.12
        )
        
        services = list(ttft_results.service_results.keys())
        
        # 1. Enhanced Box Plot - TTFT Distribution
        self._add_distribution_plot(fig, ttft_results, services, row=1, col=1)
        
        # 2. Enhanced Bar Chart - Mean Performance
        self._add_performance_bars(fig, ttft_results, comparison, services, row=1, col=2)
        
        # 3. Enhanced Success Rate Analysis
        self._add_success_rate_analysis(fig, ttft_results, comparison, services, row=2, col=1)
        
        # 4. Enhanced Statistical Summary Table
        self._add_statistical_table(fig, ttft_results, comparison, services, row=2, col=2)
        
        # Apply modern, professional styling
        self._apply_modern_styling(fig)
        
        self.console.print("[green]✅ TTFT comparison chart created successfully[/green]")
        return fig
    
    def _add_distribution_plot(self, fig: go.Figure, ttft_results: TTFTBenchmarkResult, 
                              services: List[str], row: int, col: int):
        """Add enhanced box plot showing TTFT distribution"""
        
        for service_name in services:
            if service_name in ttft_results.service_results:
                ttft_values = [
                    r.ttft_ms for r in ttft_results.service_results[service_name] 
                    if r.success and r.ttft_ms > 0
                ]
                
                if ttft_values:
                    # Enhanced box plot with better styling
                    fig.add_trace(
                        go.Box(
                            y=ttft_values,
                            name=service_name.upper(),
                            marker_color=self.COLORS.get(service_name, '#666666'),
                            boxmean='sd',  # Show mean and standard deviation
                            boxpoints='outliers',  # Show outliers
                            notched=True,  # Show confidence interval
                            fillcolor=self.COLORS.get(service_name, '#666666'),
                            line=dict(width=2),
                            opacity=0.8
                        ),
                        row=row, col=col
                    )
        
        # Add target line with enhanced styling
        fig.add_hline(
            y=ttft_results.target_ms,
            line_dash="dash",
            line_color=self.COLORS['target'],
            line_width=3,
            annotation_text=f"🎯 Target: {ttft_results.target_ms}ms",
            annotation_position="top left",
            row=row, col=col
        )
    
    def _add_performance_bars(self, fig: go.Figure, ttft_results: TTFTBenchmarkResult,
                             comparison: Optional[BenchmarkComparison], services: List[str], 
                             row: int, col: int):
        """Add enhanced bar chart showing mean performance vs target"""
        
        if comparison:
            mean_values = []
            colors = []
            text_values = []
            
            for service_name in services:
                metrics = comparison.service_metrics[service_name]
                mean_values.append(metrics.ttft_mean)
                
                # Dynamic color based on target achievement
                if metrics.ttft_target_achieved:
                    colors.append(self.COLORS['success'])
                    text_values.append(f"✅ {metrics.ttft_mean:.1f}ms")
                else:
                    colors.append(self.COLORS.get(service_name, '#666666'))
                    text_values.append(f"❌ {metrics.ttft_mean:.1f}ms")
            
            fig.add_trace(
                go.Bar(
                    x=services,
                    y=mean_values,
                    name='Mean TTFT',
                    marker_color=colors,
                    text=text_values,
                    textposition='outside',
                    textfont=dict(size=10, color='black'),
                    marker_line=dict(width=1, color='rgba(0,0,0,0.3)')
                ),
                row=row, col=col
            )
        
        # Enhanced target line
        fig.add_hline(
            y=ttft_results.target_ms,
            line_dash="dash",
            line_color=self.COLORS['target'],
            line_width=3,
            annotation_text=f"🎯 Target: {ttft_results.target_ms}ms",
            row=row, col=col
        )
    
    def _add_success_rate_analysis(self, fig: go.Figure, ttft_results: TTFTBenchmarkResult,
                                  comparison: Optional[BenchmarkComparison], services: List[str],
                                  row: int, col: int):
        """Add enhanced success rate analysis"""
        
        if comparison:
            success_rates = [
                comparison.service_metrics[s].ttft_success_rate * 100 
                for s in services
            ]
            
            # Enhanced success rate bars with gradient colors
            colors = []
            text_values = []
            
            for i, (service, rate) in enumerate(zip(services, success_rates)):
                if rate >= 95:
                    colors.append(self.COLORS['success'])
                    text_values.append(f"🌟 {rate:.1f}%")
                elif rate >= 80:
                    colors.append(self.COLORS['warning'])
                    text_values.append(f"⚠️ {rate:.1f}%")
                else:
                    colors.append(self.COLORS['error'])
                    text_values.append(f"❌ {rate:.1f}%")
            
            fig.add_trace(
                go.Bar(
                    x=services,
                    y=success_rates,
                    name='Success Rate',
                    marker_color=colors,
                    text=text_values,
                    textposition='outside',
                    textfont=dict(size=10, color='black'),
                    marker_line=dict(width=1, color='rgba(0,0,0,0.3)')
                ),
                row=row, col=col
            )
            
            # Add target line at 95%
            fig.add_hline(
                y=95,
                line_dash="dot",
                line_color=self.COLORS['target'],
                line_width=2,
                annotation_text="🎯 95% Target",
                row=row, col=col
            )
    
    def _add_statistical_table(self, fig: go.Figure, ttft_results: TTFTBenchmarkResult,
                              comparison: Optional[BenchmarkComparison], services: List[str],
                              row: int, col: int):
        """Add enhanced statistical summary table"""
        
        if comparison:
            # Prepare table data with enhanced formatting
            headers = ['Service', 'Mean (ms)', 'Median (ms)', 'P95 (ms)', 'P99 (ms)', 'Std Dev', 'Target ✅']
            
            table_data = []
            for service in services:
                metrics = comparison.service_metrics[service]
                table_data.append([
                    service.upper(),
                    f"{metrics.ttft_mean:.1f}",
                    f"{metrics.ttft_median:.1f}",
                    f"{metrics.ttft_p95:.1f}",
                    f"{metrics.ttft_p99:.1f}",
                    f"{metrics.ttft_std_dev:.1f}",
                    "✅" if metrics.ttft_target_achieved else "❌"
                ])
            
            # Transpose for table display
            values = list(map(list, zip(*table_data)))
            
            # Enhanced table with better styling
            fig.add_trace(
                go.Table(
                    header=dict(
                        values=headers,
                        fill_color='lightblue',
                        font=dict(size=12, color='black'),
                        align='center',
                        height=30
                    ),
                    cells=dict(
                        values=values,
                        fill_color=[['white', 'lightgray'] * len(services)],
                        font=dict(size=11),
                        align=['center'] * len(headers),
                        height=25
                    )
                ),
                row=row, col=col
            )
    
    def _apply_modern_styling(self, fig: go.Figure):
        """Apply modern, professional styling to the figure"""
        
        fig.update_layout(
            # Enhanced title
            title=dict(
                text="<b>🚀 TTFT Performance Analysis Dashboard</b>",
                x=0.5,
                font=dict(size=20, color='#2E3440')
            ),
            
            # Modern color scheme
            font=self.FONT_CONFIG,
            plot_bgcolor='white',
            paper_bgcolor='white',
            
            # Enhanced legend
            showlegend=True,
            legend=dict(
                orientation='h',
                yanchor='bottom',
                y=-0.15,
                xanchor='center',
                x=0.5,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.2)',
                borderwidth=1
            ),
            
            # Better margins
            margin=dict(l=60, r=60, t=100, b=120),
            
            # Enhanced grid
            height=800,
            
            # Modern annotations
            annotations=[
                dict(
                    text="Generated by vLLM Benchmarking Suite",
                    showarrow=False,
                    x=1, y=0,
                    xref="paper", yref="paper",
                    xanchor="right", yanchor="bottom",
                    font=dict(size=10, color="gray")
                )
            ]
        )
        
        # Update subplot titles with better styling
        for i in fig['layout']['annotations']:
            if 'text' in i and any(title in i['text'] for title in ['🔍', '📊', '✅', '📋']):
                i.update(font=dict(size=14, color='#2E3440'))
        
        # Enhanced axis styling
        fig.update_xaxes(
            title_font=dict(size=12, color='#2E3440'),
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)',
            gridwidth=1
        )
        
        fig.update_yaxes(
            title_font=dict(size=12, color='#2E3440'),
            tickfont=dict(size=10),
            gridcolor='rgba(0,0,0,0.1)',
            gridwidth=1
        )
