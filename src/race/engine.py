"""
Race execution engine for managing three-way performance races.

This module contains the core race execution logic, separated from the UI
and visualization concerns.
"""

import asyncio
import time
import random
from typing import Optional, Dict, List, AsyncGenerator, Any
from dataclasses import dataclass

from .models import ThreeWayRace, RaceParticipant, ServicePersonality
from ..api_clients import UnifiedAPIClient, create_chat_request, GenerationRequest


@dataclass
class RaceResults:
    """Results from a single race execution"""
    race: ThreeWayRace
    winner: Optional[str]
    ttft_rankings: List[tuple]
    execution_time: float
    success: bool
    error_message: Optional[str] = None


@dataclass 
class StatisticalResults:
    """Results from multiple race iterations"""
    race: ThreeWayRace
    total_runs: int
    successful_runs: int
    overall_winner: Optional[str]
    average_execution_time: float
    
    def get_winner_confidence(self) -> float:
        """Get confidence level for the winner (0-1)"""
        if not self.overall_winner or self.successful_runs < 3:
            return 0.0
        
        winner_stats = self.race.statistics[self.overall_winner]
        winner_wins = 0
        
        # Count how many times the winner actually won individual races
        for service_name, stats in self.race.statistics.items():
            if len(stats.ttft_times) > 0:
                if service_name == self.overall_winner:
                    # Approximate wins based on consistency
                    mean_ttft = winner_stats.get_ttft_stats()["mean"]
                    other_means = [
                        other_stats.get_ttft_stats()["mean"] 
                        for other_name, other_stats in self.race.statistics.items() 
                        if other_name != self.overall_winner and other_stats.ttft_times
                    ]
                    if other_means and mean_ttft < min(other_means):
                        winner_wins = self.successful_runs
                    break
        
        return min(winner_wins / self.successful_runs, 1.0)


