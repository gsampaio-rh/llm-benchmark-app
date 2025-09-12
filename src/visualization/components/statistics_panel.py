"""
StatisticsPanel - Analytics display component.

This component creates panels for displaying statistical analysis,
performance metrics, and comparative analytics.
"""

from typing import Dict, List, Optional, Any
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED

from ...race.models import RaceStatistics, ThreeWayRace
from ..core.base_visualizer import BaseVisualizer


class StatisticsPanel(BaseVisualizer):
    """Statistical analysis display component"""
    
    def __init__(self):
        """Initialize the statistics panel"""
        super().__init__()
    
    def render(self, data: Dict[str, Any]) -> Panel:
        """Render the statistics panel
        
        Args:
            data: Dictionary containing statistics data
                - race: ThreeWayRace object with statistics
                - title: Optional title for the panel
                
        Returns:
            Formatted Rich Panel with statistics
        """
        race = data.get("race")
        title = data.get("title", "📊 Performance Statistics")
        
        if not race or not isinstance(race, ThreeWayRace):
            return Panel(Text("No statistics data available", style="dim"), title=title)
        
        return self.create_statistics_panel(race, title)
    
    def create_statistics_panel(self, race: ThreeWayRace, title: str = "📊 Performance Statistics") -> Panel:
        """Create comprehensive statistics panel
        
        Args:
            race: Race with statistics data
            title: Panel title
            
        Returns:
            Panel with formatted statistics
        """
        if not race.statistics:
            return Panel(Text("No race statistics available", style="dim"), title=title)
        
        # Create statistics table
        stats_table = self.create_statistics_table(race.statistics)
        
        return Panel(stats_table, title=title, border_style="blue")
    
    def create_statistics_table(self, statistics: Dict[str, RaceStatistics]) -> Table:
        """Create a table with detailed statistics
        
        Args:
            statistics: Dictionary of service_name -> RaceStatistics
            
        Returns:
            Rich Table with statistics
        """
        table = Table(box=ROUNDED)
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Runs", justify="center")
        table.add_column("TTFT Mean", justify="right") 
        table.add_column("TTFT P95", justify="right")
        table.add_column("Success Rate", justify="right")
        table.add_column("Performance", justify="center")
        
        for service_name, stats in statistics.items():
            if not stats.ttft_times:
                # No successful runs
                table.add_row(
                    service_name.upper(),
                    "0",
                    "N/A",
                    "N/A", 
                    "0%",
                    "❌ No Data"
                )
                continue
            
            # Calculate statistics
            ttft_stats = stats.get_ttft_stats()
            total_runs = len(stats.ttft_times) + stats.errors
            success_rate = stats.get_success_rate(total_runs)
            
            # Performance rating
            mean_ttft = ttft_stats["mean"]
            if mean_ttft < 100:
                performance = "🏆 Excellent"
                performance_style = "green"
            elif mean_ttft < 200:
                performance = "⚡ Great"
                performance_style = "green"
            elif mean_ttft < 500:
                performance = "✅ Good"
                performance_style = "yellow"
            else:
                performance = "⚠️ Slow"
                performance_style = "red"
            
            table.add_row(
                service_name.upper(),
                str(len(stats.ttft_times)),
                f"{mean_ttft:.1f}ms",
                f"{ttft_stats['p95']:.1f}ms",
                f"{success_rate:.1f}%",
                Text(performance, style=performance_style)
            )
        
        return table
    
    def create_ttft_comparison_panel(self, statistics: Dict[str, RaceStatistics]) -> Panel:
        """Create TTFT-focused comparison panel
        
        Args:
            statistics: Dictionary of service statistics
            
        Returns:
            Panel focused on TTFT comparison
        """
        content = Text()
        content.append("⚡ Time To First Token Analysis\n\n", style="bold cyan")
        
        # Sort services by mean TTFT
        sorted_services = []
        for service_name, stats in statistics.items():
            if stats.ttft_times:
                ttft_stats = stats.get_ttft_stats()
                sorted_services.append((service_name, ttft_stats["mean"]))
        
        sorted_services.sort(key=lambda x: x[1])
        
        # Show rankings
        for rank, (service_name, mean_ttft) in enumerate(sorted_services, 1):
            emoji = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉"
            content.append(f"{emoji} {rank}. {service_name.upper()}: {mean_ttft:.1f}ms\n", 
                          style="white" if rank == 1 else "dim")
        
        if sorted_services:
            # Show winner advantage
            if len(sorted_services) > 1:
                winner_time = sorted_services[0][1]
                second_time = sorted_services[1][1]
                advantage = second_time - winner_time
                content.append(f"\n🎯 Winner Advantage: {advantage:.1f}ms faster", style="green")
        
        return Panel(content, title="⚡ TTFT Rankings", border_style="yellow")
    
    def create_success_rate_panel(self, statistics: Dict[str, RaceStatistics]) -> Panel:
        """Create reliability/success rate panel
        
        Args:
            statistics: Dictionary of service statistics
            
        Returns:
            Panel showing reliability metrics
        """
        table = Table(title="🛡️ Reliability Analysis", box=ROUNDED)
        table.add_column("Service", style="cyan")
        table.add_column("Successful", justify="center")
        table.add_column("Errors", justify="center")
        table.add_column("Success Rate", justify="center")
        table.add_column("Reliability", justify="center")
        
        for service_name, stats in statistics.items():
            successful = len(stats.ttft_times)
            errors = stats.errors
            total = successful + errors
            
            if total > 0:
                success_rate = (successful / total) * 100
                
                # Reliability rating
                if success_rate >= 95:
                    reliability = "🛡️ Excellent"
                    reliability_style = "green"
                elif success_rate >= 90:
                    reliability = "✅ Good"
                    reliability_style = "green"
                elif success_rate >= 80:
                    reliability = "⚠️ Fair"
                    reliability_style = "yellow"
                else:
                    reliability = "❌ Poor"
                    reliability_style = "red"
                
                table.add_row(
                    service_name.upper(),
                    str(successful),
                    str(errors),
                    f"{success_rate:.1f}%",
                    Text(reliability, style=reliability_style)
                )
            else:
                table.add_row(
                    service_name.upper(),
                    "0",
                    "0", 
                    "N/A",
                    Text("No Data", style="dim")
                )
        
        return Panel(table, border_style="green")
    
    def create_token_efficiency_panel(self, statistics: Dict[str, RaceStatistics]) -> Panel:
        """Create token efficiency analysis panel
        
        Args:
            statistics: Dictionary of service statistics
            
        Returns:
            Panel showing token generation efficiency
        """
        content = Text()
        content.append("🎯 Token Generation Efficiency\n\n", style="bold cyan")
        
        for service_name, stats in statistics.items():
            if not stats.token_counts or not stats.total_times:
                content.append(f"{service_name.upper()}: No data\n", style="dim")
                continue
            
            # Calculate tokens per second
            avg_tokens = sum(stats.token_counts) / len(stats.token_counts)
            avg_time_seconds = sum(stats.total_times) / len(stats.total_times) / 1000
            
            if avg_time_seconds > 0:
                tokens_per_second = avg_tokens / avg_time_seconds
                content.append(f"{service_name.upper()}: {tokens_per_second:.1f} tokens/sec\n", 
                              style="white")
                content.append(f"  Average tokens: {avg_tokens:.1f}\n", style="dim")
                content.append(f"  Average time: {avg_time_seconds:.2f}s\n\n", style="dim")
        
        return Panel(content, title="🎯 Token Efficiency", border_style="purple")
    
    def create_comprehensive_analysis(self, race: ThreeWayRace) -> List[Panel]:
        """Create comprehensive analysis with multiple panels
        
        Args:
            race: Race with complete statistics
            
        Returns:
            List of panels for comprehensive analysis
        """
        panels = []
        
        if not race.statistics:
            return [Panel(Text("No statistics available", style="dim"))]
        
        # Main statistics table
        panels.append(self.create_statistics_panel(race))
        
        # TTFT comparison
        panels.append(self.create_ttft_comparison_panel(race.statistics))
        
        # Success rate analysis
        panels.append(self.create_success_rate_panel(race.statistics))
        
        # Token efficiency if we have data
        if any(stats.token_counts for stats in race.statistics.values()):
            panels.append(self.create_token_efficiency_panel(race.statistics))
        
        return panels
