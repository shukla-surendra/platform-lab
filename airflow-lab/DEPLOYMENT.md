# Deploying DAGs when Airflow is run by another team

Scenario: the DevOps/platform team owns the Airflow setup (this lab plays that role). A data
engineer owns a **separate repo** with DAGs and never edits files on the Airflow server.

Key idea: **deploying a DAG = delivering a Python file to a place Airflow reads.** Airflow has no
"upload DAG" API. So deployment is decoupled from Airflow being up: files can be delivered while
Airflow is down and get picked up when it returns.

Two layers, two lifecycles:

| Layer | Owner | Changes | Tool |
|---|---|---|---|
| Infrastructure (Airflow itself) | DevOps | rarely | Terraform, Helm, compose |
| DAG code | Data engineers | many times a day | Git + CI/sync |

## The contract between the two repos

**Platform repo provides:** Airflow, one agreed place DAGs are read from (git-sync source, bucket,
volume, or DAG bundle), a base image with the allowed packages, Connections/secrets backend.

**Data engineer repo provides:** DAG files in the agreed layout, a CI check, and (depending on the
model) the delivery step.

```
data-pipelines/                (data engineer repo)
├── dags/
├── tests/test_dagbag.py       (CI: no import errors)
├── requirements.txt           (only matters when the DE builds an image)
└── .github/workflows/deploy.yml
```

## Four delivery models

**1. Git-sync / Git DAG bundle: Airflow pulls from the DE repo.** No CI delivery step. The DE merges
to `main` and Airflow fetches it within the refresh interval (about 60s). Helm example:

```yaml
dags:
  gitSync:
    enabled: true
    repo: git@github.com:company/data-pipelines.git
    branch: main
    subPath: dags
    period: 60s
```

**2. CI pushes to a bucket** (MWAA, Composer, many VM setups). DevOps grants the DE's CI role write
access to one prefix only:

```bash
aws s3 sync dags/ s3://company-airflow-dags/team-data/ --delete
```

**3. Team image.** DE CI builds `FROM company/airflow-base:3.0.6`, copies `dags/` and
`requirements.txt`, pushes the image; it is rolled out. The only model where the DE fully owns
dependencies, at the cost of a slower deploy.

**4. One Airflow per team.** DevOps provides a template. Strongest isolation, most overhead.

**Rule of thumb:** DAG code change = sync files. Dependency change = new image.

## Are multiple DAG folders supported?

Yes, but be precise about what "folders" means.

| Approach | Works? | Notes |
|---|---|---|
| Subfolders inside the one `dags_folder` | Yes | Scanned **recursively**. `dags/team-a/`, `dags/team-b/` all work. |
| Several sources mounted as subfolders | Yes | e.g. mount repo A at `dags/team-a`, repo B at `dags/team-b`. Simple and works in any version. |
| Several *independent* `dags_folder` paths in config | **No** | `[core] dags_folder` is a single path, not a list. |
| **DAG bundles** (Airflow 3) | Yes | The proper multi-source feature. A list of bundles, each a local folder or a git repo. |
| Symlinks to other directories | Yes | Followed by the scanner; fine for local use. |

Details that matter with several sources:

- **`dag_id` must be unique across all sources.** Two files defining the same `dag_id` collide.
  Use a team prefix (`team_data__orders_daily`).
- **`.airflowignore`** (in any folder, regex or glob-style per config) excludes files and folders from parsing.
- Only files that contain the strings `dag` and `airflow` are parsed by default (safe mode).
- **Python imports:** `dags/` is on `sys.path`, so shared helper modules inside it can be imported.
  Put shared code in a package, not copy-pasted per team.

### DAG bundles (Airflow 3)

A bundle is a source of DAG files plus versioning. They are set in the `dag-processor` config:

```
AIRFLOW__DAG_PROCESSOR__DAG_BUNDLE_CONFIG_LIST='[
  {"name": "dags-folder",
   "classpath": "airflow.dag_processing.bundles.local.LocalDagBundle",
   "kwargs": {}},
  {"name": "team-data",
   "classpath": "airflow.providers.git.bundles.git.GitDagBundle",
   "kwargs": {"tracking_ref": "main", "git_conn_id": "team_data_git",
              "subdir": "dags", "refresh_interval": 60}}
]'
```

Each bundle is parsed separately, and the UI shows which bundle a DAG came from. `GitDagBundle`
also keeps versions, so a running DAG run uses the code version it started with.

> Not tested in this lab. I wrote this from the Airflow 3 documentation without being able to
> start Docker. Check the exact config key, class path and provider version against the docs for
> the version you run before relying on it.

## Can this local setup read from Git?

Yes, two ways.

### A. Clone the repo and mount it (simplest, works today)

The compose file mounts `./dags` into the containers. Clone the DE repo anywhere and mount its
`dags/` folder as an extra volume, as a subfolder:

```yaml
    volumes:
      - ./dags:/opt/airflow/dags
      - ../data-pipelines/dags:/opt/airflow/dags/team-data   # the DE's repo
```

`git pull` in that repo updates what Airflow sees. Nothing in Airflow needs to know about Git.
This mimics what git-sync does in production.

### B. Let Airflow fetch from Git itself (GitDagBundle)

Use the bundle config above. Needs:

1. The Git provider installed (`apache-airflow-providers-git`). For this lab, set
   `_PIP_ADDITIONAL_REQUIREMENTS` or build a small image on top of `apache/airflow:3.0.6`.
2. The `git` binary available in the image.
3. A Connection of type Git (`team_data_git`) with the repo URL, plus a token or SSH key for
   private repos. Public repos need no credentials.
4. Network access from the containers to the Git host.

Trade-off: A is simpler and good for learning. B is closer to a real deployment, and it handles
versioning, but needs the provider, a connection and credentials.

## Things to agree on with DevOps up front

- Folder layout, `dag_id` naming (team prefix), tags and `owner`.
- Which packages are in the image, and how to request new ones.
- Secrets: reference Connections/Variables by name; never commit credentials.
- Environments: `dev`/`stage`/`prod` branches or buckets, and who can promote.
- Access: which team can see or trigger which DAGs (Airflow roles and DAG-level access).
- Local dev: the DE runs the platform's compose file (same image version) with their own `dags/`.

## If Airflow is unavailable

- **Temporarily down:** git-sync, bucket and shared-folder deploys still succeed, because they never
  talk to Airflow. The new DAGs appear when it is back. Image-based deploys wait for the rollout.
  Scheduled runs missed during the outage are created on return only when `catchup=True`.
- **Does not exist yet:** there is nothing to deploy to. Provision it first (compose on a VM, Helm on
  Kubernetes, or a managed service like MWAA), then connect the delivery path.
- **CI steps that call the Airflow REST API** (unpause, trigger, set a Variable) do need Airflow
  reachable. Keep them separate and retryable from the file delivery.
