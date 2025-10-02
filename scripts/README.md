# 🚀 LLM Benchmark Scripts

Beautiful, guided Python scripts for benchmarking LLM engines. Each script provides an interactive, step-by-step experience with rich visual feedback.

## 📋 Available Scripts

### 🔍 `check_engines.py` - Engine Health Checker
Check the health and connectivity of all configured LLM engines.

**What it does:**
- Verifies connectivity to Ollama, vLLM, and TGI engines
- Measures response times
- Retrieves engine information and capabilities
- Lists available models

**Usage:**
```bash
python scripts/check_engines.py
```

**When to use:**
- Before running benchmarks to ensure engines are available
- To verify engine configuration
- To troubleshoot connectivity issues
- To discover available models

---

### 🔎 `discover_models.py` - Model Discovery Explorer
Explore and discover all available models across your configured engines.

**What it does:**
- Scans all engines for available models
- Displays model families, sizes, and availability
- Shows detailed model metadata
- Organizes models by engine and family

**Usage:**
```bash
python scripts/discover_models.py
```

**When to use:**
- To see what models are available before benchmarking
- To explore model families and their properties
- To verify model availability across engines
- To discover new models after updating engines

---

### 🧪 `test_request.py` - Single Request Tester
Send a test request to a specific engine and model with detailed metrics.

**What it does:**
- Interactive engine and model selection
- Guided prompt input
- Real-time request execution
- **Detailed performance metrics display**
- Shows model response
- **Automatically exports metrics to JSON**

**Usage:**
```bash
python scripts/test_request.py
```

**When to use:**
- To test a specific model before running full benchmarks
- To verify model configuration and output quality
- To get quick performance metrics for a single request
- To debug issues with specific models

---

### 🏃 `run_benchmark.py` - Comprehensive Benchmark Runner
Run full-scale benchmarks across multiple engines, models, and configurations.

**What it does:**
- Interactive benchmark configuration
- Multi-engine and multi-model testing
- Configurable test prompts (short, medium, long, mixed)
- Parallel request execution with progress tracking
- **Real-time metrics display during execution**
- **Aggregate performance comparison with visualizations**
- **Automatic results export to JSON (default)**

**Usage:**
```bash
python scripts/run_benchmark.py
```

**Configuration Options:**
- **Description**: Name your benchmark run
- **Number of Requests**: How many requests per model (5-10 for quick tests, 50+ for production)
- **Prompt Strategy**: 
  - Short (10-20 words)
  - Medium (30-50 words)
  - Long (100+ words)
  - Mixed (variety)
- **Target Selection**: Choose engines and models to benchmark

**When to use:**
- To run comprehensive performance tests
- To compare multiple engines and models
- To generate benchmark reports
- To stress test your LLM infrastructure

---

## 🎨 Design Features

All scripts feature:
- **✨ Beautiful Terminal UI** - Rich colors, tables, panels, and progress bars
- **📝 Step-by-Step Guidance** - Clear explanations at each step
- **🎯 Interactive Prompts** - Intuitive selection and configuration
- **⚡ Real-time Feedback** - Progress indicators and status updates
- **🛡️ Error Handling** - Graceful error messages and recovery
- **🎨 Visual Hierarchy** - Color-coded status (✅ success, ❌ error, ⚠️ warning)

---

## 🔄 Typical Workflow

### Quick Test Workflow
```bash
# 1. Check engine health
python scripts/check_engines.py

# 2. Test a single request (shows metrics immediately)
python scripts/test_request.py
```

### Comprehensive Benchmark Workflow
```bash
# 1. Discover available models
python scripts/discover_models.py

# 2. Run full benchmark (shows results & auto-exports)
python scripts/run_benchmark.py
```

### Troubleshooting Workflow
```bash
# 1. Check engine health
python scripts/check_engines.py

# 2. Verify specific model
python scripts/test_request.py

# 3. Check logs if needed
# (review error messages from scripts)
```

---

## 🎯 Best Practices

### Before Benchmarking
1. ✅ Run `check_engines.py` to verify all engines are healthy
2. ✅ Run `discover_models.py` to see available models
3. ✅ Test with `test_request.py` to verify configuration

### During Benchmarking
1. 🎯 Start with small request counts (5-10) to verify setup
2. 🎯 Use appropriate prompt strategy for your use case
3. 🎯 Monitor real-time progress and watch for errors
4. 🎯 Don't interrupt running benchmarks (Ctrl+C to cancel if needed)

### After Benchmarking
1. 📊 Review results displayed at the end of the script
2. 📊 Find exported JSON in `benchmark_results/` directory
3. 📊 Use exported data for further analysis or visualization
4. 📊 Compare results across different benchmark runs

---

## 🔧 Configuration

Scripts use the engine configurations from `configs/engines/`:
- `ollama.yaml` - Ollama engine settings
- `vllm.yaml` - vLLM engine settings
- `tgi.yaml` - TGI engine settings

Edit these files to:
- Change engine URLs
- Adjust timeouts
- Add authentication tokens
- Configure custom headers

---

## 📁 Output Files

Results are saved to `benchmark_results/`:
```
benchmark_results/
├── benchmark_20250102_143022.json    # Full benchmark results
├── metrics_20250102_143545.json      # Exported metrics
└── metrics_20250102_143545.csv       # CSV export for spreadsheets
```

**JSON Format**: Complete metrics with all details
**CSV Format**: Tabular format for Excel/Google Sheets analysis

---

## 🆘 Troubleshooting

### "No engines available"
→ Check engine configurations in `configs/engines/`
→ Verify engines are running and accessible
→ Run `check_engines.py` to diagnose

### "No models found"
→ Ensure models are loaded on the engine
→ Check engine logs for model loading errors
→ Run `discover_models.py` to scan

### "Connection timeout"
→ Increase timeout in engine config files
→ Verify network connectivity to engines
→ Check firewall rules

### "Authentication failed"
→ Add auth tokens to engine configs
→ Verify token validity
→ Check engine authentication requirements

---

## 🎓 Learning Resources

- **README.md** - Project overview and setup
- **docs/PRD.md** - Product requirements and features
- **docs/METRICS.md** - Metrics collection guide
- **docs/PROJECT_STATUS_AND_PLAN.md** - Current status and roadmap

---

## 💡 Tips & Tricks

1. **Use Tab completion** - Most prompts support default values (just press Enter)
2. **Interrupt safely** - Press Ctrl+C to safely cancel operations
3. **Start small** - Begin with 5-10 requests to test before scaling up
4. **Results are auto-exported** - Find JSON files in `benchmark_results/` directory
5. **Compare runs** - Timestamps in filenames help track different configurations
6. **Review on-screen results** - All metrics are displayed immediately after execution

---

## 🤝 Contributing

To add a new script:
1. Follow the existing script structure
2. Use Rich library for beautiful output
3. Implement step-by-step guidance
4. Add error handling and recovery
5. Update this README

---

**Happy Benchmarking! 🚀**

