| **Category**             | **KPI**                            | **Definition**                                 | **How to Measure / Source**  |
| ------------------------ | ---------------------------------- | ---------------------------------------------- | ---------------------------- |
| **Per-Request Runtime**  | Load Duration                      | Setup time before prompt evaluation (per call) | `load_duration` (Ollama log) |
|                          | Prompt Evaluation Count            | Number of input tokens processed               | `prompt_eval_count`          |
|                          | Prompt Evaluation Time             | Time spent processing input tokens             | `prompt_eval_duration`       |
|                          | Prompt Token Rate                  | Input tokens processed per sec                 | `prompt_token/s`             |
|                          | Response Token Count               | Number of output tokens generated              | `eval_count`                 |
|                          | Response Generation Time           | Time spent generating output tokens            | `eval_duration`              |
|                          | Response Token Rate                | Output tokens/sec                              | `response_token/s`           |
|                          | End-to-End Latency                 | Total request runtime (all phases)             | `total_duration`             |
| **Latency**              | First Token Latency                | Time to first output token                     | Request trace (p50/p95/p99)  |
|                          | Inter-token Latency                | Avg time per generated token                   | `eval_duration / eval_count` |
|                          | Tail Latency Variance              | Latency stability (p95/p99)                    | Aggregate logs               |
| **Throughput**           | Aggregate TPS                      | All tokens/sec across concurrent users         | Sum of token/s logs          |
|                          | Requests per Second (RPS)          | Sustained queries handled under load           | Load test                    |
|                          | Batch Size Efficiency              | Speedup factor when batching is enabled        | Compare batched vs. single   |
|                          | Streaming vs Non-Streaming TPS     | Throughput difference for streaming mode       | Engine metrics               |
| **Resource Utilization** | GPU Utilization                    | Compute % used                                 | `nvidia-smi`, profiler       |
|                          | CPU Utilization                    | Pre/post-processing load                       | System monitor               |
|                          | Memory Footprint                   | VRAM + host RAM usage                          | Peak logs                    |
|                          | KV Cache Hit Rate                  | Cache reuse effectiveness                      | Engine logs                  |
|                          | Network Usage                      | Bandwidth in multi-node serving                | Net monitor                  |
| **Scalability**          | Multi-GPU Scaling                  | Speedup vs. linear ideal                       | Tokens/sec vs GPU count      |
|                          | Multi-node Scalability             | RPS gain with more nodes                       | Cluster benchmarks           |
|                          | Elastic Scaling Latency            | Time to add/remove capacity                    | Orchestration logs           |
|                          | Load Distribution                  | Fairness across GPUs/nodes                     | Engine scheduling logs       |
| **Reliability**          | Success Rate                       | Completed requests %                           | Success vs total             |
|                          | Timeout Rate                       | Requests exceeding SLA                         | Timeout counter              |
|                          | Error Breakdown                    | Failures by type (OOM, crash)                  | Logs                         |
|                          | Recovery Time                      | Time to resume after failure                   | Monitor restart latency      |
| **Serving Features**     | Continuous Batching Efficiency     | Queueing delay vs. throughput gain             | Compare batched runs         |
|                          | Speculative Decoding Effectiveness | Speedup from speculative decoding              | TPS gain %                   |
|                          | Streaming Responsiveness           | Delay to first streamed chunk                  | Trace timestamps             |
|                          | Model Hot-Swap Latency             | Downtime for model switch                      | Deployment logs              |
| **Cost & Efficiency**    | Tokens per Dollar                  | Efficiency under GPU pricing                   | `(tokens/sec) / $/hour`      |
|                          | Requests per Dollar                | SLA-compliant efficiency                       | `(RPS) / $/hour`             |
|                          | Energy Efficiency                  | Tokens per Joule                               | Power monitor                |
|                          | Idle Waste                         | GPU underutilization %                         | Idle GPU time logs           |
| **User Experience**      | Queueing Time                      | Time request waits before execution            | Scheduler metrics            |
|                          | Streaming Smoothness               | Jitter in token emission                       | Inter-token logs             |
|                          | Predictability                     | Variance across identical requests             | Std. dev of latency          |
|                          | Responsiveness Score               | Human tester rating                            | Survey / UX test             |
