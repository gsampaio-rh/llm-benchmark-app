# LLM Engine Metrics Collection Guide

This document defines the key performance indicators (KPIs) for benchmarking LLM engines and specifies how to measure each metric across Ollama, TGI, and vLLM engines.

## Metrics by Engine Implementation

| **Category**             | **KPI**                            | **Definition**                                 | **Ollama**                   | **TGI**                     | **vLLM**                    |
| ------------------------ | ---------------------------------- | ---------------------------------------------- | ---------------------------- | --------------------------- | --------------------------- |
| **Per-Request Runtime**  | Load Duration                      | Setup time before prompt evaluation (per call) | `load_duration` (nanosec)    | *Not available*             | *Estimated from timing*     |
|                          | Prompt Evaluation Count            | Number of input tokens processed               | `prompt_eval_count`          | `details.prefill` length    | `usage.prompt_tokens`       |
|                          | Prompt Evaluation Time             | Time spent processing input tokens             | `prompt_eval_duration` (ns)  | *Estimated from timing*     | *Measured from streaming*   |
|                          | Prompt Token Rate                  | Input tokens processed per sec                 | *Calculated*                 | *Calculated*                | *Calculated*                |
|                          | Response Token Count               | Number of output tokens generated              | `eval_count`                 | `details.tokens` length     | `usage.completion_tokens`   |
|                          | Response Generation Time           | Time spent generating output tokens            | `eval_duration` (nanosec)    | *Calculated from tokens*    | *Measured from streaming*   |
|                          | Response Token Rate                | Output tokens/sec                              | *Calculated*                 | *Calculated*                | *Calculated*                |
|                          | End-to-End Latency                 | Total request runtime (all phases)             | `total_duration` (nanosec)   | *Client-side timing*        | *Client-side timing*        |
| **Latency**              | First Token Latency                | Time to first output token                     | *Estimated from timing*      | *From streaming response*   | *From streaming response*   |
|                          | Inter-token Latency                | Avg time per generated token                   | `eval_duration / eval_count` | *From token timestamps*     | *From streaming timing*     |
|                          | Tail Latency Variance              | Latency stability (p95/p99)                    | *Aggregate logs*             | *Aggregate logs*            | *Aggregate logs*            |
| **Throughput**           | Aggregate TPS                      | All tokens/sec across concurrent users         | *Sum concurrent requests*    | *Sum concurrent requests*   | *Sum concurrent requests*   |
|                          | Requests per Second (RPS)          | Sustained queries handled under load           | *Load test framework*        | *Load test framework*       | *Load test framework*       |
|                          | Batch Size Efficiency              | Speedup factor when batching is enabled        | *Compare batch vs single*    | *TGI batching metrics*      | *vLLM batching metrics*     |
|                          | Streaming vs Non-Streaming TPS     | Throughput difference for streaming mode       | *Compare modes*              | *Compare modes*             | *Compare modes*             |
| **Resource Utilization** | GPU Utilization                    | Compute % used                                 | `nvidia-smi` + profiler      | `nvidia-smi` + `/metrics`   | `nvidia-smi` + profiler     |
|                          | CPU Utilization                    | Pre/post-processing load                       | System monitor               | System monitor              | System monitor              |
|                          | Memory Footprint                   | VRAM + host RAM usage                          | Peak monitoring              | `/metrics` endpoint         | Peak monitoring             |
|                          | KV Cache Hit Rate                  | Cache reuse effectiveness                      | *Engine logs*                | *TGI internal metrics*      | *vLLM internal metrics*     |
|                          | Network Usage                      | Bandwidth in multi-node serving                | Network monitor              | Network monitor             | Network monitor             |
| **Scalability**          | Multi-GPU Scaling                  | Speedup vs. linear ideal                       | *Multi-GPU benchmarks*       | *TGI tensor parallelism*    | *vLLM tensor parallelism*   |
|                          | Multi-node Scalability             | RPS gain with more nodes                       | *Cluster benchmarks*         | *Cluster benchmarks*        | *Cluster benchmarks*        |
|                          | Elastic Scaling Latency            | Time to add/remove capacity                    | *Orchestration logs*         | *K8s HPA metrics*           | *K8s HPA metrics*           |
|                          | Load Distribution                  | Fairness across GPUs/nodes                     | *Engine scheduling logs*     | *TGI scheduler metrics*     | *vLLM scheduler metrics*    |
| **Reliability**          | Success Rate                       | Completed requests %                           | Success vs total             | Success vs total            | Success vs total            |
|                          | Timeout Rate                       | Requests exceeding SLA                         | *Client timeout tracking*    | *Client timeout tracking*   | *Client timeout tracking*   |
|                          | Error Breakdown                    | Failures by type (OOM, crash)                  | *Error categorization*       | *TGI error logs*            | *vLLM error logs*           |
|                          | Recovery Time                      | Time to resume after failure                   | *Health check monitoring*    | *Health check monitoring*   | *Health check monitoring*   |
| **Serving Features**     | Continuous Batching Efficiency     | Queueing delay vs. throughput gain             | *Not supported*              | *TGI batching analysis*     | *vLLM batching analysis*    |
|                          | Speculative Decoding Effectiveness | Speedup from speculative decoding              | *Not supported*              | *Not supported*             | *vLLM speculative metrics*  |
|                          | Streaming Responsiveness           | Delay to first streamed chunk                  | *Streaming timing*           | *SSE timing analysis*       | *SSE timing analysis*       |
|                          | Model Hot-Swap Latency             | Downtime for model switch                      | *Model load timing*          | *Container restart time*    | *Model load timing*         |
| **Cost & Efficiency**    | Tokens per Dollar                  | Efficiency under GPU pricing                   | `(tokens/sec) / $/hour`      | `(tokens/sec) / $/hour`     | `(tokens/sec) / $/hour`     |
|                          | Requests per Dollar                | SLA-compliant efficiency                       | `(RPS) / $/hour`             | `(RPS) / $/hour`            | `(RPS) / $/hour`            |
|                          | Energy Efficiency                  | Tokens per Joule                               | *Power monitor*              | *Power monitor*             | *Power monitor*             |
|                          | Idle Waste                         | GPU underutilization %                         | *Idle GPU time logs*         | *Idle GPU time logs*        | *Idle GPU time logs*        |
| **User Experience**      | Queueing Time                      | Time request waits before execution            | *Not applicable*             | *TGI queue metrics*         | *vLLM queue metrics*        |
|                          | Streaming Smoothness               | Jitter in token emission                       | *Inter-token timing*         | *Token timestamp analysis*  | *Token timestamp analysis*  |
|                          | Predictability                     | Variance across identical requests             | *Latency std deviation*      | *Latency std deviation*     | *Latency std deviation*     |
|                          | Responsiveness Score               | Human tester rating                            | *Survey / UX test*           | *Survey / UX test*          | *Survey / UX test*          |

