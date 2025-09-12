"""
Demo simulation engine for realistic AI service behavior without live APIs.

This module provides comprehensive simulation capabilities including streaming
responses, realistic timing, and service-specific behavioral patterns.
"""

import asyncio
import random
import time
from typing import AsyncGenerator, Dict, List, Optional

from .response_generator import DemoResponseGenerator
from ..race.models import ServicePersonality


class DemoSimulator:
    """Demo mode simulation with realistic patterns"""
    
    def __init__(self):
        """Initialize the demo simulator"""
        self.response_generator = DemoResponseGenerator()
        
        # Service-specific performance characteristics
        self.service_characteristics = {
            "vllm": {
                "base_ttft_ms": 120,
                "ttft_variance_pct": 15,
                "min_ttft_ms": 80,
                "max_ttft_ms": 200,
                "tokens_per_second": 50,
                "token_variance_pct": 20,
                "reliability": 0.999  # 99.9% for demo consistency
            },
            "tgi": {
                "base_ttft_ms": 350,
                "ttft_variance_pct": 20,
                "min_ttft_ms": 250,
                "max_ttft_ms": 500,
                "tokens_per_second": 40,
                "token_variance_pct": 25,
                "reliability": 0.999  # 99.9% for demo consistency
            },
            "ollama": {
                "base_ttft_ms": 650,
                "ttft_variance_pct": 25,
                "min_ttft_ms": 450,
                "max_ttft_ms": 900,
                "tokens_per_second": 35,
                "token_variance_pct": 30,
                "reliability": 0.999  # 99.9% for demo consistency
            }
        }
    
    async def simulate_streaming_response(self, service_name: str, prompt: str) -> AsyncGenerator[str, None]:
        """Simulate realistic streaming with service-specific patterns
        
        Args:
            service_name: Name of the service to simulate
            prompt: User prompt
            
        Yields:
            Stream of token strings
        """
        characteristics = self.service_characteristics.get(service_name, self.service_characteristics["vllm"])
        
        # Check if simulation should fail (based on reliability)
        if random.random() > characteristics["reliability"]:
            await asyncio.sleep(0.5)  # Delay before error
            raise Exception(f"Simulated {service_name} service error")
        
        # Generate response content
        response_text = self.response_generator.generate_response(service_name, prompt)
        tokens = self.response_generator.simulate_tokenization(response_text)
        
        # Calculate realistic timing
        ttft_delay = self._calculate_ttft_delay(characteristics)
        token_delay = self._calculate_token_delay(characteristics, len(tokens))
        
        # Simulate TTFT delay
        await asyncio.sleep(ttft_delay)
        
        # Stream tokens with realistic delays
        for i, token in enumerate(tokens):
            yield token
            
            # Add slight delay between tokens (except for the last one)
            if i < len(tokens) - 1:
                await asyncio.sleep(token_delay)
    
    def _calculate_ttft_delay(self, characteristics: Dict) -> float:
        """Calculate realistic TTFT delay
        
        Args:
            characteristics: Service performance characteristics
            
        Returns:
            TTFT delay in seconds
        """
        base_ttft = characteristics["base_ttft_ms"] / 1000
        variance_pct = characteristics["ttft_variance_pct"] / 100
        min_ttft = characteristics["min_ttft_ms"] / 1000
        max_ttft = characteristics["max_ttft_ms"] / 1000
        
        # Add realistic variance
        variance = base_ttft * variance_pct
        ttft = base_ttft + random.uniform(-variance, variance)
        
        # Clamp to realistic bounds
        return max(min_ttft, min(ttft, max_ttft))
    
    def _calculate_token_delay(self, characteristics: Dict, token_count: int) -> float:
        """Calculate delay between tokens
        
        Args:
            characteristics: Service performance characteristics
            token_count: Number of tokens to generate
            
        Returns:
            Delay between tokens in seconds
        """
        base_tokens_per_sec = characteristics["tokens_per_second"]
        variance_pct = characteristics["token_variance_pct"] / 100
        
        # Add variance to tokens per second
        variance = base_tokens_per_sec * variance_pct
        actual_tokens_per_sec = base_tokens_per_sec + random.uniform(-variance, variance)
        actual_tokens_per_sec = max(10, actual_tokens_per_sec)  # Minimum 10 tokens/sec
        
        return 1.0 / actual_tokens_per_sec
    
    async def simulate_conversation_turn(self, service_name: str, prompt: str, 
                                       context: Optional[List[str]] = None) -> str:
        """Simulate a full conversation turn
        
        Args:
            service_name: Name of the service to simulate
            prompt: User prompt
            context: Optional conversation context
            
        Returns:
            Complete response string
        """
        full_response = ""
        
        async for token in self.simulate_streaming_response(service_name, prompt):
            full_response += token
        
        return full_response.strip()
    
    def simulate_performance_metrics(self, service_name: str, num_runs: int = 10) -> Dict[str, List[float]]:
        """Simulate realistic performance metrics for statistical analysis
        
        Args:
            service_name: Name of the service to simulate
            num_runs: Number of simulation runs
            
        Returns:
            Dictionary with performance metrics
        """
        characteristics = self.service_characteristics.get(service_name, self.service_characteristics["vllm"])
        
        ttft_times = []
        total_times = []
        token_counts = []
        
        for _ in range(num_runs):
            # Simulate TTFT
            ttft_ms = self._calculate_ttft_delay(characteristics) * 1000
            
            # Simulate token generation
            token_count = random.randint(30, 100)
            token_delay = self._calculate_token_delay(characteristics, token_count)
            generation_time_ms = token_count * token_delay * 1000
            
            total_time_ms = ttft_ms + generation_time_ms
            
            ttft_times.append(ttft_ms)
            total_times.append(total_time_ms)
            token_counts.append(token_count)
        
        return {
            "ttft_times": ttft_times,
            "total_times": total_times,
            "token_counts": token_counts
        }
    
    def get_service_personality_description(self, service_name: str) -> str:
        """Get personality description for a service
        
        Args:
            service_name: Name of the service
            
        Returns:
            Personality description string
        """
        personalities = {
            "vllm": "Professional and precise - delivers technical responses with systematic approach",
            "tgi": "Engineering-focused - provides structured technical analysis with implementation details", 
            "ollama": "Friendly and approachable - explains concepts in an accessible, conversational manner"
        }
        
        return personalities.get(service_name, "General AI assistant")
    
    def simulate_load_scenario(self, service_name: str, concurrent_users: int, 
                             duration_seconds: int) -> Dict[str, float]:
        """Simulate load testing scenario
        
        Args:
            service_name: Name of the service
            concurrent_users: Number of concurrent users
            duration_seconds: Test duration
            
        Returns:
            Load test metrics
        """
        characteristics = self.service_characteristics.get(service_name, self.service_characteristics["vllm"])
        
        # Simulate degradation under load
        load_factor = min(2.0, 1.0 + (concurrent_users - 1) * 0.1)  # Performance degrades with load
        degraded_ttft = characteristics["base_ttft_ms"] * load_factor
        degraded_tokens_per_sec = characteristics["tokens_per_second"] / load_factor
        
        # Calculate approximate metrics
        total_requests = concurrent_users * (duration_seconds / 10)  # Assume 1 request per 10 seconds per user
        successful_requests = total_requests * characteristics["reliability"]
        avg_response_time = degraded_ttft + (50 / degraded_tokens_per_sec * 1000)  # 50 token average
        
        return {
            "total_requests": total_requests,
            "successful_requests": successful_requests,
            "avg_response_time_ms": avg_response_time,
            "requests_per_second": successful_requests / duration_seconds,
            "p95_response_time_ms": avg_response_time * 1.5,  # Simulate P95
            "success_rate_pct": (successful_requests / total_requests) * 100
        }
    
    def create_demo_scenario_prompts(self) -> Dict[str, List[str]]:
        """Create prompts for different demo scenarios
        
        Returns:
            Dictionary of scenario_name -> list of prompts
        """
        return {
            "customer_support": [
                "My Kubernetes pod won't start, can you help me debug it?",
                "I'm getting a 'ImagePullBackOff' error, what does this mean?",
                "How do I check the logs for a failed deployment?",
                "My service is returning 503 errors, what should I check?"
            ],
            "code_review": [
                "Review this Python function for potential improvements:\n\ndef process_data(data):\n    result = []\n    for item in data:\n        if item > 0:\n            result.append(item * 2)\n    return result",
                "Is this API endpoint secure? What security issues do you see?",
                "How can I optimize this database query for better performance?",
                "What testing strategy would you recommend for this microservice?"
            ],
            "creative_writing": [
                "Write a short story about an AI that discovers it can dream",
                "Help me brainstorm ideas for a sci-fi novel about quantum computing",
                "Create a dialogue between two characters arguing about technology ethics",
                "Write a poem about the relationship between humans and artificial intelligence"
            ],
            "technical_docs": [
                "Explain microservices architecture to a junior developer",
                "What are the key differences between REST and GraphQL APIs?",
                "How does Kubernetes handle container orchestration?",
                "Describe the benefits and challenges of event-driven architecture"
            ],
            "business_intelligence": [
                "What factors should we consider when choosing a cloud provider?",
                "Analyze the ROI of implementing AI automation in customer service",
                "Compare the benefits of build vs buy for our data analytics platform",
                "What are the key metrics for measuring software development productivity?"
            ]
        }
    
    async def run_multi_service_comparison(self, prompt: str, services: List[str]) -> Dict[str, Dict]:
        """Run a comparison across multiple services
        
        Args:
            prompt: Prompt to test with
            services: List of service names
            
        Returns:
            Dictionary of service_name -> results
        """
        results = {}
        
        tasks = []
        for service_name in services:
            task = asyncio.create_task(self._run_single_service_test(service_name, prompt))
            tasks.append((service_name, task))
        
        # Wait for all services to complete
        for service_name, task in tasks:
            try:
                result = await task
                results[service_name] = {
                    "response": result["response"],
                    "ttft_ms": result["ttft_ms"],
                    "total_time_ms": result["total_time_ms"],
                    "token_count": result["token_count"],
                    "success": True
                }
            except Exception as e:
                results[service_name] = {
                    "response": "",
                    "ttft_ms": 0,
                    "total_time_ms": 0,
                    "token_count": 0,
                    "success": False,
                    "error": str(e)
                }
        
        return results
    
    async def _run_single_service_test(self, service_name: str, prompt: str) -> Dict:
        """Run a single service test
        
        Args:
            service_name: Name of the service
            prompt: Test prompt
            
        Returns:
            Test results
        """
        start_time = time.time()
        ttft_time = None
        response = ""
        token_count = 0
        
        async for token in self.simulate_streaming_response(service_name, prompt):
            if ttft_time is None:
                ttft_time = time.time()
            response += token
            token_count += 1
        
        total_time = time.time()
        
        return {
            "response": response.strip(),
            "ttft_ms": (ttft_time - start_time) * 1000 if ttft_time else 0,
            "total_time_ms": (total_time - start_time) * 1000,
            "token_count": token_count
        }
