"""
Connection manager for handling multiple engine adapters.

This module provides centralized management of engine connections,
health monitoring, and adapter lifecycle management.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Type
from datetime import datetime, timedelta

from ..models.engine_config import EngineConfig, EngineHealthStatus, EngineInfo, ModelInfo, BenchmarkConfig
from ..adapters.base_adapter import BaseAdapter, AdapterError, ConnectionError


logger = logging.getLogger(__name__)


class ConnectionManagerError(Exception):
    """Raised when connection manager operations fail."""
    pass


class ConnectionManager:
    """
    Manages connections to multiple LLM engines.
    
    Provides centralized management of engine adapters, health monitoring,
    and connection lifecycle management.
    """
    
    def __init__(self):
        """Initialize the connection manager."""
        self.adapters: Dict[str, BaseAdapter] = {}
        self.adapter_classes: Dict[str, Type[BaseAdapter]] = {}
        self.last_health_check: Dict[str, datetime] = {}
        self.health_cache: Dict[str, EngineHealthStatus] = {}
        self.health_cache_ttl = timedelta(minutes=5)  # Cache health status for 5 minutes
        
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initialized connection manager")
    
    def register_adapter_class(self, engine_type: str, adapter_class: Type[BaseAdapter]) -> None:
        """
        Register an adapter class for a specific engine type.
        
        Args:
            engine_type: Engine type identifier (e.g., 'ollama', 'vllm', 'tgi')
            adapter_class: Adapter class to register
        """
        self.adapter_classes[engine_type] = adapter_class
        self.logger.info(f"Registered adapter class for {engine_type}: {adapter_class.__name__}")
    
    async def register_engine(self, config: EngineConfig) -> bool:
        """
        Register and initialize an engine connection.
        
        Args:
            config: Engine configuration
            
        Returns:
            True if registration successful, False otherwise
            
        Raises:
            ConnectionManagerError: If adapter class not found or initialization fails
        """
        try:
            # Check if adapter class is registered
            if config.engine_type not in self.adapter_classes:
                raise ConnectionManagerError(
                    f"No adapter class registered for engine type: {config.engine_type}"
                )
            
            # Create adapter instance
            adapter_class = self.adapter_classes[config.engine_type]
            adapter = adapter_class(config)
            
            # Test connection
            health_status = await adapter.health_check()
            if not health_status.is_healthy:
                self.logger.warning(
                    f"Engine {config.name} is not healthy: {health_status.error_message}"
                )
                await adapter.close()
                return False
            
            # Store adapter
            self.adapters[config.name] = adapter
            self.health_cache[config.name] = health_status
            self.last_health_check[config.name] = datetime.utcnow()
            
            self.logger.info(f"Successfully registered engine: {config.name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to register engine {config.name}: {e}")
            raise ConnectionManagerError(f"Failed to register engine {config.name}: {e}")
    
    async def register_engines_from_config(self, config: BenchmarkConfig) -> Dict[str, bool]:
        """
        Register multiple engines from benchmark configuration.
        
        Args:
            config: Benchmark configuration with engine list
            
        Returns:
            Dictionary mapping engine names to registration success status
        """
        results = {}
        
        for engine_config in config.engines:
            try:
                success = await self.register_engine(engine_config)
                results[engine_config.name] = success
            except Exception as e:
                self.logger.error(f"Failed to register {engine_config.name}: {e}")
                results[engine_config.name] = False
        
        successful = sum(1 for success in results.values() if success)
        total = len(results)
        self.logger.info(f"Registered {successful}/{total} engines successfully")
        
        return results
    
    def get_adapter(self, engine_name: str) -> Optional[BaseAdapter]:
        """
        Get adapter for a specific engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            BaseAdapter instance or None if not found
        """
        return self.adapters.get(engine_name)
    
    def list_engines(self) -> List[str]:
        """
        List all registered engine names.
        
        Returns:
            List of engine names
        """
        return list(self.adapters.keys())
    
    def list_engine_types(self) -> List[str]:
        """
        List all registered engine types.
        
        Returns:
            List of unique engine types
        """
        return list(set(adapter.config.engine_type for adapter in self.adapters.values()))
    
    async def health_check(self, engine_name: str, use_cache: bool = True) -> EngineHealthStatus:
        """
        Check health of a specific engine.
        
        Args:
            engine_name: Name of the engine to check
            use_cache: Whether to use cached health status if available
            
        Returns:
            EngineHealthStatus
            
        Raises:
            ConnectionManagerError: If engine not found
        """
        if engine_name not in self.adapters:
            raise ConnectionManagerError(f"Engine not found: {engine_name}")
        
        # Check cache if requested
        if use_cache and engine_name in self.health_cache:
            last_check = self.last_health_check.get(engine_name)
            if last_check and datetime.utcnow() - last_check < self.health_cache_ttl:
                self.logger.debug(f"Using cached health status for {engine_name}")
                return self.health_cache[engine_name]
        
        # Perform fresh health check
        adapter = self.adapters[engine_name]
        try:
            health_status = await adapter.health_check()
            
            # Update cache
            self.health_cache[engine_name] = health_status
            self.last_health_check[engine_name] = datetime.utcnow()
            
            return health_status
            
        except Exception as e:
            # Create unhealthy status for failed check
            error_status = EngineHealthStatus(
                engine_name=engine_name,
                is_healthy=False,
                error_message=str(e)
            )
            
            # Update cache with error status
            self.health_cache[engine_name] = error_status
            self.last_health_check[engine_name] = datetime.utcnow()
            
            return error_status
    
    async def health_check_all(self, use_cache: bool = True) -> Dict[str, EngineHealthStatus]:
        """
        Check health of all registered engines.
        
        Args:
            use_cache: Whether to use cached health status if available
            
        Returns:
            Dictionary mapping engine names to health status
        """
        if not self.adapters:
            self.logger.warning("No engines registered for health check")
            return {}
        
        # Run health checks concurrently
        tasks = []
        engine_names = []
        
        for engine_name in self.adapters.keys():
            task = self.health_check(engine_name, use_cache=use_cache)
            tasks.append(task)
            engine_names.append(engine_name)
        
        # Wait for all health checks to complete
        health_statuses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results = {}
        for engine_name, status in zip(engine_names, health_statuses):
            if isinstance(status, Exception):
                # Create error status for exceptions
                results[engine_name] = EngineHealthStatus(
                    engine_name=engine_name,
                    is_healthy=False,
                    error_message=str(status)
                )
            else:
                results[engine_name] = status
        
        healthy_count = sum(1 for status in results.values() if status.is_healthy)
        total_count = len(results)
        self.logger.info(f"Health check completed: {healthy_count}/{total_count} engines healthy")
        
        return results
    
    async def get_engine_info(self, engine_name: str) -> EngineInfo:
        """
        Get detailed information about a specific engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            EngineInfo with engine details
            
        Raises:
            ConnectionManagerError: If engine not found
        """
        if engine_name not in self.adapters:
            raise ConnectionManagerError(f"Engine not found: {engine_name}")
        
        adapter = self.adapters[engine_name]
        return await adapter.get_engine_info()
    
    async def discover_models(self, engine_name: str) -> List[ModelInfo]:
        """
        Discover available models for a specific engine.
        
        Args:
            engine_name: Name of the engine
            
        Returns:
            List of available models
            
        Raises:
            ConnectionManagerError: If engine not found
        """
        if engine_name not in self.adapters:
            raise ConnectionManagerError(f"Engine not found: {engine_name}")
        
        adapter = self.adapters[engine_name]
        return await adapter.list_models()
    
    async def discover_all_models(self) -> Dict[str, List[ModelInfo]]:
        """
        Discover models for all registered engines.
        
        Returns:
            Dictionary mapping engine names to model lists
        """
        if not self.adapters:
            return {}
        
        # Run model discovery concurrently
        tasks = []
        engine_names = []
        
        for engine_name in self.adapters.keys():
            task = self.discover_models(engine_name)
            tasks.append(task)
            engine_names.append(engine_name)
        
        # Wait for all discoveries to complete
        model_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        results = {}
        for engine_name, models in zip(engine_names, model_lists):
            if isinstance(models, Exception):
                self.logger.error(f"Failed to discover models for {engine_name}: {models}")
                results[engine_name] = []
            else:
                results[engine_name] = models
        
        total_models = sum(len(models) for models in results.values())
        self.logger.info(f"Discovered {total_models} models across {len(results)} engines")
        
        return results
    
    async def close_all(self) -> None:
        """Close all adapter connections and clean up resources."""
        if not self.adapters:
            return
        
        self.logger.info(f"Closing {len(self.adapters)} adapter connections")
        
        # Close all adapters concurrently
        close_tasks = [adapter.close() for adapter in self.adapters.values()]
        await asyncio.gather(*close_tasks, return_exceptions=True)
        
        # Clear all state
        self.adapters.clear()
        self.health_cache.clear()
        self.last_health_check.clear()
        
        self.logger.info("All adapter connections closed")
    
    async def __aenter__(self):
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all()
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get a summary of the connection manager state.
        
        Returns:
            Dictionary with connection manager statistics
        """
        healthy_engines = []
        unhealthy_engines = []
        
        for engine_name, health_status in self.health_cache.items():
            if health_status.is_healthy:
                healthy_engines.append(engine_name)
            else:
                unhealthy_engines.append(engine_name)
        
        return {
            "total_engines": len(self.adapters),
            "healthy_engines": len(healthy_engines),
            "unhealthy_engines": len(unhealthy_engines),
            "registered_engine_types": self.list_engine_types(),
            "engine_names": self.list_engines(),
            "healthy_engine_names": healthy_engines,
            "unhealthy_engine_names": unhealthy_engines,
            "last_health_check": max(self.last_health_check.values()) if self.last_health_check else None
        }


# Global connection manager instance
connection_manager = ConnectionManager()

