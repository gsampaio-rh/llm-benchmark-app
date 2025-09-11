"""
Metrics Collection and Statistical Analysis
Advanced statistical analysis for benchmark results
"""

import json
import time
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field, asdict
from statistics import mean, median, stdev, mode
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult

console = Console()

@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics for a service"""
    service_name: str
    
    # TTFT Metrics
    ttft_mean: float = 0.0
    ttft_median: float = 0.0
    ttft_p95: float = 0.0
    ttft_p99: float = 0.0
    ttft_std_dev: float = 0.0
    ttft_target_achieved: bool = False
    ttft_success_rate: float = 0.0
    
    # Load Test Metrics  
    load_success_rate: float = 0.0
    load_rps: float = 0.0
    load_mean_latency: float = 0.0
    load_p95_latency: float = 0.0
    load_p99_latency: float = 0.0
    load_target_achieved: bool = False
    
    # Composite Scores
    latency_score: float = 0.0  # Lower is better
    throughput_score: float = 0.0  # Higher is better
    reliability_score: float = 0.0  # Higher is better
    overall_score: float = 0.0  # Higher is better

@dataclass
class BenchmarkComparison:
    """Complete benchmark comparison across all services"""
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S"))
    test_name: str = "vLLM vs TGI vs Ollama"
    services_tested: List[str] = field(default_factory=list)
    
    # Individual service metrics
    service_metrics: Dict[str, PerformanceMetrics] = field(default_factory=dict)
    
    # Winners by category
    ttft_winner: Optional[str] = None
    load_winner: Optional[str] = None
    overall_winner: Optional[str] = None
    
    # Summary statistics
    total_requests: int = 0
    total_test_duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    def save_to_file(self, filepath: str):
        """Save comparison to JSON file"""
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        
        with open(filepath, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)
        
        console.print(f"[green]✅ Results saved to: {filepath}[/green]")

class MetricsCalculator:
    """Advanced metrics calculation and analysis"""
    
    def __init__(self):
        self.console = console
    
    def calculate_ttft_metrics(self, ttft_results: TTFTBenchmarkResult) -> Dict[str, PerformanceMetrics]:
        """Calculate comprehensive TTFT metrics for all services"""
        metrics = {}
        
        for service_name in ttft_results.service_results:
            stats = ttft_results.get_statistics(service_name)
            
            metrics[service_name] = PerformanceMetrics(
                service_name=service_name,
                ttft_mean=stats["mean_ttft"],
                ttft_median=stats["median_ttft"], 
                ttft_p95=stats["p95_ttft"],
                ttft_p99=stats["p99_ttft"],
                ttft_std_dev=stats["std_dev"],
                ttft_target_achieved=stats["target_achieved"],
                ttft_success_rate=stats["success_rate"]
            )
        
        return metrics
    
    def calculate_load_metrics(self, load_results: Dict[str, ServiceBenchmarkResult]) -> Dict[str, PerformanceMetrics]:
        """Calculate comprehensive load test metrics for all services"""
        metrics = {}
        
        for service_name, result in load_results.items():
            percentiles = result.get_percentiles()
            
            # Create new metrics or update existing
            if service_name in metrics:
                service_metrics = metrics[service_name]
            else:
                service_metrics = PerformanceMetrics(service_name=service_name)
            
            # Update load test metrics
            service_metrics.load_success_rate = result.success_rate
            service_metrics.load_rps = result.requests_per_second
            service_metrics.load_mean_latency = percentiles["mean"]
            service_metrics.load_p95_latency = percentiles["p95"]
            service_metrics.load_p99_latency = percentiles["p99"]
            service_metrics.load_target_achieved = result.target_achieved
            
            metrics[service_name] = service_metrics
        
        return metrics
    
    def calculate_composite_scores(self, metrics: Dict[str, PerformanceMetrics]) -> Dict[str, PerformanceMetrics]:
        """Calculate composite performance scores"""
        
        # Get best values for normalization
        valid_metrics = {name: m for name, m in metrics.items() 
                        if m.ttft_success_rate > 0 and m.load_success_rate > 0}
        
        if not valid_metrics:
            return metrics
        
        # Find best values for scoring
        best_ttft = min(m.ttft_mean for m in valid_metrics.values() if m.ttft_mean > 0)
        best_load_p95 = min(m.load_p95_latency for m in valid_metrics.values() if m.load_p95_latency > 0)
        best_rps = max(m.load_rps for m in valid_metrics.values())
        
        for service_name, service_metrics in metrics.items():
            if service_name not in valid_metrics:
                continue
            
            # Latency score (lower is better, normalized to 0-100)
            ttft_score = (best_ttft / max(service_metrics.ttft_mean, 1)) * 100
            load_score = (best_load_p95 / max(service_metrics.load_p95_latency, 1)) * 100
            service_metrics.latency_score = (ttft_score + load_score) / 2
            
            # Throughput score (higher is better, normalized to 0-100)
            service_metrics.throughput_score = (service_metrics.load_rps / max(best_rps, 1)) * 100
            
            # Reliability score (success rates weighted)
            ttft_reliability = service_metrics.ttft_success_rate * 100
            load_reliability = service_metrics.load_success_rate
            service_metrics.reliability_score = (ttft_reliability + load_reliability) / 2
            
            # Overall score (weighted combination)
            service_metrics.overall_score = (
                service_metrics.latency_score * 0.4 +      # 40% latency
                service_metrics.throughput_score * 0.3 +   # 30% throughput  
                service_metrics.reliability_score * 0.3    # 30% reliability
            )
        
        return metrics
    
    def determine_winners(self, metrics: Dict[str, PerformanceMetrics]) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Determine winners by category"""
        
        valid_services = [name for name, m in metrics.items() 
                         if m.ttft_success_rate > 0 and m.load_success_rate > 0]
        
        if not valid_services:
            return None, None, None
        
        # TTFT winner (fastest average TTFT)
        ttft_winner = min(valid_services, 
                         key=lambda x: metrics[x].ttft_mean)
        
        # Load test winner (best P95 latency with good success rate)
        load_candidates = [s for s in valid_services if metrics[s].load_success_rate >= 95.0]
        if not load_candidates:
            load_candidates = valid_services
        
        load_winner = min(load_candidates,
                         key=lambda x: metrics[x].load_p95_latency)
        
        # Overall winner (highest composite score)
        overall_winner = max(valid_services,
                           key=lambda x: metrics[x].overall_score)
        
        return ttft_winner, load_winner, overall_winner
    
    def create_comparison_report(self, 
                               ttft_results: Optional[TTFTBenchmarkResult] = None,
                               load_results: Optional[Dict[str, ServiceBenchmarkResult]] = None,
                               test_name: str = "vLLM vs TGI vs Ollama") -> BenchmarkComparison:
        """Create comprehensive comparison report"""
        
        comparison = BenchmarkComparison(test_name=test_name)
        
        # Collect all services
        all_services = set()
        if ttft_results:
            all_services.update(ttft_results.service_results.keys())
        if load_results:
            all_services.update(load_results.keys())
        
        comparison.services_tested = list(all_services)
        
        # Calculate metrics
        metrics = {}
        
        # Add TTFT metrics
        if ttft_results:
            ttft_metrics = self.calculate_ttft_metrics(ttft_results)
            for service_name, service_metrics in ttft_metrics.items():
                metrics[service_name] = service_metrics
        
        # Add load test metrics
        if load_results:
            load_metrics = self.calculate_load_metrics(load_results)
            for service_name, service_metrics in load_metrics.items():
                if service_name in metrics:
                    # Update existing metrics
                    existing = metrics[service_name]
                    existing.load_success_rate = service_metrics.load_success_rate
                    existing.load_rps = service_metrics.load_rps
                    existing.load_mean_latency = service_metrics.load_mean_latency
                    existing.load_p95_latency = service_metrics.load_p95_latency
                    existing.load_p99_latency = service_metrics.load_p99_latency
                    existing.load_target_achieved = service_metrics.load_target_achieved
                else:
                    metrics[service_name] = service_metrics
        
        # Calculate composite scores
        metrics = self.calculate_composite_scores(metrics)
        comparison.service_metrics = metrics
        
        # Determine winners
        ttft_winner, load_winner, overall_winner = self.determine_winners(metrics)
        comparison.ttft_winner = ttft_winner
        comparison.load_winner = load_winner
        comparison.overall_winner = overall_winner
        
        # Calculate summary statistics
        if load_results:
            comparison.total_requests = sum(r.total_requests for r in load_results.values())
            comparison.total_test_duration = sum(r.total_time_seconds for r in load_results.values())
        
        return comparison
    
    def display_comprehensive_results(self, comparison: BenchmarkComparison):
        """Display beautiful comprehensive results"""
        
        self.console.print(f"\n[bold blue]🏆 {comparison.test_name} - Final Results[/bold blue]")
        self.console.print(f"[dim]Test completed at: {comparison.timestamp}[/dim]")
        
        if not comparison.service_metrics:
            self.console.print("[red]❌ No valid results to display[/red]")
            return
        
        # Performance comparison table
        table = Table(title="🚀 Performance Comparison Dashboard")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("TTFT (ms)", style="yellow")
        table.add_column("P95 Load (ms)", style="orange1") 
        table.add_column("RPS", style="green")
        table.add_column("Reliability", style="blue")
        table.add_column("Overall Score", style="magenta")
        table.add_column("Rank", style="bold")
        
        # Sort by overall score
        sorted_services = sorted(
            comparison.service_metrics.items(),
            key=lambda x: x[1].overall_score,
            reverse=True
        )
        
        for rank, (service_name, metrics) in enumerate(sorted_services, 1):
            # Format TTFT
            if metrics.ttft_mean > 0:
                ttft_text = f"{metrics.ttft_mean:.1f}"
                if metrics.ttft_target_achieved:
                    ttft_text = f"[green]{ttft_text}[/green]"
                else:
                    ttft_text = f"[red]{ttft_text}[/red]"
            else:
                ttft_text = "[dim]N/A[/dim]"
            
            # Format P95 load latency  
            if metrics.load_p95_latency > 0:
                p95_text = f"{metrics.load_p95_latency:.0f}"
                if metrics.load_target_achieved:
                    p95_text = f"[green]{p95_text}[/green]"
                else:
                    p95_text = f"[red]{p95_text}[/red]"
            else:
                p95_text = "[dim]N/A[/dim]"
            
            # Format RPS
            rps_text = f"{metrics.load_rps:.1f}" if metrics.load_rps > 0 else "[dim]N/A[/dim]"
            
            # Format reliability
            reliability_text = f"{metrics.reliability_score:.1f}%"
            
            # Format overall score
            score_text = f"{metrics.overall_score:.1f}"
            
            # Format rank with medals
            if rank == 1:
                rank_text = "🥇 1st"
                rank_style = "bold gold1"
            elif rank == 2:
                rank_text = "🥈 2nd" 
                rank_style = "bold grey70"
            elif rank == 3:
                rank_text = "🥉 3rd"
                rank_style = "bold gold3"
            else:
                rank_text = f"{rank}th"
                rank_style = "dim"
            
            table.add_row(
                service_name.upper(),
                ttft_text,
                p95_text,
                rps_text,
                reliability_text,
                score_text,
                f"[{rank_style}]{rank_text}[/{rank_style}]"
            )
        
        self.console.print(table)
        
        # Winners summary
        self._display_winners_summary(comparison)
        
        # Performance insights
        self._display_performance_insights(comparison)
    
    def _display_winners_summary(self, comparison: BenchmarkComparison):
        """Display winners summary panel"""
        
        winners_text = Text()
        
        if comparison.ttft_winner:
            ttft_metrics = comparison.service_metrics[comparison.ttft_winner]
            winners_text.append("⚡ TTFT Champion: ", style="bold yellow")
            winners_text.append(f"{comparison.ttft_winner.upper()}", style="bold green")
            winners_text.append(f" ({ttft_metrics.ttft_mean:.1f}ms)\n", style="green")
        
        if comparison.load_winner:
            load_metrics = comparison.service_metrics[comparison.load_winner]
            winners_text.append("📊 Load Test Champion: ", style="bold blue")
            winners_text.append(f"{comparison.load_winner.upper()}", style="bold green")
            winners_text.append(f" (P95: {load_metrics.load_p95_latency:.0f}ms)\n", style="green")
        
        if comparison.overall_winner:
            overall_metrics = comparison.service_metrics[comparison.overall_winner]
            winners_text.append("🏆 Overall Champion: ", style="bold magenta")
            winners_text.append(f"{comparison.overall_winner.upper()}", style="bold gold1")
            winners_text.append(f" (Score: {overall_metrics.overall_score:.1f})", style="gold1")
        
        if winners_text.plain:
            self.console.print(Panel.fit(winners_text, title="🏆 Champions", border_style="gold1"))
    
    def _display_performance_insights(self, comparison: BenchmarkComparison):
        """Display performance insights and recommendations"""
        
        if len(comparison.service_metrics) < 2:
            return
        
        insights = []
        
        # TTFT insights
        if comparison.ttft_winner:
            winner_metrics = comparison.service_metrics[comparison.ttft_winner]
            other_services = {k: v for k, v in comparison.service_metrics.items() if k != comparison.ttft_winner}
            
            if other_services:
                worst_ttft = max(other_services.values(), key=lambda x: x.ttft_mean)
                if worst_ttft.ttft_mean > 0:
                    improvement = ((worst_ttft.ttft_mean - winner_metrics.ttft_mean) / worst_ttft.ttft_mean) * 100
                    insights.append(f"💡 {comparison.ttft_winner.upper()} delivers {improvement:.1f}% faster first tokens")
        
        # Load test insights  
        if comparison.load_winner:
            winner_metrics = comparison.service_metrics[comparison.load_winner]
            other_services = {k: v for k, v in comparison.service_metrics.items() if k != comparison.load_winner}
            
            if other_services:
                worst_load = max(other_services.values(), key=lambda x: x.load_p95_latency)
                if worst_load.load_p95_latency > 0:
                    improvement = ((worst_load.load_p95_latency - winner_metrics.load_p95_latency) / worst_load.load_p95_latency) * 100
                    insights.append(f"📈 {comparison.load_winner.upper()} provides {improvement:.1f}% better P95 latency under load")
        
        # Reliability insights
        reliability_scores = [(name, metrics.reliability_score) for name, metrics in comparison.service_metrics.items()]
        reliability_scores.sort(key=lambda x: x[1], reverse=True)
        
        if len(reliability_scores) >= 2:
            best_reliability = reliability_scores[0]
            if best_reliability[1] >= 99.0:
                insights.append(f"🛡️ {best_reliability[0].upper()} shows excellent reliability ({best_reliability[1]:.1f}%)")
        
        # Target achievement insights
        ttft_achievers = [name for name, metrics in comparison.service_metrics.items() if metrics.ttft_target_achieved]
        load_achievers = [name for name, metrics in comparison.service_metrics.items() if metrics.load_target_achieved]
        
        if ttft_achievers:
            insights.append(f"🎯 TTFT target achieved by: {', '.join(s.upper() for s in ttft_achievers)}")
        
        if load_achievers:
            insights.append(f"🎯 Load target achieved by: {', '.join(s.upper() for s in load_achievers)}")
        
        if insights:
            insights_text = "\n".join(f"• {insight}" for insight in insights)
            self.console.print(Panel.fit(insights_text, title="💡 Performance Insights", border_style="blue"))

