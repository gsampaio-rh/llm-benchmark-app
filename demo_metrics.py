#!/usr/bin/env python3
"""
Demo script to show metrics collection and export functionality.
This runs multiple requests and exports metrics in a single session.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.config.config_manager import ConfigManager
from src.core.connection_manager import ConnectionManager
from src.core.metrics_collector import initialize_metrics_collector
from src.adapters.ollama_adapter import OllamaAdapter
from src.adapters.vllm_adapter import VLLMAdapter
from src.adapters.tgi_adapter import TGIAdapter


async def main():
    """Demo metrics collection and export."""
    print("🚀 Starting Metrics Collection Demo")
    
    # Initialize components
    config_manager = ConfigManager()
    connection_manager = ConnectionManager()
    metrics_collector = initialize_metrics_collector(connection_manager)
    
    # Register adapters
    connection_manager.register_adapter_class("ollama", OllamaAdapter)
    connection_manager.register_adapter_class("vllm", VLLMAdapter)
    connection_manager.register_adapter_class("tgi", TGIAdapter)
    
    try:
        # Load configuration and register engines
        print("📋 Loading configuration...")
        benchmark_config = config_manager.load_benchmark_config()
        registration_results = await connection_manager.register_engines_from_config(benchmark_config)
        
        successful_engines = [name for name, success in registration_results.items() if success]
        print(f"✅ Successfully registered engines: {successful_engines}")
        
        if not successful_engines:
            print("❌ No engines available for testing")
            return
        
        # Start metrics collection
        print("\n📊 Starting metrics collection...")
        collection_id = metrics_collector.start_collection("Demo metrics collection")
        print(f"Collection ID: {collection_id}")
        
        # Run multiple test requests
        test_prompts = [
            "Hello, how are you?",
            "What is machine learning?",
            "Explain quantum computing in simple terms.",
        ]
        
        engine_name = successful_engines[0]  # Use first available engine
        model_name = "qwen2.5:0.5b"  # Small, fast model
        
        print(f"\n🧪 Running {len(test_prompts)} test requests on {engine_name}...")
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n[{i}/{len(test_prompts)}] Testing: {prompt[:30]}...")
            try:
                result = await metrics_collector.collect_single_request_metrics(
                    engine_name, prompt, model_name
                )
                if result.success:
                    print(f"✅ Success: {len(result.response)} chars response")
                    if result.parsed_metrics:
                        print(f"   📈 Duration: {result.parsed_metrics.total_duration:.2f}s, "
                              f"Tokens: {result.parsed_metrics.eval_count}, "
                              f"Rate: {result.parsed_metrics.response_token_rate:.1f} tok/s")
                else:
                    print(f"❌ Failed: {result.error_message}")
            except Exception as e:
                print(f"❌ Error: {e}")
        
        # Show collection summary
        print("\n📊 Metrics Collection Summary:")
        summary = metrics_collector.get_collection_summary()
        print(f"   • Total requests: {summary['total_parsed_metrics']}")
        print(f"   • Success rate: {summary['success_rate']:.1%}")
        print(f"   • Engines: {', '.join(summary['engines'])}")
        
        # Aggregate metrics
        print("\n🔢 Aggregating metrics...")
        aggregates = metrics_collector.aggregate_metrics()
        for agg in aggregates:
            print(f"   Engine: {agg.engine_name}")
            print(f"   • Requests: {agg.successful_requests}/{agg.total_requests}")
            print(f"   • Avg latency: {agg.latency_mean:.2f}s")
            print(f"   • Throughput: {agg.aggregate_tps:.1f} tokens/s")
        
        # Export metrics
        print("\n💾 Exporting metrics...")
        
        # Export JSON
        json_file = metrics_collector.export_metrics("./benchmark_results/demo_metrics.json", "json")
        print(f"✅ JSON exported to: {json_file}")
        
        # Export CSV
        csv_file = metrics_collector.export_metrics("./benchmark_results/demo_metrics.csv", "csv")
        print(f"✅ CSV exported to: {csv_file}")
        
        print(f"\n🎉 Demo completed! Check the exported files:")
        print(f"   📄 JSON: {json_file}")
        print(f"   📊 CSV: {csv_file}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        await connection_manager.close_all()
        print("\n🧹 Cleanup completed")


if __name__ == "__main__":
    asyncio.run(main())
