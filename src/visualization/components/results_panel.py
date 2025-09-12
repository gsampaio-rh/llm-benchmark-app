"""
ResultsPanel - Race results display component.

This component creates panels for displaying race results, winner announcements,
and performance summaries.
"""

from typing import Dict, List, Optional, Tuple, Any
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.box import ROUNDED

from ...race.models import ThreeWayRace, RaceParticipant
from ..core.base_visualizer import BaseVisualizer


class ResultsPanel(BaseVisualizer):
    """Race results display component"""
    
    def __init__(self):
        """Initialize the results panel"""
        super().__init__()
        
        # Service emoji mapping
        self.service_emojis = {
            "vllm": "🔵",
            "tgi": "🟢",
            "ollama": "🟠"
        }
    
    def render(self, data: Dict[str, Any]) -> Panel:
        """Render the results panel
        
        Args:
            data: Dictionary containing results data
                - race: ThreeWayRace object
                - show_winner: Whether to highlight winner
                - title: Optional title for the panel
                
        Returns:
            Formatted Rich Panel with results
        """
        race = data.get("race")
        show_winner = data.get("show_winner", True)
        title = data.get("title", "🏆 Race Results")
        
        if not race or not isinstance(race, ThreeWayRace):
            return Panel(Text("No race results available", style="dim"), title=title)
        
        return self.create_results_panel(race, show_winner, title)
    
    def create_results_panel(self, race: ThreeWayRace, show_winner: bool = True, title: str = "🏆 Race Results") -> Panel:
        """Create comprehensive results panel
        
        Args:
            race: Race with results data
            show_winner: Whether to highlight the winner
            title: Panel title
            
        Returns:
            Panel with formatted results
        """
        # Get TTFT rankings
        ttft_rankings = race.get_ttft_rankings()
        
        if not ttft_rankings:
            return Panel(Text("No race data available", style="dim"), title=title)
        
        # Create results table
        results_table = self.create_results_table(race, ttft_rankings)
        
        # Add winner announcement if requested
        if show_winner and ttft_rankings:
            winner_text = self.create_winner_announcement(ttft_rankings[0])
            
            # Combine winner and results
            content = Text()
            content.append_text(winner_text)
            content.append("\n\n")
            
            # Create a combined panel
            from rich.columns import Columns
            return Panel(
                Columns([winner_text, results_table], equal=True, expand=True),
                title=title,
                border_style="gold1"
            )
        
        return Panel(results_table, title=title, border_style="yellow")
    
    def create_results_table(self, race: ThreeWayRace, ttft_rankings: List[Tuple[str, float]]) -> Table:
        """Create detailed results table
        
        Args:
            race: Race object with participant data
            ttft_rankings: List of (service_name, ttft_ms) sorted by performance
            
        Returns:
            Rich Table with race results
        """
        table = Table(title="🏆 Race Results & Performance Analysis", box=ROUNDED)
        table.add_column("Rank", style="bold", width=6)
        table.add_column("Service", style="bold", width=12)
        table.add_column("TTFT", style="cyan", width=10)
        table.add_column("Tokens", style="green", width=8)
        table.add_column("Experience", style="yellow")
        
        # Add results rows
        for rank, (service_name, ttft_ms) in enumerate(ttft_rankings, 1):
            participant = race.participants[service_name]
            emoji = self.service_emojis.get(service_name, "⚪")
            
            # Experience rating based on TTFT
            experience = self._get_experience_rating(ttft_ms)
            
            # Rank styling
            rank_text = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else str(rank)
            
            table.add_row(
                rank_text,
                f"{emoji} {service_name.upper()}",
                f"{ttft_ms:.1f}ms",
                str(participant.tokens_received),
                experience
            )
        
        return table
    
    def _get_experience_rating(self, ttft_ms: float) -> str:
        """Get user experience rating based on TTFT
        
        Args:
            ttft_ms: Time to first token in milliseconds
            
        Returns:
            Experience rating string
        """
        if ttft_ms < 100:
            return "⚡ Instant & Smooth"
        elif ttft_ms < 200:
            return "🔶 Fast Response"
        elif ttft_ms < 500:
            return "✅ Good Response"
        elif ttft_ms < 1000:
            return "⚠️ Noticeable Delay"
        else:
            return "🐌 Slow Response"
    
    def create_winner_announcement(self, winner_info: Tuple[str, float]) -> Text:
        """Create winner announcement text
        
        Args:
            winner_info: Tuple of (winner_name, ttft_ms)
            
        Returns:
            Rich Text with winner announcement
        """
        winner_name, ttft_ms = winner_info
        emoji = self.service_emojis.get(winner_name, "⚪")
        
        content = Text()
        content.append("🏆 WINNER\n", style="bold gold1")
        content.append(f"{emoji} {winner_name.upper()}\n", style="bold green")
        content.append(f"⚡ {ttft_ms:.1f}ms TTFT", style="cyan")
        
        return content
    
    def create_business_impact_panel(self, race: ThreeWayRace) -> Panel:
        """Create business impact analysis panel
        
        Args:
            race: Race with results data
            
        Returns:
            Panel with business impact analysis
        """
        ttft_rankings = race.get_ttft_rankings()
        
        if len(ttft_rankings) < 2:
            return Panel(Text("Need at least 2 services for comparison", style="dim"), 
                        title="📊 Business Impact")
        
        winner_ttft = ttft_rankings[0][1]
        second_ttft = ttft_rankings[1][1]
        improvement_ms = second_ttft - winner_ttft
        improvement_pct = (improvement_ms / second_ttft) * 100
        
        content = Text()
        content.append("📊 Business Impact Analysis\n\n", style="bold cyan")
        
        # Performance advantage
        content.append("⚡ Performance Advantage:\n", style="bold")
        content.append(f"• {improvement_ms:.1f}ms faster ({improvement_pct:.1f}% improvement)\n", style="green")
        
        # User experience impact
        content.append("\n👤 User Experience Impact:\n", style="bold")
        if improvement_ms > 200:
            content.append("• Users will notice significantly faster responses\n", style="green")
        elif improvement_ms > 50:
            content.append("• Noticeable improvement in responsiveness\n", style="green")
        else:
            content.append("• Subtle but measurable improvement\n", style="yellow")
        
        # Business metrics (estimated)
        daily_interactions = 1000
        time_saved_per_day = (improvement_ms / 1000) * daily_interactions  # seconds
        content.append(f"\n💰 Estimated Daily Impact:\n", style="bold")
        content.append(f"• {time_saved_per_day:.1f} seconds saved per 1000 interactions\n", style="white")
        content.append(f"• {time_saved_per_day/60:.1f} minutes saved daily\n", style="white")
        
        return Panel(content, title="📊 Business Value", border_style="blue")
    
    def create_quick_summary_panel(self, race: ThreeWayRace) -> Panel:
        """Create quick summary panel for rapid display
        
        Args:
            race: Race with results data
            
        Returns:
            Compact panel with key results
        """
        ttft_rankings = race.get_ttft_rankings()
        
        if not ttft_rankings:
            return Panel(Text("No results available", style="dim"), title="📋 Summary")
        
        winner_name, winner_ttft = ttft_rankings[0]
        emoji = self.service_emojis.get(winner_name, "⚪")
        
        content = Text()
        content.append(f"🏆 Winner: {emoji} {winner_name.upper()}\n", style="bold green")
        content.append(f"⚡ TTFT: {winner_ttft:.1f}ms\n", style="cyan")
        
        if len(ttft_rankings) > 1:
            advantage = ttft_rankings[1][1] - winner_ttft
            content.append(f"🎯 Advantage: {advantage:.1f}ms faster", style="yellow")
        
        return Panel(content, title="📋 Quick Summary", border_style="green")
    
    def create_detailed_comparison(self, race: ThreeWayRace) -> List[Panel]:
        """Create detailed comparison with multiple panels
        
        Args:
            race: Race with complete data
            
        Returns:
            List of panels for detailed comparison
        """
        panels = []
        
        # Main results
        panels.append(self.create_results_panel(race))
        
        # Business impact
        panels.append(self.create_business_impact_panel(race))
        
        # Quick summary
        panels.append(self.create_quick_summary_panel(race))
        
        return panels
    
    def create_multi_run_summary(self, race: ThreeWayRace) -> Panel:
        """Create summary for multi-run statistical races
        
        Args:
            race: Race with multiple run statistics
            
        Returns:
            Panel with statistical summary
        """
        if not race.statistics:
            return Panel(Text("No statistical data available", style="dim"), 
                        title="📊 Statistical Summary")
        
        content = Text()
        content.append(f"📊 Statistical Analysis ({race.total_runs} runs)\n\n", style="bold cyan")
        
        # Find overall winner based on mean TTFT
        service_means = {}
        for service_name, stats in race.statistics.items():
            if stats.ttft_times:
                ttft_stats = stats.get_ttft_stats()
                service_means[service_name] = ttft_stats["mean"]
        
        if service_means:
            winner = min(service_means.keys(), key=lambda x: service_means[x])
            emoji = self.service_emojis.get(winner, "⚪")
            
            content.append(f"🏆 Statistical Winner: {emoji} {winner.upper()}\n", style="bold green")
            content.append(f"⚡ Mean TTFT: {service_means[winner]:.1f}ms\n", style="cyan")
            
            # Show consistency
            winner_stats = race.statistics[winner].get_ttft_stats()
            content.append(f"📈 Consistency: ±{winner_stats['std']:.1f}ms std dev\n", style="white")
            
            # Show advantage over second place
            if len(service_means) > 1:
                sorted_means = sorted(service_means.items(), key=lambda x: x[1])
                advantage = sorted_means[1][1] - sorted_means[0][1]
                content.append(f"🎯 Average Advantage: {advantage:.1f}ms", style="yellow")
        
        return Panel(content, title="📊 Statistical Summary", border_style="purple")
