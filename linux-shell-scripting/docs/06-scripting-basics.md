# 06 — Scripting Basics: Shebang, Variables, Quoting, Arithmetic

This is where "typing commands" becomes "writing a script."

## The shebang and making it runnable

Every script starts with a line telling the OS which interpreter to run it
with:

```bash
#!/usr/bin/env bash
```

`#!/usr/bin/env bash` finds `bash` on `$PATH` (portable across machines);
`#!/bin/bash` hardcodes the path (only use it if you're sure that's where
bash lives). Then make the file executable and run it:

```bash
chmod +x myscript.sh
./myscript.sh          # run it directly
# or, without the executable bit / shebang:
bash myscript.sh
```

## Variables

```bash
name="Surendra"          # NO spaces around =. `name = "x"` is a syntax error — bash reads it as running a command called `name`.
echo "$name"              # read it: $name or ${name}
echo "${name}_suffix"     # {} needed here so bash doesn't try to read a variable called name_suffix
```

## Quoting rules — the single most important habit in shell scripting

```bash
value="two words"
echo $value       # WRONG for most purposes: expands to two separate arguments, "two" and "words"
echo "$value"      # RIGHT: stays one string, "two words"
echo '$value'      # literal: prints the text $value, no expansion at all
```

Rule of thumb: **always double-quote a variable reference** (`"$var"`)
unless you specifically want word-splitting/globbing to happen. This one
habit prevents the majority of real-world shell script bugs.

## Command substitution — run a command, capture its stdout as a string

```bash
today=$(date +%F)
echo "Today is $today"
count=$(ls | wc -l)
```

(`$(...)` is preferred over the older backtick syntax `` `...` `` — it
nests cleanly and is easier to read.)

## Arithmetic

```bash
x=5
y=$((x + 3))          # arithmetic context: $(( ... ))
echo $((x * 2))
```

## Special variables bash gives you for free

| Variable | Meaning |
|---|---|
| `$0` | the script's own name |
| `$1`, `$2`, ... | positional arguments passed to the script |
| `$@` | all arguments, as separate words |
| `$#` | number of arguments |
| `$?` | exit code of the *last* command run |
| `$$` | PID of the current shell |

```bash
#!/usr/bin/env bash
echo "Script: $0"
echo "First arg: $1"
echo "All args: $@"
echo "Arg count: $#"
```

**Run it:** [`examples/06_hello.sh`](examples/06_hello.sh) uses everything
above — a variable, a double-quoted echo, command substitution for
today's date, and `$1`/`$#`.

```bash
./examples/06_hello.sh Surendra
```

---
**Previous:** [05 — Terminal Productivity](05-terminal-productivity.md) · **Next:** [07 — Conditionals and Control Flow](07-conditionals-and-control-flow.md)
