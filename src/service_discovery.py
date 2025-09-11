"""
Service Discovery for vLLM Benchmarking
Enhanced service discovery with multiple fallback strategies
"""

import os
import time
import subprocess
import json
import asyncio
from pathlib import Path
from typing import Dict, Optional, List
from dataclasses import dataclass

import httpx
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@dataclass
class ServiceInfo:
    """Service information with enhanced metadata"""
    name: str
    url: Optional[str] = None
    internal_url: Optional[str] = None
    status: str = "unknown"
    response_time: Optional[float] = None
    service_type: Optional[str] = None
    port: Optional[int] = None
    health_endpoint: str = "/health"

class ServiceDiscovery:
    """Enhanced service discovery with multiple fallback strategies"""
    
    def __init__(self, namespace: str = "vllm-benchmark"):
        self.namespace = namespace
        self.console = console
        
        # Expected services configuration
        self.expected_services = {
            "vllm": {
                "port": 8000,
                "health_endpoints": ["/health", "/v1/models"],
                "service_names": ["vllm", "vllm-test", "vllm-dev"]
            },
            "tgi": {
                "port": 8080,
                "health_endpoints": ["/health", "/info"],
                "service_names": ["tgi", "tgi-test", "tgi-dev"]
            },
            "ollama": {
                "port": 11434,
                "health_endpoints": ["/api/tags", "/api/version"],
                "service_names": ["ollama", "ollama-test", "ollama-dev"]
            }
        }
    
    async def discover_all_services(self, manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
        """Main service discovery entry point"""
        self.console.print("[blue]🔍 Starting service discovery...[/blue]")
        
        services = {}
        
        # Initialize service info objects
        for service_name, config in self.expected_services.items():
            services[service_name] = ServiceInfo(
                name=service_name,
                service_type=service_name,
                port=config["port"],
                health_endpoint=config["health_endpoints"][0]
            )
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            
            task = progress.add_task("Discovering services...", total=len(services))
            
            for service_name, service_info in services.items():
                # Apply manual URL override if provided
                if manual_urls and service_name in manual_urls:
                    service_info.url = manual_urls[service_name]
                    service_info.status = "manual_override"
                    self.console.print(f"[green]✅ Manual override {service_name}: {service_info.url}[/green]")
                else:
                    # Attempt automatic discovery
                    await self._discover_service_url(service_info)
                
                progress.advance(task)
        
        return services
    
    async def _discover_service_url(self, service_info: ServiceInfo) -> None:
        """Discover service URL using multiple strategies"""
        config = self.expected_services[service_info.name]
        
        # Strategy 1: OpenShift Routes
        url = await self._find_openshift_route(service_info.name, config["service_names"])
        if url:
            service_info.url = url
            service_info.status = "discovered_route"
            self.console.print(f"[dim]Found {service_info.name} route: {url}[/dim]")
            return
        
        # Strategy 2: Kubernetes Ingress
        url = await self._find_kubernetes_ingress(service_info.name, config["service_names"])
        if url:
            service_info.url = url
            service_info.status = "discovered_ingress"
            self.console.print(f"[dim]Found {service_info.name} ingress: {url}[/dim]")
            return
        
        # Strategy 3: NodePort Services
        url = await self._find_nodeport_service(service_info.name, config["service_names"], service_info.port)
        if url:
            service_info.url = url
            service_info.status = "discovered_nodeport"
            self.console.print(f"[dim]Found {service_info.name} NodePort: {url}[/dim]")
            return
        
        # Strategy 4: LoadBalancer Services
        url = await self._find_loadbalancer_service(service_info.name, config["service_names"], service_info.port)
        if url:
            service_info.url = url
            service_info.status = "discovered_loadbalancer"
            self.console.print(f"[dim]Found {service_info.name} LoadBalancer: {url}[/dim]")
            return
        
        # Strategy 5: Internal cluster service (fallback)
        if await self._is_running_in_cluster():
            internal_url = await self._find_internal_service(service_info.name, config["service_names"], service_info.port)
            if internal_url:
                service_info.url = internal_url
                service_info.internal_url = internal_url
                service_info.status = "discovered_internal"
                self.console.print(f"[yellow]⚠️ Using internal service URL for {service_info.name}: {internal_url}[/yellow]")
                return
        
        # No URL found
        service_info.status = "not_found"
        self.console.print(f"[dim]{service_info.name}: No external URL found[/dim]")
    
    async def _find_openshift_route(self, service_name: str, service_names: List[str]) -> Optional[str]:
        """Find OpenShift route for service"""
        try:
            cmd = ["oc", "get", "routes", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                routes_data = json.loads(result.stdout)
                for route in routes_data.get("items", []):
                    route_name = route["metadata"]["name"].lower()
                    
                    # Check if route matches any expected service name
                    for svc_name in service_names:
                        if svc_name.lower() in route_name:
                            host = route["spec"]["host"]
                            # Check if TLS is configured
                            if "tls" in route["spec"] and route["spec"]["tls"]:
                                return f"https://{host}"
                            else:
                                return f"http://{host}"
            
            return None
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return None
    
    async def _find_kubernetes_ingress(self, service_name: str, service_names: List[str]) -> Optional[str]:
        """Find Kubernetes ingress for service"""
        try:
            cmd = ["kubectl", "get", "ingress", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                ingress_data = json.loads(result.stdout)
                for ingress in ingress_data.get("items", []):
                    ingress_name = ingress["metadata"]["name"].lower()
                    
                    # Check if ingress matches any expected service name
                    for svc_name in service_names:
                        if svc_name.lower() in ingress_name:
                            rules = ingress["spec"].get("rules", [])
                            if rules:
                                host = rules[0].get("host")
                                if host:
                                    # Check for TLS
                                    if "tls" in ingress["spec"]:
                                        return f"https://{host}"
                                    else:
                                        return f"http://{host}"
            
            return None
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return None
    
    async def _find_nodeport_service(self, service_name: str, service_names: List[str], target_port: int) -> Optional[str]:
        """Find NodePort service and construct external URL"""
        try:
            cmd = ["kubectl", "get", "svc", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                for svc in services_data.get("items", []):
                    svc_name = svc["metadata"]["name"].lower()
                    
                    # Check if service matches any expected service name
                    for expected_name in service_names:
                        if expected_name.lower() in svc_name:
                            svc_type = svc["spec"].get("type", "ClusterIP")
                            if svc_type == "NodePort":
                                # Find the NodePort for our target port
                                for port_spec in svc["spec"].get("ports", []):
                                    if (port_spec.get("port") == target_port or 
                                        port_spec.get("targetPort") == target_port):
                                        node_port = port_spec.get("nodePort")
                                        if node_port:
                                            # Get a node IP
                                            node_ip = await self._get_node_ip()
                                            if node_ip:
                                                return f"http://{node_ip}:{node_port}"
            
            return None
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return None
    
    async def _find_loadbalancer_service(self, service_name: str, service_names: List[str], target_port: int) -> Optional[str]:
        """Find LoadBalancer service external IP"""
        try:
            cmd = ["kubectl", "get", "svc", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                for svc in services_data.get("items", []):
                    svc_name = svc["metadata"]["name"].lower()
                    
                    # Check if service matches any expected service name
                    for expected_name in service_names:
                        if expected_name.lower() in svc_name:
                            svc_type = svc["spec"].get("type", "ClusterIP")
                            if svc_type == "LoadBalancer":
                                # Check for external IP
                                status = svc.get("status", {})
                                ingress = status.get("loadBalancer", {}).get("ingress", [])
                                if ingress:
                                    external_ip = ingress[0].get("ip") or ingress[0].get("hostname")
                                    if external_ip:
                                        return f"http://{external_ip}:{target_port}"
            
            return None
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return None
    
    async def _get_node_ip(self) -> Optional[str]:
        """Get an external node IP"""
        try:
            cmd = ["kubectl", "get", "nodes", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                nodes_data = json.loads(result.stdout)
                for node in nodes_data.get("items", []):
                    addresses = node["status"].get("addresses", [])
                    # Prefer ExternalIP, fallback to InternalIP
                    for addr_type in ["ExternalIP", "InternalIP"]:
                        for addr in addresses:
                            if addr["type"] == addr_type:
                                return addr["address"]
            
            return None
            
        except (subprocess.SubprocessError, subprocess.TimeoutExpired, json.JSONDecodeError, KeyError):
            return None
    
    async def _is_running_in_cluster(self) -> bool:
        """Check if we're running inside the Kubernetes cluster"""
        try:
            # Check for service account token (common indicator)
            token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            return os.path.exists(token_path)
        except:
            return False
    
    async def _find_internal_service(self, service_name: str, service_names: List[str], target_port: int) -> Optional[str]:
        """Find internal cluster service URL (fallback)"""
        try:
            cmd = ["kubectl", "get", "svc", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                for svc in services_data.get("items", []):
                    svc_name = svc["metadata"]["name"]
                    
                    # Check if service matches any expected service name
                    for expected_name in service_names:
                        if expected_name.lower() in svc_name.lower():
                            return f"http://{svc_name}.{self.namespace}.svc.cluster.local:{target_port}"
            
            return None
            
        except Exception:
            return None
    
    async def health_check_services(self, services: Dict[str, ServiceInfo]) -> Dict[str, ServiceInfo]:
        """Perform health checks on discovered services"""
        self.console.print("[blue]🏥 Performing health checks...[/blue]")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console,
        ) as progress:
            
            task = progress.add_task("Health checking services...", total=len(services))
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for service_name, service_info in services.items():
                    if service_info.url and service_info.status not in ["not_found"]:
                        await self._health_check_service(client, service_info)
                    
                    progress.advance(task)
        
        return services
    
    async def _health_check_service(self, client: httpx.AsyncClient, service_info: ServiceInfo) -> None:
        """Health check a single service"""
        config = self.expected_services[service_info.name]
        
        try:
            start_time = time.time()
            
            # Try different health endpoints
            for endpoint in config["health_endpoints"]:
                try:
                    response = await client.get(f"{service_info.url}{endpoint}")
                    if response.status_code < 400:
                        service_info.status = "healthy"
                        service_info.response_time = time.time() - start_time
                        service_info.health_endpoint = endpoint
                        return
                except:
                    continue
            
            # If no health endpoint worked, try root
            try:
                response = await client.get(service_info.url)
                if response.status_code < 500:  # Even 404 means service is responding
                    service_info.status = "responding"
                    service_info.response_time = time.time() - start_time
                    return
            except:
                pass
            
            service_info.status = "unhealthy"
            
        except Exception as e:
            service_info.status = "unreachable"
            self.console.print(f"[dim]Health check error for {service_info.name}: {e}[/dim]")
    
    def display_service_status(self, services: Dict[str, ServiceInfo]) -> bool:
        """Display beautiful service status table"""
        table = Table(title="🚀 Service Discovery Results")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("URL", style="blue", max_width=50)
        table.add_column("Response Time", style="green")
        table.add_column("Health Endpoint", style="yellow")
        
        for service_name, service_info in services.items():
            # Status styling
            status_styles = {
                "healthy": "[green]✅ Healthy[/green]",
                "responding": "[yellow]🟡 Responding[/yellow]",
                "discovered_route": "[blue]🔍 Route Found[/blue]",
                "discovered_ingress": "[blue]🔍 Ingress Found[/blue]",
                "discovered_nodeport": "[blue]🔍 NodePort Found[/blue]",
                "discovered_loadbalancer": "[blue]🔍 LoadBalancer Found[/blue]",
                "discovered_internal": "[yellow]🔍 Internal Only[/yellow]",
                "manual_override": "[purple]⚙️ Manual[/purple]",
                "not_found": "[red]❌ Not Found[/red]",
                "unhealthy": "[orange1]⚠️ Unhealthy[/orange1]",
                "unreachable": "[red]💥 Unreachable[/red]"
            }
            
            status = status_styles.get(service_info.status, f"[dim]{service_info.status}[/dim]")
            
            # Response time formatting
            response_time = ""
            if service_info.response_time:
                response_time = f"{service_info.response_time:.3f}s"
            
            # Health endpoint
            health_endpoint = service_info.health_endpoint or "N/A"
            
            table.add_row(
                service_name.upper(),
                status,
                service_info.url or "Not found",
                response_time,
                health_endpoint
            )
        
        self.console.print(table)
        
        # Summary
        healthy_count = sum(1 for s in services.values() if s.status in ["healthy", "responding"])
        discovered_count = sum(1 for s in services.values() if s.url is not None)
        total_count = len(services)
        
        if healthy_count == total_count:
            self.console.print("\n[green]🎉 All services are healthy and ready for benchmarking![/green]")
            return True
        elif healthy_count > 0:
            self.console.print(f"\n[yellow]⚠️ {healthy_count}/{total_count} services are healthy ({discovered_count} discovered)[/yellow]")
            return healthy_count >= 2  # At least 2 services for comparison
        else:
            self.console.print("\n[red]❌ No services are healthy - check deployments[/red]")
            return False

# Helper functions for easy integration
async def discover_services(namespace: str = "vllm-benchmark", 
                           manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
    """Main entry point for service discovery"""
    discovery = ServiceDiscovery(namespace)
    
    # Discover services
    services = await discovery.discover_all_services(manual_urls)
    
    # Health check
    services = await discovery.health_check_services(services)
    
    # Display results
    all_ready = discovery.display_service_status(services)
    
    return services

def get_manual_urls_template() -> Dict[str, str]:
    """Template for manual URL configuration"""
    return {
        "vllm": "https://vllm-route-hostname.apps.cluster.com",
        "tgi": "https://tgi-route-hostname.apps.cluster.com", 
        "ollama": "https://ollama-route-hostname.apps.cluster.com"
    }
