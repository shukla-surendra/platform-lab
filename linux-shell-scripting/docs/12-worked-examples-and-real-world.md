# 12 — Worked Examples and Real-World References

The patterns from every previous topic — shebang, `set -euo pipefail`,
argument parsing, functions, a loop, explicit exit codes, errors to
stderr — are exactly what a real script looks like. This topic ties them
together into two complete, runnable scripts, then points at real
non-teaching scripts in this repo that use the same primitives.

## Worked example 1 — housekeeping script

[`examples/backup_and_alert.sh`](examples/backup_and_alert.sh) archives a
directory, checks the result, and reports success/failure with a proper
exit code — the shape of most "housekeeping" scripts you'll actually
write (log rotation, backups, health checks).

```bash
./examples/backup_and_alert.sh ~/practice ~/practice_backups
```

## Worked example 2 — fan-out health check

[`examples/parallel_health_check.sh`](examples/parallel_health_check.sh)
puts the trickier tools from earlier topics into one script: `getopts`
for `-f`/`-t`/`-p` flags
([08 — Functions and Arguments](08-functions-and-arguments.md)), process
substitution (`< <(...)`) to read a hosts file without losing loop state
([09 — Arrays, Strings, and I/O](09-arrays-strings-and-io.md)),
backgrounded jobs capped with `wait -n` for bounded parallelism, and
`trap` on `EXIT` *and* `INT`/`TERM`
([10 — Error Handling and Debugging](10-error-handling-and-debugging.md))
so Ctrl+C mid-run still cleans up its temp directory, ending with `[
"$fail_count" -eq 0 ]` as the script's own exit code — the shape of a
fan-out check script (health checks across N hosts, a parallel deploy
verification, anything "do this same thing to a list of targets and tell
me what failed"). Run it against `examples/sample_hosts.txt` to see it
live:

```bash
./examples/parallel_health_check.sh -f examples/sample_hosts.txt -t 5 -p 4
```

## Relationship to other tools/scripts in this repo

This repo already leans on the exact patterns above in real files, which
are worth reading directly once the syntax in earlier topics makes sense:

- [`applied_genai/agents/aiops_mlops_agent/docker/entrypoint.sh`](../applied_genai/agents/aiops_mlops_agent/docker/entrypoint.sh) —
  a minimal Docker entrypoint: `set -e`, a default-value pattern
  (`${OPS_SERVER_PORT:-8001}` — use the env var if set, else fall back to
  `8001`), and `exec "$@"` at the end, which replaces the shell process
  with whatever command Docker was told to run (instead of running it as
  a child process) so signals like `SIGTERM` reach it directly.
- [`public_docker_images/rust-api/scripts/verify.sh`](../public_docker_images/rust-api/scripts/verify.sh) —
  a full acceptance-test script: `set -uo pipefail`, small reusable
  functions (`ok()`, `bad()`, `assert()`), heavy use of command
  substitution to capture `curl` responses, and an explicit `exit 0` /
  `exit 1` at the end based on an accumulated pass/fail count — the same
  "functions + exit code as the final verdict" shape as worked example 1
  above, just applied to HTTP checks instead of file backups.

Both are good next reading once the syntax topics feel solid: same
primitives (redirection, `set` flags, functions, `$(...)`, quoting),
applied to a real problem instead of a teaching example.

## Capstone exercise

Write a script from scratch, using nothing but these 12 topics as
reference, that:

1. Takes a directory path as `-d` and a file-age-in-days as `-a`
   (`getopts`).
2. Finds files older than that age (`find ... -mtime`).
3. For each, logs its path + size to a report file (function + loop +
   `du`/`stat`).
4. Exits nonzero if it found zero matching files, with a clear stderr
   message.
5. Uses `set -euo pipefail`, a `trap cleanup EXIT`, and quotes every
   variable.

If you can write that without flipping back to earlier topics more than
once or twice, the material has actually stuck.

Try it yourself first, then check your work against
[`examples/12_capstone_reference.sh`](examples/12_capstone_reference.sh):

```bash
./examples/12_capstone_reference.sh -d /path/to/some/dir -a 30
```

---
**Previous:** [11 — JSON with jq and Cron Scheduling](11-json-and-cron.md) · **Next:** [13 — Sockets: Talking Between Two Machines](13-sockets-between-machines.md) · **Back to:** [README](README.md)
