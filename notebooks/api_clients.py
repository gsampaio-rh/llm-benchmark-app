"""
API Clients for vLLM, TGI, and Ollama Services
Clean, unified API interface following Section 2 UX pattern
"""

import asyncio
import json
import time
from typing import Dict, List, Optional, AsyncGenerator, Any
from dataclasses import dataclass, field
from enum import Enum

import httpx
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

console = Console()

class ServiceType(Enum):
    VLLM = "vllm"
    TGI = "tgi" 
    OLLAMA = "ollama"

@dataclass
class ChatMessage:
    """Standard chat message format"""
    role: str  # "user", "assistant", "system"
    content: str

@dataclass
class GenerationRequest:
    """Unified generation request across all services"""
    messages: List[ChatMessage] = field(default_factory=list)
    prompt: str = ""
    max_tokens: int = 256
    temperature: float = 0.7
    stream: bool = False
    model: str = ""

@dataclass
class TokenMetrics:
    """Token generation metrics for TTFT measurement"""
    ttft_ms: Optional[float] = None  # Time to first token
    total_time_ms: float = 0.0
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    request_start: float = 0.0
    first_token_time: Optional[float] = None

@dataclass
class GenerationResponse:
    """Unified response format"""
    content: str = ""
    metrics: TokenMetrics = field(default_factory=TokenMetrics)
    raw_response: Any = None
    service_type: ServiceType = ServiceType.VLLM
    error: Optional[str] = None

class BaseAPIClient:
    """Base class for all API clients"""
    
    def __init__(self, base_url: str, service_type: ServiceType):
        self.base_url = base_url.rstrip('/')
        self.service_type = service_type
        self.client = httpx.AsyncClient(timeout=30.0)
        
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()
        
    async def health_check(self) -> bool:
        """Check if service is healthy"""
        try:
            health_endpoints = {
                ServiceType.VLLM: "/health",
                ServiceType.TGI: "/health", 
                ServiceType.OLLAMA: "/api/tags"
            }
            
            endpoint = health_endpoints[self.service_type]
            response = await self.client.get(f"{self.base_url}{endpoint}")
            return response.status_code < 400
            
        except Exception:
            return False
    
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text - to be implemented by subclasses"""
        raise NotImplementedError
        
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate streaming text - to be implemented by subclasses"""
        raise NotImplementedError

