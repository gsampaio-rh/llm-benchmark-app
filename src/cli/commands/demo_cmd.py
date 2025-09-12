"""
Unified demo command - consolidates race, conversation, and try-it functionality
Provides interactive demonstrations of vLLM, TGI, and Ollama performance
"""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..utils.console_utils import print_status, show_progress_spinner
from ..utils.async_utils import run_async_command


@click.command()
@click.option("--mode", 
              type=click.Choice(['race', 'conversation', 'interactive'], case_sensitive=False),
              help="Demo mode: race (live performance), conversation (multi-turn), interactive (try-it-yourself)")
@click.option("--scenario", type=int, help="Scenario number for conversation mode (1-5)")
@click.option("--prompt", help="Custom prompt for race mode")
@click.option("--runs", default=1, help="Number of runs for statistical analysis (race mode)")
@click.option("--mock", is_flag=True, help="Use demo mode with simulated responses")
@click.option("--services", help="Comma-separated services to include (vllm,tgi,ollama)")
def demo(mode: Optional[str], scenario: Optional[int], prompt: Optional[str], 
         runs: int, mock: bool, services: Optional[str]):
    """🎭 Interactive demonstrations showing vLLM, TGI, and Ollama performance
    
    Available modes:
    - race: Live three-way performance race with real-time comparison
    - conversation: Multi-turn conversation showing context retention
    - interactive: Try-it-yourself mode where you control the prompts
    
    Examples:
        vllm_benchmark.py demo --mode race --prompt "Explain AI" --runs 3
        vllm_benchmark.py demo --mode conversation --scenario 1
        vllm_benchmark.py demo --mode interactive
        vllm_benchmark.py demo   # Interactive mode selector
    """
    console = Console()
    
    # Show header
    console.print("\n[bold yellow]🎭 INTERACTIVE DEMO SUITE[/bold yellow]")
    console.print("[cyan]Experience the power of different AI inference engines![/cyan]\n")
    
    # Parse services if provided
    service_list = ["vllm", "tgi", "ollama"]
    if services:
        service_list = [s.strip().lower() for s in services.split(",")]
        console.print(f"[blue]🎯 Testing services: {', '.join(service_list.upper())}[/blue]\n")
    
    # Interactive mode selection if no mode specified
    if not mode:
        mode = _show_mode_selector(console)
        if not mode:
            console.print("[yellow]Demo cancelled.[/yellow]")
            return
    
    # Execute the selected demo mode
    if mode == 'race':
        _run_race_demo(console, prompt, runs, mock, service_list)
    elif mode == 'conversation':
        _run_conversation_demo(console, scenario, mock, service_list)
    elif mode == 'interactive':
        _run_interactive_demo(console, mock, service_list)
    else:
        console.print(f"[red]❌ Unknown demo mode: {mode}[/red]")


def _show_mode_selector(console: Console) -> Optional[str]:
    """Show interactive mode selection menu"""
    
    console.print("[bold blue]Select Demo Mode:[/bold blue]")
    
    # Create mode selection table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Mode", style="cyan", width=12)
    table.add_column("Description", style="white")
    table.add_column("Best For", style="green")
    
    table.add_row(
        "1. race", 
        "🏁 Live three-way performance race", 
        "Seeing speed differences in real-time"
    )
    table.add_row(
        "2. conversation", 
        "💬 Multi-turn conversation analysis", 
        "Testing context retention and quality"
    )
    table.add_row(
        "3. interactive", 
        "🎮 Try-it-yourself with custom prompts", 
        "Hands-on exploration and testing"
    )
    
    console.print(table)
    console.print()
    
    # Get user selection
    try:
        choice = console.input("[bold yellow]Enter your choice (1-3) or 'q' to quit: [/bold yellow]")
        
        if choice.lower() == 'q':
            return None
        elif choice == '1':
            return 'race'
        elif choice == '2':
            return 'conversation'
        elif choice == '3':
            return 'interactive'
        else:
            console.print("[red]Invalid choice. Please enter 1, 2, 3, or 'q'[/red]")
            return _show_mode_selector(console)
            
    except (KeyboardInterrupt, EOFError):
        return None


def _run_race_demo(console: Console, prompt: Optional[str], runs: int, mock: bool, services: list):
    """Run the race demo mode"""
    from ...orchestrator import get_orchestrator
    import asyncio
    
    console.print("[bold green]🏁 PERFORMANCE RACE MODE[/bold green]")
    console.print("[cyan]Watch vLLM, TGI, and Ollama compete in real-time![/cyan]\n")
    
    # Use default prompt if none provided
    if not prompt:
        prompt = "Explain transformers in simple terms"
        console.print(f"[blue]Using default prompt: {prompt}[/blue]\n")
    
    # Get orchestrator and run race
    orchestrator = get_orchestrator()
    
    try:
        if mock:
            print_status(console, "Running in demo mode with simulated responses", "info")
        else:
            print_status(console, "Connecting to real AI services...", "info")
        
        # Execute race (async call with correct parameters)
        async def _run_async_race():
            await orchestrator.run_three_way_race(
                prompt=prompt,
                services=services,
                num_runs=runs,
                use_real_apis=not mock
            )
        
        asyncio.run(_run_async_race())
        
    except Exception as e:
        console.print(f"[red]❌ Race demo failed: {str(e)}[/red]")
        if not mock:
            console.print("[yellow]💡 Try adding --mock flag to use simulation mode[/yellow]")


