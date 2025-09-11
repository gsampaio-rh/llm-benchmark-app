# **PRD: Low-Latency Chat Notebook for vLLM vs TGI vs Ollama**

## **Document Details**

* **Document Owner:** \[Your Name / Team]
* **Stakeholders:** Product Manager, ML Platform Team, DevOps, SRE
* **Last Updated:** 2025-09-10
* **Version:** 1.0

---

## **1. Goal**

Create an **interactive notebook** that:

1. Demonstrates vLLM’s superior performance for **low-latency chat applications** compared to TGI.
2. Provides **step-by-step guidance** for configuration, deployment, and benchmarking.
3. Captures **real-world metrics** such as TTFT (Time To First Token), ITL (Inter-Token Latency), and E2E latency.
4. Runs seamlessly in an **OpenShift cluster** using pre-deployed Helm charts (provided separately in the `helms/` folder).

The final notebook will:

* Act as both a **demo and tutorial** for internal teams and external stakeholders.
* Feel like an **Apple Store demo**, with clean visuals, clear steps, and instant feedback.
* Be **self-contained**, assuming:

  * Helm charts for vLLM and TGI are pre-installed.
  * All configuration is completed before running the notebook.

---

## **2. Target Audience**

* **ML Engineers:** Experiment with low-latency workloads.
* **Product Managers:** Understand performance trade-offs.
* **DevOps/SRE:** Validate infrastructure scalability and stability.
* **Leadership:** Visualize value of vLLM in real-time applications.

---

## **3. Success Metrics**

| Metric                     | Target Outcome                                    |
| -------------------------- | ------------------------------------------------- |
| TTFT (Time To First Token) | vLLM consistently < 100ms                         |
| P95 Latency (E2E)          | < 1 second under 50 concurrent users              |
| Tokens/sec per user        | Smooth streaming, no bursty output                |
| Demo completion time       | < 20 minutes total                                |
| Usability                  | Clear step-by-step flow, no external dependencies |

---

## **4. Requirements**

### **4.1 Functional Requirements**

| ID   | Requirement                                                               |
| ---- | ------------------------------------------------------------------------- |
| FR-1 | Launch vLLM and TGI servers using pre-installed Helm charts on OpenShift. |
| FR-2 | Provide clear configuration for vLLM low-latency tuning parameters.       |
| FR-3 | Generate concurrent user traffic using `wrk` or `locust`.                 |
| FR-4 | Capture and visualize key metrics (TTFT, ITL, E2E latency).               |
| FR-5 | Compare performance metrics between vLLM and TGI.                         |
| FR-6 | Create polished visualizations inline in the notebook.                    |
| FR-7 | Support reproducibility with predefined test prompts.                     |

---

### **4.2 Non-Functional Requirements**

| ID    | Requirement                                                              |
| ----- | ------------------------------------------------------------------------ |
| NFR-1 | Notebook must run end-to-end without manual intervention.                |
| NFR-2 | All logs and artifacts stored in a `/results` directory within notebook. |
| NFR-3 | Visualization must be interactive and easy to interpret.                 |
| NFR-4 | Demo must not require internet access beyond cluster connectivity.       |
| NFR-5 | Helm chart management occurs outside notebook in `helms/` folder.        |

---

## **5. Architecture**

### **High-Level Flow**

```
+-----------------------+
| OpenShift Cluster     |
| (Helm charts deployed)|
+-----------+-----------+
            |
            v
+-----------+-----------+
| Notebook (User)       |
|                       |
| 1. Launch Tests       |
| 2. Run Benchmarks     |
| 3. Collect Metrics    |
| 4. Visualize Results  |
+-----------+-----------+
            |
            v
+-----------------------+
| Results + Artifacts   |
| /results directory    |
+-----------------------+
```

---

### **Deployment Assumptions**

* vLLM and TGI are deployed via Helm charts in the `helms/` directory.
* OpenShift provides:

  * GPU access
  * Load balancers for serving endpoints
* The notebook communicates with vLLM and TGI via HTTP endpoints exposed by OpenShift.

---

## **6. Notebook Flow**

### **Step-by-Step Sections**

| Section                  | Description                                               |
| ------------------------ | --------------------------------------------------------- |
| **1. Introduction**      | Explain purpose of demo and goals (Apple Store style).    |
| **2. Environment Check** | Validate that vLLM and TGI services are up and reachable. |
| **3. Configure vLLM**    | Set low-latency parameters (batch size, GPU utilization). |
| **4. Load Generation**   | Simulate 50-100 concurrent chat users using `wrk`.        |
| **5. Metrics Capture**   | Collect TTFT, ITL, E2E latency.                           |
| **6. Visualization**     | Show real-time charts comparing vLLM vs TGI.              |
| **7. Summary**           | Recap performance differences and key learnings.          |

---

### **Key Commands**

**vLLM Config Example**

```bash
vllm serve mistralai/Mistral-7B-Instruct \
  --max-num-batched-tokens 2048 \
  --max-num-seqs 64 \
  --gpu-memory-utilization 0.92 \
  --max-model-len 4096
```

**Benchmark Command**

```bash
wrk -t4 -c50 -d30s --latency http://vllm-service:8000/generate
```

---

## **7. Staged Implementation Plan**

### **Stage 1: Foundations**

* [ ] Define notebook structure and template.
* [ ] Verify OpenShift access and GPU availability.
* [ ] Validate vLLM and TGI endpoints are running via Helm charts.

### **Stage 2: Core Functionality**

* [ ] Implement vLLM and TGI configuration steps.
* [ ] Add code to run benchmarking (`wrk` load tests).
* [ ] Capture logs and save to `/results`.

### **Stage 3: Metrics & Visualization**

* [ ] Parse benchmark output.
* [ ] Generate charts:

  * TTFT distribution
  * ITL trends
  * P50/P95/P99 latency
* [ ] Compare vLLM vs TGI side-by-side.

### **Stage 4: Polishing**

* [ ] Add clear markdown explanations for each step.
* [ ] Style notebook for tutorial-like flow.
* [ ] Validate usability with a dry run.

### **Stage 5: Finalization**

* [ ] Package notebook and place in `/notebooks`.
* [ ] Ensure `/helms` folder is documented separately.
* [ ] Final QA and stakeholder review.

---

## **8. Deliverables**

| Deliverable                         | Location     |
| ----------------------------------- | ------------ |
| Notebook (`low_latency_chat.ipynb`) | `/notebooks` |
| Helm charts (vLLM & TGI)            | `/helms`     |
| PRD.md (this document)              | `/docs`      |
| Sample test prompts (`prompts.txt`) | `/data`      |

---

## **9. Risks & Mitigations**

| Risk                         | Mitigation Strategy                     |
| ---------------------------- | --------------------------------------- |
| Cluster GPU unavailable      | Mock test using CPU-only small model.   |
| Helm chart misconfiguration  | Validate in staging environment first.  |
| Metrics parsing fails        | Store raw logs for manual review.       |
| Notebook dependency mismatch | Use `requirements.txt` pinned versions. |

---

## **10. Future Extensions**

* Support for high-throughput scenario (Scenario 2).
* Integrate with Prometheus for real-time metrics.
* Add cost-optimized scaling visualizations.

---

**Final Output:**
Save this document as `PRD.md` in the `/docs` directory to serve as the blueprint for development.