class vLLMClient(BaseAPIClient):
    """vLLM OpenAI-compatible API client"""
    
    def __init__(self, base_url: str):
        super().__init__(base_url, ServiceType.VLLM)
        
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using vLLM OpenAI-compatible API"""
        try:
            metrics = TokenMetrics()
            metrics.request_start = time.time()
            
            # Convert to OpenAI format
            if request.messages:
                # Chat completion format
                payload = {
                    "model": request.model or "Qwen/Qwen2.5-7B",
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": request.stream
                }
                endpoint = "/v1/chat/completions"
            else:
                # Completion format  
                payload = {
                    "model": request.model or "Qwen/Qwen2.5-7B",
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": request.stream
                }
                endpoint = "/v1/completions"
            
            response = await self.client.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            metrics.total_time_ms = (time.time() - metrics.request_start) * 1000
            
            result = response.json()
            
            if "choices" in result and result["choices"]:
                if request.messages:
                    # Chat completion
                    content = result["choices"][0]["message"]["content"]
                else:
                    # Text completion
                    content = result["choices"][0]["text"]
                    
                # Estimate tokens (rough approximation)
                metrics.tokens_generated = len(content.split())
                if metrics.total_time_ms > 0:
                    metrics.tokens_per_second = (metrics.tokens_generated / metrics.total_time_ms) * 1000
                
                return GenerationResponse(
                    content=content,
                    metrics=metrics,
                    raw_response=result,
                    service_type=ServiceType.VLLM
                )
            else:
                return GenerationResponse(
                    error="No content in response",
                    service_type=ServiceType.VLLM
                )
                
        except Exception as e:
            return GenerationResponse(
                error=str(e),
                service_type=ServiceType.VLLM
            )
    
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate streaming text for TTFT measurement"""
        try:
            metrics = TokenMetrics()
            metrics.request_start = time.time()
            
            # Force streaming
            request.stream = True
            
            if request.messages:
                payload = {
                    "model": request.model or "Qwen/Qwen2.5-7B",
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": True
                }
                endpoint = "/v1/chat/completions"
            else:
                payload = {
                    "model": request.model or "Qwen/Qwen2.5-7B", 
                    "prompt": request.prompt,
                    "max_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "stream": True
                }
                endpoint = "/v1/completions"
            
            async with self.client.stream("POST", f"{self.base_url}{endpoint}", json=payload) as response:
                response.raise_for_status()
                
                first_token = True
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: "
                        if data_str == "[DONE]":
                            break
                            
                        try:
                            data = json.loads(data_str)
                            if "choices" in data and data["choices"]:
                                if request.messages:
                                    # Chat completion delta
                                    delta = data["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                else:
                                    # Text completion
                                    content = data["choices"][0].get("text", "")
                                
                                if content and first_token:
                                    metrics.first_token_time = time.time()
                                    metrics.ttft_ms = (metrics.first_token_time - metrics.request_start) * 1000
                                    first_token = False
                                
                                if content:
                                    yield content
                                    
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            console.print(f"[red]❌ vLLM streaming error: {e}[/red]")

class TGIClient(BaseAPIClient):
    """Text Generation Inference API client"""
    
    def __init__(self, base_url: str):
        super().__init__(base_url, ServiceType.TGI)
        
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using TGI API"""
        try:
            metrics = TokenMetrics()
            metrics.request_start = time.time()
            
            # Convert messages to prompt for TGI
            if request.messages:
                prompt_parts = []
                for msg in request.messages:
                    if msg.role == "user":
                        prompt_parts.append(f"User: {msg.content}")
                    elif msg.role == "assistant":
                        prompt_parts.append(f"Assistant: {msg.content}")
                    elif msg.role == "system":
                        prompt_parts.append(f"System: {msg.content}")
                prompt = "\n".join(prompt_parts) + "\nAssistant:"
            else:
                prompt = request.prompt
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "do_sample": True,
                    "stream": request.stream
                }
            }
            
            response = await self.client.post(f"{self.base_url}/generate", json=payload)
            response.raise_for_status()
            
            metrics.total_time_ms = (time.time() - metrics.request_start) * 1000
            
            result = response.json()
            
            if "generated_text" in result:
                content = result["generated_text"]
                
                # Remove the original prompt from response
                if content.startswith(prompt):
                    content = content[len(prompt):].strip()
                
                metrics.tokens_generated = len(content.split())
                if metrics.total_time_ms > 0:
                    metrics.tokens_per_second = (metrics.tokens_generated / metrics.total_time_ms) * 1000
                
                return GenerationResponse(
                    content=content,
                    metrics=metrics,
                    raw_response=result,
                    service_type=ServiceType.TGI
                )
            else:
                return GenerationResponse(
                    error="No generated_text in response",
                    service_type=ServiceType.TGI
                )
                
        except Exception as e:
            return GenerationResponse(
                error=str(e),
                service_type=ServiceType.TGI
            )
    
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate streaming text for TTFT measurement"""
        try:
            metrics = TokenMetrics()
            metrics.request_start = time.time()
            
            # Convert messages to prompt for TGI
            if request.messages:
                prompt_parts = []
                for msg in request.messages:
                    if msg.role == "user":
                        prompt_parts.append(f"User: {msg.content}")
                    elif msg.role == "assistant":
                        prompt_parts.append(f"Assistant: {msg.content}")
                    elif msg.role == "system":
                        prompt_parts.append(f"System: {msg.content}")
                prompt = "\n".join(prompt_parts) + "\nAssistant:"
            else:
                prompt = request.prompt
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": request.max_tokens,
                    "temperature": request.temperature,
                    "do_sample": True,
                    "stream": True
                }
            }
            
            async with self.client.stream("POST", f"{self.base_url}/generate_stream", json=payload) as response:
                response.raise_for_status()
                
                first_token = True
                async for line in response.aiter_lines():
                    if line.startswith("data:"):
                        data_str = line[5:].strip()  # Remove "data:"
                        
                        try:
                            data = json.loads(data_str)
                            if "token" in data:
                                content = data["token"]["text"]
                                
                                if content and first_token:
                                    metrics.first_token_time = time.time()
                                    metrics.ttft_ms = (metrics.first_token_time - metrics.request_start) * 1000
                                    first_token = False
                                
                                if content:
                                    yield content
                                    
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            console.print(f"[red]❌ TGI streaming error: {e}[/red]")

