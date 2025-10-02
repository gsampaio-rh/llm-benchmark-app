# Universal LLM Engine Benchmark — Clean Implementation Plan (v1.2)

**Project**: Universal LLM Engine Benchmarking Tool
**Owner**: Gabriel Sampaio ([gab@redhat.com](mailto:gab@redhat.com))
**Date**: 2025-10-02 (America/São_Paulo)
**Version**: v1.2
**Status**: Phase 1 ✅ complete → Phase 2 🚧 in progress

---

## 0) One-Page Summary

**Goal**: A Python benchmarking toolkit that runs standardized workloads across **Ollama**, **vLLM**, and **HuggingFace TGI**, collects engine-native metrics, and outputs comparable KPIs (latency, throughput, reliability, cost-efficiency later).

**MVP (done)**: Engine connectivity, single-request metrics, JSON/CSV export, minimal CLI.

**Next (Phase 2)**: Introduce **core benchmarking modules and scenario framework** plus **script-based entry points** (no monolithic CLI).

**Later (Phase 3)**: Expand to full metrics parity, load testing (concurrency, RPS), streaming analytics, and resource monitoring.

---

## 1) Scope

### 1.1 In-Scope (Phase 2)

* Build missing **core modules**:

  * `benchmark_engine.py` (orchestrator)
  * `load_engine.py` (async concurrency loop)
  * `metrics_agg.py` (percentiles & summary stats)
  * `base_scenario.py` + `prompt_length.py`

* Add **script-based UX** under `/scripts`:

  * `quick_benchmark.py`
  * `load_test.py`
  * `compare_engines.py`

* Introduce **results/` directory** for artifacts.

* Migrate away from `cli/` (keep for backward compatibility, mark deprecated).

### 1.2 Out-of-Scope (Phase 2)

* Streaming metrics (TTFT, inter-token)
* Resource monitoring (CPU/GPU/Memory)
* Advanced load patterns (burst, ramp-up, heterogeneous workloads)
* Reporting dashboards (HTML, plots, cost analysis)

---

## 2) Architecture

**Target Phase 2 structure**

```
benchmarking-tool/
├─ src/
│  ├─ adapters/              # (exists)
│  ├─ core/
│  │  ├─ benchmark_engine.py # NEW
│  │  ├─ load_engine.py      # NEW
│  │  ├─ metrics_agg.py      # NEW
│  ├─ scenarios/
│  │  ├─ base_scenario.py    # NEW
│  │  ├─ prompt_length.py    # NEW
│  ├─ models/                # (exists)
│  ├─ config/                # (exists)
│  └─ cli/                   # (legacy, deprecated)
├─ scripts/
│  ├─ quick_benchmark.py     # NEW
│  ├─ load_test.py           # NEW
│  └─ compare_engines.py     # NEW
├─ results/                  # gitignored artifacts
├─ tests/{unit,integration}
└─ docs/
```

---

## 3) Interfaces

### Benchmark Engine

```python
class BenchmarkEngine:
    async def run(self, adapter: BaseAdapter, scenario: BaseScenario, cfg: BenchmarkConfig) -> BenchmarkResult: ...
    async def compare(self, adapters: list[BaseAdapter], scenario: BaseScenario, cfg: BenchmarkConfig) -> ComparisonResult: ...
```

### Base Scenario

```python
class BaseScenario(ABC):
    async def generate(self) -> RequestSpec: ...
```

### Load Engine

```python
class LoadEngine:
    async def run_concurrent(self, adapter, requests: list[RequestSpec], concurrency: int) -> list[RequestResult]: ...
