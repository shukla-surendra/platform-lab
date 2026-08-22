# System Design — Track B

This section covers **Track B (ML System Design)** from the 12-week transition plan:
moving from "described components" to "reasoned about trade-offs." It's organized as a
sequence of tutorials that follow the plan's week-by-week topic order, extended with five
more covering Track D tools and LLMOps — topics that don't have their own tutorial in the
original plan — plus a bank of scenario-debugging problems.

## Read This First: Prerequisite Concepts

If terms like **p99 latency**, **the nines**, **sharding vs. replication**, or
**idempotency** aren't things you could explain from first principles yet, start with the
**[Prerequisite Concepts](00_prerequisite_concepts/01_performance_and_scale.md)** primer
(thirty-one short parts: [Performance & Scale](00_prerequisite_concepts/01_performance_and_scale.md),
[Data & Consistency](00_prerequisite_concepts/02_data_and_consistency.md),
[Communication & Resilience](00_prerequisite_concepts/03_communication_and_resilience.md),
[CPU vs. GPU](00_prerequisite_concepts/04_cpu_vs_gpu.md),
[Choosing a GPU & Code Optimization](00_prerequisite_concepts/05_gpu_selection_and_code_optimization.md),
[Mechanical Sympathy & the Physics of Latency](00_prerequisite_concepts/06_mechanical_sympathy_and_physics_of_latency.md),
[Saturation, Amdahl's Law & Hedged Requests](00_prerequisite_concepts/07_saturation_amdahls_law_and_hedged_requests.md),
[The Cost of Communication](00_prerequisite_concepts/08_cost_of_communication.md),
[The Anatomy of a Request (DNS, BGP, and the Edge)](00_prerequisite_concepts/09_dns_bgp_and_the_edge.md),
[The Physics of Persistence (B-Trees vs. LSM-Trees)](00_prerequisite_concepts/10_physics_of_persistence.md),
[Taxonomy of Storage — Choosing by First Principles, Not Fashion](00_prerequisite_concepts/11_taxonomy_of_storage_choice.md),
[Sharding — The Illusion of Infinite Space, and the Vertical Wall](00_prerequisite_concepts/12_sharding_and_the_vertical_wall.md),
[CAP Theorem & PACELC](00_prerequisite_concepts/13_cap_theorem_and_pacelc.md),
[Geospatial Indexing — Finding What's Nearby](00_prerequisite_concepts/14_geospatial_indexing.md),
[Caching — Trading Freshness for Speed](00_prerequisite_concepts/15_caching.md),
[Observability — Metrics, Logs, and Traces](00_prerequisite_concepts/16_observability.md),
[Isolation Levels & Concurrency Control](00_prerequisite_concepts/17_isolation_and_concurrency_control.md),
[Message Queues & Event-Driven Semantics](00_prerequisite_concepts/18_message_queues_and_event_driven_semantics.md),
[Load Balancing](00_prerequisite_concepts/19_load_balancing.md),
[Microservices Architecture Patterns](00_prerequisite_concepts/20_microservices_architecture_patterns.md),
[The FR/NFR Framework and a Real-Tools Quick Reference](00_prerequisite_concepts/21_fr_nfr_framework_and_architecture_tools.md),
[Proxies — Forward, Reverse, and Why "Reverse Proxy vs. Load Balancer" Is a Trick Question](00_prerequisite_concepts/22_proxies_forward_and_reverse.md),
[Long-Polling, WebSockets, and Server-Sent Events](00_prerequisite_concepts/23_realtime_communication_long_polling_websockets_sse.md),
[Cardinality — One Word, Five Meanings, One Underlying Idea](00_prerequisite_concepts/24_cardinality.md),
[Redis — Data Structures as System Design Primitives](00_prerequisite_concepts/25_redis_as_a_system_design_primitive.md),
[SSH Keys and Public-Key Cryptography](00_prerequisite_concepts/26_ssh_keys_and_public_key_cryptography.md),
[Metrics Collection Mechanics](00_prerequisite_concepts/27_metrics_collection_and_scraping_mechanics.md),
[Log Collection Mechanics — Loki](00_prerequisite_concepts/28_log_collection_mechanics_loki.md),
[The Rest of the Stack — Grafana, Tempo, Alertmanager](00_prerequisite_concepts/29_the_rest_of_the_stack_grafana_tempo_alertmanager.md),
[Coalition vs. Unified — LGTM, SigNoz, OpenObserve](00_prerequisite_concepts/30_coalition_vs_unified_lgtm_signoz_openobserve.md),
[OpenTelemetry and Its Ecosystem](00_prerequisite_concepts/31_opentelemetry_and_its_ecosystem.md))
before the Interview Framework below. It's the shared vocabulary every tutorial in this
section — and in the [Distributed Systems Design track](../system_design_practice/README.md) — assumes
without re-explaining.

## How the core six map to the transition plan

| Weeks | Tutorial | Anchor it to |
|---|---|---|
| 1-2 | [Fundamentals: Building Blocks](ml_system_design/00_interview_framework_fundamentals.md) | General warm-up (URL shortener, rate limiter) |
| 3-4 | [High-Throughput Ingestion Pipelines](ml_system_design/02_ingestion_pipeline.md) (+ [deep-dive: Lambda vs. EKS cost/speed](ml_system_design/02_ingestion_pipeline_serverless_vs_eks_receipt_processing.md)) | Your production-style pipeline: Step Functions/Lambda/S3/Databricks |
| 5-6 | [Feature Store + Model Promotion](ml_system_design/03_feature_store_model_promotion.md) (+ [deep-dive: is it worth it when reuse is low?](ml_system_design/03_feature_store_model_promotion_is_a_feature_store_worth_it.md)) | Your production ML platform: dev/qa/stage/prod/ml-prod, Unity Catalog, MLflow, Feast |
| 7-8 | [Model Serving & Deployment](ml_system_design/04_model_serving_deployment.md) | Extending a production serving layer with canary/shadow, KServe/Seldon |
| 9-10 | [ML/LLM Observability & Drift](ml_system_design/05_observability_drift.md) (+ [deep-dive: promotion and observability as one closed-loop system](ml_system_design/05_observability_drift_closed_loop_promotion_and_monitoring.md)) | Generalizing a production drift/monitoring setup; Prometheus/Grafana + Evidently/Arize |
| 11-12 | [RAG + LLM-Serving at Scale](ml_system_design/06_rag_llm_serving_at_scale.md) | Your Track C project: vector DB, LangChain, vLLM/Triton serving |

Read **[00 — The Interview Framework](ml_system_design/00_interview_framework.md)** before any of
the topic tutorials — it's the four-step structure (clarify → high-level design → deep-dive
→ trade-offs) every tutorial in this section is written around, plus a clarifying-question
bank and a trade-off vocabulary cheat sheet you'll reuse in every round.

## Five more tutorials: Track D tools and LLMOps, given the same full treatment

The transition plan's Track D checklist lists several tools as "mention if a round goes
there — not worth dedicated build time." These tutorials give them (plus LLMOps, which the
original plan folds into RAG but deserves its own treatment) the same full treatment as the
core six, since a real interview follow-up on any of them deserves more than a name-drop:

