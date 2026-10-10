# 8. Cost, operations and troubleshooting

## Where the money goes

```
total cost = cloud VMs/storage/network (to your cloud)  +  DBUs × price per DBU (to Databricks)
```

DBU rate depends on **workload type** (job vs all-purpose vs SQL vs serverless), tier/edition and cloud.
Check system table `system.billing.usage` for actual consumption by job, cluster and tag.

## Cost levers (biggest first)

| Lever | Action |
|---|---|
| **Job clusters instead of all-purpose** | Production runs on job compute, which has a lower DBU rate and terminates after the run |
| **Auto-termination** | Interactive clusters stop after 10–30 idle minutes |
| **Right-sizing and autoscaling** | Min workers small; don't over-provision for the peak of one stage |
| **Spot instances** | Workers on spot with on-demand fallback; **driver on-demand** |
| **Photon** | Often cheaper in total even at a higher DBU rate, since jobs finish faster |
| **Serverless** | No idle cost, no start-up; check price per DBU vs steady workloads |
| **Don't run streaming 24/7 if you don't need to** | `availableNow` scheduled incremental jobs |
| **Fix the query before scaling the cluster** | Skew, shuffles and small files waste far more than node size |
| **Storage hygiene** | `VACUUM`, lifecycle rules on old checkpoints/logs, avoid unneeded copies |
| **Cluster policies** | Cap node types, max workers, force auto-termination and cost-allocation tags |
| **Tagging** | Tags on clusters/jobs → chargeback reports |
| **Budgets and alerts** | Account-level budgets, billing system-table alerts |

## Choosing compute

| Workload | Choice |
|---|---|
| Scheduled ETL | Job cluster (or serverless jobs) |
| Exploration | Small autoscaling all-purpose cluster or serverless notebook, auto-terminating |
| BI / SQL | SQL warehouse (serverless for spiky use) |
| Heavy ML | GPU or ML runtime cluster, only for the training time |
| Many tiny tasks | Shared job cluster across tasks, or a pool |

Sizing starting point: pick **fewer, larger nodes** for shuffle-heavy work (less network); memory-optimised
for joins/caching, compute-optimised for CPU-bound transforms, storage-optimised for heavy spill or disk cache.

## Operations

### Monitoring
- **Jobs:** run history, durations, failure alerts, SLA/duration warnings.
- **Pipelines:** event log (expectation metrics, update status).
- **Streaming:** `lastProgress`, input vs processed rate, batch duration, state size.
- **Platform:** system tables (`system.compute`, `system.lakeflow`, `system.access`, `system.billing`).
- **Data:** freshness and volume checks, row-count anomalies, Lakehouse Monitoring.
- **Logs:** driver/executor logs and Spark UI; configure cluster log delivery to cloud storage so they survive termination.

### Reliability practices
1. Idempotent tasks and safe retries.
2. Alerts on failures **and on absence** (job didn't run, loaded 0 rows).
3. Repair runs instead of full reruns.
4. Pin Databricks Runtime versions; upgrade deliberately, test on staging.
5. Separate prod from dev by workspace or catalog, with different service principals.
6. Runbooks for the top failure modes.

### Disaster recovery (outline)
- Data in your cloud storage: use cross-region replication or deep clones for critical tables.
- Metadata (UC, jobs, notebooks): rebuild from code (bundles/Terraform) rather than backups.
- Define RPO/RTO; practise a failover. Time travel is not DR.

## Troubleshooting playbook

| Symptom | Where to look | Likely causes and fixes |
|---|---|---|
| Job slow after months | Stage timeline, file count | Small files, data growth, skew; `OPTIMIZE`, fix partitioning, clustering |
| One task takes forever | Stage task-time distribution | Skew: salting, broadcast, AQE skew join |
| Out of memory (driver) | Driver log, stack trace | `collect()`/`toPandas()`, large broadcast, huge file listing |
| Out of memory (executor) | Executor lost/exit 137 | Skew, too few partitions, high `memoryOverhead` needs, exploding arrays |
| Heavy spill to disk | Stage "Spill (disk)" | More partitions, more memory per core, fix skew |
| Cluster won't start | Event log | Cloud quota, IAM, subnet/IP exhaustion, spot capacity |
| `ConcurrentAppendException` | Stack trace | Overlapping writers; narrow `ON`, partition, serialise, retry |
| `FileNotFound` / missing parquet | Read vs `VACUUM` | Retention too short; reader older than vacuum horizon |
| Stream stuck / lagging | Streaming UI | Insufficient compute, state growth, source throttling |
| Stream fails after code change | Error on restart | Checkpoint incompatible with new state schema |
| Schema mismatch on write | Delta error | Enforcement; `mergeSchema` or fix upstream |
| Auto Loader re-ingests or misses files | Checkpoint and source path | Wrong checkpoint, path changed, file overwritten in place (Auto Loader tracks by path, not content) |
| `TABLE_OR_VIEW_NOT_FOUND` | Catalog/schema in session | Wrong default catalog, missing `USE` grant |
| Job works interactively, fails scheduled | Run-as identity, cluster | Permissions of the service principal, different runtime, missing libs/secrets |
| Costs spike | `system.billing.usage` grouped by job/tag | Runaway job, no auto-termination, retry storm, all-purpose cluster used for prod |

## The first five minutes of any performance incident

1. Open the **Spark UI** for the slowest job → which **stage** is the long pole?
2. Is it a **shuffle** stage? Check **task duration distribution** (max vs median) → skew?
3. Check **spill** and **GC time**.
4. Check the **scan**: files read, bytes read, pushed filters.
5. Check the **plan** (`explain`) for the wrong join strategy or an unexpected cartesian.

Then fix the plan or layout; only after that, resize.
