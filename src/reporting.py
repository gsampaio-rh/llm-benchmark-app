"""
Professional Report Generation System
HTML and PDF report generation with executive summaries and recommendations
"""

import json
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import asdict
import csv

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .metrics import BenchmarkComparison, PerformanceMetrics
from .benchmarking import TTFTBenchmarkResult, ServiceBenchmarkResult

console = Console()

class BenchmarkReporter:
    """Professional report generation system"""
    
    def __init__(self, output_dir: str = "results/reports"):
        """Initialize reporter with output directory"""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_executive_summary(self, comparison: BenchmarkComparison) -> Dict[str, Any]:
        """
        Generate executive summary with key insights and recommendations
        """
        console.print("[blue]📋 Generating executive summary...[/blue]")
        
        # Find best and worst performers
        services = list(comparison.service_metrics.keys())
        if not services:
            return {"error": "No services to analyze"}
        
        # Performance analysis
        ttft_performance = {}
        load_performance = {}
        overall_performance = {}
        
        for service in services:
            metrics = comparison.service_metrics[service]
            ttft_performance[service] = metrics.ttft_mean
            load_performance[service] = metrics.load_p95_latency
            overall_performance[service] = metrics.overall_score
        
        # Find winners and insights
        best_ttft = min(ttft_performance.keys(), key=lambda x: ttft_performance[x]) if ttft_performance else None
        best_load = min(load_performance.keys(), key=lambda x: load_performance[x]) if load_performance else None
        best_overall = max(overall_performance.keys(), key=lambda x: overall_performance[x]) if overall_performance else None
        
        # Generate insights
        insights = []
        
        # TTFT Analysis
        if best_ttft and ttft_performance[best_ttft] > 0:
            ttft_value = ttft_performance[best_ttft]
            target_met = ttft_value < 100
            insights.append({
                "category": "TTFT Performance",
                "finding": f"{best_ttft.upper()} achieves fastest TTFT at {ttft_value:.1f}ms",
                "impact": "Critical" if target_met else "High",
                "recommendation": "Deploy for low-latency use cases" if target_met else "Optimize configuration for sub-100ms TTFT"
            })
        
        # Load Performance Analysis
        if best_load and load_performance[best_load] > 0:
            load_value = load_performance[best_load]
            target_met = load_value < 1000
            insights.append({
                "category": "Load Performance", 
                "finding": f"{best_load.upper()} handles load best with {load_value:.0f}ms P95 latency",
                "impact": "High" if target_met else "Medium",
                "recommendation": "Scale for production" if target_met else "Review resource allocation"
            })
        
        # Overall Winner Analysis
        if best_overall:
            overall_score = overall_performance[best_overall]
            insights.append({
                "category": "Overall Performance",
                "finding": f"{best_overall.upper()} wins overall with {overall_score:.1f}/100 score",
                "impact": "Strategic",
                "recommendation": f"Recommended for production deployment based on comprehensive analysis"
            })
        
        # Reliability Analysis
        reliability_issues = []
        for service in services:
            metrics = comparison.service_metrics[service]
            if metrics.reliability_score < 95:
                reliability_issues.append(f"{service.upper()}: {metrics.reliability_score:.1f}% success rate")
        
        if reliability_issues:
            insights.append({
                "category": "Reliability Concerns",
                "finding": "Some services show reliability issues: " + ", ".join(reliability_issues),
                "impact": "Critical",
                "recommendation": "Investigate error causes before production deployment"
            })
        
        summary = {
            "test_overview": {
                "test_name": comparison.test_name,
                "timestamp": comparison.timestamp,
                "services_tested": comparison.services_tested,
                "total_requests": comparison.total_requests,
                "test_duration": comparison.total_test_duration
            },
            "winners": {
                "ttft_winner": comparison.ttft_winner,
                "load_winner": comparison.load_winner, 
                "overall_winner": comparison.overall_winner
            },
            "key_insights": insights,
            "performance_summary": {
                service: {
                    "ttft_ms": comparison.service_metrics[service].ttft_mean,
                    "load_p95_ms": comparison.service_metrics[service].load_p95_latency,
                    "success_rate": comparison.service_metrics[service].reliability_score,
                    "overall_score": comparison.service_metrics[service].overall_score
                }
                for service in services
            }
        }
        
        return summary
    
    def generate_technical_analysis(self, comparison: BenchmarkComparison) -> Dict[str, Any]:
        """
        Generate detailed technical analysis for engineering teams
        """
        console.print("[blue]🔧 Generating technical analysis...[/blue]")
        
        services = list(comparison.service_metrics.keys())
        
        technical_details = {
            "performance_breakdown": {},
            "statistical_analysis": {},
            "configuration_recommendations": {},
            "troubleshooting_notes": {}
        }
        
        for service in services:
            metrics = comparison.service_metrics[service]
            
            # Performance breakdown
            technical_details["performance_breakdown"][service] = {
                "ttft_metrics": {
                    "mean": metrics.ttft_mean,
                    "p95": metrics.ttft_p95,
                    "p99": metrics.ttft_p99,
                    "std_dev": metrics.ttft_std_dev,
                    "target_achieved": metrics.ttft_target_achieved
                },
                "load_metrics": {
                    "rps": metrics.load_rps,
                    "mean_latency": metrics.load_mean_latency,
                    "p95_latency": metrics.load_p95_latency,
                    "p99_latency": metrics.load_p99_latency,
                    "success_rate": metrics.load_success_rate
                },
                "composite_scores": {
                    "latency_score": metrics.latency_score,
                    "throughput_score": metrics.throughput_score,
                    "reliability_score": metrics.reliability_score,
                    "overall_score": metrics.overall_score
                }
            }
            
            # Configuration recommendations
            config_recs = []
            
            if metrics.ttft_mean > 100:
                config_recs.append("Consider increasing GPU memory utilization")
                config_recs.append("Optimize batch size for lower latency")
            
            if metrics.load_p95_latency > 1000:
                config_recs.append("Increase max concurrent requests")
                config_recs.append("Review resource allocation")
            
            if metrics.reliability_score < 95:
                config_recs.append("Investigate error handling")
                config_recs.append("Check resource constraints")
            
            technical_details["configuration_recommendations"][service] = config_recs
            
            # Troubleshooting notes
            issues = []
            if metrics.ttft_success_rate < 1.0:
                issues.append(f"TTFT failures: {(1-metrics.ttft_success_rate)*100:.1f}%")
            if metrics.load_success_rate < 100:
                issues.append(f"Load test failures: {100-metrics.load_success_rate:.1f}%")
            
            technical_details["troubleshooting_notes"][service] = issues
        
        return technical_details
    
    def generate_html_report(self, 
                           comparison: BenchmarkComparison,
                           charts_html: Optional[Dict[str, str]] = None) -> str:
        """
        Generate comprehensive HTML report
        """
        console.print("[blue]📄 Generating HTML report...[/blue]")
        
        executive_summary = self.generate_executive_summary(comparison)
        technical_analysis = self.generate_technical_analysis(comparison)
        
        # HTML template with embedded CSS
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>{comparison.test_name} - Comprehensive Report</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    margin: 0;
                    padding: 0;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    min-height: 100vh;
                }}
                .container {{
                    max-width: 1200px;
                    margin: 0 auto;
                    background: white;
                    min-height: 100vh;
                    box-shadow: 0 0 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #2E86AB 0%, #A23B72 100%);
                    color: white;
                    padding: 40px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 2.5em;
                    font-weight: 300;
                }}
                .header .subtitle {{
                    font-size: 1.2em;
                    margin-top: 10px;
                    opacity: 0.9;
                }}
                .section {{
                    padding: 40px;
                    border-bottom: 1px solid #eee;
                }}
                .section:last-child {{
                    border-bottom: none;
                }}
                .section h2 {{
                    color: #2E86AB;
                    border-bottom: 2px solid #2E86AB;
                    padding-bottom: 10px;
                    margin-top: 0;
                }}
                .section h3 {{
                    color: #A23B72;
                    margin-top: 30px;
                }}
                .winner {{
                    color: #4CAF50;
                    font-weight: bold;
                    font-size: 1.1em;
                }}
                .metric-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                    gap: 20px;
                    margin: 20px 0;
                }}
                .metric-card {{
                    background: #f8f9fa;
                    border-left: 4px solid #2E86AB;
                    padding: 20px;
                    border-radius: 8px;
                }}
                .metric-card h4 {{
                    margin: 0 0 10px 0;
                    color: #2E86AB;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                    font-size: 0.9em;
                }}
                .metric-value {{
                    font-size: 1.5em;
                    font-weight: bold;
                    color: #333;
                }}
                .insight {{
                    background: #e3f2fd;
                    border-left: 4px solid #2196F3;
                    padding: 15px;
                    margin: 15px 0;
                    border-radius: 4px;
                }}
                .insight-high {{
                    border-left-color: #FF9800;
                    background: #fff3e0;
                }}
                .insight-critical {{
                    border-left-color: #F44336;
                    background: #ffebee;
                }}
                .insight-strategic {{
                    border-left-color: #4CAF50;
                    background: #e8f5e8;
                }}
                .table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 20px 0;
                }}
                .table th, .table td {{
                    border: 1px solid #ddd;
                    padding: 12px;
                    text-align: left;
                }}
                .table th {{
                    background: #2E86AB;
                    color: white;
                    font-weight: 500;
                }}
                .table tr:nth-child(even) {{
                    background: #f9f9f9;
                }}
                .recommendations {{
                    background: #f1f8e9;
                    border: 1px solid #c8e6c9;
                    border-radius: 8px;
                    padding: 20px;
                    margin: 20px 0;
                }}
                .recommendations h4 {{
                    color: #2e7d32;
                    margin-top: 0;
                }}
                .footer {{
                    background: #263238;
                    color: #eceff1;
                    padding: 20px 40px;
                    text-align: center;
                }}
                .chart-container {{
                    margin: 30px 0;
                    text-align: center;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚀 {comparison.test_name}</h1>
                    <div class="subtitle">Comprehensive Performance Analysis Report</div>
                    <div class="subtitle">Generated on {comparison.timestamp}</div>
                </div>
                
                <div class="section">
                    <h2>📊 Executive Summary</h2>
                    
                    <div class="metric-grid">
                        <div class="metric-card">
                            <h4>Services Tested</h4>
                            <div class="metric-value">{len(comparison.services_tested)}</div>
                            <small>{', '.join(comparison.services_tested).upper()}</small>
                        </div>
                        <div class="metric-card">
                            <h4>Total Requests</h4>
                            <div class="metric-value">{comparison.total_requests:,}</div>
                            <small>Across all services</small>
                        </div>
                        <div class="metric-card">
                            <h4>Test Duration</h4>
                            <div class="metric-value">{comparison.total_test_duration:.1f}s</div>
                            <small>End-to-end execution</small>
                        </div>
                        <div class="metric-card">
                            <h4>Overall Winner</h4>
                            <div class="metric-value winner">{comparison.overall_winner or 'N/A'}</div>
                            <small>Best comprehensive performance</small>
                        </div>
                    </div>
                    
                    <h3>🏆 Performance Winners</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Category</th>
                                <th>Winner</th>
                                <th>Key Metric</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr>
                                <td>⚡ TTFT Performance</td>
                                <td class="winner">{comparison.ttft_winner or 'N/A'}</td>
                                <td>{comparison.service_metrics.get(comparison.ttft_winner, {}).ttft_mean if comparison.ttft_winner else 'N/A':.1f}ms</td>
                            </tr>
                            <tr>
                                <td>📈 Load Performance</td>
                                <td class="winner">{comparison.load_winner or 'N/A'}</td>
                                <td>{comparison.service_metrics.get(comparison.load_winner, {}).load_p95_latency if comparison.load_winner else 'N/A':.0f}ms P95</td>
                            </tr>
                            <tr>
                                <td>🎯 Overall Performance</td>
                                <td class="winner">{comparison.overall_winner or 'N/A'}</td>
                                <td>{comparison.service_metrics.get(comparison.overall_winner, {}).overall_score if comparison.overall_winner else 'N/A':.1f}/100</td>
                            </tr>
                        </tbody>
                    </table>
                    
                    <h3>💡 Key Insights</h3>
        """
        
        # Add insights
        for insight in executive_summary.get("key_insights", []):
            impact_class = f"insight-{insight['impact'].lower()}"
            html_content += f"""
                    <div class="insight {impact_class}">
                        <strong>{insight['category']}:</strong> {insight['finding']}<br>
                        <strong>Recommendation:</strong> {insight['recommendation']}
                    </div>
            """
        
        # Performance comparison table
        html_content += """
                    <h3>📊 Performance Comparison</h3>
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Service</th>
                                <th>TTFT (ms)</th>
                                <th>P95 Latency (ms)</th>
                                <th>Success Rate (%)</th>
                                <th>Overall Score</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for service in comparison.services_tested:
            metrics = comparison.service_metrics.get(service, {})
            html_content += f"""
                            <tr>
                                <td><strong>{service.upper()}</strong></td>
                                <td>{metrics.ttft_mean:.1f}</td>
                                <td>{metrics.load_p95_latency:.0f}</td>
                                <td>{metrics.reliability_score:.1f}%</td>
                                <td>{metrics.overall_score:.1f}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
        """
        
        # Technical Analysis Section
        html_content += """
                <div class="section">
                    <h2>🔧 Technical Analysis</h2>
                    
                    <h3>⚡ TTFT Analysis</h3>
                    <p>Time To First Token (TTFT) is critical for user experience in interactive applications. 
                    Target: &lt; 100ms for optimal responsiveness.</p>
                    
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Service</th>
                                <th>Mean TTFT</th>
                                <th>P95 TTFT</th>
                                <th>P99 TTFT</th>
                                <th>Target Met</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for service in comparison.services_tested:
            metrics = comparison.service_metrics.get(service, {})
            target_met = "✅ Yes" if metrics.ttft_target_achieved else "❌ No"
            html_content += f"""
                            <tr>
                                <td><strong>{service.upper()}</strong></td>
                                <td>{metrics.ttft_mean:.1f}ms</td>
                                <td>{metrics.ttft_p95:.1f}ms</td>
                                <td>{metrics.ttft_p99:.1f}ms</td>
                                <td>{target_met}</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                    
                    <h3>📈 Load Test Analysis</h3>
                    <p>Load testing evaluates performance under concurrent user load. 
                    Target: P95 latency &lt; 1000ms for production readiness.</p>
                    
                    <table class="table">
                        <thead>
                            <tr>
                                <th>Service</th>
                                <th>RPS</th>
                                <th>Mean Latency</th>
                                <th>P95 Latency</th>
                                <th>Success Rate</th>
                            </tr>
                        </thead>
                        <tbody>
        """
        
        for service in comparison.services_tested:
            metrics = comparison.service_metrics.get(service, {})
            html_content += f"""
                            <tr>
                                <td><strong>{service.upper()}</strong></td>
                                <td>{metrics.load_rps:.2f}</td>
                                <td>{metrics.load_mean_latency:.0f}ms</td>
                                <td>{metrics.load_p95_latency:.0f}ms</td>
                                <td>{metrics.load_success_rate:.1f}%</td>
                            </tr>
            """
        
        html_content += """
                        </tbody>
                    </table>
                </div>
        """
        
        # Configuration Recommendations
        html_content += """
                <div class="section">
                    <h2>⚙️ Configuration Recommendations</h2>
        """
        
        for service in comparison.services_tested:
            recs = technical_analysis["configuration_recommendations"].get(service, [])
            if recs:
                html_content += f"""
                    <div class="recommendations">
                        <h4>{service.upper()} Optimization</h4>
                        <ul>
                """
                for rec in recs:
                    html_content += f"<li>{rec}</li>"
                
                html_content += """
                        </ul>
                    </div>
                """
        
        html_content += """
                </div>
        """
        
        # Add charts if provided
        if charts_html:
            html_content += """
                <div class="section">
                    <h2>📊 Interactive Charts</h2>
            """
            for chart_name, chart_html in charts_html.items():
                html_content += f"""
                    <div class="chart-container">
                        <h3>{chart_name.replace('_', ' ').title()}</h3>
                        {chart_html}
                    </div>
                """
            html_content += "</div>"
        
        # Footer
        html_content += f"""
                <div class="footer">
                    <p>Generated by vLLM Benchmarking Suite • {comparison.timestamp}</p>
                    <p>🚀 AI Platform Team - Enterprise Performance Testing</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Save report
        report_filename = f"benchmark_report_{int(time.time())}.html"
        report_path = self.output_dir / report_filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        console.print(f"[green]✅ HTML report saved: {report_path}[/green]")
        return str(report_path)
    
    def export_csv_summary(self, comparison: BenchmarkComparison) -> str:
        """
        Export summary data to CSV for spreadsheet analysis
        """
        console.print("[blue]📄 Exporting CSV summary...[/blue]")
        
        csv_filename = f"benchmark_summary_{int(time.time())}.csv"
        csv_path = self.output_dir / csv_filename
        
        with open(csv_path, 'w', newline='') as csvfile:
            fieldnames = [
                'service_name', 'ttft_mean', 'ttft_p95', 'ttft_target_achieved',
                'load_p95_latency', 'load_rps', 'load_target_achieved',
                'reliability_score', 'overall_score'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for service_name, metrics in comparison.service_metrics.items():
                writer.writerow({
                    'service_name': service_name,
                    'ttft_mean': metrics.ttft_mean,
                    'ttft_p95': metrics.ttft_p95,
                    'ttft_target_achieved': metrics.ttft_target_achieved,
                    'load_p95_latency': metrics.load_p95_latency,
                    'load_rps': metrics.load_rps,
                    'load_target_achieved': metrics.load_target_achieved,
                    'reliability_score': metrics.reliability_score,
                    'overall_score': metrics.overall_score
                })
        
        console.print(f"[green]✅ CSV summary saved: {csv_path}[/green]")
        return str(csv_path)
    
    def export_json_detailed(self, comparison: BenchmarkComparison) -> str:
        """
        Export detailed JSON for programmatic analysis
        """
        console.print("[blue]📄 Exporting detailed JSON...[/blue]")
        
        json_filename = f"benchmark_detailed_{int(time.time())}.json"
        json_path = self.output_dir / json_filename
        
        # Add executive summary and technical analysis
        detailed_data = {
            "benchmark_results": comparison.to_dict(),
            "executive_summary": self.generate_executive_summary(comparison),
            "technical_analysis": self.generate_technical_analysis(comparison),
            "export_timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        with open(json_path, 'w') as f:
            json.dump(detailed_data, f, indent=2)
        
        console.print(f"[green]✅ Detailed JSON saved: {json_path}[/green]")
        return str(json_path)
    
    def generate_comprehensive_report(self, 
                                    comparison: BenchmarkComparison,
                                    charts_html: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """
        Generate all report formats
        Returns dict of format -> file_path
        """
        console.print("[bold blue]📋 Generating comprehensive report suite...[/bold blue]")
        
        reports = {}
        
        # HTML Report
        reports['html'] = self.generate_html_report(comparison, charts_html)
        
        # CSV Export
        reports['csv'] = self.export_csv_summary(comparison)
        
        # JSON Export  
        reports['json'] = self.export_json_detailed(comparison)
        
        console.print(f"[green]✅ Generated {len(reports)} report formats[/green]")
        console.print(f"[dim]Reports saved to: {self.output_dir}[/dim]")
        
        return reports


def export_metrics_csv(comparison: BenchmarkComparison, filepath: str):
    """
    Legacy function for backward compatibility
    Exports basic metrics to CSV format
    """
    Path(filepath).parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', newline='') as csvfile:
        fieldnames = [
            'service_name', 'ttft_mean', 'ttft_p95', 'ttft_target_achieved',
            'load_p95_latency', 'load_rps', 'load_target_achieved',
            'reliability_score', 'overall_score'
        ]
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for service_name, metrics in comparison.service_metrics.items():
            writer.writerow({
                'service_name': service_name,
                'ttft_mean': metrics.ttft_mean,
                'ttft_p95': metrics.ttft_p95,
                'ttft_target_achieved': metrics.ttft_target_achieved,
                'load_p95_latency': metrics.load_p95_latency,
                'load_rps': metrics.load_rps,
                'load_target_achieved': metrics.load_target_achieved,
                'reliability_score': metrics.reliability_score,
                'overall_score': metrics.overall_score
            })
    
    console.print(f"[green]✅ Metrics exported to: {filepath}[/green]")