| Tutorial | Covers |
|---|---|
| [7. Distributed Training & Ray/Ray Serve](ml_system_design/07_distributed_training_serving.md) | Data/model/pipeline parallelism, checkpointing at scale, Ray Core/Train/Serve |
| [8. ML Orchestration](ml_system_design/08_ml_orchestration.md) | Kubeflow/Argo Workflows vs. Airflow — the actual architectural trade-off, not just the names |
| [9. GitOps & CI/CD for ML](ml_system_design/09_gitops_ml_cicd.md) | ArgoCD reconciliation, DVC vs. Delta Lake/Unity Catalog, ML-specific CI gates |
| [10. Cost, Security & Multi-Region Governance](ml_system_design/10_cost_security_multiregion.md) | Cost attribution, PII/compliance, RTO/RPO and active-active vs. active-passive DR |
| [11. LLMOps: Prompting, Fine-Tuning, Evals & Guardrails](ml_system_design/11_llmops.md) | Fine-tuning vs. RAG vs. prompting, LoRA/QLoRA, eval gates, prompt injection, LLM gateway/cost routing |
| [13. Running a ~1TB LLM: Multi-GPU, Multi-Node Inference](01_ml_system_design/13_large_model_multi_gpu_inference/README.md) | Why a huge model forces multi-*node* serving, tensor/pipeline parallelism, KV-cache memory math, vLLM/TensorRT-LLM/TGI/SGLang compared, a concrete AWS (EFA/FSx/SageMaker LMI vs. EKS) reference architecture |

## Going deeper: the hardware/systems layer underneath all of this

**[GPU Fleet / AI Infrastructure](../gpu_infrastructure/README.md)** is a separate,
undated track covering what this section treats as a black box: GPU architecture (SMs,
Tensor Cores, HBM bandwidth), NCCL/RDMA/InfiniBand networking, Kubernetes GPU scheduling,
quantization internals, and fleet-scale production operations. Worth reaching for when a
question here ("why not just add more GPUs," "what's actually inside an H100") deserves
an answer grounded in hardware, not just architecture-diagram vocabulary.

## Tricky MLOps Scenarios: debugging, not designing

[**Thirteen scenario-debugging problems**](ml_system_design/12_tricky_scenarios_readme.md) — realistic,
ambiguous production incidents (a canary that passed but still caused a P1, drift
dashboards that stayed green while a model silently degraded, GPU costs tripling
overnight, a prompt change that passed eval but bypassed a guardrail) with a structured
walkthrough of clarifying questions, ranked hypotheses, diagnostic steps, the fix, and the
systemic lesson. This tests the skill design questions don't: reasoning about a system
that's already broken, not building one from scratch. Every scenario is cross-referenced
back to the tutorial covering its underlying pattern.

## How to practice this

- **Out loud, not in writing.** Most interviews expect verbal reasoning with light
  diagramming (paper or Excalidraw), not a finished document — rehearse it that way from
  day one, not just the week before an interview.
- **Anchor to your own systems.** Every tutorial below ends with a "Make It Yours" section
  of prompts referencing your own production systems — fill those in with your own
  specifics once, then reuse that story across interviews. Real, specific trade-offs you
  actually lived through
  beat textbook architectures every time; this is a real advantage over candidates who
  only know the generic version.
- **Weight the trade-off discussion heaviest.** At senior level, interviewers score the
  deep-dive and trade-off portions far more than the high-level box diagram. The first few
  clarifying questions you ask also signal seniority more than anything after them — don't
  rush past that step.
- **One weekend block, 2-3 hrs**, ideally with a friend or a mock-interview platform, per
  the plan's weekly time budget.
