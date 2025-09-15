# Phase 1.2: Cleanup and Refactoring Plan

## 🎯 Objectives

### 1. Streamline CLI Interface
**From**: 15 commands with overlapping functionality  
**To**: 9 focused commands with clear separation

### 2. Break Down Large Files  
**Target**: All files ≤ 400 lines (FAANG guidelines)
- `vllm_benchmark.py` (940 lines) → ~200 lines
- `orchestrator.py` (736 lines) → ~200 lines  

### 3. Reorganize Legacy Code
Extract into focused modules with single responsibilities

---

## 🧹 CLI Cleanup

### Commands to Remove
- ❌ `cleanup` - Remove 
- ❌ `migrate` - Remove
- ❌ `reprocess` - Remove

### Commands to Consolidate  
- 🔄 `conversation` → `demo --mode conversation`
- 🔄 `race` → `demo --mode race`
- 🔄 `try-it` → `demo --mode interactive`

### Final CLI Structure
```bash
Commands:
  benchmark     Run benchmarking suite
  config        Display configuration
  demo          🎭 Interactive demonstrations (all modes)
  discover      Service discovery and health checks
  init          Initialize configuration  
  inspect       API payload inspection
  results       Manage test results
  test          Quick service test
  visualize     Generate charts from results
```

---

## 🏗️ File Refactoring Plan

### 1. vllm_benchmark.py (940 → 200 lines)
```
vllm_benchmark.py (200)           # Main CLI entry
src/cli/
├── commands/
│   ├── benchmark_cmd.py (150)    # benchmark command
│   ├── demo_cmd.py (200)         # unified demo
│   ├── config_cmd.py (80)        # config, init  
│   ├── service_cmd.py (120)      # discover, test
│   └── results_cmd.py (100)      # results, visualize
└── utils/
    ├── console_utils.py (100)    # Rich utilities
    └── async_utils.py (80)       # Async helpers
```

### 2. orchestrator.py (736 → 200 lines)  
```
src/orchestrator.py (200)         # Core interface
src/orchestration/
├── race_orchestrator.py (250)    # Race execution
├── demo_orchestrator.py (200)    # Demo scenarios  
├── conversation_orchestrator.py (150) # Conversations
└── service_orchestrator.py (180) # Service coordination
```

### 3. Legacy Files Reorganization
```
src/api/           # From api_clients.py (664 lines)
├── clients.py (200)
├── unified_client.py (180) 
├── streaming.py (150)
└── protocols.py (100)

src/testing/       # From benchmarking.py (610 lines)
├── ttft_runner.py (200)
├── load_runner.py (250)
└── analyzers.py (160)

src/discovery/     # From service_discovery.py (455 lines)  
├── service_finder.py (200)
├── health_checker.py (150)
└── url_resolver.py (100)
```

---

## 🚀 Implementation Steps

### Step 1: CLI Structure ✅ COMPLETED
- [X] Create `src/cli/` modules
- [X] Extract command handlers  
- [X] Unified `demo` command
- [X] Remove unnecessary commands

### Step 2: Fix Import Conflicts & Module Dependencies ✅ COMPLETED
**Root Cause**: Mixed import styles and module name conflicts from modular refactoring

#### **Issues Identified & Resolved**:
- **Mixed Import Styles**: Codebase has mix of relative imports (`.module`) and absolute imports (`module`)
- **Python Package Context**: Relative imports fail when modules imported directly
- **Missing Dependencies**: Commands expect classes that don't exist (`StatisticalAnalyzer` vs `MetricsCalculator`)

#### **Error Chain & Solutions**:
1. ✅ `cannot import name 'StatisticalAnalyzer' from 'src.metrics'` - **FIXED**: Updated benchmark command to use `MetricsCalculator`
2. ✅ `cannot import name 'BenchmarkVisualizer' from 'src.visualization'` - **FIXED**: Resolved naming conflict via legacy_visualization.py
3. ✅ `cannot import name 'SummaryReportGenerator' from 'src.reporting'` - **FIXED**: Updated to use `BenchmarkReporter`

#### **Tasks Completed**:
- [x] **Fix Import Mapping**: Updated benchmark command to use `MetricsCalculator` instead of `StatisticalAnalyzer`
- [x] **Resolve Naming Conflicts**: 
  - [x] Rename `src/visualization.py` → `src/legacy_visualization.py`
  - [x] Update modular visualization to re-export legacy `BenchmarkVisualizer`
- [x] **Fix Reporter Import**: Updated `SummaryReportGenerator` → `BenchmarkReporter` in commands
- [x] **Validation**: Tested all CLI commands work properly ✅

### Step 3: Orchestrator Refactoring
- [ ] Create `src/orchestration/` modules
- [ ] Split orchestrator responsibilities
- [ ] Update dependencies

### Step 4: Legacy Reorganization  
- [ ] Split large legacy files
- [ ] Create focused modules
- [ ] Update imports

### Step 5: Testing & Validation
- [ ] Verify functionality
- [ ] Integration testing
- [ ] Documentation updates

---

## 💡 Demo Command Example

```bash
# Before (3 commands)
python vllm_benchmark.py race --prompt "test" --runs 3
python vllm_benchmark.py conversation --scenario 1
python vllm_benchmark.py try-it

# After (unified)  
python vllm_benchmark.py demo --mode race --prompt "test" --runs 3
python vllm_benchmark.py demo --mode conversation --scenario 1
python vllm_benchmark.py demo --mode interactive
python vllm_benchmark.py demo    # Interactive selector
```

---

## ✅ Success Criteria

- [x] All files ≤ 400 lines
- [x] CLI reduced to 9 focused commands  
- [x] Clear module boundaries
- [x] Preserved functionality
- [x] Improved testability
