# 📄 Product Requirements Document (PRD)

**Project:** Universal LLM Engine Benchmarking Tool
**Owner:** Gabriel Sampaio — [gab@redhat.com](mailto:gab@redhat.com)
**Date:** Oct 25, 2025
**Version:** v1.1 (Phase 2 alignment)

---

## 1. Overview

A **Python benchmarking toolkit** to evaluate runtime performance of **Ollama, vLLM, and Hugging Face TGI**.

The toolkit provides **standardized workloads**, collects **engine-native metrics**, normalizes them, and outputs **comparable KPIs** (latency, throughput, reliability).

**Interface:** *scripts per use case* (`quick_benchmark.py`, `load_test.py`, `compare_engines.py`) — CLI framework is being retired.

---

## 2. Goals & Non-Goals

### Goals

* Provide **unified benchmarking harness** across Ollama, vLLM, TGI.
* Support **realistic workloads** (prompt/completion variation, concurrency, streaming toggle).
* Collect **per-request runtime metrics** (load, eval, TTFT, TPS) and aggregate into KPIs.
* Export results as **JSON + CSV** with deterministic schema.
* Enable **side-by-side comparison** via dedicated script.

### Non-Goals (Phase 2)

* LLM quality/accuracy metrics (BLEU, ROUGE, factual correctness).
* Production monitoring (alerts, dashboards, regressions).
* Long endurance, ramp-up, or burst scenarios (Phase 3).
* Cost-per-token or cost-per-request analysis (Phase 4).

---

## 3. Personas

* **ML Engineer:** Optimize serving backends for cost/performance.
* **Infra/SRE:** Stress-test concurrency, tail latency, failure handling.
* **Researcher/Hobbyist:** Run quick comparisons on personal hardware.

---

## 4. Use Cases

1. Run a **quick benchmark** of short/medium/long prompts on Ollama, export metrics.
2. Run a **sustained load test** (e.g. 10 users, 60s) on vLLM and measure throughput scaling.
3. Compare **Ollama vs vLLM vs TGI** on identical scenario, export comparison CSV.
4. Toggle **streaming vs non-streaming** to measure time-to-first-token.

---

## 5. Requirements

### Functional

1. **Engine Connectors** (already in repo)

   * Ollama: REST API adapter.
   * vLLM: OpenAI-compatible adapter.
   * TGI: HuggingFace inference adapter.
   * Abstract base adapter defines `send_request`, `health_check`, `parse_metrics`.

2. **Core Modules** (to be added in Phase 2)

   * `benchmark_engine.py`: Orchestrates workloads + adapters.
   * `load_engine.py`: Runs bounded concurrent async requests.
   * `metrics_agg.py`: Aggregates per-request into KPIs (p50/p95/p99, RPS, TPS, success_rate).

3. **Scenarios** (to be added in Phase 2)

   * `base_scenario.py`: Defines `RequestSpec` and abstract generator.
   * `prompt_length.py`: Implements short (16), medium (256), long (1024) token prompts.

4. **Scripts (UX layer)**

   * `_common.py`: Adapter factory, export utils.
   * `quick_benchmark.py`: Single-engine quick run.
   * `load_test.py`: Sustained load with concurrency.
   * `compare_engines.py`: Run multiple engines and export side-by-side.

5. **Metrics**

   * Per-request: durations, token counts, first token latency, request timestamps.
   * Aggregates: p50/p95/p99, RPS, avg TPS, success_rate.

### Non-Functional

* Overhead ≤5% vs naive calls.
* Retry/backoff for failures.
* Typed code + adapter pattern.
* Artifacts saved under `results/`.

---

## 6. Data Model

**Per-Request (row)**

* `engine, model, request_id, request_start, first_token_time?, completion_time, total_duration, load_duration?, prompt_eval_count?, eval_count?, eval_duration?, response_token_rate?, status, error_type?`

**Aggregate**

* `count, latency_p50, latency_p95, latency_p99, rps, avg_response_tps, success_rate`

---

## 7. Architecture

### Current (as of Oct 25)

```
src/
  adapters/         # ✅ Ollama, vLLM, TGI, base adapter
  core/             # connection_manager.py, metrics_collector.py
  models/           # engine_config, metrics
  config/           # config_manager
  cli/              # legacy CLI (to be deprecated)
```

### Target (Phase 2 structure)

```
src/
  adapters/              # (unchanged)
  core/
    benchmark_engine.py  # new
    load_engine.py       # new
    metrics_agg.py       # new
  scenarios/
    base_scenario.py     # new
    prompt_length.py     # new
  models/                # (unchanged)
  config/                # (unchanged)
scripts/
  _common.py             # new
  quick_benchmark.py     # new
  load_test.py           # new
  compare_engines.py     # new
results/                 # gitignored artifacts
```

---

## 8. Success Criteria (Phase 2)

* vLLM & TGI achieve **metric parity** with Ollama (8/8 per-request runtime).
* Load test handles **100+ concurrent requests** stably.
* Aggregates (p50/p95/p99, RPS, TPS, success_rate) exported in JSON + CSV.
* Three scripts run end-to-end with minimal config.
* Docs include “Scripts Quickstart” section.

---

## 9. Risks & Mitigations

* **API drift** → pin versions, defensive parsing.
* **High concurrency instability** → bounded semaphore, retries.
* **Partial metric availability** → nullable fields, clear docs.

---

## 10. Deliverables

* Core modules (`benchmark_engine.py`, `load_engine.py`, `metrics_agg.py`).
* Scenario framework (`base_scenario.py`, `prompt_length.py`).
* Three scripts for UX.
* Example artifacts under `results/`.
* Updated README with Scripts Quickstart.