def _run_conversation_demo(console: Console, scenario: Optional[int], mock: bool, services: list):
    """Run the conversation demo mode"""
    from ...orchestrator import get_orchestrator
    import asyncio
    
    console.print("[bold green]💬 CONVERSATION MODE[/bold green]")
    console.print("[cyan]Multi-turn conversations showing context retention![/cyan]\n")
    
    # Map scenario numbers to scenario keys
    scenario_map = {
        1: "customer_support",
        2: "code_review", 
        3: "creative_writing",
        4: "technical_docs",
        5: "business_intelligence"
    }
    
    # Show available scenarios if none specified
    if scenario is None:
        scenario = _show_scenario_selector(console)
        if scenario is None:
            console.print("[yellow]Conversation demo cancelled.[/yellow]")
            return
    
    # Convert scenario number to scenario key
    scenario_key = scenario_map.get(scenario, "customer_support")
    
    # Get orchestrator and run conversation
    orchestrator = get_orchestrator()
    
    try:
        if mock:
            print_status(console, "Running conversation with simulated responses", "info")
        else:
            print_status(console, "Starting conversation with real AI services...", "info")
        
        # Execute conversation (async call with correct parameters)
        async def _run_async_conversation():
            await orchestrator.run_conversation_scenario(
                scenario_key=scenario_key,
                services=services,
                use_real_apis=not mock
            )
        
        asyncio.run(_run_async_conversation())
        
    except Exception as e:
        console.print(f"[red]❌ Conversation demo failed: {str(e)}[/red]")


def _run_interactive_demo(console: Console, mock: bool, services: list):
    """Run the interactive try-it-yourself demo mode"""
    from ...orchestrator import get_orchestrator
    import asyncio
    
    console.print("[bold green]🎮 INTERACTIVE MODE[/bold green]")
    console.print("[cyan]Try it yourself! Enter your own prompts and see the results![/cyan]\n")
    
    # Show predefined prompts for easy testing
    demo_prompts = [
        "Explain transformers in simple terms",
        "How do I debug a Kubernetes pod that won't start?", 
        "Write 3 Python optimization tips",
        "What are the benefits of microservices architecture?",
        "Summarize machine learning in one paragraph"
    ]
    
    console.print("[bold cyan]📝 Choose a prompt or enter your own:[/bold cyan]")
    for i, demo_prompt in enumerate(demo_prompts, 1):
        console.print(f"  {i}. {demo_prompt}")
    console.print("  6. Enter your own prompt")
    
    try:
        choice = console.input("\n[bold yellow]Enter choice (1-6): [/bold yellow]").strip()
        
        prompt = None
        if choice.isdigit() and 1 <= int(choice) <= 5:
            prompt = demo_prompts[int(choice) - 1]
        elif choice == "6":
            prompt = console.input("[yellow]Enter your prompt: [/yellow]").strip()
            if not prompt:
                prompt = demo_prompts[0]  # Default fallback
        else:
            prompt = demo_prompts[0]  # Default fallback
        
        console.print(f"\n[green]🚀 Running interactive race with: {prompt}[/green]")
        
        # Get orchestrator and run interactive race
        orchestrator = get_orchestrator()
        
        async def _run_async_interactive():
            await orchestrator.run_three_way_race(
                prompt=prompt,
                services=services,
                use_real_apis=not mock
            )
        
        asyncio.run(_run_async_interactive())
        
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Interactive demo cancelled by user[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Interactive demo failed: {str(e)}[/red]")


def _show_scenario_selector(console: Console) -> Optional[int]:
    """Show scenario selection for conversation mode"""
    
    console.print("[bold blue]Available Conversation Scenarios:[/bold blue]")
    
    scenarios_table = Table(show_header=True, header_style="bold blue")
    scenarios_table.add_column("ID", style="cyan", width=3)
    scenarios_table.add_column("Scenario", style="white")
    scenarios_table.add_column("Description", style="green")
    
    scenarios_table.add_row("1", "Customer Support", "Kubernetes troubleshooting conversation")
    scenarios_table.add_row("2", "Code Review", "Python function optimization discussion")
    scenarios_table.add_row("3", "Creative Writing", "AI story generation collaboration")
    scenarios_table.add_row("4", "Technical Docs", "Microservices explanation walkthrough")
    scenarios_table.add_row("5", "Business Intelligence", "Cloud provider selection analysis")
    
    console.print(scenarios_table)
    console.print()
    
    try:
        choice = console.input("[bold yellow]Enter scenario number (1-5) or 'q' to quit: [/bold yellow]")
        
        if choice.lower() == 'q':
            return None
        elif choice in ['1', '2', '3', '4', '5']:
            return int(choice)
        else:
            console.print("[red]Invalid choice. Please enter 1-5 or 'q'[/red]")
            return _show_scenario_selector(console)
            
    except (KeyboardInterrupt, EOFError):
        return None
    except ValueError:
        console.print("[red]Invalid input. Please enter a number.[/red]")
        return _show_scenario_selector(console)
