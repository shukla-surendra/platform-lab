# 07 — Conditionals and Control Flow

## Conditionals

```bash
if [ "$1" = "prod" ]; then
    echo "deploying to production"
elif [ "$1" = "staging" ]; then
    echo "deploying to staging"
else
    echo "unknown environment"
fi
```

`[ ... ]` is actually a command (historically the `test` program) — that's
why the spaces around the brackets are mandatory, and why it needs `-eq`
for numeric equality instead of `==`. `[[ ... ]]` is bash's improved
version: safer with unquoted variables, supports `&&`/`||`/`=~` (regex)
inside it directly. **Prefer `[[ ]]` in bash scripts**; use `[ ]` only if
the script must run under plain `/bin/sh` (POSIX shell, not bash).

| Test | `[ ]` / `[[ ]]` operator |
|---|---|
| string equal | `=` (or `==` inside `[[ ]]`) |
| string not equal | `!=` |
| string empty | `-z "$s"` |
| string non-empty | `-n "$s"` |
| numbers equal | `-eq` |
| number greater than | `-gt` |
| number less than | `-lt` |
| file exists | `-e "$f"` |
| is a regular file | `-f "$f"` |
| is a directory | `-d "$f"` |
| is readable/writable/executable | `-r` / `-w` / `-x` |
| AND / OR | `&&` / `\|\|` |

## Parameter expansion defaults — handling missing input gracefully

Beyond plain `$var`, bash has a small family of `${var...}` forms built
specifically for "what if this variable wasn't set" — used constantly in
scripts that read config from the environment:

```bash
echo "${name:-anonymous}"     # use "anonymous" if $name is unset OR empty; $name itself is unchanged
echo "${name:=anonymous}"     # same, but also ASSIGNS "anonymous" to $name if it was unset/empty
echo "${config:?missing config path}"   # if unset/empty, print that message to stderr and exit the script
echo "${flag:+enabled}"       # print "enabled" if $flag IS set (non-empty); otherwise print nothing
```

Read them as a sentence: `:-` = "or, if that's not there, use this
instead"; `:=` = "...and remember it for next time"; `:?` = "...or stop,
this is required"; `:+` = "only if it's actually set." This is also
exactly the pattern used by the Docker entrypoint referenced in
[12 — Worked Examples and Real-World References](12-worked-examples-and-real-world.md)
(`${OPS_SERVER_PORT:-8001}`).

## `case` — cleaner than a chain of `if`/`elif` for matching one value

```bash
case "$1" in
    start)
        echo "starting"
        ;;
    stop|halt)                 # `|` matches either pattern
        echo "stopping"
        ;;
    restart)
        echo "restarting"
        ;;
    *)                          # default case, like `else`
        echo "usage: $0 {start|stop|restart}" >&2
        exit 1
        ;;
esac
```

Each branch ends with `;;`. Patterns support globs (`*.log)`, not just
literal words, which is what makes `case` a good fit for dispatching on a
subcommand or file extension.

## Loops

```bash
# for: iterate a list
for f in *.log; do
    echo "found: $f"
done

# for: iterate a range
for i in {1..5}; do
    echo "iteration $i"
done

# while: loop while a condition holds
count=0
while [ "$count" -lt 3 ]; do
    echo "count=$count"
    count=$((count + 1))
done

# while read: the correct way to process a file line by line
while IFS= read -r line; do
    echo "line: $line"
done < input.txt
```

(`IFS=` and `-r` in that last pattern matter: without them, `read`
trims leading/trailing whitespace and mangles backslashes. This exact
snippet is the standard, safe way to read a file line by line in bash —
worth memorizing as a unit.)

`break` exits a loop early; `continue` skips to the next iteration.

**Run it:** [`examples/07_deploy.sh`](examples/07_deploy.sh) dispatches on
`dev`/`staging`/`prod` with `case` (anything else prints usage and exits
1), then runs a `for` loop of fake "deploy step" messages inside the
matched branch.

```bash
./examples/07_deploy.sh staging
./examples/07_deploy.sh bogus     # exercises the default case
```

---
**Previous:** [06 — Scripting Basics](06-scripting-basics.md) · **Next:** [08 — Functions and Arguments](08-functions-and-arguments.md)
