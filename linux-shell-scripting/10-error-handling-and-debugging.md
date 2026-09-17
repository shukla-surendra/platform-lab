# 10 — Error Handling, Gotchas, and Debugging

The difference between a toy script and a production one.

## Exit codes and error handling

By default, bash **keeps running after a command fails**, which is almost
never what you want in automation. Three flags fix this, and are the
single highest-leverage thing to add to every script you write:

```bash
#!/usr/bin/env bash
set -euo pipefail
```

- `-e` — exit immediately if any command fails (nonzero exit code),
  instead of plowing ahead with a half-finished state.
- `-u` — treat referencing an unset variable as an error, instead of
  silently substituting an empty string (catches typos like `$FILE_PTH`).
- `-o pipefail` — in a pipeline (`a | b | c`), fail if *any* stage fails,
  not just the last one. Without this, `false | true` reports success,
  because bash only looks at the exit code of the last command in the
  pipe by default.

`trap` lets you run cleanup code no matter how the script exits:

```bash
cleanup() {
    rm -f "$tmpfile"
}
trap cleanup EXIT
```

`EXIT` fires on *any* exit — normal completion, `exit N`, or an error
under `set -e`. Trap specific signals too, when a script needs different
behavior for "someone hit Ctrl+C" versus "finished normally":

```bash
trap 'echo "interrupted, cleaning up"; cleanup; exit 130' INT   # Ctrl+C (SIGINT)
trap 'echo "terminated"; cleanup; exit 143' TERM                 # kill's default signal (SIGTERM)
```

(130 and 143 follow the shell convention `128 + signal number` — `SIGINT`
is signal 2, `SIGTERM` is signal 15 — so a caller inspecting `$?` can
tell *which* signal ended the script, not just that it did.)

Exit the script explicitly (and give the caller — a human, cron, or CI —
something to check) with `exit N`:

```bash
if [ ! -f "$config" ]; then
    echo "ERROR: config file not found: $config" >&2   # errors go to stderr, not stdout
    exit 1
fi
```

## Common gotchas (production reality / failure modes)

- **Unquoted variables + `rm` is the classic disaster.** If `$dir` is
  empty and you run `rm -rf $dir/*` unquoted, word-splitting can turn
  that into `rm -rf /*` in the worst case (empty variable, then a
  stray/misplaced flag). Always quote: `rm -rf "${dir:?}"/*` — the `:?`
  additionally makes bash *error out* if the variable is unset or empty,
  instead of silently proceeding.
- **`[ ]` vs `[[ ]]`**: `[ $var = foo ]` breaks (syntax error) if `$var`
  is empty or contains spaces and isn't quoted; `[[ $var = foo ]]`
  tolerates it. Still quote inside `[[ ]]` as a habit — it costs nothing
  and keeps behavior predictable.
- **`sh` is not `bash`.** `#!/bin/sh` on many systems (Debian/Ubuntu, and
  entrypoint scripts in many Docker images) links to `dash`, a stricter
  POSIX shell — arrays, `[[ ]]`, and `local` either behave differently or
  don't exist. If a script needs bash-only features, its shebang must say
  so explicitly (`#!/usr/bin/env bash`), or it will fail (or silently
  behave differently) on a system where `/bin/sh` isn't bash.
- **No floating-point math in bash.** `$((1/3))` is `0` (integer
  division) — bash arithmetic is integers only. Use `bc` or `awk` for
  real decimal math: `echo "scale=2; 1/3" | bc`.
- **Silent failures without `set -e`.** A script that doesn't set `-e`
  will happily run step 5 after step 3 failed, often corrupting state
  in a way that's harder to debug than a clean early exit would have
  been.
- **CRLF line endings** (a script edited on Windows) break the shebang
  line with a cryptic `bad interpreter: /bin/bash^M: no such file or
  directory`. Fix with `dos2unix script.sh` or `sed -i 's/\r$//'
  script.sh`.
- **Globs that match nothing expand to themselves.** `for f in *.log; do`
  in an empty directory loops once with the literal string `*.log`,
  not zero times. Guard with `shopt -s nullglob` if that matters to the
  script's logic.

## Debugging

```bash
bash -x script.sh          # print every command as it's executed, with expanded variables, before running it
set -x                      # turn the same tracing on mid-script
set +x                      # turn it back off
```

`shellcheck script.sh` (a static analyzer, install via package manager) is
the fastest way to catch quoting bugs, unused variables, and portability
mistakes before running a script at all — worth running on any script
before it goes into cron or CI.

**Run it:** [`examples/10_error_handling_demo.sh`](examples/10_error_handling_demo.sh)
runs the unset-variable and unquoted-`rm` disasters side by side with
their guarded, safe versions, and shows `pipefail` changing a pipeline's
exit code — all without touching a single real file.

```bash
./examples/10_error_handling_demo.sh
```

---
**Previous:** [09 — Arrays, Strings, and I/O](09-arrays-strings-and-io.md) · **Next:** [11 — JSON with jq and Cron Scheduling](11-json-and-cron.md)
