# Tools & Technologies Log

Lightweight index of tools and technologies discussed in chat for this
project. Each tool has its own folder under `docs/tools/<tool-slug>/README.md`
with the full write-up (purpose, alternatives, usage examples, code samples).
This file just points to them. Maintained automatically by the `tech-log`
skill (see `../../.claude/skills/tech-log/SKILL.md`, at the repo root).

## Index

<!-- INDEX_START -->
- [Airflow](tools/airflow/README.md) — workflow orchestrator (DAG scheduler and executor)
- [Amazon CloudWatch](tools/cloudwatch/README.md) — observability / monitoring (AWS-native)
- [ClickHouse](tools/clickhouse/README.md) — database (column-oriented OLAP)
- [Databricks Lakehouse Monitoring](tools/databricks-lakehouse-monitoring/README.md) — ML monitoring / observability (Databricks-native)
- [Datadog](tools/datadog/README.md) — observability / monitoring (commercial, all-in-one)
- [Dynatrace](tools/dynatrace/README.md) — observability / monitoring (commercial, all-in-one)
- [Elasticsearch (ELK / EFK Stack)](tools/elasticsearch/README.md) — observability / monitoring (logs), search
- [Evidently (Evidently AI)](tools/evidently/README.md) — ML monitoring / observability
- [Feast](tools/feast/README.md) — feature store
- [Grafana](tools/grafana/README.md) — observability / monitoring (Kubernetes/EKS)
- [Jaeger](tools/jaeger/README.md) — observability / monitoring (tracing)
- [Kafka](tools/kafka/README.md) — distributed event streaming platform (partitioned commit log)
- [LGTM Stack](tools/lgtm-stack/README.md) — observability / monitoring (open-source stack, unified metrics+logs+traces)
- [Linux & Shell Scripting](tools/linux-shell-scripting/README.md) — operating system / command-line automation (Bash)
- [LocalStack](tools/localstack/README.md) — local cloud emulator (AWS, self-hosted/CI)
- [Loki](tools/loki/README.md) — observability / monitoring (Kubernetes/EKS)
- [Microservices](tools/microservices/README.md) — distributed systems architecture pattern (production failure modes and operations, not a single tool)
- [Mimir](tools/mimir/README.md) — observability / monitoring (metrics, long-term storage)
- [MinIO](tools/minio/README.md) — object storage (self-hosted, S3-API-compatible)
- [MLflow](tools/mlflow/README.md) — experiment tracking / model registry / model lifecycle
- [Instrumentation Tradeoffs](observability-instrumentation-tradeoffs.md) — cross-cutting: platform vs. developer responsibility for telemetry, critical-path/sampling/cardinality cost tradeoffs
- [OTLP, the OpenTelemetry Collector, and Datadog](observability-otel-collector-and-datadog.md) — cross-cutting: OTLP transport mechanics, Collector scaling, Grafana-stack vs. Datadog, MLflow autologging as instrumentation
- [Production Logging Guidelines](production-logging-guidelines.md) — cross-cutting: log levels (ERROR/WARN/INFO/DEBUG/TRACE), structured logging, correlation IDs, sampling, retention, anti-patterns
- [ML & GenAI Lifecycle and Governance](ml-genai-lifecycle-and-governance.md) — cross-cutting: lifecycle stages, data/model governance, SR 11-7, EU AI Act, GDPR Art. 22
- [MLOps, AIOps, LLMOps (definitions & origins)](mlops-aiops-llmops.md) — cross-cutting: what each discipline is, who defines it, where they overlap
- [New Relic](tools/new-relic/README.md) — observability / monitoring (commercial, all-in-one)
- [NumPy](tools/numpy/README.md) — numerical computing (array/memory foundation of the Python ML stack)
- [Observability on EKS (overview)](observability-on-eks.md) — cross-cutting: Prometheus, Grafana, Loki, ELK/EFK, tracing, alerting, alternatives
- [Observability Terminology (telemetry, tracing, cardinality)](observability-terminology.md) — cross-cutting: term definitions, origins, analogies, CloudWatch vocabulary mapping
- [OpenTelemetry](tools/opentelemetry/README.md) — observability / monitoring (tracing, instrumentation standard)
- [pandas](tools/pandas/README.md) — data manipulation / analysis (single-machine, in-memory)
- [PostgreSQL](tools/postgresql/README.md) — relational database (query engine, storage engine, and — via extensions — spatial/full-text/hybrid-NoSQL engine)
- [Prometheus](tools/prometheus/README.md) — observability / monitoring (Kubernetes/EKS)
- [RabbitMQ](tools/rabbitmq/README.md) — message broker (AMQP 0-9-1 — exchange/queue/binding routing model)
- [Ray](tools/ray/README.md) — distributed compute framework (general-purpose Python parallelism — tasks and actors)
- [Redis](tools/redis/README.md) — in-memory data store (cache, message broker, primitive toolkit)
- [scikit-learn](tools/scikit-learn/README.md) — ML modeling (classical/non-deep-learning algorithms; also the standard Python estimator API convention)
- [SigNoz](tools/signoz/README.md) — observability / monitoring (open-source, unified metrics+logs+traces)
- [Apache Spark](tools/spark/README.md) — distributed data processing (batch + streaming + classical ML via MLlib)
- [Splunk](tools/splunk/README.md) — observability / monitoring (commercial, logs/SIEM roots)
- [Tempo](tools/tempo/README.md) — observability / monitoring (tracing)
- [vLLM](tools/vllm/README.md) — LLM inference / serving
- [XGBoost](tools/xgboost/README.md) — ML modeling (gradient-boosted decision trees)
- [Zookeeper / ClickHouse Keeper](tools/zookeeper/README.md) — distributed coordination service
<!-- INDEX_END -->