```

---

## 4) Metrics

### Phase 2 coverage

* **Per request**: request ID, timestamps, duration, success/failure, error type, token counts (if provided).
* **Aggregate**: average latency, p50/p95/p99, request count, success_rate.

> Extended metrics (TTFT, inter-token, GPU/CPU, TPS/RPS) → **Phase 3**.

---

## 5) Scripts (UX)

* `quick_benchmark.py` → run a single engine/scenario, export JSON+CSV.
* `load_test.py` → run sustained fixed-concurrency tests.
* `compare_engines.py` → execute one scenario across multiple engines, merge outputs.

---

## 6) Phase Plan

### Phase 1 — Platform Foundation ✅

Gotcha — here’s a **compact Phase 1 summary** you can paste in:

---

## Phase 1 — Summary (1-pager)

**Objective:** Stand up a reliable platform that connects to Ollama, vLLM, and TGI and collects per-request metrics to enable future benchmarking.

**Outcomes (✅):**

* Adapters for **Ollama, vLLM, TGI** with health checks & model discovery.
* **Single-request metrics** collected and **exported (JSON/CSV)**.
* **Typed models** (Pydantic) for config & metrics; defensive parsing.
* Minimal **CLI** for engines/models/test-request (to be deprecated later).

**What shipped (code):**

* `adapters/{base,ollama,vllm,tgi}.py`
* `core/{connection_manager,metrics_collector}.py`
* `models/{engine_config,metrics}.py`
* CLI commands: engines, models, test-request, metrics export.

**Coverage (now):**

* Metrics: **17/42 (40.5%)** — full per-request runtime on Ollama; partial parity on vLLM/TGI.
* Latency: TTFT & inter-token captured where available.
* Reliability: success rate + basic error taxonomy.

**Evidence (numbers):**

* Health check ~**12.9 ms** (Ollama, local).
* TTFT ~**117–148 ms**.
* Prompt proc **~728–2159 tok/s**; generation **~177–185 tok/s** (single request, indicative only).
* **58/58 tests** passing; setup <5 min.

**Known gaps (defer):**

* No load/concurrency engine, no percentiles/RPS/TPS.
* Incomplete vLLM/TGI metric parity.
* No streaming analytics beyond basic TTFT hooks.
* No resource telemetry (CPU/GPU).

**Decision log:**

* **Adapter pattern** confirmed; **nullable normalized schema** for metrics.
* Streaming kept minimal; richer handling later.

**Next (Phase 2 focus):**

* Add core modules: `benchmark_engine.py`, `load_engine.py`, `metrics_agg.py`.
* Add scenarios: `base_scenario.py`, `prompt_length.py`.
* Replace CLI flows with **scripts**: `quick_benchmark.py`, `load_test.py`, `compare_engines.py`.
* Keep CLI available but **deprecated** until script parity.

### Phase 2 — Core Modules & Script UX 🚧 (current)

**Deliverables**

1. Core orchestrators (`benchmark_engine.py`, `load_engine.py`, `metrics_agg.py`).
2. Scenario framework (`base_scenario.py`, `prompt_length.py`).
3. Scripts (`quick_benchmark.py`, `load_test.py`, `compare_engines.py`).
4. Results directory and export validation.
5. Integration tests for scripts (basic end-to-end).

**Exit criteria**

* Scripts work against all three adapters.
* Aggregated results (avg + percentiles) exported correctly.
* Repo no longer depends on CLI for core flows.
* Documentation updated (“Scripts Quickstart”).

### Phase 3 — Metrics & Load Testing

* Streaming metrics (TTFT, inter-token).
* vLLM/TGI metric parity (8/8 runtime).
* Advanced load testing (concurrency ≥100, burst, ramp-up).
* Resource monitoring (psutil + NVML).
* Error taxonomy & variance analysis.

### Phase 4 — Reporting & Visualization

* HTML reports, cost per token, regression detection.

---

## 7) Backlog (condensed)

| ID     | Epic     | Story                         | Must/Should | Status |
| ------ | -------- | ----------------------------- | ----------- | ------ |
| US-001 | Infra    | Project structure             | Must        | ✅      |
| US-002 | Config   | Pydantic + YAML + env         | Must        | ✅      |
| US-003 | Adapters | Base adapter (async, retries) | Must        | ✅      |
| US-004 | Ollama   | Connect/list/generate         | Must        | ✅      |
| US-005 | vLLM     | Connect via OpenAI API        | Must        | ✅      |
| US-006 | TGI      | Connect + streaming path      | Must        | ✅      |
| US-007 | Metrics  | Models (raw/parsed)           | Must        | ✅      |
| US-008 | Metrics  | Ollama parsing completeness   | Must        | ✅      |
| US-009 | Metrics  | Collector + export JSON/CSV   | Must        | ✅      |
| US-010 | Core     | BenchmarkEngine orchestrator  | Must        | ⬜      |
| US-011 | Core     | LoadEngine concurrency loop   | Must        | ⬜      |
| US-012 | Core     | MetricsAgg (p50/p95/p99)      | Must        | ⬜      |
| US-013 | Scenario | Base + PromptLengthScenario   | Must        | ⬜      |
| US-014 | UX       | quick_benchmark.py            | Must        | ⬜      |
| US-015 | UX       | load_test.py                  | Must        | ⬜      |
| US-016 | UX       | compare_engines.py            | Must        | ⬜      |

---

## 8) Concrete Next Actions (48h)

1. Scaffold `benchmark_engine.py` with stub methods.
2. Implement `metrics_agg.py` with percentile helpers.
3. Write `base_scenario.py` + `prompt_length.py`.
4. Create `quick_benchmark.py` to prove end-to-end run.
5. Add `results/` folder and export JSON/CSV schema.

