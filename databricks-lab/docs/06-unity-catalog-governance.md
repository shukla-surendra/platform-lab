# 6. Unity Catalog, governance and security

## What Unity Catalog (UC) is

The centralised governance layer for data and AI assets across workspaces: one place for
**access control, auditing, lineage, discovery, and data sharing**.

## Object model

```
account
 └─ metastore (one per cloud region; attached to many workspaces)
     ├─ catalog
     │   └─ schema
     │       ├─ table (managed / external), view, materialized view, streaming table
     │       ├─ volume (managed / external): files
     │       ├─ function
     │       └─ registered model
     ├─ storage credential   ← cloud IAM role/identity UC uses to access storage
     ├─ external location    ← a storage path + a storage credential
     ├─ connection           ← to an external database (Lakehouse Federation)
     └─ share / recipient    ← Delta Sharing
```

Address: `catalog.schema.table`. Typical layout: a catalog per environment (`dev`, `prod`) or per
domain (`finance`), schemas per layer or subject (`bronze`, `silver`, `gold`).

## Identity

- **Account-level** users, groups and service principals (not per workspace), synced from your IdP via SCIM.
- **Grant to groups**, not individuals.
- **Service principals** run production jobs. No human credentials in jobs.
- Workspace-to-metastore assignment decides which workspaces see which data; **workspace bindings** can restrict a catalog to specific workspaces.

## Privileges

```sql
GRANT USE CATALOG ON CATALOG prod TO `analysts`;
GRANT USE SCHEMA  ON SCHEMA prod.sales TO `analysts`;
GRANT SELECT      ON TABLE prod.sales.orders TO `analysts`;
GRANT SELECT ON SCHEMA prod.sales TO `analysts`;      -- inherits to current and future tables
```

- To read a table you need `SELECT` on it **and** `USE SCHEMA` on its schema **and** `USE CATALOG` on its catalog. Missing the "USE" privileges is the classic "table not found / permission denied" confusion.
- Privileges **inherit downward**: grant on a schema covers all its tables.
- Other privileges: `MODIFY`, `CREATE TABLE`, `CREATE SCHEMA`, `EXECUTE`, `READ VOLUME`, `WRITE VOLUME`, `MANAGE`, `ALL PRIVILEGES`.
- Ownership: the owner can grant on the object. Make owners groups, not people.

## Fine-grained access control

| Feature | What it does |
|---|---|
| **Dynamic views** | A view using `is_account_group_member('hr')` / `current_user()` to filter rows or mask columns |
| **Row filters** | A function attached to a table; returns whether a row is visible to the caller |
| **Column masks** | A function attached to a column that returns a masked value per caller |
| **ABAC / tags** | Tags (`pii=true`) on assets plus policies that apply based on tags (check current availability) |

```sql
CREATE FUNCTION mask_email(email STRING) RETURNS STRING
  RETURN CASE WHEN is_account_group_member('pii_readers') THEN email ELSE '***' END;
ALTER TABLE prod.crm.customers ALTER COLUMN email SET MASK mask_email;
```

Row filters/masks run on every query regardless of how it's reached (SQL, notebook, BI), which is
better than copying a "masked version" of the table.

## Storage access: credentials, external locations, volumes

```
cloud IAM role ──> STORAGE CREDENTIAL ──> EXTERNAL LOCATION (s3://bucket/path) ──> external tables / volumes
```

- UC accesses storage with the credential; **users never hold storage keys**. Direct path access
  is checked against external location grants.
- **Managed storage:** metastore, catalog or schema can set a managed location where managed tables live.
- **Volumes** govern non-tabular files (CSV drops, images, model artefacts): `/Volumes/<catalog>/<schema>/<volume>/path`.

## Lineage, audit, discovery

- **Lineage** (table and column level) is captured automatically from queries and jobs, including notebooks, jobs, pipelines and dashboards. Used for impact analysis ("what breaks if I drop this column?") and compliance.
- **Audit logs** and **system tables** (`system.access.audit`, `system.billing.usage`, `system.compute.*`, `system.lakeflow.*`) are queryable in SQL.
- **Discovery:** search, comments, tags, certification, data quality monitoring.

## Delta Sharing

Open protocol for sharing live data with other orgs or platforms without copying.
- Provider creates a **share**, adds tables, and creates a **recipient**.
- Recipients can be on Databricks (UC-to-UC) or anywhere (open sharing with a credential file).
- Data stays in the provider's storage; access is read-only and revocable.

## Lakehouse Federation

Register an external database (Postgres, MySQL, Snowflake, SQL Server, ...) as a UC **connection** and a
foreign catalog. Query it in place with UC permissions. Good for exploration and migration;
heavy joins still run against the remote system, so ingest it if you need performance.

## Security checklist

| Area | Practice |
|---|---|
| Network | Private connectivity (PrivateLink / Private Endpoints), no public IPs on clusters, IP access lists |
| Identity | SSO + SCIM, groups, MFA through IdP, service principals for automation |
| Data access | UC grants on groups, least privilege, row/column controls for PII |
| Storage | Customer-managed keys where required, no shared storage keys in code |
| Secrets | Secret scopes backed by a vault, rotate, never in notebooks |
| Compute | Cluster policies (limit sizes, enforce tags/auto-termination), shared access mode for multi-user |
| Audit | System tables and audit log delivery into your SIEM |
| Code | Git-based deployment, reviews, no personal-access-token sprawl |

## Compute access modes (matter for security)

| Mode | Use |
|---|---|
| **Standard (shared)** | Multiple users, UC enforcement incl. row/column rules, language restrictions |
| **Dedicated (single user/group)** | One principal; full feature access, UC-enforced as that principal |
| Legacy no-isolation | Avoid: no UC enforcement |

## Common gotchas

| Symptom | Cause |
|---|---|
| `PERMISSION_DENIED` on a table you were granted | Missing `USE CATALOG` or `USE SCHEMA` |
| Can't read a path | Not covered by an external location, or no `READ FILES` grant |
| Table disappears after `DROP` | Managed table: data is deleted (recoverable with `UNDROP` for a limited time) |
| Hive metastore tables still used | Legacy `hive_metastore` isn't governed by UC; migrate (`SYNC`, `CREATE TABLE CLONE`, upgrade wizard) |
| Dynamic view leaks data | A user with direct access to the underlying table bypasses the view |
| Job works for you, fails as service principal | Principal lacks the grants you personally have |
