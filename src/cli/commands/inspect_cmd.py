"""
Inspect command - Deep technical inspection  
Shows API payloads and technical details
"""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.syntax import Syntax
from rich.panel import Panel

from ..utils.console_utils import print_status


@click.command()
@click.option("--scenario", type=int, help="Scenario number to inspect (1-5)")
@click.option("--prompt", help="Custom prompt to inspect")
@click.option("--service", help="Specific service to inspect (vllm, tgi, ollama)")
@click.option("--mock", is_flag=True, help="Use demo mode for inspection")
def inspect(scenario: Optional[int], prompt: Optional[str], service: Optional[str], mock: bool):
    """Deep technical inspection showing API payloads and streaming responses
    
    This command provides detailed technical analysis of how each service
    handles requests, showing raw API payloads, streaming responses, and
    performance characteristics.
    
    Examples:
        vllm_benchmark.py inspect --scenario 1
        vllm_benchmark.py inspect --prompt "Explain AI" --service vllm
        vllm_benchmark.py inspect --mock  # Demo mode
    """
    console = Console()
    
    console.print("\n[bold blue]🔍 TECHNICAL INSPECTION MODE[/bold blue]")
    console.print("[cyan]Deep dive into API payloads and streaming responses[/cyan]\n")
    
    # Determine what to inspect
    if scenario:
        _inspect_scenario(console, scenario, mock)
    elif prompt:
        _inspect_prompt(console, prompt, service, mock)
    else:
        _show_inspection_menu(console, mock)


def _show_inspection_menu(console: Console, mock: bool):
    """Show interactive inspection menu"""
    console.print("[bold blue]Select Inspection Mode:[/bold blue]")
    
    from rich.table import Table
    table = Table(show_header=True, header_style="bold blue")
    table.add_column("Option", style="cyan", width=8)
    table.add_column("Description", style="white")
    table.add_column("Focus", style="green")
    
    table.add_row("1", "API Payload Comparison", "Request/Response structures")
    table.add_row("2", "Streaming Analysis", "Token-by-token generation")
    table.add_row("3", "Error Handling", "Failure modes and recovery")
    table.add_row("4", "Performance Profiling", "Timing and resource usage")
    table.add_row("5", "Custom Prompt", "Your own prompt inspection")
    
    console.print(table)
    console.print()
    
    try:
        choice = console.input("[bold yellow]Enter your choice (1-5) or 'q' to quit: [/bold yellow]")
        
        if choice.lower() == 'q':
            return
        elif choice == '1':
            _inspect_api_payloads(console, mock)
        elif choice == '2':
            _inspect_streaming(console, mock)
        elif choice == '3':
            _inspect_error_handling(console, mock)
        elif choice == '4':
            _inspect_performance(console, mock)
        elif choice == '5':
            prompt = console.input("[yellow]Enter your prompt: [/yellow]")
            _inspect_prompt(console, prompt, None, mock)
        else:
            console.print("[red]Invalid choice[/red]")
            _show_inspection_menu(console, mock)
            
    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Inspection cancelled[/yellow]")


def _inspect_scenario(console: Console, scenario: int, mock: bool):
    """Inspect a predefined scenario"""
    scenarios = {
        1: {
            "name": "Customer Support",
            "prompt": "How do I fix a Kubernetes pod that won't start?",
            "description": "Technical troubleshooting conversation"
        },
        2: {
            "name": "Code Review", 
            "prompt": "Review this Python function for optimization opportunities",
            "description": "Code analysis and improvement suggestions"
        },
        3: {
            "name": "Creative Writing",
            "prompt": "Write a short story about AI helping humanity",
            "description": "Creative content generation"
        },
        4: {
            "name": "Technical Docs",
            "prompt": "Explain microservices architecture benefits and challenges",
            "description": "Technical explanation and documentation"
        },
        5: {
            "name": "Business Intelligence",
            "prompt": "What factors should we consider when choosing a cloud provider?",
            "description": "Strategic analysis and decision support"
        }
    }
    
    if scenario not in scenarios:
        console.print(f"[red]❌ Invalid scenario: {scenario}. Choose 1-5.[/red]")
        return
    
    scenario_data = scenarios[scenario]
    console.print(f"[bold green]📋 Inspecting Scenario {scenario}: {scenario_data['name']}[/bold green]")
    console.print(f"[cyan]Description:[/cyan] {scenario_data['description']}")
    console.print(f"[cyan]Prompt:[/cyan] {scenario_data['prompt']}\n")
    
    _inspect_prompt(console, scenario_data['prompt'], None, mock)


def _inspect_prompt(console: Console, prompt: str, service: Optional[str], mock: bool):
    """Inspect a specific prompt across services"""
    console.print(f"[bold blue]🔍 Inspecting Prompt:[/bold blue] {prompt}")
    
    if mock:
        print_status(console, "Running in demo mode with simulated data", "info")
        _show_mock_inspection(console, prompt, service)
    else:
        print_status(console, "Connecting to real services for inspection...", "info")
        asyncio.run(_run_real_inspection(console, prompt, service))


def _show_mock_inspection(console: Console, prompt: str, service: Optional[str]):
    """Show simulated inspection data"""
    services = ['vllm', 'tgi', 'ollama'] if not service else [service]
    
    for svc in services:
        console.print(f"\n[bold cyan]🔧 {svc.upper()} API INSPECTION[/bold cyan]")
        
        # Show request payload
        request_payload = _generate_mock_request(svc, prompt)
        console.print(Panel(
            Syntax(request_payload, "json", theme="monokai"),
            title=f"[bold blue]📤 {svc.upper()} Request Payload[/bold blue]",
            border_style="blue"
        ))
        
        # Show response metadata
        response_meta = _generate_mock_response_meta(svc)
        console.print(Panel(
            response_meta,
            title=f"[bold green]📥 {svc.upper()} Response Metadata[/bold green]",
            border_style="green"
        ))
        
        # Show streaming simulation
        console.print(f"[yellow]🌊 {svc.upper()} Streaming Simulation:[/yellow]")
        _simulate_streaming_response(console, svc)


