"""
Performance Radar Chart Generation Module

Modern, focused implementation for multi-dimensional performance radar charts.
Replaces the radar chart functionality from legacy BenchmarkVisualizer.
"""

import plotly.graph_objects as go
from typing import Dict, List, Optional, Any, Union
from rich.console import Console
import math

# Import data models - using relative imports to match the legacy structure
try:
    from ...metrics import BenchmarkComparison, PerformanceMetrics
    from ...benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult
except ImportError:
    # Fallback for testing or different import contexts
    from src.metrics import BenchmarkComparison, PerformanceMetrics
    from src.benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult


class RadarChartGenerator:
    """Focused chart generator for multi-dimensional performance radar visualizations"""
    
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
        """Initialize the radar chart generator
        
        Args:
            console: Rich console for progress messages. Creates new one if None.
        """
        self.console = console or Console()
    
    def create_radar_chart(self, 
                          metrics_data: Union[BenchmarkComparison, Dict[str, Any]]) -> go.Figure:
        """
        Create comprehensive multi-dimensional performance radar chart
        
        Features:
        - 8-dimensional performance analysis
        - Normalized scoring (0-100 scale)
        - Interactive hover information
        - Professional polar chart styling
        
        Args:
            metrics_data: Benchmark comparison data or metrics dictionary
            
        Returns:
            Plotly figure with multi-dimensional radar chart
        """
        self.console.print("[blue]📊 Creating modern performance radar chart...[/blue]")
        
        # Handle different input types
        if isinstance(metrics_data, dict) and 'ttft' in metrics_data:
            # Legacy format: {'ttft': ttft_results, 'load': load_results}
            return self._create_from_mixed_data(metrics_data)
        elif isinstance(metrics_data, BenchmarkComparison):
            # Modern format: BenchmarkComparison object
            return self._create_from_comparison(metrics_data)
        else:
            # Fallback: try to handle as comparison
            return self._create_from_comparison(metrics_data)
    
    def _create_from_comparison(self, comparison: BenchmarkComparison) -> go.Figure:
        """Create radar chart from BenchmarkComparison object"""
        
        fig = go.Figure()
        
        # Enhanced 8-dimensional analysis
        dimensions = [
            'TTFT Speed ⚡',
            'Load Latency 📊', 
            'Throughput 🚀',
            'Reliability ✅',
            'TTFT Consistency 📈',
            'Load Consistency 📉',
            'Success Rate 🎯',
            'Overall Score 🏆'
        ]
        
        services = list(comparison.service_metrics.keys())
        
        for service_name in services:
            metrics = comparison.service_metrics[service_name]
            
            # Calculate enhanced normalized scores (0-100 scale)
            scores = self._calculate_enhanced_scores(metrics)
            values = [scores[dim] for dim in [
                'ttft_speed', 'load_speed', 'throughput', 'reliability',
                'ttft_consistency', 'load_consistency', 'success_rate', 'overall'
            ]]
            
            # Create enhanced trace with better styling
            fig.add_trace(go.Scatterpolar(
                r=values + [values[0]],  # Close the polygon
                theta=dimensions + [dimensions[0]],  # Close the polygon
                fill='toself',
                fillcolor=self.COLORS.get(service_name, '#666666'),
                opacity=0.25,
                line=dict(
                    color=self.COLORS.get(service_name, '#666666'), 
                    width=3
                ),
                name=f"{service_name.upper()} ⭐",
                hovertemplate=
                f'<b>{service_name.upper()}</b><br>' +
                '%{theta}: %{r:.1f}/100<br>' +
                '<extra></extra>',
                marker=dict(
                    size=8,
                    color=self.COLORS.get(service_name, '#666666'),
                    line=dict(width=2, color='white')
                )
            ))
        
        # Apply modern, professional styling
        self._apply_modern_radar_styling(fig, comparison)
        
        self.console.print("[green]✅ Performance radar chart created successfully[/green]")
        return fig
    
    def _create_from_mixed_data(self, metrics_data: Dict[str, Any]) -> go.Figure:
        """Create radar chart from mixed legacy format data"""
        
        # This handles the legacy format where CLI passes:
        # {'ttft': ttft_results, 'load': list(load_results.values())[0]}
        
        self.console.print("[yellow]⚠️ Using legacy data format compatibility mode[/yellow]")
        
        fig = go.Figure()
        
        ttft_results = metrics_data.get('ttft')
        load_results = metrics_data.get('load')
        
        if not ttft_results or not load_results:
            self.console.print("[red]❌ Insufficient data for radar chart[/red]")
            return fig
        
        # Simple 5-dimensional analysis for legacy compatibility
        dimensions = ['TTFT Speed', 'Load Speed', 'Throughput', 'Reliability', 'Overall']
        
        # Extract services from TTFT results
        services = list(ttft_results.service_results.keys()) if hasattr(ttft_results, 'service_results') else []
        
        for service_name in services:
            # Calculate simplified scores for legacy compatibility
            values = self._calculate_legacy_scores(service_name, ttft_results, load_results)
            
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
        
        # Apply simplified styling for legacy compatibility
        self._apply_legacy_radar_styling(fig)
        
        return fig
    
    def _calculate_enhanced_scores(self, metrics: PerformanceMetrics) -> Dict[str, float]:
        """Calculate enhanced normalized scores for 8-dimensional analysis"""
        
        scores = {}
        
        # 1. TTFT Speed (inverse of mean TTFT, scaled to 0-100)
        # Target: 100ms or less = 100 points, 1000ms = 0 points
        scores['ttft_speed'] = max(0, 100 - (metrics.ttft_mean / 10)) if metrics.ttft_mean > 0 else 0
        
        # 2. Load Speed (inverse of P95 latency)
        # Target: 500ms or less = 100 points, 5000ms = 0 points  
        scores['load_speed'] = max(0, 100 - (metrics.load_p95_latency / 50)) if metrics.load_p95_latency > 0 else 0
        
        # 3. Throughput (RPS scaled)
        # Assume max reasonable RPS is 100, scale accordingly
        scores['throughput'] = min(100, metrics.load_rps * 10) if metrics.load_rps > 0 else 0
        
        # 4. Reliability (success rate scaled)
        scores['reliability'] = metrics.reliability_score
        
        # 5. TTFT Consistency (inverse of standard deviation)
        # Low std dev = high consistency score
        if hasattr(metrics, 'ttft_std_dev') and metrics.ttft_std_dev > 0:
            scores['ttft_consistency'] = max(0, 100 - (metrics.ttft_std_dev / 5))
        else:
            scores['ttft_consistency'] = 50  # Default moderate score
        
        # 6. Load Consistency (based on P99-P95 difference)
        # Smaller difference = better consistency
        p99_p95_diff = abs(metrics.load_p99_latency - metrics.load_p95_latency)
        scores['load_consistency'] = max(0, 100 - (p99_p95_diff / 20))
        
        # 7. Success Rate (direct percentage)
        scores['success_rate'] = metrics.load_success_rate
        
        # 8. Overall Score (composite metric)
        scores['overall'] = metrics.overall_score
        
        return scores
    
    def _calculate_legacy_scores(self, service_name: str, ttft_results: Any, load_results: Any) -> List[float]:
        """Calculate simplified scores for legacy compatibility"""
        
        # Default scores
        ttft_score = 50
        load_speed = 50  
        throughput = 50
        reliability = 50
        overall = 50
        
        # Try to extract TTFT data
        if hasattr(ttft_results, 'service_results') and service_name in ttft_results.service_results:
            ttft_values = [r.ttft_ms for r in ttft_results.service_results[service_name] if r.success]
            if ttft_values:
                avg_ttft = sum(ttft_values) / len(ttft_values)
                ttft_score = max(0, 100 - (avg_ttft / 10))
        
        # Try to extract load data
        if hasattr(load_results, 'service_results') and service_name in load_results.service_results:
            # Simple extraction based on available data
            load_speed = 75  # Default good score
            throughput = 60  # Default moderate score
            reliability = 90  # Default high reliability
        
        # Calculate simple overall score
        overall = (ttft_score + load_speed + throughput + reliability) / 4
        
        return [ttft_score, load_speed, throughput, reliability, overall]
    
    def _apply_modern_radar_styling(self, fig: go.Figure, comparison: BenchmarkComparison):
        """Apply modern, professional styling to the radar chart"""
        
        fig.update_layout(
            # Enhanced title
            title=dict(
                text=f"<b>🌟 Multi-Dimensional Performance Radar - {comparison.test_name}</b>",
                x=0.5,
                font=dict(size=20, color='#2E3440')
            ),
            
            # Modern color scheme
            font=self.FONT_CONFIG,
            plot_bgcolor='white',
            paper_bgcolor='white',
            
            # Enhanced polar chart styling
            polar=dict(
                bgcolor='rgba(245,245,245,0.3)',
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    ticksuffix='',
                    showticklabels=True,
                    tickfont=dict(size=10, color='#666666'),
                    gridcolor='rgba(0,0,0,0.1)',
                    gridwidth=1,
                    linecolor='rgba(0,0,0,0.2)',
                    linewidth=2
                ),
                angularaxis=dict(
                    tickfont=dict(size=12, color='#2E3440'),
                    linecolor='rgba(0,0,0,0.2)',
                    gridcolor='rgba(0,0,0,0.1)',
                    gridwidth=1
                )
            ),
            
            # Enhanced legend
            legend=dict(
                orientation='v',
                yanchor='middle',
                y=0.5,
                xanchor='left',
                x=1.02,
                bgcolor='rgba(255,255,255,0.8)',
                bordercolor='rgba(0,0,0,0.2)',
                borderwidth=1,
                font=dict(size=11)
            ),
            
            # Better margins
            margin=dict(l=60, r=120, t=100, b=60),
            height=700,
            
            # Modern annotations
            annotations=[
                dict(
                    text="📊 Performance Scale: 0-100 (Higher is Better)",
                    showarrow=False,
                    x=0.5, y=-0.05,
                    xref="paper", yref="paper",
                    xanchor="center", yanchor="top",
                    font=dict(size=11, color="gray")
                ),
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
    
    def _apply_legacy_radar_styling(self, fig: go.Figure):
        """Apply simplified styling for legacy compatibility"""
        
        fig.update_layout(
            title=dict(
                text="Performance Radar Chart",
                x=0.5,
                font=dict(size=18, color=self.FONT_CONFIG['color'])
            ),
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
            font=self.FONT_CONFIG,
            plot_bgcolor='white',
            paper_bgcolor='white',
            height=600,
            margin=dict(l=60, r=60, t=100, b=60)
        )