class OllamaClient(BaseAPIClient):
    """Ollama API client"""
    
    def __init__(self, base_url: str):
        super().__init__(base_url, ServiceType.OLLAMA)
        
    async def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text using Ollama API"""
        try:
            metrics = TokenMetrics()
            metrics.request_start = time.time()
            
            if request.messages:
                # Chat format
                payload = {
                    "model": request.model or "qwen2.5:7b",
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "stream": request.stream,
                    "options": {
                        "num_predict": request.max_tokens,
                        "temperature": request.temperature
                    }
                }
                endpoint = "/api/chat"
            else:
                # Generate format
                payload = {
                    "model": request.model or "qwen2.5:7b",
                    "prompt": request.prompt,
                    "stream": request.stream,
                    "options": {
                        "num_predict": request.max_tokens,
                        "temperature": request.temperature
                    }
                }
                endpoint = "/api/generate"
            
            response = await self.client.post(f"{self.base_url}{endpoint}", json=payload)
            response.raise_for_status()
            
            metrics.total_time_ms = (time.time() - metrics.request_start) * 1000
            
            result = response.json()
            
            if request.messages and "message" in result:
                content = result["message"]["content"]
            elif "response" in result:
                content = result["response"]
            else:
                content = ""
            
            metrics.tokens_generated = len(content.split())
            if metrics.total_time_ms > 0:
                metrics.tokens_per_second = (metrics.tokens_generated / metrics.total_time_ms) * 1000
            
            return GenerationResponse(
                content=content,
                metrics=metrics,
                raw_response=result,
                service_type=ServiceType.OLLAMA
            )
                
        except Exception as e:
            return GenerationResponse(
                error=str(e),
                service_type=ServiceType.OLLAMA
            )
    
    async def generate_stream(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Generate streaming text for TTFT measurement"""
        try:
            metrics = TokenMetrics()
            metrics.request_start = time.time()
            
            if request.messages:
                payload = {
                    "model": request.model or "qwen2.5:7b",
                    "messages": [{"role": msg.role, "content": msg.content} for msg in request.messages],
                    "stream": True,
                    "options": {
                        "num_predict": request.max_tokens,
                        "temperature": request.temperature
                    }
                }
                endpoint = "/api/chat"
            else:
                payload = {
                    "model": request.model or "qwen2.5:7b",
                    "prompt": request.prompt,
                    "stream": True,
                    "options": {
                        "num_predict": request.max_tokens,
                        "temperature": request.temperature
                    }
                }
                endpoint = "/api/generate"
            
            async with self.client.stream("POST", f"{self.base_url}{endpoint}", json=payload) as response:
                response.raise_for_status()
                
                first_token = True
                async for line in response.aiter_lines():
                    try:
                        data = json.loads(line)
                        
                        if request.messages and "message" in data:
                            content = data["message"]["content"]
                        elif "response" in data:
                            content = data["response"]
                        else:
                            continue
                        
                        if content and first_token:
                            metrics.first_token_time = time.time()
                            metrics.ttft_ms = (metrics.first_token_time - metrics.request_start) * 1000
                            first_token = False
                        
                        if content:
                            yield content
                            
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            console.print(f"[red]❌ Ollama streaming error: {e}[/red]")