async def _run_real_inspection(console: Console, prompt: str, service: Optional[str]):
    """Run real inspection with actual services"""
    try:
        # Import here to avoid circular imports
        from ...orchestrator import get_orchestrator
        
        orchestrator = get_orchestrator()
        
        # Initialize real services
        if await orchestrator.initialize_real_services():
            console.print("[green]✅ Connected to real services[/green]")
            
            # Run inspection with real APIs
            await orchestrator.run_api_inspection(prompt, service)
        else:
            console.print("[yellow]⚠️ Could not connect to real services, falling back to demo mode[/yellow]")
            _show_mock_inspection(console, prompt, service)
            
    except Exception as e:
        console.print(f"[red]❌ Real inspection failed: {str(e)}[/red]")
        console.print("[yellow]💡 Try using --mock flag for demo mode[/yellow]")


def _inspect_api_payloads(console: Console, mock: bool):
    """Inspect API payload structures"""
    console.print("[bold blue]📋 API Payload Comparison[/bold blue]")
    _inspect_prompt(console, "Explain the concept of machine learning", None, mock)


def _inspect_streaming(console: Console, mock: bool):
    """Inspect streaming response behavior"""
    console.print("[bold blue]🌊 Streaming Analysis[/bold blue]")
    console.print("[cyan]Analyzing token-by-token generation patterns...[/cyan]\n")
    _inspect_prompt(console, "Generate a creative story about space exploration", None, mock)


def _inspect_error_handling(console: Console, mock: bool):
    """Inspect error handling capabilities"""
    console.print("[bold blue]⚠️ Error Handling Analysis[/bold blue]")
    console.print("[cyan]Testing error scenarios and recovery mechanisms...[/cyan]\n")
    _inspect_prompt(console, "This is an intentionally malformed request with invalid tokens <<<>>>", None, mock)


def _inspect_performance(console: Console, mock: bool):
    """Inspect performance characteristics"""
    console.print("[bold blue]⚡ Performance Profiling[/bold blue]")
    console.print("[cyan]Analyzing timing, memory usage, and efficiency...[/cyan]\n")
    _inspect_prompt(console, "Provide a detailed technical explanation of neural networks", None, mock)


def _generate_mock_request(service: str, prompt: str) -> str:
    """Generate mock request payload for inspection"""
    payloads = {
        'vllm': f'''{{
    "model": "Qwen/Qwen2.5-7B",
    "messages": [
        {{
            "role": "user",
            "content": "{prompt}"
        }}
    ],
    "max_tokens": 256,
    "temperature": 0.7,
    "top_p": 0.9,
    "stream": true
}}''',
        'tgi': f'''{{
    "inputs": "{prompt}",
    "parameters": {{
        "max_new_tokens": 256,
        "temperature": 0.7,
        "top_p": 0.9,
        "stream": true,
        "details": true
    }}
}}''',
        'ollama': f'''{{
    "model": "qwen2.5:7b",
    "prompt": "{prompt}",
    "options": {{
        "num_predict": 256,
        "temperature": 0.7,
        "top_p": 0.9
    }},
    "stream": true
}}'''
    }
    return payloads.get(service, '')


def _generate_mock_response_meta(service: str) -> str:
    """Generate mock response metadata"""
    metadata = {
        'vllm': """🔧 Engine: vLLM v0.4.0
📊 Model: Qwen/Qwen2.5-7B
💾 GPU Memory: 15.2 GB / 80 GB
⚡ TTFT: 127ms
🎯 Tokens/sec: 45.2
🌐 Endpoint: /v1/chat/completions""",
        'tgi': """🔧 Engine: Text Generation Inference v1.9.0
📊 Model: Qwen/Qwen2.5-7B
💾 GPU Memory: 14.8 GB / 40 GB  
⚡ TTFT: 189ms
🎯 Tokens/sec: 38.7
🌐 Endpoint: /generate_stream""",
        'ollama': """🔧 Engine: Ollama v0.1.32
📊 Model: qwen2.5:7b
💾 GPU Memory: 8.1 GB / 24 GB
⚡ TTFT: 245ms
🎯 Tokens/sec: 28.3
🌐 Endpoint: /api/generate"""
    }
    return metadata.get(service, '')


def _simulate_streaming_response(console: Console, service: str):
    """Simulate streaming response for demonstration"""
    import time
    
    responses = {
        'vllm': ["Machine", " learning", " is", " a", " subset", " of", " artificial", " intelligence..."],
        'tgi': ["Machine", " learning", " represents", " a", " powerful", " computational", " approach..."],
        'ollama': ["Well,", " machine", " learning", " is", " basically", " a", " way", " for", " computers..."]
    }
    
    tokens = responses.get(service, ["Sample", " streaming", " response"])
    
    console.print(f"[dim]Streaming tokens:[/dim] ", end="")
    for i, token in enumerate(tokens):
        console.print(f"[green]{token}[/green]", end="")
        if i < len(tokens) - 1:
            console.print(" → ", end="")
        time.sleep(0.1)  # Simulate streaming delay
    
    console.print(f"\n[dim]Total tokens: {len(tokens)}, Avg delay: 100ms/token[/dim]\n")
