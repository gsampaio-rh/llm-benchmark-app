"""
Results Organization System
Clean, structured organization of benchmark test results by test ID and datetime
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

@dataclass
class TestRun:
    """Represents a complete test run with all associated files"""
    test_id: str
    timestamp: str
    test_name: str
    services_tested: List[str]
    base_dir: Path
    
    # File paths within the test run directory
    comparison_file: Optional[str] = None
    summary_csv: Optional[str] = None
    detailed_json: Optional[str] = None
    executive_report: Optional[str] = None
    
    # Service-specific directories
    service_dirs: Dict[str, Path] = field(default_factory=dict)
    
    # Charts and visualizations
    charts_dir: Optional[Path] = None
    charts: Dict[str, str] = field(default_factory=dict)

class ResultsOrganizer:
    """
    Manages organized storage and retrieval of benchmark results
    
    Structure:
    results/
    └── test_quicklatency_20250911_105623/
        ├── comparison.json           # Main comparison results
        ├── summary.csv              # Summary metrics
        ├── detailed_analysis.json   # Detailed technical analysis
        ├── executive_report.html    # Executive summary report
        ├── charts/                  # All visualizations
        │   ├── ttft_analysis.html
        │   ├── load_dashboard.html
        │   ├── performance_radar.html
        │   ├── ttft_analysis.png
        │   └── load_dashboard.png
        ├── vllm/                    # Service-specific files
        │   ├── raw_responses.json
        │   ├── performance_log.csv
        │   └── error_log.txt
        ├── tgi/
        │   ├── raw_responses.json
        │   ├── performance_log.csv
        │   └── error_log.txt
        └── ollama/
            ├── raw_responses.json
            ├── performance_log.csv
            └── error_log.txt
    """
    
    def __init__(self, base_results_dir: str = "results"):
        """Initialize results organizer with base directory"""
        self.base_dir = Path(base_results_dir)
        self.base_dir.mkdir(exist_ok=True)
    
    def generate_test_id(self, test_name: str, timestamp: Optional[str] = None) -> str:
        """
        Generate a clean test ID from test name and timestamp
        
        Format: test_{clean_name}_{YYYYMMDD}_{HHMMSS}
        Example: test_quicklatency_20250911_105623
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        elif len(timestamp) == 10:  # Unix timestamp
            dt = datetime.fromtimestamp(int(timestamp))
            timestamp = dt.strftime("%Y%m%d_%H%M%S")
        
        # Clean test name - remove spaces, special chars, convert to lowercase
        clean_name = "".join(c.lower() if c.isalnum() else "" for c in test_name)
        if not clean_name:
            clean_name = "benchmark"
        
        # Truncate if too long
        if len(clean_name) > 20:
            clean_name = clean_name[:20]
        
        return f"test_{clean_name}_{timestamp}"
    
    def create_test_run(self, 
                       test_name: str, 
                       services_tested: List[str],
                       test_id: Optional[str] = None) -> TestRun:
        """
        Create a new organized test run directory structure
        """
        if test_id is None:
            test_id = self.generate_test_id(test_name)
        
        # Create main test directory
        test_dir = self.base_dir / test_id
        test_dir.mkdir(exist_ok=True)
        
        # Create charts subdirectory
        charts_dir = test_dir / "charts"
        charts_dir.mkdir(exist_ok=True)
        
        # Create service-specific directories
        service_dirs = {}
        for service in services_tested:
            service_dir = test_dir / service.lower()
            service_dir.mkdir(exist_ok=True)
            service_dirs[service] = service_dir
        
        test_run = TestRun(
            test_id=test_id,
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            test_name=test_name,
            services_tested=services_tested,
            base_dir=test_dir,
            service_dirs=service_dirs,
            charts_dir=charts_dir
        )
        
        console.print(f"[green]📁 Created test run: {test_id}[/green]")
        return test_run
    
    def save_comparison_results(self, test_run: TestRun, comparison_data: Dict[str, Any]) -> str:
        """Save main comparison results to organized location"""
        comparison_file = test_run.base_dir / "comparison.json"
        
        with open(comparison_file, 'w') as f:
            json.dump(comparison_data, f, indent=2)
        
        test_run.comparison_file = str(comparison_file)
        console.print(f"[green]💾 Saved comparison results: {comparison_file.name}[/green]")
        return str(comparison_file)
    
    def save_summary_csv(self, test_run: TestRun, csv_content: str) -> str:
        """Save summary CSV to organized location"""
        summary_file = test_run.base_dir / "summary.csv"
        
        with open(summary_file, 'w') as f:
            f.write(csv_content)
        
        test_run.summary_csv = str(summary_file)
        console.print(f"[green]📊 Saved summary CSV: {summary_file.name}[/green]")
        return str(summary_file)
    
    def save_detailed_analysis(self, test_run: TestRun, analysis_data: Dict[str, Any]) -> str:
        """Save detailed technical analysis"""
        detailed_file = test_run.base_dir / "detailed_analysis.json"
        
        with open(detailed_file, 'w') as f:
            json.dump(analysis_data, f, indent=2)
        
        test_run.detailed_json = str(detailed_file)
        console.print(f"[green]🔧 Saved detailed analysis: {detailed_file.name}[/green]")
        return str(detailed_file)
    
    def save_executive_report(self, test_run: TestRun, html_content: str) -> str:
        """Save executive HTML report"""
        report_file = test_run.base_dir / "executive_report.html"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        test_run.executive_report = str(report_file)
        console.print(f"[green]📋 Saved executive report: {report_file.name}[/green]")
        return str(report_file)
    
    def save_chart(self, test_run: TestRun, chart_name: str, chart_content: str, format: str = 'html') -> str:
        """Save individual chart to charts directory"""
        chart_file = test_run.charts_dir / f"{chart_name}.{format}"
        
        if format == 'html':
            with open(chart_file, 'w', encoding='utf-8') as f:
                f.write(chart_content)
        else:
            # For binary formats like PNG
            with open(chart_file, 'wb') as f:
                f.write(chart_content)
        
        test_run.charts[chart_name] = str(chart_file)
        console.print(f"[green]📈 Saved chart: {chart_file.name}[/green]")
        return str(chart_file)
    
    def save_service_data(self, 
                         test_run: TestRun, 
                         service_name: str, 
                         filename: str, 
                         content: Any,
                         format: str = 'json') -> str:
        """Save service-specific data to service directory"""
        service_dir = test_run.service_dirs.get(service_name)
        if not service_dir:
            console.print(f"[yellow]⚠️ Service directory not found for: {service_name}[/yellow]")
            return ""
        
        file_path = service_dir / filename
        
        if format == 'json':
            with open(file_path, 'w') as f:
                json.dump(content, f, indent=2)
        elif format == 'csv':
            with open(file_path, 'w') as f:
                f.write(content)
        else:
            with open(file_path, 'w') as f:
                f.write(str(content))
        
        console.print(f"[green]💾 Saved {service_name} data: {filename}[/green]")
        return str(file_path)
    
    def create_test_manifest(self, test_run: TestRun) -> str:
        """Create a manifest file describing the test run contents"""
        manifest = {
            "test_id": test_run.test_id,
            "timestamp": test_run.timestamp,
            "test_name": test_run.test_name,
            "services_tested": test_run.services_tested,
            "files": {
                "comparison": test_run.comparison_file,
                "summary_csv": test_run.summary_csv,
                "detailed_json": test_run.detailed_json,
                "executive_report": test_run.executive_report
            },
            "charts": test_run.charts,
            "service_directories": {k: str(v) for k, v in test_run.service_dirs.items()}
        }
        
        manifest_file = test_run.base_dir / "test_manifest.json"
        with open(manifest_file, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        console.print(f"[green]📋 Created test manifest: {manifest_file.name}[/green]")
        return str(manifest_file)
    
    def list_test_runs(self) -> List[TestRun]:
        """List all organized test runs"""
        test_runs = []
        
        for test_dir in self.base_dir.iterdir():
            if test_dir.is_dir() and test_dir.name.startswith("test_"):
                manifest_file = test_dir / "test_manifest.json"
                
                if manifest_file.exists():
                    try:
                        with open(manifest_file, 'r') as f:
                            manifest = json.load(f)
                        
                        test_run = TestRun(
                            test_id=manifest["test_id"],
                            timestamp=manifest["timestamp"],
                            test_name=manifest["test_name"],
                            services_tested=manifest["services_tested"],
                            base_dir=test_dir,
                            comparison_file=manifest["files"].get("comparison"),
                            summary_csv=manifest["files"].get("summary_csv"),
                            detailed_json=manifest["files"].get("detailed_json"),
                            executive_report=manifest["files"].get("executive_report"),
                            charts=manifest.get("charts", {}),
                            service_dirs={k: Path(v) for k, v in manifest.get("service_directories", {}).items()}
                        )
                        test_runs.append(test_run)
                        
                    except Exception as e:
                        console.print(f"[yellow]⚠️ Could not load manifest for {test_dir.name}: {e}[/yellow]")
        
        # Sort by timestamp (newest first)
        test_runs.sort(key=lambda x: x.timestamp, reverse=True)
        return test_runs
    
    def get_test_run(self, test_id: str) -> Optional[TestRun]:
        """Get a specific test run by ID"""
        test_runs = self.list_test_runs()
        for test_run in test_runs:
            if test_run.test_id == test_id:
                return test_run
        return None
    
    def cleanup_old_tests(self, keep_count: int = 10) -> List[str]:
        """
        Clean up old test runs, keeping only the most recent ones
        Returns list of deleted test IDs
        """
        test_runs = self.list_test_runs()
        
        if len(test_runs) <= keep_count:
            console.print(f"[blue]ℹ️ Only {len(test_runs)} test runs found, nothing to clean up[/blue]")
            return []
        
        to_delete = test_runs[keep_count:]
        deleted_ids = []
        
        console.print(f"[yellow]🧹 Cleaning up {len(to_delete)} old test runs...[/yellow]")
        
        for test_run in to_delete:
            try:
                import shutil
                shutil.rmtree(test_run.base_dir)
                deleted_ids.append(test_run.test_id)
                console.print(f"[red]🗑️ Deleted: {test_run.test_id}[/red]")
            except Exception as e:
                console.print(f"[red]❌ Could not delete {test_run.test_id}: {e}[/red]")
        
        return deleted_ids
    
    def display_test_runs_summary(self):
        """Display a summary of all test runs"""
        test_runs = self.list_test_runs()
        
        if not test_runs:
            console.print("[yellow]📁 No organized test runs found[/yellow]")
            return
        
        console.print(f"\n[bold blue]📊 Test Runs Summary ({len(test_runs)} total)[/bold blue]")
        
        from rich.table import Table
        table = Table(show_header=True, header_style="bold blue")
        table.add_column("Test ID", style="cyan", no_wrap=True)
        table.add_column("Test Name", style="green")
        table.add_column("Timestamp", style="yellow")
        table.add_column("Services", style="magenta")
        table.add_column("Files", style="white", justify="center")
        
        for test_run in test_runs[:10]:  # Show only latest 10
            file_count = sum([
                1 if test_run.comparison_file else 0,
                1 if test_run.summary_csv else 0,
                1 if test_run.executive_report else 0,
                len(test_run.charts)
            ])
            
            table.add_row(
                test_run.test_id,
                test_run.test_name[:30] + "..." if len(test_run.test_name) > 30 else test_run.test_name,
                test_run.timestamp,
                ", ".join(test_run.services_tested),
                str(file_count)
            )
        
        console.print(table)
        
        if len(test_runs) > 10:
            console.print(f"[dim]... and {len(test_runs) - 10} more test runs[/dim]")


def migrate_legacy_results(organizer: ResultsOrganizer, legacy_dir: Path = None) -> int:
    """
    Migrate existing unorganized results to new structure
    """
    if legacy_dir is None:
        legacy_dir = Path("results")
    
    console.print("[bold blue]🔄 Migrating legacy results...[/bold blue]")
    
    # Find legacy files
    legacy_json_files = list(legacy_dir.glob("benchmark_results_*.json"))
    legacy_csv_files = list(legacy_dir.glob("metrics_*.csv"))
    
    if not legacy_json_files:
        console.print("[yellow]📁 No legacy result files found to migrate[/yellow]")
        return 0
    
    migrated_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        task = progress.add_task("Migrating legacy results...", total=len(legacy_json_files))
        
        for json_file in legacy_json_files:
            try:
                # Extract timestamp from filename
                timestamp_str = json_file.stem.split('_')[-1]
                
                # Load the results
                with open(json_file, 'r') as f:
                    data = json.load(f)
                
                test_name = data.get('test_name', 'Legacy Test')
                services = data.get('services_tested', [])
                
                # Create new organized test run
                test_id = organizer.generate_test_id(test_name, timestamp_str)
                test_run = organizer.create_test_run(test_name, services, test_id)
                
                # Save comparison results
                organizer.save_comparison_results(test_run, data)
                
                # Find and migrate corresponding CSV
                csv_file = legacy_dir / f"metrics_{timestamp_str}.csv"
                if csv_file.exists():
                    with open(csv_file, 'r') as f:
                        csv_content = f.read()
                    organizer.save_summary_csv(test_run, csv_content)
                
                # Create manifest
                organizer.create_test_manifest(test_run)
                
                migrated_count += 1
                progress.update(task, advance=1)
                
            except Exception as e:
                console.print(f"[red]❌ Failed to migrate {json_file.name}: {e}[/red]")
                progress.update(task, advance=1)
                continue
    
    console.print(f"[green]✅ Migrated {migrated_count} test runs to organized structure[/green]")
    return migrated_count
