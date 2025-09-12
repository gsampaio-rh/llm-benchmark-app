"""
Clean orchestrator for the refactored vLLM benchmarking system.

This module provides a clean interface for orchestrating conversations and races
using the new modular architecture, replacing the monolithic conversation_viz.py.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .race.engine import RaceEngine
from .race.models import ServicePersonality, ThreeWayRace
from .analytics.metrics import PerformanceMetrics
from .analytics.business_impact import BusinessImpactAnalyzer
from .demo.simulation import DemoSimulator
from .demo.response_generator import DemoResponseGenerator
from .visualization.components.race_display import RaceDisplay
from .conversation.models import ConversationThread, ConversationMessage
from .integrations.api_adapter import APIAdapter
from .integrations.service_adapter import ServiceAdapter, MockDiscoveryProvider
from .integrations.config_manager import ConfigurationManager
from .integrations.error_handling import handle_error


class BenchmarkOrchestrator:
    """Clean orchestrator for benchmarking operations using refactored modules"""
    
    def __init__(self, api_client=None):
        """Initialize the orchestrator with dependencies
        
        Args:
            api_client: Optional API client for real service calls
        """
        self.console = Console()
        
        # Initialize core components
        self.race_engine = RaceEngine(api_client)
        self.demo_simulator = DemoSimulator()
        self.response_generator = DemoResponseGenerator()
        self.race_display = RaceDisplay(self.console)
        self.config_manager = ConfigurationManager()
        
        # API integration
        self.api_adapter = APIAdapter(api_client) if api_client else None
        self.api_client = api_client
        
        # Service discovery
        self.service_adapter = ServiceAdapter(MockDiscoveryProvider())
        self._services_initialized = False
        
        # Define scenarios
        self.scenarios = {
            "customer_support": {
                "title": "🎧 Customer Support Chat",
                "description": "Multi-turn support conversation with technical troubleshooting",
                "prompts": [
                    "My Kubernetes pod won't start, can you help me debug it?",
                    "I'm getting a 'ImagePullBackOff' error, what does this mean?",
                    "How do I check the logs for a failed deployment?",
                    "My service is returning 503 errors, what should I check?"
                ]
            },
            "code_review": {
                "title": "👨‍💻 Code Review Session",
                "description": "Technical code analysis and optimization suggestions",
                "prompts": [
                    "Review this Python function for potential improvements:\n\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
                    "Is this API endpoint secure? What security issues do you see?",
                    "How can I optimize this database query for better performance?",
                    "What testing strategy would you recommend for this microservice?"
                ]
            },
            "creative_writing": {
                "title": "✍️ Creative Writing Workshop", 
                "description": "Creative storytelling and brainstorming session",
                "prompts": [
                    "Write a short story about an AI that discovers it can dream",
                    "Help me brainstorm ideas for a sci-fi novel about quantum computing",
                    "Create a dialogue between two characters arguing about technology ethics",
                    "Write a poem about the relationship between humans and artificial intelligence"
                ]
            },
            "technical_docs": {
                "title": "📚 Technical Documentation",
                "description": "Technical explanation and documentation writing",
                "prompts": [
                    "Explain microservices architecture to a junior developer",
                    "What are the key differences between REST and GraphQL APIs?",
                    "How does Kubernetes handle container orchestration?",
                    "Describe the benefits and challenges of event-driven architecture"
                ]
            },
            "business_intelligence": {
                "title": "📊 Business Intelligence",
                "description": "Strategic analysis and business decision support",
                "prompts": [
                    "What factors should we consider when choosing a cloud provider?",
                    "Analyze the ROI of implementing AI automation in customer service",
                    "Compare the benefits of build vs buy for our data analytics platform",
                    "What are the key metrics for measuring software development productivity?"
                ]
            }
        }
    
    def display_scenario_menu(self):
        """Display the scenario selection menu"""
        menu_text = Text()
        menu_text.append("🎭 Choose Your Live Conversation Theater Scenario:\n\n", style="bold blue")
        
        for i, (key, scenario) in enumerate(self.scenarios.items(), 1):
            menu_text.append(f"{i}. ", style="bold white")
            menu_text.append(f"{scenario['title']}\n", style="bold cyan")
            menu_text.append(f"   {scenario['description']}\n\n", style="dim")
        
        menu_text.append("💡 ", style="bold yellow")
        menu_text.append("Usage: ", style="bold white")
        menu_text.append("python vllm_benchmark.py demo <scenario_number>\n", style="dim")
        
        menu_text.append("📖 ", style="bold green")
        menu_text.append("Example: ", style="bold white")
        menu_text.append("python vllm_benchmark.py demo 1", style="dim")
        
        panel = Panel(
            menu_text,
            title="🎬 Live Conversation Theater",
            border_style="magenta"
        )
        
        self.console.print(panel)
    
    async def run_conversation_scenario(self, scenario_key: str, prompt_index: int = 0,
                                      services: Optional[List[str]] = None,
                                      multi_turn: bool = False,
                                      use_real_apis: bool = True):
        """Run a conversation scenario using the new modular architecture
        
        Args:
            scenario_key: Key of the scenario to run
            prompt_index: Index of the prompt to use
            services: List of services to include
            multi_turn: Whether to run multiple conversation turns
            use_real_apis: Whether to use real APIs or demo mode
        """
        if scenario_key not in self.scenarios:
            self.console.print(f"[red]❌ Unknown scenario: {scenario_key}[/red]")
            return
        
        scenario = self.scenarios[scenario_key]
        services = services or ["vllm", "tgi", "ollama"]
        
        # Get the prompt
        prompts = scenario["prompts"]
        if prompt_index >= len(prompts):
            prompt_index = 0
        prompt = prompts[prompt_index]
        
        self.console.print(f"\n[bold blue]🎭 {scenario['title']}[/bold blue]")
        self.console.print(f"[dim]{scenario['description']}[/dim]\n")
        
        try:
            # Initialize real services if not using mock mode
            if use_real_apis:
                services_ready = await self.initialize_real_services()
                if not services_ready:
                    self.console.print("[yellow]🎪 Continuing with demo mode[/yellow]")
                    use_real_apis = False
            
            if use_real_apis and self.api_adapter:
                # Use real APIs
                await self._run_real_conversation_scenario(prompt, services, multi_turn)
            else:
                # Use demo simulation
                await self._run_demo_conversation_scenario(prompt, services, multi_turn)
        
        except Exception as e:
            error_details = handle_error(e, "conversation_scenario", "orchestrator")
            self.console.print(f"[red]❌ {error_details.user_message}[/red]")
            self.console.print(f"[dim]💡 Suggested actions: {', '.join(error_details.suggested_actions)}[/dim]")
    
    async def _run_real_conversation_scenario(self, prompt: str, services: List[str], multi_turn: bool):
        """Run conversation scenario with real APIs"""
        self.console.print("[bold green]🌐 Using Real AI Services[/bold green]\n")
        
        # Create conversation thread
        thread = ConversationThread(
            thread_id=f"real_{hash(prompt)}",
            title="Real API Conversation",
            scenario="real_api"
        )
        
        # Add user message
        user_msg = ConversationMessage(
            role="user",
            content=prompt,
            timestamp=asyncio.get_event_loop().time()
        )
        thread.add_message(user_msg)
        
        # Get responses from each service
        for service_name in services:
            try:
                self.console.print(f"[cyan]🔄 Getting response from {service_name.upper()}...[/cyan]")
                
                # Create request
                from .api_clients import create_chat_request
                request = create_chat_request(prompt)
                
                # Stream response
                response_content = ""
                async for token in self.api_adapter.stream_response(service_name, request):
                    response_content += token
                
                # Add response to thread
                response_msg = ConversationMessage(
                    role="assistant",
                    content=response_content.strip(),
                    timestamp=asyncio.get_event_loop().time(),
                    service_name=service_name
                )
                thread.add_message(response_msg)
                
                self.console.print(f"[green]✅ {service_name.upper()} completed[/green]")
                
            except Exception as e:
                error_details = handle_error(e, f"api_call_{service_name}", "orchestrator")
                self.console.print(f"[red]❌ {service_name.upper()} failed: {error_details.user_message}[/red]")
        
        # Display results
        self._display_conversation_results(thread)
    
    async def _run_demo_conversation_scenario(self, prompt: str, services: List[str], multi_turn: bool):
        """Run conversation scenario with demo simulation"""
        self.console.print("[bold yellow]🎪 Using Demo Simulation[/bold yellow]\n")
        
        # Use demo simulator for realistic responses
        results = await self.demo_simulator.run_multi_service_comparison(prompt, services)
        
        # Create conversation thread  
        thread = ConversationThread(
            thread_id=f"demo_{hash(prompt)}",
            title="Demo Conversation",
            scenario="demo"
        )
        
        # Add user message
        user_msg = ConversationMessage(
            role="user",
            content=prompt,
            timestamp=asyncio.get_event_loop().time()
        )
        thread.add_message(user_msg)
        
        # Add service responses
        for service_name, result in results.items():
            if result["success"]:
                response_msg = ConversationMessage(
                    role="assistant",
                    content=result["response"],
                    timestamp=asyncio.get_event_loop().time(),
                    service_name=service_name,
                    response_time_ms=result["ttft_ms"],
                    token_count=result["token_count"]
                )
                thread.add_message(response_msg)
                self.console.print(f"[green]✅ {service_name.upper()} - {result['ttft_ms']:.1f}ms TTFT[/green]")
            else:
                self.console.print(f"[red]❌ {service_name.upper()} failed: {result['error']}[/red]")
        
        # Display results
        self._display_conversation_results(thread)
    
    def _display_conversation_results(self, thread: ConversationThread):
        """Display conversation results in a nice format"""
        self.console.print(f"\n[bold blue]💬 Conversation Results ({thread.title})[/bold blue]\n")
        
        for message in thread.messages:
            if message.role == "user":
                self.console.print(f"[bold white]👤 User:[/bold white] {message.content}\n")
            else:
                service_name = message.service_name or "Unknown"
                service_color = {"vllm": "blue", "tgi": "green", "ollama": "orange3"}.get(service_name, "white")
                
                metrics_text = ""
                if message.response_time_ms:
                    metrics_text = f" ({message.response_time_ms:.1f}ms TTFT"
                    if message.token_count:
                        metrics_text += f", {message.token_count} tokens"
                    metrics_text += ")"
                
                self.console.print(f"[bold {service_color}]🤖 {service_name.upper()}:{metrics_text}[/bold {service_color}]")
                self.console.print(f"{message.content}\n")
    
    async def run_three_way_race(self, prompt: str, services: Optional[List[str]] = None,
                               rapid_fire: bool = False, crowd_rush: bool = False,
                               num_runs: int = 1, use_real_apis: bool = True):
        """Run a three-way performance race using the new architecture
        
        Args:
            prompt: Prompt to race with
            services: List of services to include
            rapid_fire: Whether to run rapid-fire mode
            crowd_rush: Whether to simulate crowd rush
            num_runs: Number of runs (>1 automatically enables statistical analysis)
            use_real_apis: Whether to use real APIs
        """
        services = services or ["vllm", "tgi", "ollama"]
        
        self.console.print(f"\n[bold blue]🏁 Three-Way Performance Race[/bold blue]")
        self.console.print(f"[cyan]Services: {', '.join(s.upper() for s in services)}[/cyan]")
        self.console.print(f"[dim]Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}[/dim]\n")
        
        try:
            # Initialize real services if not using mock mode
            if use_real_apis:
                services_ready = await self.initialize_real_services()
                if not services_ready:
                    self.console.print("[yellow]🎪 Continuing with demo mode[/yellow]")
                    use_real_apis = False
            
            if num_runs > 1:
                await self._run_statistical_race(prompt, services, num_runs, use_real_apis)
            else:
                await self._run_single_race(prompt, services, use_real_apis)
        
        except Exception as e:
            error_details = handle_error(e, "three_way_race", "orchestrator")
            self.console.print(f"[red]❌ {error_details.user_message}[/red]")
            self.console.print(f"[dim]💡 Suggested actions: {', '.join(error_details.suggested_actions)}[/dim]")
    
    async def _run_single_race(self, prompt: str, services: List[str], use_real_apis: bool):
        """Run a single race iteration"""
        if use_real_apis and self.api_adapter:
            # Create race with real API integration
            self.console.print("[cyan]📡 Fetching real engine configurations...[/cyan]")
            race = await self.race_engine.create_real_race(prompt, services)
            self.console.print("[bold green]🌐 Running with Real APIs[/bold green]\n")
            
            # Execute with race display
            await self.race_display.run_live_race(race, self.api_adapter)
        else:
            # Create demo race
            race = self.race_engine.create_demo_race(prompt, services)
            self.console.print("[bold yellow]🎪 Running Demo Race[/bold yellow]\n")
            
            # Execute with live race display (even for demo mode)
            await self.race_display.run_live_race(race, None)
    
    async def _run_statistical_race(self, prompt: str, services: List[str], num_runs: int, use_real_apis: bool):
        """Run multiple race iterations for statistical analysis"""
        self.console.print(f"[bold cyan]📊 Statistical Analysis Mode[/bold cyan]")
        self.console.print(f"[yellow]Running {num_runs} iterations for robust performance analysis...[/yellow]\n")
        
        # Collect all race results
        all_results = []
        all_races = []
        
        for run_number in range(1, num_runs + 1):
            self.console.print(f"[bold]🏃‍♂️ Run {run_number}/{num_runs}[/bold]")
            
            # Create and run a single race WITH LIVE VISUALIZATION
            if use_real_apis and self.api_adapter:
                self.console.print("[cyan]📡 Fetching real engine configurations...[/cyan]")
                race = await self.race_engine.create_real_race(prompt, services)
                # Show live race display for this run
                await self.race_display.run_live_race(race, self.api_adapter)
            else:
                race = self.race_engine.create_demo_race(prompt, services)
                # Show live race display for this run  
                await self.race_display.run_live_race(race, None)
            
            # Determine winner for this run (race already executed by display)
            winner = race.determine_winner()
            result_time = time.time() - race.start_time
            
            # Create a simple result object for tracking
            class RunResult:
                def __init__(self, race, winner, time):
                    self.race = race
                    self.winner = winner 
                    self.execution_time = time
                    self.success = True
            
            result = RunResult(race, winner, result_time)
            all_results.append(result)
            all_races.append(race)
            
            # Show quick result for this run
            if winner:
                self.console.print(f"[green]🏆 Run {run_number} Winner: {winner.upper()}[/green]")
            else:
                self.console.print(f"[yellow]⚠️  Run {run_number}: No clear winner[/yellow]")
            
            self.console.print("\n" + "="*60 + "\n")
        
        # Pause before showing statistical analysis
        self.console.print("\n[bold cyan]🏁 All races completed![/bold cyan]")
        self.console.print("[dim]Press Enter to view statistical analysis and performance insights...[/dim]")
        
        # Wait for user input
        try:
            input()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Statistical analysis skipped by user[/yellow]")
            return
        
        # Show final summary with statistics
        await self._show_statistical_summary(all_races, all_results, prompt, num_runs)
    
    async def _show_statistical_summary(self, races: List, results: List, prompt: str, num_runs: int):
        """Show comprehensive statistical summary with press-to-continue"""
        from .analytics.metrics import PerformanceMetrics
        from .analytics.business_impact import BusinessImpactAnalyzer
        from rich.table import Table
        from rich.panel import Panel
        import statistics
        
        self.console.print("\n" + "="*80)
        self.console.print("[bold green]📊 STATISTICAL ANALYSIS RESULTS[/bold green]")
        self.console.print("="*80)
        
        # Calculate statistics for each service
        service_stats = {}
        for service in ["vllm", "tgi", "ollama"]:
            ttft_times = []
            total_times = []
            wins = 0
            
            for race in races:
                if service in race.participants:
                    participant = race.participants[service]
                    if participant.first_token_time and participant.response_start_time:
                        ttft_ms = (participant.first_token_time - participant.response_start_time) * 1000
                        ttft_times.append(ttft_ms)
                    
                    if participant.first_token_time and participant.is_complete:
                        # Calculate total time based on response length or tokens
                        total_time = (time.time() - participant.response_start_time) * 1000 if participant.response_start_time else 0
                        total_times.append(total_time)
                
                # Check if this service won this race
                if hasattr(race, 'winner') and race.winner == service:
                    wins += 1
            
            service_stats[service] = {
                'ttft_times': ttft_times,
                'total_times': total_times,
                'wins': wins,
                'success_rate': len(ttft_times) / num_runs * 100 if num_runs > 0 else 0
            }
        
        # Create detailed statistical summary table 
        table = Table(title=f"🏆 Performance Statistics ({num_runs} runs)")
        table.add_column("Service", style="bold")
        table.add_column("Mean TTFT", style="cyan")
        table.add_column("P95 TTFT", style="yellow")
        table.add_column("Min/Max", style="green")
        table.add_column("Std Dev", style="magenta")
        table.add_column("Success Rate", style="blue")
        table.add_column("Winner Score", style="bright_green")
        
        # Calculate winner scores (based on average ranking across metrics)
        service_rankings = {}
        for service, stats in service_stats.items():
            if stats['ttft_times']:
                avg_ttft = statistics.mean(stats['ttft_times'])
                service_rankings[service] = avg_ttft
        
        # Sort by performance for scoring
        sorted_services = sorted(service_rankings.items(), key=lambda x: x[1])
        
        for service, stats in service_stats.items():
            if stats['ttft_times']:
                avg_ttft = statistics.mean(stats['ttft_times'])
                p95_ttft = sorted(stats['ttft_times'])[int(len(stats['ttft_times']) * 0.95)] if len(stats['ttft_times']) >= 20 else max(stats['ttft_times'])
                min_ttft = min(stats['ttft_times'])
                max_ttft = max(stats['ttft_times'])
                std_dev = statistics.stdev(stats['ttft_times']) if len(stats['ttft_times']) > 1 else 0
                
                # Calculate winner score (10 = best, 1 = worst)
                service_rank = next(i for i, (s, _) in enumerate(sorted_services) if s == service)
                winner_score = 10 - (service_rank * 3)  # 10, 7, 4, 1...
                
                # Add emoji to service name
                service_emoji = {"vllm": "🔵", "tgi": "🟢", "ollama": "🟠"}.get(service, "")
                
                table.add_row(
                    f"{service_emoji} {service.upper()}",
                    f"{avg_ttft:.0f}ms",
                    f"{p95_ttft:.0f}ms", 
                    f"{min_ttft:.0f}/{max_ttft:.0f}ms",
                    f"{std_dev:.1f}ms",
                    f"{stats['success_rate']:.1f}%",
                    f"{winner_score:.1f}"
                )
            else:
                table.add_row(
                    f"{service.upper()}",
                    "No data",
                    "No data",
                    "No data",
                    "No data",
                    f"{stats['success_rate']:.1f}%",
                    "0.0"
                )
        
        self.console.print(table)
        
        # Determine overall winner and detailed analysis
        overall_winner = max(service_stats.keys(), key=lambda s: service_stats[s]['wins'])
        self.console.print(f"\n[bold green]🏆 STATISTICAL WINNER: 🔵 {overall_winner.upper()}[/bold green]")
        
        # Calculate detailed performance comparisons
        fastest_service = min(service_stats.keys(), key=lambda s: statistics.mean(service_stats[s]['ttft_times']) if service_stats[s]['ttft_times'] else float('inf'))
        fastest_avg = statistics.mean(service_stats[fastest_service]['ttft_times']) if service_stats[fastest_service]['ttft_times'] else 0
        
        # Performance differences
        performance_differences = []
        for service, stats in service_stats.items():
            if service != fastest_service and stats['ttft_times']:
                avg_ttft = statistics.mean(stats['ttft_times'])
                p95_ttft = sorted(stats['ttft_times'])[int(len(stats['ttft_times']) * 0.95)] if len(stats['ttft_times']) >= 20 else max(stats['ttft_times'])
                fastest_p95 = sorted(service_stats[fastest_service]['ttft_times'])[int(len(service_stats[fastest_service]['ttft_times']) * 0.95)] if len(service_stats[fastest_service]['ttft_times']) >= 20 else max(service_stats[fastest_service]['ttft_times'])
                
                avg_diff = avg_ttft - fastest_avg
                p95_diff = p95_ttft - fastest_p95
                performance_differences.append(f"• {fastest_service.upper()} is {avg_diff:.0f}ms faster than {service.upper()} (P95: {p95_diff:.0f}ms advantage)")
        
        # Calculate consistency analysis
        consistency_analysis = []
        for service, stats in service_stats.items():
            if stats['ttft_times'] and len(stats['ttft_times']) > 1:
                std_dev = statistics.stdev(stats['ttft_times'])
                consistency_analysis.append(f"• {service.upper()} std deviation: {std_dev:.1f}ms")
        
        # Find most consistent service
        most_consistent = min(service_stats.keys(), 
                            key=lambda s: statistics.stdev(service_stats[s]['ttft_times']) if service_stats[s]['ttft_times'] and len(service_stats[s]['ttft_times']) > 1 else float('inf'))
        
        # Calculate ROI (simplified business calculation)
        daily_requests = 10000
        time_saved_per_request = fastest_avg / 1000  # Convert to seconds
        time_saved_daily = (time_saved_per_request * daily_requests) / 60  # minutes
        hourly_rate = 50  # $50/hour productivity value
        annual_value = time_saved_daily * (hourly_rate / 60) * 365
        
        # P95 performance target
        p95_target = 200  # ms
        fastest_p95 = sorted(service_stats[fastest_service]['ttft_times'])[int(len(service_stats[fastest_service]['ttft_times']) * 0.95)] if len(service_stats[fastest_service]['ttft_times']) >= 20 else max(service_stats[fastest_service]['ttft_times'])
        
        # Create comprehensive business impact summary
        business_content = f"[bold]💼 Statistical Business Impact Analysis[/bold]\n"
        business_content += f"[bold]📊 Based on {num_runs} statistically significant runs:[/bold]\n\n"
        
        # Performance differences
        if performance_differences:
            business_content += "\n".join(performance_differences) + "\n\n"
        
        business_content += f"[bold]🎯 Consistency Analysis:[/bold]\n"
        if consistency_analysis:
            business_content += "\n".join(consistency_analysis) + "\n"
        business_content += f"• {most_consistent.upper()} std deviation: {statistics.stdev(service_stats[most_consistent]['ttft_times']) if service_stats[most_consistent]['ttft_times'] and len(service_stats[most_consistent]['ttft_times']) > 1 else 0:.1f}ms (most consistent)\n"
        business_content += f"• P95 performance target (<{p95_target}ms): {fastest_service.upper()} achieves {fastest_p95:.0f}ms\n\n"
        
        business_content += f"[bold]💰 Annual ROI ({daily_requests:,} daily requests):[/bold]\n"
        business_content += f"• Time saved: {time_saved_daily:.1f} minutes/day\n"
        business_content += f"• Productivity value: ${annual_value:,.0f}/year\n\n"
        
        business_content += f"[bold]✅ Statistical Confidence:[/bold] {num_runs} runs provide robust performance baseline"
        
        impact_panel = Panel(
            business_content,
            title="📊 Statistical Business Value",
            border_style="green"
        )
        
        self.console.print("\n")
        self.console.print(impact_panel)
        
        # The cool "press Enter" feature!
        self.console.print("\n[bold cyan]📋 Detailed analysis ready![/bold cyan]")
        self.console.print("[dim]Press Enter to view detailed breakdown and recommendations...[/dim]")
        
        # Wait for user input
        try:
            input()
        except KeyboardInterrupt:
            self.console.print("\n[yellow]Analysis skipped by user[/yellow]")
            return
        
        # Show detailed breakdown
        self.console.print("\n" + "="*80)
        self.console.print("[bold]🔬 DETAILED PERFORMANCE BREAKDOWN[/bold]")
        self.console.print("="*80)
        
        for service, stats in service_stats.items():
            if stats['ttft_times']:
                self.console.print(f"\n[bold]{service.upper()} Service Analysis:[/bold]")
                self.console.print(f"  • Completed: {len(stats['ttft_times'])}/{num_runs} races ({stats['success_rate']:.1f}%)")
                self.console.print(f"  • Average TTFT: {statistics.mean(stats['ttft_times']):.1f}ms")
                self.console.print(f"  • Standard deviation: {statistics.stdev(stats['ttft_times']):.1f}ms" if len(stats['ttft_times']) > 1 else "  • Standard deviation: N/A")
                self.console.print(f"  • Wins: {stats['wins']} ({stats['wins']/num_runs*100:.1f}%)")
                
                # Performance category
                avg_ttft = statistics.mean(stats['ttft_times'])
                if avg_ttft < 500:
                    category = "[green]Excellent[/green]"
                elif avg_ttft < 1000:
                    category = "[yellow]Good[/yellow]"
                elif avg_ttft < 2000:
                    category = "[red]Fair[/red]"
                else:
                    category = "[red]Needs Improvement[/red]"
                
                self.console.print(f"  • Performance: {category}")
        
        self.console.print(f"\n[bold green]✅ Statistical analysis complete![/bold green]")
        self.console.print(f"[dim]Data from {num_runs} race iterations with prompt: '{prompt[:50]}{'...' if len(prompt) > 50 else ''}'[/dim]")
    
    def _display_race_results(self, result):
        """Display single race results"""
        if not result.success:
            self.console.print(f"[red]❌ Race failed: {result.error_message}[/red]")
            return
        
        self.console.print(f"[bold green]🏆 Race Complete![/bold green]")
        self.console.print(f"[cyan]Winner: {result.winner.upper() if result.winner else 'No clear winner'}[/cyan]")
        self.console.print(f"[dim]Execution time: {result.execution_time:.2f}s[/dim]\n")
        
        # Show TTFT rankings
        for rank, (service_name, ttft_ms) in enumerate(result.ttft_rankings, 1):
            rank_color = "green" if rank == 1 else "yellow" if rank == 2 else "red"
            self.console.print(f"[{rank_color}]{rank}. {service_name.upper()}: {ttft_ms:.1f}ms TTFT[/{rank_color}]")
    
    def _display_statistical_results(self, stats_result, profiles, winner, reasoning):
        """Display statistical analysis results"""
        self.console.print(f"[bold green]📊 Statistical Analysis Complete![/bold green]")
        self.console.print(f"[cyan]Successful runs: {stats_result.successful_runs}/{stats_result.total_runs}[/cyan]")
        
        if winner:
            self.console.print(f"[bold green]🏆 Overall Winner: {winner.upper()}[/bold green]")
            self.console.print(f"[dim]Reasoning: {reasoning}[/dim]\n")
        
        # Display performance profiles
        for service_name, profile in profiles.items():
            ttft = profile.ttft_stats
            efficiency = profile.token_efficiency
            
            self.console.print(f"[bold cyan]{service_name.upper()}[/bold cyan]")
            self.console.print(f"  TTFT: {ttft.mean:.1f}ms (P95: {ttft.p95:.1f}ms)")
            self.console.print(f"  Success Rate: {profile.success_rate:.1f}%")
            self.console.print(f"  Performance Rating: {profile.performance_rating}")
            self.console.print(f"  Overall Score: {profile.overall_score:.2f}\n")
    
    # Convenience methods for backward compatibility
    @property
    def available_scenarios(self) -> List[str]:
        """Get list of available scenario keys"""
        return list(self.scenarios.keys())
    
    def get_scenario_prompts(self, scenario_key: str) -> List[str]:
        """Get prompts for a specific scenario"""
        return self.scenarios.get(scenario_key, {}).get("prompts", [])
    
    async def initialize_real_services(self, namespace: str = "vllm-benchmark") -> bool:
        """Initialize real service connections
        
        Args:
            namespace: Kubernetes namespace to discover services in
            
        Returns:
            True if services were successfully initialized, False otherwise
        """
        if self._services_initialized:
            return True
        
        try:
            self.console.print("[cyan]🔍 Discovering available services...[/cyan]")
            
            # Use real service discovery instead of mock
            from .service_discovery import discover_services
            from .api_clients import UnifiedAPIClient
            
            # Discover services
            services = await discover_services(namespace=namespace)
            
            if not services:
                self.console.print("[yellow]⚠️  No services discovered, falling back to demo mode[/yellow]")
                return False
            
            self.console.print(f"[green]✅ Found {len(services)} services[/green]")
            
            # Create service URLs dictionary for healthy services
            service_urls = {}
            for service_name, service_info in services.items():
                if service_info.status in ["healthy", "responding"]:
                    service_urls[service_name] = service_info.url
                    self.console.print(f"[green]  ✅ {service_name.upper()}: {service_info.url}[/green]")
                else:
                    self.console.print(f"[yellow]  ⚠️  {service_name.upper()}: {service_info.status}[/yellow]")
            
            # Create unified API client with service URLs
            if service_urls:
                self.api_client = UnifiedAPIClient(service_urls)
            else:
                self.api_client = None
            
            # Create API adapter with the unified client
            if self.api_client:
                self.api_adapter = APIAdapter(self.api_client)
                self.race_engine = RaceEngine(self.api_client)  # Update race engine with real client
                self._services_initialized = True
                return True
            else:
                self.console.print("[yellow]⚠️  No healthy services found, falling back to demo mode[/yellow]")
                return False
        
        except Exception as e:
            error_details = handle_error(e, "service_initialization", "orchestrator")
            self.console.print(f"[red]❌ Service discovery failed: {error_details.user_message}[/red]")
            self.console.print("[yellow]🎪 Falling back to demo mode[/yellow]")
            return False


# Create global instance for backward compatibility
_orchestrator = None

def get_orchestrator(api_client=None) -> BenchmarkOrchestrator:
    """Get global orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = BenchmarkOrchestrator(api_client)
    return _orchestrator
