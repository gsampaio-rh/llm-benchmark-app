"""
Performance metrics calculation and analysis.

This module provides statistical analysis capabilities for race performance data,
including TTFT analysis, success rates, and performance ratings.
"""

import statistics
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from ..race.models import RaceStatistics, ThreeWayRace


@dataclass
class TTFTStats:
    """Time To First Token statistical analysis"""
    count: int
    mean: float
    median: float
    p95: float
    p99: float
    min: float
    max: float
    std_dev: float
    target_achieved: bool
    target_ms: float = 100.0


@dataclass
class TokenEfficiency:
    """Token generation efficiency metrics"""
    avg_tokens_per_second: float
    avg_tokens_generated: float
    avg_generation_time_ms: float
    efficiency_rating: str


@dataclass
class ServicePerformanceProfile:
    """Comprehensive performance profile for a service"""
    service_name: str
    ttft_stats: TTFTStats
    success_rate: float
    token_efficiency: TokenEfficiency
    reliability_rating: str
    performance_rating: str
    overall_score: float


class PerformanceMetrics:
    """Performance calculation and analysis"""
    
    @staticmethod
    def calculate_ttft_stats(times: List[float], target_ms: float = 100.0) -> TTFTStats:
        """Calculate comprehensive TTFT statistics
        
        Args:
            times: List of TTFT times in milliseconds
            target_ms: Target TTFT threshold
            
        Returns:
            Complete TTFT statistical analysis
        """
        if not times:
            return TTFTStats(
                count=0,
                mean=0.0,
                median=0.0,
                p95=0.0,
                p99=0.0,
                min=0.0,
                max=0.0,
                std_dev=0.0,
                target_achieved=False,
                target_ms=target_ms
            )
        
        sorted_times = sorted(times)
        n = len(sorted_times)
        
        mean_ttft = statistics.mean(sorted_times)
        median_ttft = statistics.median(sorted_times)
        
        # Calculate percentiles
        p95_index = min(int(0.95 * n), n - 1)
        p99_index = min(int(0.99 * n), n - 1)
        p95_ttft = sorted_times[p95_index]
        p99_ttft = sorted_times[p99_index]
        
        std_dev = statistics.stdev(sorted_times) if n > 1 else 0.0
        target_achieved = mean_ttft < target_ms
        
        return TTFTStats(
            count=n,
            mean=mean_ttft,
            median=median_ttft,
            p95=p95_ttft,
            p99=p99_ttft,
            min=min(sorted_times),
            max=max(sorted_times),
            std_dev=std_dev,
            target_achieved=target_achieved,
            target_ms=target_ms
        )
    
    @staticmethod
    def calculate_token_efficiency(token_counts: List[int], times: List[float]) -> TokenEfficiency:
        """Calculate token generation efficiency metrics
        
        Args:
            token_counts: List of token counts generated
            times: List of total generation times in milliseconds
            
        Returns:
            Token efficiency analysis
        """
        if not token_counts or not times or len(token_counts) != len(times):
            return TokenEfficiency(
                avg_tokens_per_second=0.0,
                avg_tokens_generated=0.0,
                avg_generation_time_ms=0.0,
                efficiency_rating="No Data"
            )
        
        avg_tokens = statistics.mean(token_counts)
        avg_time_ms = statistics.mean(times)
        avg_time_seconds = avg_time_ms / 1000
        
        # Calculate tokens per second
        tokens_per_second = avg_tokens / avg_time_seconds if avg_time_seconds > 0 else 0.0
        
        # Determine efficiency rating
        if tokens_per_second >= 50:
            efficiency_rating = "Excellent"
        elif tokens_per_second >= 30:
            efficiency_rating = "Good"
        elif tokens_per_second >= 20:
            efficiency_rating = "Fair"
        else:
            efficiency_rating = "Poor"
        
        return TokenEfficiency(
            avg_tokens_per_second=tokens_per_second,
            avg_tokens_generated=avg_tokens,
            avg_generation_time_ms=avg_time_ms,
            efficiency_rating=efficiency_rating
        )
    
    @staticmethod
    def calculate_success_rate(successful_runs: int, total_runs: int) -> float:
        """Calculate success rate percentage
        
        Args:
            successful_runs: Number of successful runs
            total_runs: Total number of attempted runs
            
        Returns:
            Success rate as percentage (0-100)
        """
        if total_runs == 0:
            return 0.0
        return (successful_runs / total_runs) * 100
    
    @staticmethod
    def get_reliability_rating(success_rate: float) -> str:
        """Get reliability rating based on success rate
        
        Args:
            success_rate: Success rate percentage
            
        Returns:
            Reliability rating string
        """
        if success_rate >= 99:
            return "Excellent"
        elif success_rate >= 95:
            return "Very Good"
        elif success_rate >= 90:
            return "Good"
        elif success_rate >= 80:
            return "Fair"
        else:
            return "Poor"
    
    @staticmethod
    def get_performance_rating(mean_ttft: float) -> str:
        """Get performance rating based on mean TTFT
        
        Args:
            mean_ttft: Mean time to first token in milliseconds
            
        Returns:
            Performance rating string
        """
        if mean_ttft < 100:
            return "Excellent"
        elif mean_ttft < 200:
            return "Very Good"
        elif mean_ttft < 500:
            return "Good"
        elif mean_ttft < 1000:
            return "Fair"
        else:
            return "Poor"
    
    @staticmethod
    def calculate_overall_score(ttft_stats: TTFTStats, success_rate: float, 
                              token_efficiency: TokenEfficiency) -> float:
        """Calculate overall performance score (0-1)
        
        Args:
            ttft_stats: TTFT statistical analysis
            success_rate: Success rate percentage
            token_efficiency: Token efficiency metrics
            
        Returns:
            Overall score from 0.0 to 1.0
        """
        if ttft_stats.count == 0:
            return 0.0
        
        # TTFT score (0-1, higher is better)
        # Perfect score at 50ms, degrading to 0 at 2000ms
        ttft_score = max(0, min(1, (2000 - ttft_stats.mean) / 1950))
        
        # Reliability score (0-1)
        reliability_score = success_rate / 100
        
        # Efficiency score (0-1)
        # Perfect score at 50 tokens/sec, degrading to 0 at 0 tokens/sec
        efficiency_score = min(1, token_efficiency.avg_tokens_per_second / 50)
        
        # Weighted combination
        overall_score = (
            ttft_score * 0.5 +           # TTFT is 50% of score
            reliability_score * 0.3 +     # Reliability is 30% of score
            efficiency_score * 0.2        # Efficiency is 20% of score
        )
        
        return overall_score
    
    @staticmethod
    def analyze_service_performance(stats: RaceStatistics, total_runs: int) -> ServicePerformanceProfile:
        """Create comprehensive performance profile for a service
        
        Args:
            stats: Race statistics for the service
            total_runs: Total number of runs attempted
            
        Returns:
            Complete performance profile
        """
        # Calculate TTFT statistics
        ttft_stats = PerformanceMetrics.calculate_ttft_stats(stats.ttft_times)
        
        # Calculate success rate
        successful_runs = len(stats.ttft_times)
        success_rate = PerformanceMetrics.calculate_success_rate(successful_runs, total_runs)
        
        # Calculate token efficiency
        token_efficiency = PerformanceMetrics.calculate_token_efficiency(
            stats.token_counts, stats.total_times
        )
        
        # Get ratings
        reliability_rating = PerformanceMetrics.get_reliability_rating(success_rate)
        performance_rating = PerformanceMetrics.get_performance_rating(ttft_stats.mean)
        
        # Calculate overall score
        overall_score = PerformanceMetrics.calculate_overall_score(
            ttft_stats, success_rate, token_efficiency
        )
        
        return ServicePerformanceProfile(
            service_name=stats.service_name,
            ttft_stats=ttft_stats,
            success_rate=success_rate,
            token_efficiency=token_efficiency,
            reliability_rating=reliability_rating,
            performance_rating=performance_rating,
            overall_score=overall_score
        )
    
    @staticmethod
    def determine_winner(race: ThreeWayRace, total_runs: int = None) -> Tuple[Optional[str], str]:
        """Determine race winner based on comprehensive analysis
        
        Args:
            race: Race with statistics
            total_runs: Total runs attempted (if None, calculates from statistics)
            
        Returns:
            Tuple of (winner_name, reasoning)
        """
        if not race.statistics:
            return None, "No statistics available"
        
        service_profiles = {}
        
        # Calculate total runs if not provided
        if total_runs is None:
            total_runs = max(
                len(stats.ttft_times) + stats.errors 
                for stats in race.statistics.values()
            )
        
        # Analyze all services
        for service_name, stats in race.statistics.items():
            if stats.ttft_times:  # Only consider services with successful runs
                profile = PerformanceMetrics.analyze_service_performance(stats, total_runs)
                service_profiles[service_name] = profile
        
        if not service_profiles:
            return None, "No successful runs to analyze"
        
        # Find winner based on overall score
        winner = max(service_profiles.keys(), key=lambda x: service_profiles[x].overall_score)
        winner_profile = service_profiles[winner]
        
        # Generate reasoning
        reasoning = f"{winner.upper()} wins with {winner_profile.overall_score:.2f} overall score"
        
        # Add specific strengths
        strengths = []
        if winner_profile.ttft_stats.mean < 200:
            strengths.append(f"excellent TTFT ({winner_profile.ttft_stats.mean:.1f}ms)")
        if winner_profile.success_rate > 95:
            strengths.append(f"high reliability ({winner_profile.success_rate:.1f}%)")
        if winner_profile.token_efficiency.avg_tokens_per_second > 40:
            strengths.append(f"efficient generation ({winner_profile.token_efficiency.avg_tokens_per_second:.1f} tokens/sec)")
        
        if strengths:
            reasoning += f" due to " + ", ".join(strengths)
        
        return winner, reasoning
    
    @staticmethod
    def compare_services(race: ThreeWayRace, total_runs: int = None) -> Dict[str, ServicePerformanceProfile]:
        """Compare all services in a race
        
        Args:
            race: Race with statistics
            total_runs: Total runs attempted
            
        Returns:
            Dictionary of service_name -> ServicePerformanceProfile
        """
        if total_runs is None:
            total_runs = max(
                len(stats.ttft_times) + stats.errors 
                for stats in race.statistics.values()
            ) if race.statistics else 0
        
        profiles = {}
        for service_name, stats in race.statistics.items():
            profiles[service_name] = PerformanceMetrics.analyze_service_performance(stats, total_runs)
        
        return profiles
