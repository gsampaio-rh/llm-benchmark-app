Here’s a structured **Product Requirements Document (PRD)** for the **Universal LLM Engine Benchmarking Tool** based on your summary and my proposed architecture:

---

# 📄 PRD — Universal LLM Engine Benchmarking Tool

## 1. Overview

The **Universal LLM Engine Benchmarking Tool** is a Python-based framework that allows developers, ML/infra engineers, and researchers to run standardized performance benchmarks against multiple LLM serving engines (Ollama, vLLM, HuggingFace TGI, with extensibility for others).

The tool provides **apples-to-apples comparisons** across engines by generating configurable workloads, collecting standardized metrics, and exporting results for analysis and visualization.

---

## 2. Goals & Non-Goals

### Goals

* Provide a **unified interface** to benchmark different LLM serving engines.
* Enable **reproducible, configurable workloads** (prompt length sweeps, concurrency tests, streaming vs non-streaming).
* Collect **standardized metrics**: latency, throughput, time-to-first-token (TTFT), inter-token latency, error rates.
* Export results in **JSON/CSV/Parquet** for later visualization and reporting.
* Produce **cross-engine comparisons** for cost, scalability, and efficiency tradeoffs.
* Allow **optional system telemetry** (GPU/CPU utilization, memory usage) for deeper insights.

### Non-Goals

* This is not a **production load-testing tool** (e.g., k6, Locust replacement).
* Does not manage **engine deployment** — assumes backends are already running and accessible.
* Does not provide **advanced visualization dashboards** out of the box (integration-ready, but external).

---

## 3. Target Users

* **ML Engineers** → Evaluate model serving efficiency, tokenization, and throughput.
* **Infra Engineers / SREs** → Stress test concurrency, scalability, and failure modes.
* **Researchers & Hobbyists** → Run controlled experiments on local or hosted engines.

---

## 4. Key Features

### 4.1 Engine Abstraction

* Unified **EngineAdapter API** for:

  * `warmup()`
  * `tokenize(prompt)`
  * `generate(prompt, streaming=bool)`
* Initial support: **Ollama, vLLM, HuggingFace TGI**.
* Extensible: future engines (SGLang, Text-Generation-Inference forks, TensorRT-LLM).

### 4.2 Workload Scenarios

* **Configurable workloads**:

  * Vary prompt length (short → long contexts).
  * Concurrency sweeps.
  * Streaming vs non-streaming.
* Workload definitions via YAML/JSON configs.

### 4.3 Metrics Collection

* **Per-request metrics**:

  * Latency (request, TTFT, completion).
  * Token throughput.
  * Inter-token delays.
  * Error codes.
* **Aggregated metrics**:

  * p50/p95/p99 latencies.
  * Requests/sec (RPS).
  * Tokens/sec (TPS).
  * Error rates, success ratios.

### 4.4 Reporting & Export

* Export results as:

  * **JSON** (raw event logs).
  * **CSV/Parquet** (aggregates for visualization).
* CLI summary report:

  * Tabular per-engine results.
  * Highlight outliers, p95/p99 comparisons.
* Cross-run comparison mode:

  * Deltas between runs.
  * Significance testing (optional).

### 4.5 System Telemetry (Phase 2+)

* Optional GPU/CPU monitoring:

  * Utilization, memory, power, temperature.
* Join telemetry with request events.

---

## 5. Functional Requirements

1. **Engine Support**

   * Must benchmark at least: Ollama, vLLM, TGI.
   * Must handle both streaming & non-streaming APIs.

2. **Workload Execution**

   * Support **closed-loop** (fixed concurrency).
   * Support **open-loop** (target RPS).
   * Warmup runs before measurement.
   * Timeouts & retry policies configurable.

3. **Metrics**

   * Log all events (request start, TTFT, token received, completion, error).
   * Produce per-request and aggregate stats.
   * Ensure **tokenization parity** (engine tokenizer preferred).

4. **Exports**

   * Raw logs in JSON.
   * Aggregates in CSV/Parquet.
   * Summary in Markdown/CLI.

5. **CLI Interface**

   * `unillmbench run --config workload.yaml`
   * `unillmbench report summarize --run <id>`
   * `unillmbench report compare --a runX --b runY`

---

## 6. Non-Functional Requirements

* **Performance**: Support at least 1k concurrent requests without bottlenecks (async-first design).
* **Extensibility**: Easy to add new engines/adapters.
* **Reproducibility**: Runs must capture config, seed, environment (GPU/CPU info, engine versions).
* **Portability**: Run locally or in CI pipelines.
* **Reliability**: Collect error data without crashes; handle flaky engines gracefully.

---

## 7. Architecture Summary

* **Adapters Layer** → engine-specific HTTP/gRPC clients.
* **Workload Runner** → orchestrates arrival process, manages workers.
* **Metrics Collector** → logs raw events, derives aggregates.
* **Exporter/Reporter** → formats outputs (JSON/CSV/Markdown).
* **Config System** → YAML/JSON configs define experiments.
* **Optional Telemetry** → NVML/psutil monitoring.

---

### 7.1. High-level design

**Key ideas**

* **Thin adapters, fat orchestrator.** Engines only implement a tiny, uniform interface; everything else (workload generation, timing, metrics, retries, reporting) lives in a shared layer.
* **Event-driven metrics.** Treat a single run as a stream of timestamped events (request_created, first_token, token_emitted, completed, errored). Aggregate later.
* **Config-first.** Entire experiment is a versioned, reproducible config/artifact (including environment capture).
* **Deterministic load.** Async workers generate a target arrival process (open/closed loop) so engines are comparably stressed.

#### 7.1.1 Modules & responsibilities

```
unillmbench/
  adapters/               # engine integrations (each ~150–300 LoC)
    base.py               # EngineAdapter ABC
    ollama.py
    vllm.py
    tgi.py
  workloads/
    base.py               # WorkloadSpec, Scenario (prompt generator, lengths, streaming etc.)
    canned/               # prompt length sweep, concurrency sweep, mix, etc.
  runner/
    orchestrator.py       # schedules runs, arrival processes, concurrency control
    worker.py             # async task lifecycle, per-request timing, retries
    tokenization.py       # consistent token counting across engines
  metrics/
    schema.py             # event & record pydantic models (raw + aggregates)
    collectors.py         # event logger, OTel spans optional
    aggregators.py        # p50/p95/p99, RPS, TPS, TTFT, error taxonomies
    exporters/            # JSON/CSV/Parquet, Prometheus push, SQLite
  reporting/
    summarize.py          # human-readable run summary
    compare.py            # cross-run diff & significance tests
  infra/
    env_capture.py        # GPU/CPU/mem, driver, CUDA, engine versions, model hash
    telemetry.py          # optional nvml/psutil sampling (Phase 2+)
  cli.py                  # `unillmbench …`
  config/
    models.py             # pydantic config for runs
  utils/
    time.py, ids.py, io.py, retry.py
```

---

## 8. Milestones

### Phase 1 (MVP)



### Phase 2



### Phase 3


---

## 9. Success Metrics

* **Adoption**: used internally or by community to compare LLM backends.
* **Accuracy**: reproducible results within ±5% variance.
* **Extensibility**: adding a new engine adapter in <200 LoC.
* **Scalability**: handle 1k concurrent requests with stable logging.

---

