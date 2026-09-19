# 08 — Functions and Argument Parsing

## Functions

```bash
greet() {
    local name="$1"          # `local` scopes it to the function — omit it and it leaks into the whole script
    echo "Hello, $name"
}

greet "world"                # call it like any command
result=$(greet "world")      # capture its stdout, same as command substitution on any other command
```

A function's "return value" in the shell sense is its **exit code**
(0-255, set via `return N`), not a value like in Python. If you want to
hand back *data*, print it to stdout and capture it with `$(...)` as
above — those are two independent channels and scripts commonly use both
(exit code for "did it work," stdout for "here's the answer").

## `getopts` — real `-x value` / `--flag` style argument parsing

`$1`, `$2` (positional args, from
[06 — Scripting Basics](06-scripting-basics.md)) work for a script with
one or two fixed arguments. The moment a script needs *flags* — `-f
config.yml -v --dry-run`, order-independent — reading `$1`/`$2` by hand
gets unwieldy fast. `getopts` is bash's built-in loop for this:

```bash
#!/usr/bin/env bash
verbose=false
config=""

while getopts "vc:h" opt; do
    case "$opt" in
        v) verbose=true ;;
        c) config="$OPTARG" ;;      # the `:` after `c` in "vc:h" means -c REQUIRES a value
        h) echo "Usage: $0 [-v] [-c config] "; exit 0 ;;
        *) echo "Unknown option" >&2; exit 1 ;;
    esac
done
shift $((OPTIND - 1))   # remove parsed options from $@, leaving only remaining positional args

echo "verbose=$verbose config=$config remaining_args=$*"
```

Read the option string `"vc:h"` character by character: a bare letter is
a flag with no value (`-v`); a letter followed by `:` requires a value,
captured into `$OPTARG` (`-c myfile.yml`). This is the standard pattern
any script with more than one optional argument should use — the
`case`/`getopts` combination shows up in almost every real CLI tool
written in bash.

**Run it:** [`examples/08_greet.sh`](examples/08_greet.sh) takes `-n name`
(via `getopts`) and `-c count` (default `1`), and prints `"Hello,
<name>"` `<count>` times using a `for` loop calling a `greet` function.

```bash
./examples/08_greet.sh -n Surendra -c 3
```

---
**Previous:** [07 — Conditionals and Control Flow](07-conditionals-and-control-flow.md) · **Next:** [09 — Arrays, Strings, and I/O](09-arrays-strings-and-io.md)
