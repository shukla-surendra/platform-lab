# PostgreSQL: Security and Access Control

Part of [`README.md`](README.md)'s PostgreSQL section. The scope here is what a principal
engineer needs to reason correctly about — the actual security *boundaries* PostgreSQL
provides and what each one does and doesn't guarantee — not a hardening checklist.

## Roles: PostgreSQL has no separate concept of "users" and "groups"

Everywhere else this section says "user" or "role" interchangeably, because PostgreSQL
genuinely only has one underlying concept: the **role**. A role that can log in
(`CREATE ROLE app_user LOGIN PASSWORD '...';`) is what other systems would call a "user"; a
role without login capability, used purely to bundle a set of privileges, is what other
systems would call a "group." Roles can be **members of other roles**
(`GRANT reporting_team TO alice;`), and a role automatically inherits the privileges of every
role it's a member of by default — this membership graph *is* PostgreSQL's native RBAC
implementation; there's no separate permissions system layered on top of it.

Privileges themselves are granted **on objects**: `GRANT SELECT, INSERT ON orders TO
app_user;`, `GRANT USAGE ON SCHEMA reporting TO analyst_role;`, and so on — the standard
verbs (`SELECT`, `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `REFERENCES`, `EXECUTE` for
functions) map onto the SQL operations they sound like.

### Least privilege is a design decision, not a default

PostgreSQL's defaults are permissive in ways worth actively working against: a newly created
role that owns a schema has broad rights within it, and it's easy for an application's
database credential to end up with far more power than the application actually needs. The
concrete, repeatedly-relevant design decision: **an application's runtime database
credential should almost never be a superuser, and ideally shouldn't even own the schema it
operates in.** The reasoning is a blast-radius argument, not a paranoia argument — if an
application credential leaks (a logged connection string, a compromised dependency, an
SSRF-driven credential exfiltration), the actual damage is bounded by exactly what that role
can do:

- A leaked credential scoped to `SELECT`/`INSERT`/`UPDATE` on a specific, named set of
  tables is a contained incident — bad, but bounded.
  A leaked **superuser** credential is a total loss: full read/write on every object,
  the ability to create new roles, bypass row-level security, and read or modify
  server-level configuration.
- A separate, non-superuser **owner** role for running migrations (`CREATE
  TABLE`/`ALTER TABLE`/`CREATE INDEX`), distinct from the day-to-day application role that
  only ever runs DML, means a compromised application credential can't alter schema, drop
  tables, or grant itself new privileges — because it was never given the rights to do any
  of that in the first place.

## Row-Level Security (RLS): pushing a security boundary into the database itself

Ordinary `GRANT`s are granular down to the table and column — never the *row*. If a
multi-tenant application needs "tenant A can only ever see tenant A's rows in a shared
table," and the only enforcement mechanism is `GRANT`, that guarantee has to live entirely in
application code: every single query, in every code path, everywhere in the codebase, has to
remember to add `WHERE tenant_id = current_tenant()`. One missed `WHERE` clause in one
endpoint, one raw query written for a one-off admin script, one new engineer who doesn't know
the convention — and tenant isolation silently breaks, with no error, no warning, just a
cross-tenant data leak the first time it's exercised.

**Row-Level Security moves that guarantee from "a convention every engineer has to remember"
into a policy the database enforces on every single query against the table, unconditionally
— regardless of which application code path, ORM, or ad hoc script issued it.**

```sql
ALTER TABLE orders ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation ON orders
    USING (tenant_id = current_setting('app.current_tenant')::int);
```

Once enabled, every `SELECT`/`UPDATE`/`DELETE` against `orders` has this policy's condition
silently `AND`-ed into its `WHERE` clause by the database itself — a query that never
mentions `tenant_id` at all still only ever sees rows belonging to the current session's
tenant. The application sets `app.current_tenant` once per connection/request
(`SET app.current_tenant = '42';`); everything downstream of that is enforced by the
database, not trusted to application discipline.

Two subtleties worth knowing before treating RLS as a complete solution:

- **It has a real performance cost** — the policy's condition is injected into every query
  plan against that table, which the planner has to account for like any other predicate.
  For a hot table, this is a cost worth measuring, not assuming away.
- **Table owners and superusers bypass RLS by default**, which is often exactly the
  intended behavior (an admin/migration role needs to see everything), but is a common,
  easy-to-miss gap when RLS is being relied on as a genuine security boundary rather than an
  application-logic convenience — `ALTER TABLE orders FORCE ROW LEVEL SECURITY;` closes that
  gap by applying the policy to the table owner as well, at the cost of migrations and admin
  tooling now also needing to reason about tenant scoping explicitly.

## The connection-level gate: `pg_hba.conf`

Every `GRANT` and every RLS policy only matters *after* a connection has already been
allowed to authenticate — `pg_hba.conf` ("host-based authentication") is the layer that runs
before any of that, deciding, per combination of source IP range, target database, and
username, whether a connection attempt is even allowed, and if so, by which authentication
method. This is a genuinely separate security boundary from the privilege system, and a
common, real-world misconfiguration is having overly broad network access rules or a
`trust` authentication method (accept the connection with no password check at all) left
active on an interface that's actually reachable from outside a trusted network — a
misconfiguration that no amount of correct `GRANT`/RLS design downstream can compensate for,
because the connection was never supposed to be trusted enough to reach that layer at all.

## Encryption: two different boundaries, easy to conflate

- **In transit**: `sslmode` on the client connection controls this, and the specific value
  matters more than "SSL is on or off." `sslmode=require` encrypts the connection but does
  **not** verify the server's certificate against a trusted CA — a connection can still be
  transparently intercepted by a machine-in-the-middle presenting *any* certificate, and the
  client would accept it. `sslmode=verify-full` additionally verifies the certificate chain
  *and* that the certificate's hostname matches the server actually being connected to —
  this is the level that genuinely defends against interception, and it's the level that
  matters for any connection crossing a network boundary that isn't fully trusted (which,
  in practice, is most cloud deployments).
- **At rest**: encryption of the actual data files on disk is, in almost every real
  deployment (including RDS/Aurora), handled at the **storage layer** — EBS volume
  encryption, Aurora's storage-layer encryption — not by PostgreSQL itself. This is worth
  stating plainly because it's a common point of confusion: "the database is encrypted" is
  usually a fact about the disk it sits on, not a PostgreSQL feature being configured.
- **Column-level encryption (`pgcrypto`)** exists for a narrower, different problem than
  either of the above: protecting specific, sensitive fields even from someone with
  legitimate database access — because storage-layer and in-transit encryption both still
  leave plaintext fully visible to any role with `SELECT` on the table, including a
  superuser. Encrypting a specific column at the application layer (or via `pgcrypto`
  functions) so only application code holding the decryption key can read it in plaintext is
  the mechanism for that stricter requirement — genuinely sensitive fields (SSNs, payment
  details subject to PCI scope) are the real case this matters for, not general "defense in
  depth" on ordinary columns.

## Auditing: knowing *who* did *what*, not just *what* happened

[`README.md`](README.md#diagnosing-a-slow-query-explain-analyze-and-statistics)'s
`pg_stat_statements` is not an audit log, even though it's sometimes mistaken for one — it
records aggregated statistics per normalized query *shape* (with literal values stripped
out), with no per-execution record of which specific user or session ran it, or with what
actual parameter values. For genuine audit requirements (who accessed or modified this
specific row, at this specific time — the kind of question a SOC2 or HIPAA-adjacent
compliance requirement actually asks), the built-in, coarser tools are `log_statement` and
`log_connections` (logging every statement and every connection at the server-log level,
with real but non-trivial log-volume cost), and the purpose-built tool is the **`pgAudit`**
extension, which produces structured, session-and-object-level audit logging specifically
designed to satisfy compliance-style audit requirements rather than general debugging —
worth reaching for directly rather than trying to reconstruct equivalent information from
general-purpose logs after the fact.
