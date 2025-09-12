"""
Service interfaces and abstractions.

This module defines clean interfaces and abstractions for all major components,
enabling dependency injection, testing, and future extensibility.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, AsyncGenerator, Any, Protocol
from dataclasses import dataclass

from ..race.models import ThreeWayRace, RaceParticipant, EngineInfo
from ..api_clients import GenerationRequest, GenerationResponse
from ..service_discovery import ServiceInfo
from .api_adapter import StreamingMetrics
from .service_adapter import DiscoveryResult
from .config_manager import ConfigurationContext


# ==================== Core Service Interfaces ====================

class IAPIClient(Protocol):
    """Interface for API clients"""
    
    async def stream_generate(self, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream generate response"""
        ...
    
    async def health_check(self) -> bool:
        """Check API health"""
        ...


class IServiceDiscovery(ABC):
    """Interface for service discovery"""
    
    @abstractmethod
    async def discover_services(self, namespace: str, manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
        """Discover available services"""
        pass
    
    @abstractmethod
    async def health_check_service(self, service_info: ServiceInfo) -> bool:
        """Check health of a specific service"""
        pass


class IAPIAdapter(ABC):
    """Interface for API adapters"""
    
    @abstractmethod
    async def stream_response(self, service_name: str, request: GenerationRequest) -> AsyncGenerator[str, None]:
        """Stream response from service"""
        pass
    
    @abstractmethod
    async def get_service_info(self, service_name: str) -> EngineInfo:
        """Get service technical information"""
        pass
    
    @abstractmethod
    async def health_check_all(self) -> Dict[str, bool]:
        """Health check all services"""
        pass


class IServiceAdapter(ABC):
    """Interface for service adapters"""
    
    @abstractmethod
    async def discover_services_with_retry(self, namespace: str, manual_urls: Optional[Dict[str, str]] = None) -> DiscoveryResult:
        """Discover services with retry logic"""
        pass
    
    @abstractmethod
    async def get_service_by_name(self, service_name: str, namespace: str) -> Optional[ServiceInfo]:
        """Get specific service by name"""
        pass


# ==================== Business Logic Interfaces ====================

class IRaceEngine(ABC):
    """Interface for race execution engines"""
    
    @abstractmethod
    async def execute_single_race(self, race: ThreeWayRace, use_real_apis: bool = False) -> 'RaceResults':
        """Execute a single race"""
        pass
    
    @abstractmethod
    async def execute_statistical_race(self, race: ThreeWayRace, num_runs: int, use_real_apis: bool = False) -> 'StatisticalResults':
        """Execute statistical race with multiple runs"""
        pass
    
    @abstractmethod
    def create_demo_race(self, prompt: str, services: List[str]) -> ThreeWayRace:
        """Create a demo race configuration"""
        pass


class IPerformanceAnalyzer(ABC):
    """Interface for performance analysis"""
    
    @abstractmethod
    def analyze_service_performance(self, stats: 'RaceStatistics', total_runs: int) -> 'ServicePerformanceProfile':
        """Analyze performance of a single service"""
        pass
    
    @abstractmethod
    def determine_winner(self, race: ThreeWayRace, total_runs: Optional[int] = None) -> tuple[Optional[str], str]:
        """Determine race winner with reasoning"""
        pass
    
    @abstractmethod
    def compare_services(self, race: ThreeWayRace, total_runs: Optional[int] = None) -> Dict[str, 'ServicePerformanceProfile']:
        """Compare all services in a race"""
        pass


class IBusinessAnalyzer(ABC):
    """Interface for business impact analysis"""
    
    @abstractmethod
    def calculate_time_savings(self, winner_ttft: float, loser_ttft: float, daily_interactions: int) -> 'TimeSavings':
        """Calculate time savings between services"""
        pass
    
    @abstractmethod
    def generate_impact_summary(self, race_results: Dict[str, 'ServicePerformanceProfile'], winner: str) -> 'BusinessImpactSummary':
        """Generate comprehensive business impact summary"""
        pass


class IDemoSimulator(ABC):
    """Interface for demo simulation"""
    
    @abstractmethod
    async def simulate_streaming_response(self, service_name: str, prompt: str) -> AsyncGenerator[str, None]:
        """Simulate streaming response"""
        pass
    
    @abstractmethod
    def simulate_performance_metrics(self, service_name: str, num_runs: int) -> Dict[str, List[float]]:
        """Simulate performance metrics"""
        pass
    
    @abstractmethod
    async def run_multi_service_comparison(self, prompt: str, services: List[str]) -> Dict[str, Dict]:
        """Run comparison across multiple services"""
        pass


# ==================== Visualization Interfaces ====================

class IVisualizer(ABC):
    """Interface for visualizers"""
    
    @abstractmethod
    def render(self, data: Any) -> Any:
        """Render visualization with given data"""
        pass


class IThreeWayPanel(ABC):
    """Interface for three-way panel components"""
    
    @abstractmethod
    def update_column(self, position: str, content: Any, title: Optional[str] = None):
        """Update specific column content"""
        pass
    
    @abstractmethod
    def get_layout(self) -> Any:
        """Get the layout for display"""
        pass


class IRaceDisplay(ABC):
    """Interface for race display components"""
    
    @abstractmethod
    async def run_live_race(self, race: ThreeWayRace, api_adapter: IAPIAdapter) -> None:
        """Execute live race with real-time updates"""
        pass
    
    @abstractmethod
    def setup_race(self, race: ThreeWayRace):
        """Setup race display with participants"""
        pass


class IServicePanel(ABC):
    """Interface for service panel components"""
    
    @abstractmethod
    def create_panel(self, status: str, status_color: str, show_response: bool = False) -> Any:
        """Create formatted panel for service display"""
        pass
    
    @abstractmethod
    def update_participant(self, participant: RaceParticipant):
        """Update participant information"""
        pass


# ==================== Configuration Interfaces ====================

class IConfigurationManager(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    async def load_configuration(self, sources: List['ConfigSource']) -> ConfigurationContext:
        """Load configuration from multiple sources"""
        pass
    
    @abstractmethod
    async def create_default_context(self, config_file: Optional[str] = None) -> ConfigurationContext:
        """Create default configuration context"""
        pass


class IDependencyInjector(ABC):
    """Interface for dependency injection"""
    
    @abstractmethod
    def register_instance(self, interface: type, instance: Any):
        """Register a singleton instance"""
        pass
    
    @abstractmethod
    def register_factory(self, interface: type, factory: callable):
        """Register a factory function"""
        pass
    
    @abstractmethod
    def get(self, interface: type) -> Any:
        """Get an instance of the requested type"""
        pass


# ==================== Error Handling Interfaces ====================

class IErrorHandler(ABC):
    """Interface for error handlers"""
    
    @abstractmethod
    def can_handle(self, error: Exception, context: 'ErrorContext') -> bool:
        """Check if this handler can process the error"""
        pass
    
    @abstractmethod
    def handle_error(self, error: Exception, context: 'ErrorContext') -> 'ErrorDetails':
        """Handle the error and return error details"""
        pass


# ==================== Factory Interfaces ====================

class IServiceFactory(ABC):
    """Interface for service factories"""
    
    @abstractmethod
    def create_api_adapter(self, config: ConfigurationContext) -> IAPIAdapter:
        """Create API adapter instance"""
        pass
    
    @abstractmethod
    def create_service_adapter(self, config: ConfigurationContext) -> IServiceAdapter:
        """Create service adapter instance"""
        pass
    
    @abstractmethod
    def create_race_engine(self, config: ConfigurationContext) -> IRaceEngine:
        """Create race engine instance"""
        pass


class IVisualizationFactory(ABC):
    """Interface for visualization factories"""
    
    @abstractmethod
    def create_three_way_panel(self, left_title: str, center_title: str, right_title: str) -> IThreeWayPanel:
        """Create three-way panel instance"""
        pass
    
    @abstractmethod
    def create_race_display(self) -> IRaceDisplay:
        """Create race display instance"""
        pass
    
    @abstractmethod
    def create_service_panel(self, participant: RaceParticipant) -> IServicePanel:
        """Create service panel instance"""
        pass


# ==================== Aggregate Interfaces ====================

class IBenchmarkingSystem(ABC):
    """High-level interface for the complete benchmarking system"""
    
    @abstractmethod
    async def initialize(self, config_file: Optional[str] = None) -> ConfigurationContext:
        """Initialize the benchmarking system"""
        pass
    
    @abstractmethod
    async def discover_services(self, namespace: str = "vllm-benchmark") -> DiscoveryResult:
        """Discover available services"""
        pass
    
    @abstractmethod
    async def run_benchmark(self, prompt: str, services: List[str], use_real_apis: bool = False) -> 'RaceResults':
        """Run a complete benchmark"""
        pass
    
    @abstractmethod
    async def run_statistical_benchmark(self, prompt: str, services: List[str], num_runs: int = 10) -> 'StatisticalResults':
        """Run statistical benchmark with multiple iterations"""
        pass


class IConversationSystem(ABC):
    """High-level interface for conversation visualization system"""
    
    @abstractmethod
    async def run_conversation_scenario(self, scenario: str, prompt_index: int, services: List[str]) -> None:
        """Run a conversation scenario"""
        pass
    
    @abstractmethod
    async def run_three_way_race(self, prompt: str, services: List[str]) -> None:
        """Run a three-way performance race"""
        pass
    
    @abstractmethod
    def display_scenario_menu(self) -> None:
        """Display available scenarios"""
        pass


# ==================== Data Transfer Objects ====================

@dataclass
class ServiceConfiguration:
    """Configuration for a specific service"""
    name: str
    url: Optional[str] = None
    enabled: bool = True
    timeout_seconds: int = 30
    retry_attempts: int = 3
    custom_headers: Dict[str, str] = None
    
    def __post_init__(self):
        if self.custom_headers is None:
            self.custom_headers = {}


@dataclass
class BenchmarkConfiguration:
    """Configuration for benchmark execution"""
    services: List[ServiceConfiguration]
    default_prompt: str = "Explain transformers in simple terms"
    use_real_apis: bool = False
    statistical_runs: int = 10
    timeout_seconds: int = 60
    concurrent_requests: bool = True


@dataclass
class VisualizationConfiguration:
    """Configuration for visualization components"""
    theme: str = "default"
    colors: Dict[str, str] = None
    show_technical_details: bool = True
    show_business_impact: bool = True
    auto_refresh: bool = False
    refresh_interval_ms: int = 1000
    
    def __post_init__(self):
        if self.colors is None:
            self.colors = {
                "vllm": "blue",
                "tgi": "green", 
                "ollama": "orange3"
            }


# ==================== Service Registry ====================

class ServiceRegistry:
    """Registry for service instances and factories"""
    
    def __init__(self):
        """Initialize service registry"""
        self._instances: Dict[type, Any] = {}
        self._factories: Dict[type, callable] = {}
        self._singletons: Dict[type, Any] = {}
    
    def register_singleton(self, interface: type, instance: Any):
        """Register a singleton instance"""
        self._singletons[interface] = instance
    
    def register_factory(self, interface: type, factory: callable):
        """Register a factory for creating instances"""
        self._factories[interface] = factory
    
    def register_instance(self, interface: type, instance: Any):
        """Register a specific instance"""
        self._instances[interface] = instance
    
    def get(self, interface: type) -> Any:
        """Get instance of the requested interface"""
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]
        
        # Check registered instances
        if interface in self._instances:
            return self._instances[interface]
        
        # Use factory if available
        if interface in self._factories:
            factory = self._factories[interface]
            instance = factory()
            # Cache as singleton
            self._singletons[interface] = instance
            return instance
        
        raise ValueError(f"No registration found for interface: {interface}")
    
    def has(self, interface: type) -> bool:
        """Check if interface is registered"""
        return (interface in self._singletons or 
                interface in self._instances or 
                interface in self._factories)
    
    def clear(self):
        """Clear all registrations"""
        self._instances.clear()
        self._factories.clear()
        self._singletons.clear()


# Global service registry
service_registry = ServiceRegistry()