# Helper functions
def calculate_percentile(values: List[float], percentile: float) -> float:
    """Calculate percentile from list of values"""
    if not values:
        return 0.0
    
    sorted_values = sorted(values)
    index = int(percentile * len(sorted_values))
    return sorted_values[min(index, len(sorted_values) - 1)]

def calculate_confidence_interval(values: List[float], confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate confidence interval for values"""
    if len(values) < 2:
        return (0.0, 0.0)
    
    mean_val = mean(values)
    std_val = stdev(values)
    n = len(values)
    
    # Using t-distribution approximation for 95% confidence
    margin = 1.96 * (std_val / (n ** 0.5))  
    
    return (mean_val - margin, mean_val + margin)

def export_metrics_csv(comparison: BenchmarkComparison, filepath: str):
    """Export metrics to CSV format"""
    import csv
    
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = [
            'service_name', 'ttft_mean', 'ttft_p95', 'ttft_target_achieved',
            'load_p95_latency', 'load_rps', 'load_target_achieved', 
            'reliability_score', 'overall_score'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for service_name, metrics in comparison.service_metrics.items():
            writer.writerow({
                'service_name': service_name,
                'ttft_mean': metrics.ttft_mean,
                'ttft_p95': metrics.ttft_p95,
                'ttft_target_achieved': metrics.ttft_target_achieved,
                'load_p95_latency': metrics.load_p95_latency,
                'load_rps': metrics.load_rps,
                'load_target_achieved': metrics.load_target_achieved,
                'reliability_score': metrics.reliability_score,
                'overall_score': metrics.overall_score
            })
    
    console.print(f"[green]✅ Metrics exported to CSV: {filepath}[/green]")
