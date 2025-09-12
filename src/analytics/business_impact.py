"""
Business impact analysis and ROI calculations.

This module provides business intelligence capabilities, translating technical
performance metrics into business value and ROI analysis.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

from .metrics import ServicePerformanceProfile, TTFTStats
from ..race.models import ThreeWayRace


@dataclass
class TimeSavings:
    """Time savings analysis between services"""
    improvement_ms: float
    improvement_pct: float
    daily_seconds_saved: float
    daily_minutes_saved: float
    annual_hours_saved: float
    

@dataclass
class ProductivityImpact:
    """Productivity impact analysis"""
    faster_service: str
    slower_service: str
    time_advantage: float
    interactions_per_day: int
    agents_affected: int
    daily_productivity_gain_minutes: float
    annual_productivity_gain_hours: float
    estimated_hourly_rate: float
    annual_savings_usd: float


@dataclass
class UserExperienceImpact:
    """User experience impact analysis"""
    ux_improvement_category: str  # "Major", "Significant", "Noticeable", "Minimal"
    user_satisfaction_impact: str
    abandonment_rate_impact: str
    responsiveness_perception: str
    competitive_advantage: str


@dataclass
class BusinessImpactSummary:
    """Comprehensive business impact analysis"""
    winner_service: str
    time_savings: TimeSavings
    productivity_impact: ProductivityImpact
    ux_impact: UserExperienceImpact
    roi_summary: str
    key_recommendations: List[str]


class BusinessImpactAnalyzer:
    """ROI and business value calculations"""
    
    # Default business parameters (can be customized)
    DEFAULT_INTERACTIONS_PER_DAY = 1000
    DEFAULT_AGENTS_AFFECTED = 50
    DEFAULT_HOURLY_RATE = 35.0  # USD per hour
    DEFAULT_WORKING_DAYS_PER_YEAR = 250
    
    @staticmethod
    def calculate_time_savings(winner_ttft: float, loser_ttft: float, 
                              daily_interactions: int = DEFAULT_INTERACTIONS_PER_DAY) -> TimeSavings:
        """Calculate productivity impact from performance differences
        
        Args:
            winner_ttft: Best service TTFT in milliseconds
            loser_ttft: Worst/comparison service TTFT in milliseconds  
            daily_interactions: Number of daily interactions
            
        Returns:
            Time savings analysis
        """
        improvement_ms = loser_ttft - winner_ttft
        improvement_pct = (improvement_ms / loser_ttft) * 100 if loser_ttft > 0 else 0
        
        # Calculate daily time savings
        daily_seconds_saved = (improvement_ms / 1000) * daily_interactions
        daily_minutes_saved = daily_seconds_saved / 60
        
        # Calculate annual savings
        annual_hours_saved = (daily_minutes_saved / 60) * BusinessImpactAnalyzer.DEFAULT_WORKING_DAYS_PER_YEAR
        
        return TimeSavings(
            improvement_ms=improvement_ms,
            improvement_pct=improvement_pct,
            daily_seconds_saved=daily_seconds_saved,
            daily_minutes_saved=daily_minutes_saved,
            annual_hours_saved=annual_hours_saved
        )
    
    @staticmethod
    def calculate_productivity_impact(
        time_savings: TimeSavings,
        faster_service: str,
        slower_service: str,
        agents_affected: int = DEFAULT_AGENTS_AFFECTED,
        hourly_rate: float = DEFAULT_HOURLY_RATE
    ) -> ProductivityImpact:
        """Calculate productivity and cost impact
        
        Args:
            time_savings: Time savings analysis
            faster_service: Name of faster service
            slower_service: Name of slower service
            agents_affected: Number of agents/users affected
            hourly_rate: Average hourly rate in USD
            
        Returns:
            Productivity impact analysis
        """
        # Per-agent productivity gains
        daily_productivity_gain_minutes = time_savings.daily_minutes_saved
        annual_productivity_gain_hours = time_savings.annual_hours_saved
        
        # Total organizational impact
        total_annual_hours_saved = annual_productivity_gain_hours * agents_affected
        annual_savings_usd = total_annual_hours_saved * hourly_rate
        
        return ProductivityImpact(
            faster_service=faster_service,
            slower_service=slower_service,
            time_advantage=time_savings.improvement_ms,
            interactions_per_day=BusinessImpactAnalyzer.DEFAULT_INTERACTIONS_PER_DAY,
            agents_affected=agents_affected,
            daily_productivity_gain_minutes=daily_productivity_gain_minutes,
            annual_productivity_gain_hours=annual_productivity_gain_hours,
            estimated_hourly_rate=hourly_rate,
            annual_savings_usd=annual_savings_usd
        )
    
    @staticmethod
    def analyze_user_experience_impact(improvement_ms: float) -> UserExperienceImpact:
        """Analyze user experience impact based on latency improvement
        
        Args:
            improvement_ms: Latency improvement in milliseconds
            
        Returns:
            User experience impact analysis
        """
        # Categorize improvement based on research on user perception
        if improvement_ms >= 500:
            ux_category = "Major"
            satisfaction_impact = "Significant increase in user satisfaction"
            abandonment_impact = "Measurable reduction in abandonment rates"
            responsiveness = "Users perceive system as highly responsive"
            competitive = "Strong competitive advantage in user experience"
        elif improvement_ms >= 200:
            ux_category = "Significant"
            satisfaction_impact = "Noticeable improvement in user satisfaction"
            abandonment_impact = "Potential reduction in abandonment rates"
            responsiveness = "Users perceive improved responsiveness"
            competitive = "Competitive advantage in user experience"
        elif improvement_ms >= 100:
            ux_category = "Noticeable"
            satisfaction_impact = "Subtle but measurable improvement"
            abandonment_impact = "Minimal impact on abandonment rates"
            responsiveness = "Slight improvement in perceived responsiveness"
            competitive = "Marginal competitive advantage"
        else:
            ux_category = "Minimal"
            satisfaction_impact = "Minimal user-perceivable improvement"
            abandonment_impact = "No significant impact on abandonment"
            responsiveness = "Barely perceptible improvement"
            competitive = "No significant competitive advantage"
        
        return UserExperienceImpact(
            ux_improvement_category=ux_category,
            user_satisfaction_impact=satisfaction_impact,
            abandonment_rate_impact=abandonment_impact,
            responsiveness_perception=responsiveness,
            competitive_advantage=competitive
        )
    
    @staticmethod
    def generate_impact_summary(race_results: Dict[str, ServicePerformanceProfile],
                               winner: str,
                               custom_params: Optional[Dict] = None) -> BusinessImpactSummary:
        """Generate comprehensive business impact summary
        
        Args:
            race_results: Performance profiles for all services
            winner: Name of winning service
            custom_params: Optional custom business parameters
            
        Returns:
            Complete business impact analysis
        """
        if winner not in race_results:
            raise ValueError(f"Winner {winner} not found in race results")
        
        # Use custom parameters if provided
        params = {
            "daily_interactions": BusinessImpactAnalyzer.DEFAULT_INTERACTIONS_PER_DAY,
            "agents_affected": BusinessImpactAnalyzer.DEFAULT_AGENTS_AFFECTED,
            "hourly_rate": BusinessImpactAnalyzer.DEFAULT_HOURLY_RATE
        }
        if custom_params:
            params.update(custom_params)
        
        # Find comparison service (worst performer)
        winner_ttft = race_results[winner].ttft_stats.mean
        comparison_service = None
        worst_ttft = winner_ttft
        
        for service_name, profile in race_results.items():
            if service_name != winner and profile.ttft_stats.mean > worst_ttft:
                worst_ttft = profile.ttft_stats.mean
                comparison_service = service_name
        
        if not comparison_service:
            # If no worse service, compare with average of others
            other_ttfts = [
                profile.ttft_stats.mean 
                for name, profile in race_results.items() 
                if name != winner and profile.ttft_stats.count > 0
            ]
            worst_ttft = sum(other_ttfts) / len(other_ttfts) if other_ttfts else winner_ttft
            comparison_service = "alternatives"
        
        # Calculate impacts
        time_savings = BusinessImpactAnalyzer.calculate_time_savings(
            winner_ttft, worst_ttft, params["daily_interactions"]
        )
        
        productivity_impact = BusinessImpactAnalyzer.calculate_productivity_impact(
            time_savings, winner, comparison_service,
            params["agents_affected"], params["hourly_rate"]
        )
        
        ux_impact = BusinessImpactAnalyzer.analyze_user_experience_impact(
            time_savings.improvement_ms
        )
        
        # Generate ROI summary
        roi_summary = BusinessImpactAnalyzer._generate_roi_summary(
            productivity_impact, time_savings
        )
        
        # Generate recommendations
        recommendations = BusinessImpactAnalyzer._generate_recommendations(
            race_results, winner, time_savings
        )
        
        return BusinessImpactSummary(
            winner_service=winner,
            time_savings=time_savings,
            productivity_impact=productivity_impact,
            ux_impact=ux_impact,
            roi_summary=roi_summary,
            key_recommendations=recommendations
        )
    
    @staticmethod
    def _generate_roi_summary(productivity_impact: ProductivityImpact, 
                             time_savings: TimeSavings) -> str:
        """Generate ROI summary text"""
        annual_savings = productivity_impact.annual_savings_usd
        
        if annual_savings > 100000:
            return f"High-impact optimization: ${annual_savings:,.0f} annual savings with {time_savings.improvement_pct:.1f}% performance improvement"
        elif annual_savings > 25000:
            return f"Significant value: ${annual_savings:,.0f} annual savings with measurable productivity gains"
        elif annual_savings > 5000:
            return f"Moderate impact: ${annual_savings:,.0f} annual savings with noticeable improvements"
        else:
            return f"Limited financial impact: ${annual_savings:,.0f} annual savings, focus on user experience benefits"
    
    @staticmethod
    def _generate_recommendations(race_results: Dict[str, ServicePerformanceProfile],
                                 winner: str, time_savings: TimeSavings) -> List[str]:
        """Generate actionable recommendations"""
        recommendations = []
        
        winner_profile = race_results[winner]
        
        # Primary recommendation
        recommendations.append(
            f"Deploy {winner.upper()} for production workloads based on {winner_profile.performance_rating.lower()} "
            f"performance ({winner_profile.ttft_stats.mean:.1f}ms TTFT)"
        )
        
        # Reliability recommendation
        if winner_profile.success_rate > 95:
            recommendations.append(
                f"High reliability ({winner_profile.success_rate:.1f}% success rate) makes {winner.upper()} "
                "suitable for production traffic"
            )
        else:
            recommendations.append(
                f"Monitor {winner.upper()} reliability ({winner_profile.success_rate:.1f}% success rate) "
                "and implement fallback strategies"
            )
        
        # Performance optimization
        if time_savings.improvement_ms > 200:
            recommendations.append(
                "Performance advantage is significant - prioritize migration to capture business value"
            )
        elif winner_profile.ttft_stats.mean > 200:
            recommendations.append(
                f"Consider further optimization of {winner.upper()} to achieve sub-200ms TTFT target"
            )
        
        # Capacity planning
        if winner_profile.token_efficiency.avg_tokens_per_second < 30:
            recommendations.append(
                "Monitor token generation efficiency under load and scale resources accordingly"
            )
        
        # Alternative service analysis
        alternative_services = [name for name in race_results.keys() if name != winner]
        if alternative_services:
            best_alternative = max(alternative_services, 
                                 key=lambda x: race_results[x].overall_score)
            recommendations.append(
                f"Consider {best_alternative.upper()} as backup option "
                f"(score: {race_results[best_alternative].overall_score:.2f})"
            )
        
        return recommendations
    
    @staticmethod
    def calculate_infrastructure_roi(current_cost_per_month: float,
                                   new_cost_per_month: float,
                                   productivity_savings_annual: float,
                                   migration_cost_one_time: float = 0) -> Dict[str, float]:
        """Calculate infrastructure ROI including costs
        
        Args:
            current_cost_per_month: Current monthly infrastructure cost
            new_cost_per_month: New infrastructure monthly cost
            productivity_savings_annual: Annual productivity savings
            migration_cost_one_time: One-time migration cost
            
        Returns:
            ROI analysis including payback period
        """
        annual_cost_difference = (new_cost_per_month - current_cost_per_month) * 12
        net_annual_benefit = productivity_savings_annual - annual_cost_difference
        total_investment = migration_cost_one_time + max(0, annual_cost_difference)
        
        # Calculate payback period
        if net_annual_benefit > 0:
            payback_months = total_investment / (net_annual_benefit / 12)
        else:
            payback_months = float('inf')
        
        # Calculate 3-year ROI
        three_year_benefit = net_annual_benefit * 3 - migration_cost_one_time
        three_year_roi = (three_year_benefit / total_investment) * 100 if total_investment > 0 else 0
        
        return {
            "annual_cost_difference": annual_cost_difference,
            "net_annual_benefit": net_annual_benefit,
            "payback_months": payback_months,
            "three_year_roi_percent": three_year_roi,
            "total_investment": total_investment
        }
