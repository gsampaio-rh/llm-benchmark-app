"""
Kubernetes/OpenShift pod metadata extraction.

Extracts pod information (CPU, Memory, GPU) using oc/kubectl commands
or Kubernetes API when available.
"""

import asyncio
import json
import logging
import os
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class ResourceAllocation:
    """Resource requests and limits for a pod."""
    cpu_request: Optional[str] = None      # e.g., "500m", "2"
    cpu_limit: Optional[str] = None        # e.g., "2000m", "4"
    memory_request: Optional[str] = None   # e.g., "1Gi", "512Mi"
    memory_limit: Optional[str] = None     # e.g., "4Gi", "8Gi"
    gpu_count: Optional[int] = None        # Number of GPUs
    gpu_type: Optional[str] = None         # e.g., "nvidia.com/gpu"
    
    def __str__(self) -> str:
        """Human-readable resource summary."""
        parts = []
        if self.cpu_request or self.cpu_limit:
            cpu = f"{self.cpu_request or '?'} → {self.cpu_limit or 'unlimited'}"
            parts.append(f"CPU: {cpu}")
        if self.memory_request or self.memory_limit:
            mem = f"{self.memory_request or '?'} → {self.memory_limit or 'unlimited'}"
            parts.append(f"RAM: {mem}")
        if self.gpu_count:
            parts.append(f"GPU: {self.gpu_count}x")
        return " | ".join(parts) if parts else "No resources"


@dataclass
class PodInfo:
    """Kubernetes/OpenShift pod information."""
    pod_name: Optional[str] = None
    namespace: Optional[str] = None
    node_name: Optional[str] = None
    pod_ip: Optional[str] = None
    service_name: Optional[str] = None
    replica_index: Optional[int] = None    # For StatefulSets (e.g., ollama-0, ollama-1)
    resources: Optional[ResourceAllocation] = None
    labels: Dict[str, str] = field(default_factory=dict)
    container_name: Optional[str] = None
    
    def __str__(self) -> str:
        """Human-readable pod summary."""
        parts = []
        if self.pod_name:
            parts.append(f"Pod: {self.pod_name}")
        if self.namespace:
            parts.append(f"NS: {self.namespace}")
        if self.node_name:
            parts.append(f"Node: {self.node_name}")
        return " | ".join(parts) if parts else "No pod info"


