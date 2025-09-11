"""
Visualization Utilities for vLLM Benchmarking Results
Interactive Plotly dashboards following clean UX pattern
"""

import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional
import statistics

from rich.console import Console
from rich.panel import Panel

console = Console()

class BenchmarkVisualizer:
    """Create beautiful interactive visualizations for benchmark results"""
    
    def __init__(self):
        self.colors = {
            'vllm': '#1f77b4',    # Blue
            'tgi': '#ff7f0e',     # Orange  
            'ollama': '#2ca02c'   # Green
        }
        
        self.layout_style = {
            'template': 'plotly_white',
            'font': {'family': 'Arial, sans-serif', 'size': 12},
            'title': {'font': {'size': 16, 'color': '#2e2e2e'}},
            'showlegend': True,
            'legend': {'orientation': 'h', 'yanchor': 'bottom', 'y': 1.02, 'xanchor': 'right', 'x': 1}
        }
    
    def create_ttft_comparison(self, ttft_results: Dict[str, List[float]]) -> go.Figure:
        """Create TTFT comparison visualization"""
        
        console.print(Panel.fit(
            "[bold yellow]📊 Creating TTFT Visualization[/bold yellow]\n\n"
            "Generating Time To First Token comparison charts...",
            title="Visualization: TTFT Analysis",
            border_style="yellow"
        ))
        
        # Prepare data
        services = []
        values = []
        
        for service_name, ttft_list in ttft_results.items():
            if ttft_list:
                services.extend([service_name.upper()] * len(ttft_list))
                values.extend(ttft_list)
        
        if not values:
            # Create empty figure
            fig = go.Figure()
            fig.add_annotation(
                text="No TTFT data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red")
            )
            fig.update_layout(title="Time To First Token (TTFT) Comparison")
            return fig
        
        # Create subplot with box plot and bar chart
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('TTFT Distribution', 'Average TTFT'),
            specs=[[{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Box plot for distribution
        df = pd.DataFrame({'Service': services, 'TTFT (ms)': values})
        
        for service in df['Service'].unique():
            service_data = df[df['Service'] == service]['TTFT (ms)']
            fig.add_trace(
                go.Box(
                    y=service_data,
                    name=service,
                    marker_color=self.colors.get(service.lower(), '#999999'),
                    boxmean=True
                ),
                row=1, col=1
            )
        
        # Bar chart for averages
        avg_data = []
        for service_name, ttft_list in ttft_results.items():
            if ttft_list:
                avg_ttft = statistics.mean(ttft_list)
                avg_data.append({'Service': service_name.upper(), 'Avg TTFT': avg_ttft})
        
        if avg_data:
            avg_df = pd.DataFrame(avg_data)
            fig.add_trace(
                go.Bar(
                    x=avg_df['Service'],
                    y=avg_df['Avg TTFT'],
                    marker_color=[self.colors.get(s.lower(), '#999999') for s in avg_df['Service']],
                    text=[f"{v:.1f}ms" for v in avg_df['Avg TTFT']],
                    textposition='auto',
                    showlegend=False
                ),
                row=1, col=2
            )
        
        # Add target line (100ms)
        target_ttft = 100.0
        fig.add_hline(y=target_ttft, line_dash="dash", line_color="red", 
                     annotation_text="Target: 100ms", row=1, col=1)
        fig.add_hline(y=target_ttft, line_dash="dash", line_color="red", 
                     annotation_text="Target: 100ms", row=1, col=2)
        
        fig.update_layout(
            title="⚡ Time To First Token (TTFT) Analysis",
            **self.layout_style
        )
        
        fig.update_yaxes(title_text="TTFT (milliseconds)", row=1, col=1)
        fig.update_yaxes(title_text="Average TTFT (milliseconds)", row=1, col=2)
        fig.update_xaxes(title_text="Service", row=1, col=2)
        
        return fig
    
    def create_load_test_dashboard(self, load_test_results: List[Any]) -> go.Figure:
        """Create comprehensive load test dashboard"""
        
        console.print(Panel.fit(
            "[bold red]📊 Creating Load Test Dashboard[/bold red]\n\n"
            "Generating comprehensive performance analysis...",
            title="Visualization: Load Test Analysis", 
            border_style="red"
        ))
        
        if not load_test_results:
            fig = go.Figure()
            fig.add_annotation(
                text="No load test data available",
                xref="paper", yref="paper", 
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="red")
            )
            return fig
        
        # Create 2x2 subplot layout
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'P95 Latency by Test Scenario',
                'Success Rate by Service', 
                'Throughput (Tokens/sec)',
                'Mean TTFT by Scenario'
            ),
            specs=[[{"secondary_y": False}, {"secondary_y": False}],
                   [{"secondary_y": False}, {"secondary_y": False}]]
        )
        
        # Prepare data
        scenarios = []
        services = []
        p95_latencies = []
        success_rates = []
        throughputs = []
        ttft_means = []
        
        for result in load_test_results:
            scenario_name = result.config.name
            
            for service_name, service_result in result.services.items():
                scenarios.append(scenario_name)
                services.append(service_name.upper())
                p95_latencies.append(service_result.p95_response_time)
                
                success_rate = (service_result.successful_requests / service_result.total_requests * 100) if service_result.total_requests > 0 else 0
                success_rates.append(success_rate)
                
                throughputs.append(service_result.mean_tokens_per_sec)
                ttft_means.append(service_result.mean_ttft)
        
        df = pd.DataFrame({
            'Scenario': scenarios,
            'Service': services,
            'P95_Latency': p95_latencies,
            'Success_Rate': success_rates,
            'Throughput': throughputs,
            'TTFT_Mean': ttft_means
        })
        
        # Plot 1: P95 Latency by Scenario
        for service in df['Service'].unique():
            service_data = df[df['Service'] == service]
            fig.add_trace(
                go.Bar(
                    x=service_data['Scenario'],
                    y=service_data['P95_Latency'],
                    name=service,
                    marker_color=self.colors.get(service.lower(), '#999999'),
                    text=[f"{v:.0f}ms" for v in service_data['P95_Latency']],
                    textposition='auto',
                    showlegend=True
                ),
                row=1, col=1
            )
        
        # Plot 2: Success Rate
        for service in df['Service'].unique():
            service_data = df[df['Service'] == service]
            fig.add_trace(
                go.Bar(
                    x=service_data['Scenario'],
                    y=service_data['Success_Rate'],
                    name=service,
                    marker_color=self.colors.get(service.lower(), '#999999'),
                    text=[f"{v:.1f}%" for v in service_data['Success_Rate']],
                    textposition='auto',
                    showlegend=False
                ),
                row=1, col=2
            )
        
        # Plot 3: Throughput
        for service in df['Service'].unique():
            service_data = df[df['Service'] == service]
            fig.add_trace(
                go.Bar(
                    x=service_data['Scenario'],
                    y=service_data['Throughput'],
                    name=service,
                    marker_color=self.colors.get(service.lower(), '#999999'),
                    text=[f"{v:.1f}" for v in service_data['Throughput']],
                    textposition='auto',
                    showlegend=False
                ),
                row=2, col=1
            )
        
        # Plot 4: TTFT Means
        for service in df['Service'].unique():
            service_data = df[df['Service'] == service]
            fig.add_trace(
                go.Bar(
                    x=service_data['Scenario'],
                    y=service_data['TTFT_Mean'],
                    name=service,
                    marker_color=self.colors.get(service.lower(), '#999999'),
                    text=[f"{v:.1f}ms" for v in service_data['TTFT_Mean']],
                    textposition='auto',
                    showlegend=False
                ),
                row=2, col=2
            )
        
        # Add target lines
        fig.add_hline(y=1000, line_dash="dash", line_color="red", 
                     annotation_text="P95 Target: 1000ms", row=1, col=1)
        fig.add_hline(y=100, line_dash="dash", line_color="red",
                     annotation_text="TTFT Target: 100ms", row=2, col=2)
        
        # Update layout
        fig.update_layout(
            title="🔥 Load Testing Performance Dashboard",
            height=800,
            **self.layout_style
        )
        
        # Update axes
        fig.update_yaxes(title_text="P95 Latency (ms)", row=1, col=1)
        fig.update_yaxes(title_text="Success Rate (%)", row=1, col=2)
        fig.update_yaxes(title_text="Tokens/sec", row=2, col=1)
        fig.update_yaxes(title_text="Mean TTFT (ms)", row=2, col=2)
        
        return fig
    
    def create_performance_comparison_radar(self, load_test_results: List[Any]) -> go.Figure:
        """Create radar chart comparing overall performance"""
        
        console.print(Panel.fit(
            "[bold blue]📊 Creating Performance Radar[/bold blue]\n\n"
            "Generating multi-dimensional performance comparison...",
            title="Visualization: Performance Radar",
            border_style="blue"
        ))
        
        if not load_test_results:
            return go.Figure()
        
        # Calculate normalized scores for each service
        services_scores = {}
        
        # Use the stress test results (most comprehensive)
        stress_test = load_test_results[-1] if load_test_results else None
        if not stress_test:
            return go.Figure()
        
        for service_name, result in stress_test.services.items():
            if result.successful_requests == 0:
                continue
                
            # Calculate normalized scores (higher is better, 0-100 scale)
            # TTFT Score: Lower is better, normalize to 0-100
            ttft_score = max(0, 100 - (result.mean_ttft / 2))  # 200ms = 0 points
            
            # P95 Latency Score: Lower is better  
            p95_score = max(0, 100 - (result.p95_response_time / 20))  # 2000ms = 0 points
            
            # Success Rate Score: Direct percentage
            success_score = (result.successful_requests / result.total_requests * 100) if result.total_requests > 0 else 0
            
            # Throughput Score: Higher is better, normalize
            throughput_score = min(100, result.mean_tokens_per_sec * 2)  # 50 tokens/sec = 100 points
            
            # Reliability Score: Based on error rate
            error_rate = (result.failed_requests / result.total_requests * 100) if result.total_requests > 0 else 100
            reliability_score = max(0, 100 - error_rate)
            
            services_scores[service_name] = {
                'TTFT Response': ttft_score,
                'P95 Latency': p95_score, 
                'Success Rate': success_score,
                'Throughput': throughput_score,
                'Reliability': reliability_score
            }
        
        if not services_scores:
            return go.Figure()
        
        # Create radar chart
        fig = go.Figure()
        
        metrics = list(next(iter(services_scores.values())).keys())
        
        for service_name, scores in services_scores.items():
            values = [scores[metric] for metric in metrics]
            values.append(values[0])  # Close the radar chart
            
            fig.add_trace(go.Scatterpolar(
                r=values,
                theta=metrics + [metrics[0]],
                fill='toself',
                name=service_name.upper(),
                line_color=self.colors.get(service_name.lower(), '#999999'),
                fillcolor=self.colors.get(service_name.lower(), '#999999'),
                opacity=0.6
            ))
        
        fig.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickvals=[20, 40, 60, 80, 100],
                    ticktext=['20', '40', '60', '80', '100']
                )
            ),
            title="🎯 Multi-Dimensional Performance Comparison",
            **self.layout_style
        )
        
        return fig
    
    def create_summary_report(self, ttft_results: Dict[str, List[float]], 
                            load_test_results: List[Any]) -> Dict[str, Any]:
        """Generate summary report with key insights"""
        
        console.print(Panel.fit(
            "[bold green]📋 Generating Summary Report[/bold green]\n\n"
            "Analyzing results and generating insights...",
            title="Analysis: Summary Report",
            border_style="green"
        ))
        
        report = {
            'ttft_analysis': {},
            'load_test_analysis': {},
            'winners': {},
            'recommendations': []
        }
        
        # TTFT Analysis
        if ttft_results:
            ttft_winners = {}
            for service_name, ttft_list in ttft_results.items():
                if ttft_list:
                    avg_ttft = statistics.mean(ttft_list)
                    report['ttft_analysis'][service_name] = {
                        'average_ms': avg_ttft,
                        'min_ms': min(ttft_list),
                        'max_ms': max(ttft_list),
                        'target_met': avg_ttft < 100.0,
                        'samples': len(ttft_list)
                    }
                    ttft_winners[service_name] = avg_ttft
            
            if ttft_winners:
                fastest_ttft = min(ttft_winners.keys(), key=lambda x: ttft_winners[x])
                report['winners']['ttft'] = {
                    'service': fastest_ttft,
                    'value': ttft_winners[fastest_ttft]
                }
        
        # Load Test Analysis
        if load_test_results:
            for test_result in load_test_results:
                test_name = test_result.config.name
                report['load_test_analysis'][test_name] = {}
                
                p95_winners = {}
                for service_name, result in test_result.services.items():
                    if result.successful_requests > 0:
                        success_rate = (result.successful_requests / result.total_requests * 100)
                        
                        report['load_test_analysis'][test_name][service_name] = {
                            'p95_latency_ms': result.p95_response_time,
                            'success_rate_percent': success_rate,
                            'mean_ttft_ms': result.mean_ttft,
                            'throughput_tokens_per_sec': result.mean_tokens_per_sec,
                            'total_requests': result.total_requests,
                            'target_p95_met': result.p95_response_time < test_result.config.target_p95_ms,
                            'target_ttft_met': result.mean_ttft < test_result.config.target_ttft_ms
                        }
                        
                        p95_winners[service_name] = result.p95_response_time
                
                # Determine winner for this test
                if p95_winners:
                    winner = min(p95_winners.keys(), key=lambda x: p95_winners[x])
                    report['winners'][test_name] = {
                        'service': winner,
                        'p95_latency': p95_winners[winner]
                    }
        
        # Generate recommendations
        if 'ttft' in report['winners']:
            ttft_winner = report['winners']['ttft']['service']
            ttft_value = report['winners']['ttft']['value']
            
            if ttft_value < 100:
                report['recommendations'].append(
                    f"✅ {ttft_winner.upper()} achieves excellent TTFT ({ttft_value:.1f}ms < 100ms target)"
                )
            else:
                report['recommendations'].append(
                    f"⚠️ All services exceed TTFT target. Best: {ttft_winner.upper()} ({ttft_value:.1f}ms)"
                )
        
        # Count overall wins
        service_wins = {}
        for test_name, winner_info in report['winners'].items():
            if test_name != 'ttft':  # Only count load test wins
                service = winner_info['service']
                service_wins[service] = service_wins.get(service, 0) + 1
        
        if service_wins:
            overall_winner = max(service_wins.keys(), key=lambda x: service_wins[x])
            report['winners']['overall'] = {
                'service': overall_winner,
                'wins': service_wins[overall_winner],
                'total_tests': len([k for k in report['winners'].keys() if k != 'ttft'])
            }
            
            report['recommendations'].append(
                f"🏆 Overall Performance Winner: {overall_winner.upper()} "
                f"({service_wins[overall_winner]} test wins)"
            )
        
        return report

# Helper functions for notebook usage
def create_visualizer() -> BenchmarkVisualizer:
    """Create visualizer instance for notebook"""
    return BenchmarkVisualizer()

def display_all_visualizations(ttft_results: Dict[str, List[float]], 
                             load_test_results: List[Any]) -> Dict[str, go.Figure]:
    """Generate all visualizations and return figures"""
    visualizer = BenchmarkVisualizer()
    
    figures = {}
    
    # TTFT Comparison
    figures['ttft'] = visualizer.create_ttft_comparison(ttft_results)
    
    # Load Test Dashboard  
    figures['load_test'] = visualizer.create_load_test_dashboard(load_test_results)
    
    # Performance Radar
    figures['radar'] = visualizer.create_performance_comparison_radar(load_test_results)
    
    # Summary Report
    report = visualizer.create_summary_report(ttft_results, load_test_results)
    
    return figures, report