class RaceEngine:
    """Core race execution logic"""
    
    def __init__(self, api_client: Optional[UnifiedAPIClient] = None):
        """Initialize the race engine
        
        Args:
            api_client: Optional API client for real service calls
        """
        self.api_client = api_client
        
        # Performance characteristics for demo mode
        self.demo_characteristics = {
            "vllm": {
                "base_ttft_ms": 120,
                "variance_pct": 20,
                "min_ttft_ms": 80,
                "tokens_per_sec": 50
            },
            "tgi": {
                "base_ttft_ms": 350, 
                "variance_pct": 25,
                "min_ttft_ms": 200,
                "tokens_per_sec": 40
            },
            "ollama": {
                "base_ttft_ms": 650,
                "variance_pct": 30, 
                "min_ttft_ms": 400,
                "tokens_per_sec": 35
            }
        }
    
    async def execute_single_race(self, race: ThreeWayRace, use_real_apis: bool = False) -> RaceResults:
        """Execute one race iteration
        
        Args:
            race: The race to execute
            use_real_apis: Whether to use real APIs or demo mode
            
        Returns:
            Results from the race execution
        """
        start_time = time.time()
        race.start_time = start_time
        
        try:
            if use_real_apis and self.api_client:
                await self._execute_real_race(race)
            else:
                await self._execute_demo_race(race)
            
            # Determine winner
            winner = race.determine_winner()
            ttft_rankings = race.get_ttft_rankings()
            
            execution_time = time.time() - start_time
            
            return RaceResults(
                race=race,
                winner=winner,
                ttft_rankings=ttft_rankings,
                execution_time=execution_time,
                success=True
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            return RaceResults(
                race=race,
                winner=None,
                ttft_rankings=[],
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def execute_statistical_race(self, race: ThreeWayRace, num_runs: int, 
                                    use_real_apis: bool = False) -> StatisticalResults:
        """Execute multiple races for statistical analysis
        
        Args:
            race: The race to execute
            num_runs: Number of iterations to run
            use_real_apis: Whether to use real APIs or demo mode
            
        Returns:
            Statistical results from multiple runs
        """
        successful_runs = 0
        total_execution_time = 0.0
        
        for i in range(num_runs):
            race.reset_for_next_run()
            result = await self.execute_single_race(race, use_real_apis)
            
            if result.success:
                successful_runs += 1
                total_execution_time += result.execution_time
        
        # Determine overall winner based on statistics
        overall_winner = self._determine_statistical_winner(race)
        
        avg_execution_time = total_execution_time / max(successful_runs, 1)
        
        return StatisticalResults(
            race=race,
            total_runs=num_runs,
            successful_runs=successful_runs,
            overall_winner=overall_winner,
            average_execution_time=avg_execution_time
        )
    
    async def _execute_real_race(self, race: ThreeWayRace):
        """Execute race using real API calls"""
        if not self.api_client:
            raise ValueError("No API client available for real race execution")
        
        request = create_chat_request(race.prompt, max_tokens=256)
        
        # Start all services concurrently
        tasks = []
        for service_name, participant in race.participants.items():
            if service_name in self.api_client.clients:
                task = asyncio.create_task(
                    self._execute_real_service(race, service_name, request)
                )
                tasks.append(task)
        
        # Wait for all services to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _execute_real_service(self, race: ThreeWayRace, service_name: str, request: GenerationRequest):
        """Execute real API call for a single service"""
        try:
            participant = race.participants[service_name]
            participant.response_start_time = time.time()
            
            first_token = True
            token_count = 0
            
            async for chunk in self.api_client.stream_generate(service_name, request):
                if first_token:
                    participant.first_token_time = time.time()
                    first_token = False
                
                participant.current_response += chunk
                token_count += 1
            
            participant.tokens_received = token_count
            participant.is_complete = True
            
        except Exception as e:
            participant.error_message = str(e)
    
    async def _execute_demo_race(self, race: ThreeWayRace):
        """Execute race using demo simulation"""
        # Start all services concurrently
        tasks = []
        for service_name, participant in race.participants.items():
            task = asyncio.create_task(
                self._execute_demo_service(race, service_name)
            )
            tasks.append(task)
        
        # Wait for all services to complete
        await asyncio.gather(*tasks)
    
    async def _execute_demo_service(self, race: ThreeWayRace, service_name: str):
        """Execute demo simulation for a single service"""
        participant = race.participants[service_name]
        characteristics = self.demo_characteristics.get(service_name, self.demo_characteristics["vllm"])
        
        # Calculate realistic TTFT with variance
        base_ttft = characteristics["base_ttft_ms"] / 1000  # Convert to seconds
        variance_pct = characteristics["variance_pct"] / 100
        min_ttft = characteristics["min_ttft_ms"] / 1000
        
        variance = base_ttft * variance_pct
        actual_ttft = base_ttft + random.uniform(-variance, variance)
        actual_ttft = max(min_ttft, actual_ttft)
        
        # Mark response start and simulate TTFT delay
        participant.response_start_time = time.time()
        await asyncio.sleep(actual_ttft)
        participant.first_token_time = time.time()
        
        # Simulate token generation
        token_count = random.randint(30, 80)
        tokens_per_sec = characteristics["tokens_per_sec"]
        generation_time = token_count / tokens_per_sec
        
        # Generate response content gradually
        for i in range(token_count):
            await asyncio.sleep(generation_time / token_count)
            participant.current_response += f"token_{i} "
            participant.tokens_received = i + 1
        
        participant.is_complete = True
    
    def _determine_statistical_winner(self, race: ThreeWayRace) -> Optional[str]:
        """Determine overall winner based on mean TTFT across all runs"""
        service_means = {}
        
        for service_name, stats in race.statistics.items():
            if stats.ttft_times:
                ttft_stats = stats.get_ttft_stats()
                service_means[service_name] = ttft_stats["mean"]
        
        if not service_means:
            return None
        
        return min(service_means.keys(), key=lambda x: service_means[x])
    
    def create_demo_race(self, prompt: str, services: List[str]) -> ThreeWayRace:
        """Create a new race configured for demo mode
        
        Args:
            prompt: The prompt to race with
            services: List of service names to include
            
        Returns:
            Configured ThreeWayRace object
        """
        race_id = f"demo_{int(time.time())}"
        race = ThreeWayRace(
            race_id=race_id,
            prompt=prompt,
            start_time=time.time(),
            use_real_apis=False
        )
        
        # Add participants
        personality_map = {
            "vllm": ServicePersonality.VLLM,
            "tgi": ServicePersonality.TGI,
            "ollama": ServicePersonality.OLLAMA
        }
        
        for service_name in services:
            if service_name in personality_map:
                race.add_participant(service_name, personality_map[service_name])
        
        return race
    
    async def create_real_race(self, prompt: str, services: List[str]) -> ThreeWayRace:
        """Create a new race configured for real API calls
        
        Args:
            prompt: The prompt to race with
            services: List of service names to include
            
        Returns:
            Configured ThreeWayRace object
        """
        race_id = f"real_{int(time.time())}"
        race = ThreeWayRace(
            race_id=race_id,
            prompt=prompt,
            start_time=time.time(),
            use_real_apis=True,
            api_client=self.api_client
        )
        
        # Add participants with real service information
        personality_map = {
            "vllm": ServicePersonality.VLLM,
            "tgi": ServicePersonality.TGI,
            "ollama": ServicePersonality.OLLAMA
        }
        
        for service_name in services:
            if service_name in personality_map:
                # Get real engine info if API client is available
                engine_info = None
                if self.api_client and hasattr(self.api_client, 'clients') and service_name in self.api_client.clients:
                    engine_info = await self._create_real_engine_info(service_name, self.api_client.clients[service_name])
                
                race.add_participant(service_name, personality_map[service_name], engine_info)
        
        return race
    
    async def _create_real_engine_info(self, service_name: str, api_client) -> 'EngineInfo':
        """Create real engine information by querying the actual service
        
        Args:
            service_name: Name of the service
            api_client: The API client instance for this service
            
        Returns:
            EngineInfo with real service details fetched from the engine
        """
        from .models import EngineInfo
        import httpx
        
        # Get the real base URL from the API client
        real_url = getattr(api_client, 'base_url', f'https://{service_name}-route.apps.cluster.com')
        
        try:
            # Fetch real configuration from each engine type
            if service_name == "vllm":
                return await self._fetch_vllm_info(real_url)
            elif service_name == "tgi":
                return await self._fetch_tgi_info(real_url)
            elif service_name == "ollama":
                return await self._fetch_ollama_info(real_url)
            else:
                # Fallback to default info with real URL
                return EngineInfo(engine_url=real_url)
                
        except Exception as e:
            # If we can't fetch real info, fall back to reasonable defaults with real URL
            print(f"⚠️  Could not fetch real config for {service_name}: {e}")
            return self._create_fallback_engine_info(service_name, real_url)
    
    async def _fetch_vllm_info(self, base_url: str) -> 'EngineInfo':
        """Fetch real configuration from vLLM engine"""
        from .models import EngineInfo
        import httpx
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Get model information
                models_response = await client.get(f"{base_url}/v1/models")
                models_data = models_response.json()
                
                model_name = "Unknown Model"
                if models_data.get("data") and len(models_data["data"]) > 0:
                    model_name = models_data["data"][0].get("id", "Unknown Model")
                
                # Try to get version info (may not be available)
                version = "vLLM Engine"
                try:
                    version_response = await client.get(f"{base_url}/version")
                    if version_response.status_code == 200:
                        version_data = version_response.json()
                        version = f"v{version_data.get('version', 'unknown')}"
                except:
                    pass
                
                return EngineInfo(
                    engine_url=base_url,
                    model_name=model_name,
                    version=version,
                    gpu_type="Unknown",
                    memory_gb=0,  # Unknown
                    max_batch_size=0,  # Unknown
                    max_context_length=0,  # Unknown
                    deployment="Unknown"
                )
                
            except Exception as e:
                raise Exception(f"Failed to fetch vLLM info: {e}")
    
    async def _fetch_tgi_info(self, base_url: str) -> 'EngineInfo':
        """Fetch real configuration from TGI engine"""
        from .models import EngineInfo
        import httpx
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # TGI has an /info endpoint with configuration details
                info_response = await client.get(f"{base_url}/info")
                info_data = info_response.json()
                
                model_name = info_data.get("model_id", "Unknown Model")
                version = f"TGI v{info_data.get('version', 'unknown')}"
                max_batch_size = info_data.get("max_batch_total_tokens", 32) // 1000  # Rough estimate
                max_context_length = info_data.get("max_input_length", 4096)
                
                return EngineInfo(
                    engine_url=base_url,
                    model_name=model_name,
                    version=version,
                    gpu_type="Unknown",
                    memory_gb=0,  # Unknown
                    max_batch_size=max_batch_size,
                    max_context_length=max_context_length,
                    deployment="Unknown"
                )
                
            except Exception as e:
                raise Exception(f"Failed to fetch TGI info: {e}")
    
    async def _fetch_ollama_info(self, base_url: str) -> 'EngineInfo':
        """Fetch real configuration from Ollama engine"""
        from .models import EngineInfo
        import httpx
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # Get available models
                tags_response = await client.get(f"{base_url}/api/tags")
                tags_data = tags_response.json()
                
                model_name = "No models loaded"
                if tags_data.get("models") and len(tags_data["models"]) > 0:
                    model_name = tags_data["models"][0].get("name", "Unknown Model")
                
                # Get version info
                version = "Ollama"
                try:
                    version_response = await client.get(f"{base_url}/api/version")
                    if version_response.status_code == 200:
                        version_data = version_response.json()
                        version = f"v{version_data.get('version', 'unknown')}"
                except:
                    pass
                
                return EngineInfo(
                    engine_url=base_url,
                    model_name=model_name,
                    version=version,
                    gpu_type="Unknown",
                    memory_gb=0,  # Unknown
                    max_batch_size=0,  # Unknown
                    max_context_length=0,  # Unknown
                    deployment="Unknown"
                )
                
            except Exception as e:
                raise Exception(f"Failed to fetch Ollama info: {e}")
    
    def _create_fallback_engine_info(self, service_name: str, real_url: str) -> 'EngineInfo':
        """Create fallback engine info when real queries fail"""
        from .models import EngineInfo
        
        # Fallback configs with real URL but unknown settings
        service_configs = {
            "vllm": EngineInfo(
                engine_url=real_url,
                model_name="Config unavailable",
                version="Unknown",
                gpu_type="Unknown",
                memory_gb=0,
                max_batch_size=0,
                max_context_length=0,
                deployment="Unknown"
            ),
            "tgi": EngineInfo(
                engine_url=real_url,
                model_name="Config unavailable", 
                version="Unknown",
                gpu_type="Unknown",
                memory_gb=0,
                max_batch_size=0,
                max_context_length=0,
                deployment="Unknown"
            ),
            "ollama": EngineInfo(
                engine_url=real_url,
                model_name="Config unavailable",
                version="Unknown",
                gpu_type="Unknown",
                memory_gb=0,
                max_batch_size=0,
                max_context_length=0,
                deployment="Unknown"
            )
        }
        
        return service_configs.get(service_name, EngineInfo(engine_url=real_url))
