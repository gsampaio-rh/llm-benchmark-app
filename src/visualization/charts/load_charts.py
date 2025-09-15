"""
Load Test Dashboard Chart Generation Module

Modern, focused implementation for load test performance dashboards.
Replaces the load dashboard functionality from legacy BenchmarkVisualizer.
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, List, Optional, Any
from rich.console import Console

# Import data models - using relative imports to match the legacy structure
try:
    from ...metrics import BenchmarkComparison, PerformanceMetrics
    from ...benchmarking import ServiceBenchmarkResult
except ImportError:
    # Fallback for testing or different import contexts
    from src.metrics import BenchmarkComparison, PerformanceMetrics
    from src.benchmarking import ServiceBenchmarkResult


class LoadChartGenerator:
    """Focused chart generator for load test dashboard visualizations"""
    
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
        """Initialize the load test chart generator
        
        Args:
            console: Rich console for progress messages. Creates new one if None.
        """
        self.console = console or Console()
    
    def create_dashboard(self, comparison: BenchmarkComparison) -> go.Figure:
        """
        Create comprehensive load test dashboard with modern, clean design
        
        Features:
        - Latency distribution analysis (P95 vs target)
        - Throughput performance (requests/second)
        - Success rate and reliability metrics
        - Overall performance scoring
        
        Args:
            comparison: Benchmark comparison data with load test metrics
            
        Returns:
            Plotly figure with comprehensive load test dashboard
        """
        self.console.print("[blue]📊 Creating modern load test dashboard...[/blue]")
        
        # Create sophisticated subplot layout
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                '⚡ Latency Performance Analysis',
                '🚀 Throughput & Capacity',
                '✅ Reliability & Success Rates',
                '🏆 Overall Performance Ranking'
            ),
            specs=[
                [{"secondary_y": False}, {"secondary_y": False}],
                [{"secondary_y": False}, {"secondary_y": False}]
            ],
            vertical_spacing=0.15,
            horizontal_spacing=0.12
        )
        
        services = list(comparison.service_metrics.keys())
        
        # 1. Enhanced Latency Analysis
        self._add_latency_analysis(fig, comparison, services, row=1, col=1)
        
        # 2. Enhanced Throughput Chart
        self._add_throughput_analysis(fig, comparison, services, row=1, col=2)
        
        # 3. Enhanced Reliability Analysis
        self._add_reliability_analysis(fig, comparison, services, row=2, col=1)
        
        # 4. Enhanced Performance Ranking
        self._add_performance_ranking(fig, comparison, services, row=2, col=2)
        
        # Apply modern, professional styling
        self._apply_modern_styling(fig, comparison)
        
        self.console.print("[green]✅ Load test dashboard created successfully[/green]")
        return fig
    
    def _add_latency_analysis(self, fig: go.Figure, comparison: BenchmarkComparison,
                             services: List[str], row: int, col: int):
        """Add enhanced latency performance analysis"""
        
        p95_values = []
        p99_values = []
        mean_values = []
        colors = []
        text_values = []
        
        # Determine common target (most frequent target value)
        target_values = []
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            # Estimate target based on achievement and actual values
            if metrics.load_target_achieved:
                target_values.append(1000)  # Standard target for achieved
            else:
                target_values.append(1500)  # Higher target for failed
        
        common_target = max(set(target_values), key=target_values.count) if target_values else 1000
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            p95_values.append(metrics.load_p95_latency)
            p99_values.append(metrics.load_p99_latency)
            mean_values.append(metrics.load_mean_latency)
            
            # Dynamic color and text based on performance
            if metrics.load_target_achieved:
                colors.append(self.COLORS['success'])
                text_values.append(f"✅ {metrics.load_p95_latency:.0f}ms")
            else:
                colors.append(self.COLORS.get(service_name, '#666666'))
                text_values.append(f"❌ {metrics.load_p95_latency:.0f}ms")
        
        # Add P95 latency bars
        fig.add_trace(
            go.Bar(
                x=services,
                y=p95_values,
                name='P95 Latency',
                marker_color=colors,
                text=text_values,
                textposition='outside',
                textfont=dict(size=10, color='black'),
                marker_line=dict(width=1, color='rgba(0,0,0,0.3)'),
                customdata=p99_values,
                hovertemplate=
                '<b>%{x}</b><br>' +
                'P95 Latency: %{y:.0f}ms<br>' +
                'P99 Latency: %{customdata:.0f}ms<br>' +
                '<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Add target line with enhanced styling
        fig.add_hline(
            y=common_target,
            line_dash="dash",
            line_color=self.COLORS['target'],
            line_width=3,
            annotation_text=f"🎯 Target: {common_target}ms",
            annotation_position="top left",
            row=row, col=col
        )
    
    def _add_throughput_analysis(self, fig: go.Figure, comparison: BenchmarkComparison,
                                services: List[str], row: int, col: int):
        """Add enhanced throughput and capacity analysis"""
        
        rps_values = []
        colors = []
        text_values = []
        
        # Find the maximum RPS for relative performance
        max_rps = max(comparison.service_metrics[s].load_rps for s in services)
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            rps_values.append(metrics.load_rps)
            
            # Dynamic color based on relative performance
            relative_performance = metrics.load_rps / max_rps if max_rps > 0 else 0
            
            if relative_performance >= 0.9:
                colors.append(self.COLORS['success'])
                text_values.append(f"🌟 {metrics.load_rps:.1f}")
            elif relative_performance >= 0.7:
                colors.append(self.COLORS['warning'])
                text_values.append(f"⚠️ {metrics.load_rps:.1f}")
            else:
                colors.append(self.COLORS.get(service_name, '#666666'))
                text_values.append(f"📉 {metrics.load_rps:.1f}")
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=rps_values,
                name='Requests/Second',
                marker_color=colors,
                text=text_values,
                textposition='outside',
                textfont=dict(size=10, color='black'),
                marker_line=dict(width=1, color='rgba(0,0,0,0.3)'),
                hovertemplate=
                '<b>%{x}</b><br>' +
                'Throughput: %{y:.2f} RPS<br>' +
                'Relative Performance: ' + str([f"{(rps/max_rps)*100:.1f}%" for rps in rps_values]) + '<br>' +
                '<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Add average line for reference
        avg_rps = sum(rps_values) / len(rps_values) if rps_values else 0
        fig.add_hline(
            y=avg_rps,
            line_dash="dot",
            line_color="gray",
            line_width=2,
            annotation_text=f"📊 Average: {avg_rps:.1f} RPS",
            row=row, col=col
        )
    
    def _add_reliability_analysis(self, fig: go.Figure, comparison: BenchmarkComparison,
                                 services: List[str], row: int, col: int):
        """Add enhanced reliability and success rate analysis"""
        
        success_rates = []
        colors = []
        text_values = []
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            success_rate = metrics.load_success_rate
            success_rates.append(success_rate)
            
            # Dynamic color and text based on success rate
            if success_rate >= 99:
                colors.append(self.COLORS['success'])
                text_values.append(f"🌟 {success_rate:.1f}%")
            elif success_rate >= 95:
                colors.append(self.COLORS['warning'])
                text_values.append(f"✅ {success_rate:.1f}%")
            elif success_rate >= 90:
                colors.append(self.COLORS['warning'])
                text_values.append(f"⚠️ {success_rate:.1f}%")
            else:
                colors.append(self.COLORS['error'])
                text_values.append(f"❌ {success_rate:.1f}%")
        
        fig.add_trace(
            go.Bar(
                x=services,
                y=success_rates,
                name='Success Rate',
                marker_color=colors,
                text=text_values,
                textposition='outside',
                textfont=dict(size=10, color='black'),
                marker_line=dict(width=1, color='rgba(0,0,0,0.3)'),
                hovertemplate=
                '<b>%{x}</b><br>' +
                'Success Rate: %{y:.2f}%<br>' +
                'Reliability Grade: ' + [self._get_reliability_grade(sr) for sr in success_rates] + '<br>' +
                '<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Add target lines for different reliability levels
        fig.add_hline(y=99, line_dash="dash", line_color=self.COLORS['success'], 
                     line_width=2, annotation_text="🌟 Excellent (99%)", row=row, col=col)
        fig.add_hline(y=95, line_dash="dot", line_color=self.COLORS['warning'], 
                     line_width=2, annotation_text="✅ Good (95%)", row=row, col=col)
    
    def _add_performance_ranking(self, fig: go.Figure, comparison: BenchmarkComparison,
                                services: List[str], row: int, col: int):
        """Add enhanced overall performance ranking"""
        
        overall_scores = []
        colors = []
        text_values = []
        
        # Sort services by overall score for ranking
        service_scores = [(s, comparison.service_metrics[s].overall_score) for s in services]
        service_scores.sort(key=lambda x: x[1], reverse=True)
        
        for i, (service_name, score) in enumerate(service_scores):
            overall_scores.append(score)
            
            # Ranking-based colors and text
            if i == 0:  # Winner
                colors.append(self.COLORS['success'])
                text_values.append(f"🥇 {score:.1f}")
            elif i == 1:  # Second place
                colors.append(self.COLORS['warning'])
                text_values.append(f"🥈 {score:.1f}")
            elif i == 2:  # Third place
                colors.append(self.COLORS.get(service_name, '#666666'))
                text_values.append(f"🥉 {score:.1f}")
            else:
                colors.append(self.COLORS.get(service_name, '#666666'))
                text_values.append(f"📊 {score:.1f}")
        
        fig.add_trace(
            go.Bar(
                x=[s[0] for s in service_scores],
                y=overall_scores,
                name='Overall Score',
                marker_color=colors,
                text=text_values,
                textposition='outside',
                textfont=dict(size=11, color='black'),
                marker_line=dict(width=1, color='rgba(0,0,0,0.3)'),
                hovertemplate=
                '<b>%{x}</b><br>' +
                'Overall Score: %{y:.2f}<br>' +
                'Ranking: ' + [f"#{i+1}" for i in range(len(services))] + '<br>' +
                '<extra></extra>'
            ),
            row=row, col=col
        )
        
        # Add performance grade lines
        fig.add_hline(y=80, line_dash="dash", line_color=self.COLORS['success'], 
                     line_width=2, annotation_text="🏆 Excellent (80+)", row=row, col=col)
        fig.add_hline(y=60, line_dash="dot", line_color=self.COLORS['warning'], 
                     line_width=2, annotation_text="✅ Good (60+)", row=row, col=col)
    
    def _get_reliability_grade(self, success_rate: float) -> str:
        """Get reliability grade based on success rate"""
        if success_rate >= 99:
            return "Excellent"
        elif success_rate >= 95:
            return "Good"
        elif success_rate >= 90:
            return "Fair"
        else:
            return "Poor"
    
    def _apply_modern_styling(self, fig: go.Figure, comparison: BenchmarkComparison):
        """Apply modern, professional styling to the figure"""
        
        fig.update_layout(
            # Enhanced title
            title=dict(
                text=f"<b>📊 Load Test Performance Dashboard - {comparison.test_name}</b>",
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
            if 'text' in i and any(emoji in i['text'] for emoji in ['⚡', '🚀', '✅', '🏆']):
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
        
        # Update specific axis labels
        fig.update_yaxes(title_text="Latency (ms)", row=1, col=1)
        fig.update_yaxes(title_text="Requests/Second", row=1, col=2)
        fig.update_yaxes(title_text="Success Rate (%)", row=2, col=1)
        fig.update_yaxes(title_text="Performance Score", row=2, col=2)
        
        # Update x-axis labels for all subplots
        for row in [1, 2]:
            for col in [1, 2]:
                fig.update_xaxes(title_text="Service", row=row, col=col)
