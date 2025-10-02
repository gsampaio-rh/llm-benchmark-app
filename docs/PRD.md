# 📄 Product Requirements Document (PRD)

**Project:** Universal LLM Engine Benchmarking Tool
**Owner:** Gabriel Sampaio gab@redhat.com
**Date:** Oct 25
**Version:** v0.1

---

## 1. **Overview**

This project will deliver a **Python-based benchmarking framework** capable of evaluating the runtime performance of **Ollama, vLLM, and HuggingFace Text Generation Inference (TGI)**.

The tool will provide **standardized workloads**, collect **engine-native metrics**, and output **comparable KPIs** (latency, throughput, utilization, cost-efficiency).

---

## 2. **Goals & Non-Goals**

### Goals

* Provide a **unified benchmarking harness** that can run against Ollama, vLLM, and TGI.
* Support **realistic workload scenarios** (prompt length variation, completion length variation, concurrency, streaming vs non-streaming).
* Capture **per-request runtime metrics** (load duration, prompt_eval_count, eval_count, etc.) and aggregate into KPIs.
* Export results into **JSON, CSV, and dashboard-ready formats**.
* Enable **apples-to-apples comparison** across engines.

### Non-Goals

* Not a tool for **evaluating LLM accuracy/quality** (e.g., BLEU, ROUGE, factual correctness).
* Not a production-grade monitoring system — only for **offline benchmarking and local experiments**.
* Not limited to a single hardware type, but first focus will be **GPU evaluation on local/cloud machines**.

---

## 3. **Personas**

* **ML Engineer**: Needs to compare serving backends for cost/performance tradeoffs.
* **Infra Engineer / SRE**: Needs to test concurrency, scalability, and failure modes.
* **Researcher / Hobbyist**: Wants to run benchmarks on personal machines to explore tradeoffs.

---

## 4. **Use Cases**

1. Benchmark **Ollama** with per-request metrics (`load_duration`, `eval_duration`, etc.).
2. Benchmark **vLLM** under concurrent traffic and measure **throughput scaling**.
3. Benchmark **TGI** in **streaming vs. non-streaming mode**.
4. Run **mixed workload scenarios**: short Q&A + long summarization in parallel.
5. Compare **tokens/sec per dollar** between backends on the same GPU.

---

## 5. **Requirements**

### Functional Requirements

1. **Engine Connectors**

   * Ollama: Call via REST API / CLI and parse returned runtime metrics.
   * vLLM: Call via OpenAI-compatible API.
   * TGI: Call via HuggingFace Inference API (REST).
2. **Workload Generator**

   * Configurable prompt/completion length.
   * Support for streaming vs. non-streaming.
   * Support for concurrency (async requests).
3. **Metrics Collection**

   * Check the metrics.md file for the metrics to collect.
   
4. **Reporting**

   * CLI output (human-readable tables).
   * JSON/CSV export.
   * Optional plots (matplotlib for latency distribution, throughput curves).
5. **Benchmark Scenarios**

   * Check the user_stories.md file for the user stories to test.



### Tech Stack

* **Python**: Core implementation.
* **httpx / aiohttp**: Async API calls.
* **pandas**: Aggregation & CSV export.
* **matplotlib**: Plotting throughput/latency.
* **typer / click**: CLI interface.
* **PyYAML**: Config parsing.


---

## 10. **Success Criteria**

* Able to run **one workload config across Ollama, vLLM, TGI** and produce **comparable JSON output**.
* Users can interpret results easily via **tables and plots**.
* Tool supports both **interactive chat-like benchmarking** and **offline batch benchmarking**.

---

✅ This PRD gives you a **roadmap + architecture** for your personal project.

Do you want me to now draft a **concrete folder structure + starter Python files (with stubs for adapters, workload generator, etc.)** so you can bootstrap coding right away?