## Engine-Specific Notes

### Ollama
- **Strengths**: Rich native metrics with nanosecond precision timing
- **API Response**: Direct metrics in `/api/generate` response
- **Limitations**: No advanced batching or speculative decoding

### TGI (Text Generation Inference)
- **Strengths**: Continuous batching, Prometheus metrics endpoint
- **API Response**: Detailed token-level information in `details` field
- **Metrics Endpoint**: `/metrics` for Prometheus-style metrics
- **Limitations**: Limited native timing breakdowns

### vLLM
- **Strengths**: OpenAI-compatible API, advanced features (speculative decoding)
- **API Response**: Standard OpenAI format with `usage` statistics
- **Streaming**: Server-Sent Events (SSE) for token-level timing
- **Limitations**: Less detailed native metrics than Ollama

## Implementation Status

| Engine | Per-Request Runtime | Latency | Throughput | Resource | Reliability |
|--------|-------------------|---------|------------|----------|-------------|
| Ollama | 8/8 ✅ (100%)     | 2/3 ✅  | 0/4 ❌     | 0/5 ❌   | 1/4 ✅      |
| vLLM   | 8/8 ✅ (100%) 🎉  | 2/3 ✅  | 0/4 ❌     | 0/5 ❌   | 1/4 ✅      |
| TGI    | 1/8 ❌ (13%)      | 0/3 ❌  | 0/4 ❌     | 0/5 ❌   | 1/4 ✅      |

*Legend: ✅ Implemented, ⚠️ Partial, ❌ Not implemented*

**🎉 US-201 COMPLETED**: vLLM enhanced metrics successfully achieve 8/8 per-request runtime coverage!
