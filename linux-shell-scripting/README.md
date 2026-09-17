# Linux & Shell Scripting

**Category:** operating system / command-line automation (Bash — the interface between you and the Linux kernel)

A topic-by-topic tutorial, beginner to advanced. Each numbered doc is
self-contained with its own explanation and runnable examples, and links
to the previous/next topic so you can go straight through or jump to
whatever you need.

## Topics

1. [Introduction and Mental Model](01-introduction-and-mental-model.md) — what a shell/terminal/script actually is, and the two ideas (processes + streams) everything else builds on.
2. [Filesystem and Permissions](02-filesystem-and-permissions.md) — the directory tree, `ls -la` anatomy, `chmod`/`chown`.
3. [Files and Text Processing](03-files-and-text-processing.md) — `find`, `cat`/`less`/`tail -f`, the `grep`/`sed`/`awk`/`sort`/`uniq` pipeline toolkit, `xargs`.
4. [Processes, Redirection, and Networking](04-processes-redirection-networking.md) — `ps`/`kill`/background jobs, the redirection cheat sheet, `curl`/`scp`/`tar`/`rsync`-adjacent basics.
5. [Terminal Productivity](05-terminal-productivity.md) — history/aliases, `pushd`/`popd`, `rsync`, symlinks, `tmux`.
6. [Scripting Basics](06-scripting-basics.md) — shebang, variables, quoting, command substitution, arithmetic, special variables.
7. [Conditionals and Control Flow](07-conditionals-and-control-flow.md) — `if`/`[[ ]]`, parameter expansion defaults, `case`, `for`/`while` loops.
8. [Functions and Arguments](08-functions-and-arguments.md) — functions, `local`, and `getopts` flag parsing.
9. [Arrays, Strings, and I/O](09-arrays-strings-and-io.md) — indexed/associative arrays, string manipulation, heredocs, process substitution, backgrounding/`wait`.
10. [Error Handling and Debugging](10-error-handling-and-debugging.md) — `set -euo pipefail`, `trap`, common gotchas, `bash -x`/`shellcheck`.
11. [JSON with `jq` and Cron Scheduling](11-json-and-cron.md) — parsing JSON in scripts, crontab syntax and habits.
12. [Worked Examples and Real-World References](12-worked-examples-and-real-world.md) — two full runnable scripts, plus real scripts elsewhere in this repo using the same patterns, and a capstone exercise.

## Examples

Every topic above has a runnable script under `examples/` (linked inline
from that topic's doc), numbered to match: `01_pipes_and_streams.sh`
through `12_capstone_reference.sh`. Two additional complete scripts,
referenced from topic 12, show the same patterns applied to real
housekeeping/fan-out problems:

- [`examples/backup_and_alert.sh`](examples/backup_and_alert.sh)
- [`examples/parallel_health_check.sh`](examples/parallel_health_check.sh) (run with `examples/sample_hosts.txt`)

## How to use this

Read topics in order the first time through — each one assumes the
previous ones. After that, use the numbered list above as reference and
jump straight to whatever topic you need.