class K8sMetadataExtractor:
    """
    Extract pod metadata from Kubernetes/OpenShift.
    
    Uses `oc` commands to query pod information based on service URLs.
    Falls back gracefully when not in K8s or when commands fail.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._k8s_available: Optional[bool] = None
        self._oc_available: Optional[bool] = None
        self._current_namespace: Optional[str] = None
    
    async def is_k8s_available(self) -> bool:
        """Check if we're in a Kubernetes/OpenShift environment."""
        if self._k8s_available is not None:
            return self._k8s_available
        
        # Check for Kubernetes service account
        if os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount"):
            self._k8s_available = True
            return True
        
        # Check for Kubernetes environment variables
        if os.getenv("KUBERNETES_SERVICE_HOST"):
            self._k8s_available = True
            return True
        
        # Try running oc/kubectl command
        self._k8s_available = await self._check_cli_available()
        return self._k8s_available
    
    async def _check_cli_available(self) -> bool:
        """Check if oc or kubectl CLI is available."""
        # Check oc first (OpenShift)
        try:
            result = await asyncio.create_subprocess_exec(
                "oc", "version", "--client",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode == 0:
                self._oc_available = True
                self.logger.info("OpenShift CLI (oc) detected")
                return True
        except FileNotFoundError:
            pass
        
        # Try kubectl
        try:
            result = await asyncio.create_subprocess_exec(
                "kubectl", "version", "--client",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode == 0:
                self._oc_available = False
                self.logger.info("Kubernetes CLI (kubectl) detected")
                return True
        except FileNotFoundError:
            pass
        
        return False
    
    def _get_cli_command(self) -> str:
        """Get the appropriate CLI command (oc or kubectl)."""
        return "oc" if self._oc_available else "kubectl"
    
    async def get_current_namespace(self) -> str:
        """Get the current namespace."""
        if self._current_namespace:
            return self._current_namespace
        
        # Try getting from service account
        sa_namespace_file = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
        if os.path.exists(sa_namespace_file):
            try:
                with open(sa_namespace_file, 'r') as f:
                    self._current_namespace = f.read().strip()
                    return self._current_namespace
            except Exception as e:
                self.logger.debug(f"Could not read namespace from service account: {e}")
        
        # Try getting from oc/kubectl
        try:
            cmd = self._get_cli_command()
            result = await asyncio.create_subprocess_exec(
                cmd, "config", "view", "--minify", "-o", "jsonpath={..namespace}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await result.communicate()
            if result.returncode == 0 and stdout:
                self._current_namespace = stdout.decode().strip() or "default"
                return self._current_namespace
        except Exception as e:
            self.logger.debug(f"Could not get namespace from CLI: {e}")
        
        self._current_namespace = "default"
        return self._current_namespace
    
    def _extract_service_and_namespace_from_url(self, base_url: str) -> tuple[Optional[str], Optional[str]]:
        """
        Extract service name and namespace from base URL.
        
        Examples:
            http://ollama:11434 -> (ollama, None)
            http://ollama.default.svc.cluster.local:11434 -> (ollama, default)
            http://ollama-test-vllm-benchmark.apps.cluster.com -> (ollama-test, vllm-benchmark)
            https://vllm-test-vllm-benchmark.apps.cluster.com -> (vllm-test, vllm-benchmark)
        
        OpenShift route pattern: {service-name}-{namespace}.apps.{cluster}.{domain}
        """
        try:
            parsed = urlparse(base_url)
            hostname = parsed.hostname or parsed.netloc.split(':')[0]
            
            # Check if it's an OpenShift route (contains .apps.)
            if '.apps.' in hostname:
                # Extract the part before .apps.
                route_part = hostname.split('.apps.')[0]
                
                # OpenShift route pattern: {service}-{namespace}.apps...
                # Try to identify namespace by looking for common patterns
                # Common namespaces might have patterns like: default, vllm-benchmark, etc.
                
                # Try known multi-part namespace patterns first
                known_namespace_patterns = ['vllm-benchmark', 'llm-benchmark', 'benchmark']
                
                for ns_pattern in known_namespace_patterns:
                    if route_part.endswith(f'-{ns_pattern}'):
                        # Found a match
                        service_name = route_part[:-len(f'-{ns_pattern}')]
                        return service_name, ns_pattern
                
                # Fallback: assume last part after last hyphen is namespace
                parts = route_part.split('-')
                if len(parts) >= 2:
                    # Try different split points
                    # For "ollama-test-vllm-benchmark", try:
                    # 1. Last 2 parts as namespace: "vllm-benchmark"
                    # 2. Last 1 part as namespace: "benchmark"
                    
                    # Check if last 2 parts form a reasonable namespace
                    if len(parts) >= 3:
                        potential_ns = f"{parts[-2]}-{parts[-1]}"
                        service_name = '-'.join(parts[:-2])
                        if service_name:  # Make sure service name isn't empty
                            return service_name, potential_ns
                    
                    # Otherwise use last part only
                    namespace = parts[-1]
                    service_name = '-'.join(parts[:-1])
                    return service_name, namespace
                else:
                    return route_part, None
            
            # Check if it's a K8s service URL (contains .svc.)
            elif '.svc.' in hostname or '.svc' in hostname:
                parts = hostname.split('.')
                service_name = parts[0]
                namespace = parts[1] if len(parts) > 1 else None
                return service_name, namespace
            
            # Simple hostname (e.g., ollama:11434)
            else:
                service_name = hostname.split('.')[0]
                return service_name, None
                
        except Exception as e:
            self.logger.warning(f"Could not parse service from URL {base_url}: {e}")
            return None, None
    
    async def get_pod_info_by_service(
        self,
        service_name: str,
        namespace: Optional[str] = None
    ) -> Optional[PodInfo]:
        """
        Get pod information by service name.
        
        Args:
            service_name: Name of the service (e.g., "ollama", "vllm")
            namespace: Kubernetes namespace (defaults to current namespace)
            
        Returns:
            PodInfo object or None if not found
        """
        if not await self.is_k8s_available():
            return None
        
        ns = namespace or await self.get_current_namespace()
        cmd = self._get_cli_command()
        
        try:
            # Get pods with label matching service name or matching pod name prefix
            result = await asyncio.create_subprocess_exec(
                cmd, "get", "pods",
                "-n", ns,
                "-o", "json",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await result.communicate()
            
            if result.returncode != 0:
                self.logger.warning(f"Failed to get pods: {stderr.decode()}")
                return None
            
            pods_data = json.loads(stdout.decode())
            
            # Find matching pod
            for pod in pods_data.get("items", []):
                pod_name = pod["metadata"]["name"]
                labels = pod["metadata"].get("labels", {})
                
                # Match by multiple criteria:
                # 1. app.kubernetes.io/instance label matches service name (Helm chart pattern)
                app_instance = labels.get("app.kubernetes.io/instance", "")
                # 2. app.kubernetes.io/name label
                app_name = labels.get("app.kubernetes.io/name", "")
                # 3. app label (traditional pattern)
                app_label = labels.get("app", "")
                # 4. Pod name prefix
                
                if (app_instance == service_name or 
                    app_name == service_name or 
                    app_label == service_name or 
                    pod_name.startswith(service_name)):
                    return self._parse_pod_info(pod, ns)
            
            self.logger.debug(f"No pod found matching service {service_name} in namespace {ns}")
            return None
            
        except Exception as e:
            self.logger.warning(f"Error getting pod info for service {service_name}: {e}")
            return None
    
    async def get_pod_info_by_url(self, base_url: str) -> Optional[PodInfo]:
        """
        Get pod information from a base URL.
        
        Args:
            base_url: Engine base URL (e.g., "http://ollama:11434")
            
        Returns:
            PodInfo object or None if not found
        """
        service_name, url_namespace = self._extract_service_and_namespace_from_url(base_url)
        if not service_name:
            return None
        
        # Use namespace from URL if available, otherwise use current/default
        namespace = url_namespace if url_namespace else None
        
        return await self.get_pod_info_by_service(service_name, namespace)
    
    def _parse_pod_info(self, pod_data: Dict[str, Any], namespace: str) -> PodInfo:
        """Parse pod JSON data into PodInfo object."""
        metadata = pod_data.get("metadata", {})
        spec = pod_data.get("spec", {})
        status = pod_data.get("status", {})
        
        pod_name = metadata.get("name", "")
        
        # Extract replica index from StatefulSet pods (e.g., "ollama-0" -> 0)
        replica_index = None
        match = re.match(r".*-(\d+)$", pod_name)
        if match:
            replica_index = int(match.group(1))
        
        # Extract resources from first container
        resources = None
        containers = spec.get("containers", [])
        if containers:
            container = containers[0]
            container_name = container.get("name")
            container_resources = container.get("resources", {})
            
            if container_resources:
                resources = self._parse_resources(container_resources)
        
        return PodInfo(
            pod_name=pod_name,
            namespace=namespace,
            node_name=spec.get("nodeName"),
            pod_ip=status.get("podIP"),
            service_name=metadata.get("labels", {}).get("app"),
            replica_index=replica_index,
            resources=resources,
            labels=metadata.get("labels", {}),
            container_name=container_name
        )
    
    def _parse_resources(self, resources_data: Dict[str, Any]) -> ResourceAllocation:
        """Parse resource requests and limits."""
        requests = resources_data.get("requests", {})
        limits = resources_data.get("limits", {})
        
        allocation = ResourceAllocation(
            cpu_request=requests.get("cpu"),
            cpu_limit=limits.get("cpu"),
            memory_request=requests.get("memory"),
            memory_limit=limits.get("memory")
        )
        
        # Check for GPU resources
        gpu_keys = ["nvidia.com/gpu", "amd.com/gpu", "gpu"]
        for key in gpu_keys:
            if key in limits:
                try:
                    allocation.gpu_count = int(limits[key])
                    allocation.gpu_type = key
                    break
                except (ValueError, TypeError):
                    pass
        
        return allocation


# Global instance
_extractor: Optional[K8sMetadataExtractor] = None


def get_k8s_extractor() -> K8sMetadataExtractor:
    """Get or create the global K8s metadata extractor."""
    global _extractor
    if _extractor is None:
        _extractor = K8sMetadataExtractor()
    return _extractor


async def get_pod_info_for_url(base_url: str) -> Optional[PodInfo]:
    """
    Convenience function to get pod info for a base URL.
    
    Args:
        base_url: Engine base URL
        
    Returns:
        PodInfo or None
    """
    extractor = get_k8s_extractor()
    return await extractor.get_pod_info_by_url(base_url)