class UnifiedAPIClient:
    """Unified client that manages all three services"""
    
    def __init__(self, services: Dict[str, str]):
        """
        Initialize with service URLs
        services = {"vllm": "http://...", "tgi": "http://...", "ollama": "http://..."}
        """
        self.clients = {}
        
        if "vllm" in services and services["vllm"]:
            self.clients["vllm"] = vLLMClient(services["vllm"])
            
        if "tgi" in services and services["tgi"]:
            self.clients["tgi"] = TGIClient(services["tgi"])
            
        if "ollama" in services and services["ollama"]:
            self.clients["ollama"] = OllamaClient(services["ollama"])
    
    async def __aenter__(self):
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        for client in self.clients.values():
            await client.__aexit__(exc_type, exc_val, exc_tb)
    
    async def health_check_all(self) -> Dict[str, bool]:
        """Check health of all services"""
        results = {}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Checking API health...", total=len(self.clients))
            
            for service_name, client in self.clients.items():
                results[service_name] = await client.health_check()
                progress.advance(task)
        
        return results
    
    async def generate_comparison(self, request: GenerationRequest) -> Dict[str, GenerationResponse]:
        """Generate text from all services for comparison"""
        results = {}
        
        console.print(Panel.fit(
            f"[bold blue]🚀 Running Comparison Test[/bold blue]\n\n"
            f"Prompt: [dim]{request.prompt or (request.messages[-1].content if request.messages else 'N/A')}[/dim]\n"
            f"Services: {', '.join(self.clients.keys()).upper()}",
            title="API Comparison",
            border_style="blue"
        ))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            
            task = progress.add_task("Generating responses...", total=len(self.clients))
            
            # Run all services concurrently
            tasks = []
            for service_name, client in self.clients.items():
                tasks.append(self._generate_with_name(service_name, client, request))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, (service_name, client) in enumerate(self.clients.items()):
                if isinstance(responses[i], Exception):
                    results[service_name] = GenerationResponse(
                        error=str(responses[i]),
                        service_type=ServiceType(service_name)
                    )
                else:
                    results[service_name] = responses[i]
                progress.advance(task)
        
        # Display results table
        self._display_results_table(results)
        
        return results
    
    async def _generate_with_name(self, service_name: str, client: BaseAPIClient, request: GenerationRequest) -> GenerationResponse:
        """Helper to generate with service name context"""
        return await client.generate(request)
    
    def _display_results_table(self, results: Dict[str, GenerationResponse]):
        """Display beautiful results comparison table"""
        table = Table(title="🏆 Generation Results Comparison")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Response Time", style="green")
        table.add_column("Tokens/sec", style="yellow")
        table.add_column("Content Preview", style="blue", max_width=50)
        
        for service_name, response in results.items():
            if response.error:
                status = "[red]❌ Error[/red]"
                response_time = "N/A"
                tokens_per_sec = "N/A"
                content = f"[red]{response.error}[/red]"
            else:
                status = "[green]✅ Success[/green]"
                response_time = f"{response.metrics.total_time_ms:.1f}ms"
                tokens_per_sec = f"{response.metrics.tokens_per_second:.1f}"
                content = response.content[:100] + "..." if len(response.content) > 100 else response.content
            
            table.add_row(
                service_name.upper(),
                status,
                response_time,
                tokens_per_sec,
                content
            )
        
        console.print(table)
        
        # Find fastest service
        fastest_service = None
        fastest_time = float('inf')
        
        for service_name, response in results.items():
            if not response.error and response.metrics.total_time_ms < fastest_time:
                fastest_time = response.metrics.total_time_ms
                fastest_service = service_name
        
        if fastest_service:
            console.print(f"\n[bold green]🏆 Fastest Service: {fastest_service.upper()} ({fastest_time:.1f}ms)[/bold green]")

# Helper functions for notebook usage
async def create_unified_client(discovered_services) -> UnifiedAPIClient:
    """Create unified client from discovered services (Section 2 output)"""
    service_urls = {}
    
    for service_name, service_info in discovered_services.items():
        if hasattr(service_info, 'url') and service_info.url and service_info.status == "healthy":
            service_urls[service_name] = service_info.url
        elif hasattr(service_info, 'url') and service_info.url:
            service_urls[service_name] = service_info.url
    
    return UnifiedAPIClient(service_urls)

def create_chat_request(message: str, max_tokens: int = 256) -> GenerationRequest:
    """Helper to create a chat request"""
    return GenerationRequest(
        messages=[ChatMessage(role="user", content=message)],
        max_tokens=max_tokens,
        temperature=0.7
    )

def create_completion_request(prompt: str, max_tokens: int = 256) -> GenerationRequest:
    """Helper to create a completion request"""
    return GenerationRequest(
        prompt=prompt,
        max_tokens=max_tokens,
        temperature=0.7
    )
