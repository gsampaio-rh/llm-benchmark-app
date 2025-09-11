"""
Environment Utilities for vLLM Benchmarking Notebook
Clean, minimal utilities that leverage infrastructure-validation.sh
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
    """Simple service information"""
    name: str
    url: str
    status: str = "unknown"
    response_time: Optional[float] = None

class QuickEnvironmentCheck:
    """Lightweight environment checker using infrastructure-validation.sh"""
    
    def __init__(self, namespace: str = "vllm-benchmark"):
        self.namespace = namespace
        self.script_path = Path.cwd().parent / "scripts" / "infrastructure-validation.sh"
        
    async def run_validation(self) -> bool:
        """Run the infrastructure validation script"""
        console.print("[blue]🔧 Running infrastructure validation...[/blue]")
        
        try:
            result = subprocess.run(
                [str(self.script_path)], 
                capture_output=True, 
                text=True, 
                timeout=60,
                env={**dict(os.environ), "NAMESPACE": self.namespace}
            )
            
            if result.returncode == 0:
                console.print("[green]✅ Infrastructure validation passed![/green]")
                return True
            else:
                console.print("[red]❌ Infrastructure validation failed[/red]")
                console.print(f"[dim]{result.stderr}[/dim]")
                return False
                
        except subprocess.TimeoutExpired:
            console.print("[red]❌ Validation script timed out[/red]")
            return False
        except Exception as e:
            console.print(f"[red]❌ Error running validation: {e}[/red]")
            return False
    
    async def discover_services(self) -> Dict[str, ServiceInfo]:
        """Quick service discovery"""
        services = {}
        
        # Expected services with their typical ports
        expected_services = {
            "vllm": 8000,
            "tgi": 8080, 
            "ollama": 11434
        }
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Discovering services...", total=len(expected_services))
            
            for service_name, port in expected_services.items():
                # Try to find service URL
                url = await self._find_service_url(service_name, port)
                
                services[service_name] = ServiceInfo(
                    name=service_name,
                    url=url,
                    status="discovered" if url else "not_found"
                )
                
                # Debug output
                if url:
                    console.print(f"[dim]Found {service_name}: {url}[/dim]")
                else:
                    console.print(f"[dim]{service_name}: No external URL found[/dim]")
                
                progress.advance(task)
        
        return services
    
    async def _find_service_url(self, service_name: str, port: int) -> Optional[str]:
        """Find externally accessible service URL using routes/ingress"""
        try:
            # First, try to find OpenShift routes
            route_url = await self._find_openshift_route(service_name)
            if route_url:
                return route_url
            
            # Then try Kubernetes ingress
            ingress_url = await self._find_kubernetes_ingress(service_name, port)
            if ingress_url:
                return ingress_url
            
            # Fallback: try to find NodePort services
            nodeport_url = await self._find_nodeport_service(service_name, port)
            if nodeport_url:
                return nodeport_url
            
            # Last resort: check if we're running inside the cluster (service URLs work)
            if await self._is_running_in_cluster():
                internal_url = await self._find_internal_service(service_name, port)
                if internal_url:
                    console.print(f"[yellow]⚠️ Using internal service URL for {service_name}: {internal_url}[/yellow]")
                    return internal_url
            
            return None
            
        except Exception as e:
            console.print(f"[dim]Debug: Error finding service URL for {service_name}: {e}[/dim]")
            return None
    
    async def _find_openshift_route(self, service_name: str) -> Optional[str]:
        """Find OpenShift route for service"""
        try:
            cmd = ["oc", "get", "routes", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                routes_data = json.loads(result.stdout)
                for route in routes_data.get("items", []):
                    route_name = route["metadata"]["name"]
                    if service_name in route_name.lower():
                        host = route["spec"]["host"]
                        # Check if TLS is configured
                        if "tls" in route["spec"] and route["spec"]["tls"]:
                            return f"https://{host}"
                        else:
                            return f"http://{host}"
            
            return None
            
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
            return None
    
    async def _find_kubernetes_ingress(self, service_name: str, port: int) -> Optional[str]:
        """Find Kubernetes ingress for service"""
        try:
            cmd = ["kubectl", "get", "ingress", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                ingress_data = json.loads(result.stdout)
                for ingress in ingress_data.get("items", []):
                    ingress_name = ingress["metadata"]["name"]
                    if service_name in ingress_name.lower():
                        rules = ingress["spec"].get("rules", [])
                        if rules:
                            host = rules[0]["host"]
                            # Check for TLS
                            if "tls" in ingress["spec"]:
                                return f"https://{host}"
                            else:
                                return f"http://{host}"
            
            return None
            
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
            return None
    
    async def _find_nodeport_service(self, service_name: str, port: int) -> Optional[str]:
        """Find NodePort service and construct external URL"""
        try:
            cmd = ["kubectl", "get", "svc", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                for svc in services_data.get("items", []):
                    svc_name = svc["metadata"]["name"]
                    if service_name in svc_name.lower():
                        svc_type = svc["spec"].get("type", "ClusterIP")
                        if svc_type == "NodePort":
                            # Find the NodePort for our target port
                            for port_spec in svc["spec"].get("ports", []):
                                if port_spec.get("port") == port or port_spec.get("targetPort") == port:
                                    node_port = port_spec.get("nodePort")
                                    if node_port:
                                        # Get a node IP
                                        node_ip = await self._get_node_ip()
                                        if node_ip:
                                            return f"http://{node_ip}:{node_port}"
            
            return None
            
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
            return None
    
    async def _get_node_ip(self) -> Optional[str]:
        """Get an external node IP"""
        try:
            cmd = ["kubectl", "get", "nodes", "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
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
            
        except (subprocess.SubprocessError, json.JSONDecodeError, KeyError):
            return None
    
    async def _is_running_in_cluster(self) -> bool:
        """Check if we're running inside the Kubernetes cluster"""
        try:
            # Check for service account token (common indicator)
            token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            return os.path.exists(token_path)
        except:
            return False
    
    async def _find_internal_service(self, service_name: str, port: int) -> Optional[str]:
        """Find internal cluster service URL (fallback)"""
        try:
            cmd = ["kubectl", "get", "svc", "-n", self.namespace, "-o", "json"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                services_data = json.loads(result.stdout)
                for svc in services_data.get("items", []):
                    svc_name = svc["metadata"]["name"]
                    if service_name in svc_name.lower():
                        return f"http://{svc_name}.{self.namespace}.svc.cluster.local:{port}"
            
            return None
            
        except Exception:
            return None
    
    async def quick_health_check(self, services: Dict[str, ServiceInfo]) -> Dict[str, ServiceInfo]:
        """Quick health check for discovered services"""
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            
            task = progress.add_task("Health checking services...", total=len(services))
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                for service_name, service_info in services.items():
                    if service_info.url and service_info.status == "discovered":
                        try:
                            start_time = time.time()
                            
                            # Try different health endpoints
                            health_endpoints = ["/health", "/api/tags", "/v1/models"]
                            
                            for endpoint in health_endpoints:
                                try:
                                    response = await client.get(f"{service_info.url}{endpoint}")
                                    if response.status_code < 400:
                                        service_info.status = "healthy"
                                        service_info.response_time = time.time() - start_time
                                        break
                                except:
                                    continue
                            else:
                                service_info.status = "unhealthy"
                                
                        except Exception:
                            service_info.status = "unreachable"
                    
                    progress.advance(task)
        
        return services
    
    def display_service_status(self, services: Dict[str, ServiceInfo]):
        """Display beautiful service status table"""
        table = Table(title="🚀 Service Status")
        
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("URL", style="blue")
        table.add_column("Response Time", style="green")
        
        for service_name, service_info in services.items():
            # Status styling
            if service_info.status == "healthy":
                status = "[green]✅ Healthy[/green]"
            elif service_info.status == "discovered":
                status = "[yellow]🔍 Discovered[/yellow]"
            elif service_info.status == "not_found":
                status = "[red]❌ Not Found[/red]"
            elif service_info.status == "unhealthy":
                status = "[orange1]⚠️ Unhealthy[/orange1]"
            else:
                status = "[red]💥 Unreachable[/red]"
            
            # Response time formatting
            response_time = ""
            if service_info.response_time:
                response_time = f"{service_info.response_time:.3f}s"
            
            table.add_row(
                service_name.upper(),
                status,
                service_info.url or "Not found",
                response_time
            )
        
        console.print(table)
        
        # Summary
        healthy_count = sum(1 for s in services.values() if s.status == "healthy")
        total_count = len(services)
        
        if healthy_count == total_count:
            console.print("\n[green]🎉 All services are healthy and ready for benchmarking![/green]")
        elif healthy_count > 0:
            console.print(f"\n[yellow]⚠️ {healthy_count}/{total_count} services are healthy[/yellow]")
        else:
            console.print("\n[red]❌ No services are healthy - check deployments[/red]")
        
        return healthy_count == total_count

# Quick helper functions for notebook
async def quick_environment_check(namespace: str = "vllm-benchmark", 
                                 manual_urls: Optional[Dict[str, str]] = None) -> Dict[str, ServiceInfo]:
    """One-liner environment check for notebook"""
    checker = QuickEnvironmentCheck(namespace)
    
    # Run validation
    validation_ok = await checker.run_validation()
    if not validation_ok:
        console.print("[yellow]⚠️ Continuing despite validation issues...[/yellow]")
    
    # Discover and health check services
    services = await checker.discover_services()
    
    # Apply manual URL overrides if provided
    if manual_urls:
        console.print("[blue]🔧 Applying manual URL overrides...[/blue]")
        for service_name, url in manual_urls.items():
            if service_name in services:
                services[service_name].url = url
                services[service_name].status = "discovered"
                console.print(f"[green]✅ Override {service_name}: {url}[/green]")
    
    services = await checker.quick_health_check(services)
    
    # Display results
    all_healthy = checker.display_service_status(services)
    
    return services

def get_manual_urls_example() -> Dict[str, str]:
    """Example manual URLs for when automatic discovery fails"""
    return {
        "vllm": "https://vllm-route-hostname.apps.cluster.com",
        "tgi": "https://tgi-route-hostname.apps.cluster.com", 
        "ollama": "https://ollama-route-hostname.apps.cluster.com"
    }
