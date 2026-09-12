# Linux & Shell Scripting

**Category:** operating system / command-line automation (Bash — the interface between you and the Linux kernel)

## What it is

The **shell** is a program whose only job is: read a line of text you type,
figure out what program you mean, run it, and show you the result. The
**terminal** is just a window that displays this conversation. A **shell
script** is that same conversation, pre-written into a file, so the
computer can replay it instead of you typing it live. That's the entire
concept — everything below is just vocabulary and syntax built on top of
"type a line, a program runs, something comes back."

## The problem it solves, and why not just click around

Doing things by hand (clicking in a file browser, running commands one at
a time) breaks down for three concrete reasons:

- **It doesn't repeat reliably.** If a task takes 15 manual steps, step 11
  gets fat-fingered eventually. A script runs the same 15 steps identically
  every time.
- **It can't run unattended.** A cron job, a CI pipeline, a Docker
  container starting up — none of these have a human present to click
  anything. They need something that runs on its own from a file.
- **It isn't shareable or auditable.** "I ran some commands" is not
  reproducible by a teammate or reviewable in a PR. A `.sh` file is both.

Shell scripting is the layer that turns "a sequence of manual steps" into
"a file that does the steps."

## First-principles mental model (the only two ideas you actually need)

Everything else in this doc is vocabulary layered on two ideas:

1. **A command is a process, and every process has three pipes and one
   number.** When you run `ls`, the shell starts a new process. That
   process has three streams already connected for it — **stdin** (input,
   stream 0), **stdout** (normal output, stream 1), **stderr** (error
   output, stream 2) — and when it finishes, it reports back exactly one
   number, its **exit code**: `0` means "succeeded," anything else means
   "failed," and the specific nonzero value is up to the program to define.
   That's it. No process has more state than this to reason about at the
   shell level.

2. **You can rewire those three streams.** By default stdout and stderr
   both print to your terminal, and stdin reads your keyboard. Two
   mechanisms let you rewire them: **redirection** (send a stream to a
   file instead) and **piping** (send one process's stdout into the next
   process's stdin). Nearly every "Linux trick" you'll ever see is one of
   these two mechanisms applied to a well-chosen pair of commands.

Once these two ideas are solid, `grep error app.log | wc -l` reads itself:
run `grep`, its stdout becomes the next command's stdin, count lines.
Nothing about it needs memorizing — it falls out of the model.

## Filesystem and permissions crash course (needed before anything else)

- **Everything lives under one tree**, rooted at `/`. There's no `C:\` —
  a USB drive, a network share, all of it gets *mounted* somewhere under
  `/`. `~` is shorthand for your home directory (e.g. `/home/you`); `.` is
  "here"; `..` is "one level up."
- **Paths are absolute or relative.** `/etc/hosts` is absolute (starts
  from `/`, unambiguous from anywhere). `../config.yml` is relative
  (depends on your current directory — see `pwd`).
- **`ls -la` anatomy** — run it and you'll see rows like:

  ```
  -rwxr-xr-x  1 alice  staff   220 Aug 10 09:14 deploy.sh
  ```

  Left to right: file type + permissions (`-` = regular file, `d` would be
  a directory; then three permission triplets — **owner / group /
  other**, each `r`/`w`/`x` = read/write/execute), link count, owner,
  group, size in bytes, modified date, name. `x` on a directory means
  "can enter it / list contents via a path," not "can execute it."
- **`chmod`** changes permissions. `chmod +x deploy.sh` adds execute
  permission for everyone; `chmod 644 file` sets owner=read+write,
  group=read, other=read using the octal shorthand (`r=4, w=2, x=1`,
  summed per triplet — `755` = `rwxr-xr-x`, `644` = `rw-r--r--`).
- **`chown user:group file`** changes who owns it (usually needs `sudo`).
- **"Everything is a file" is a real design principle**, not a slogan —
  devices (`/dev/sda`), running processes (`/proc/1234/`), and kernel
  settings (`/proc/sys/...`) are all exposed as things you can `cat`,
  `read`, or `write` with the exact same tools you use on a text file.
  That's why the same small toolkit (redirection, `cat`, `grep`) keeps
  working in places that don't look like "files" at first.

## Navigating and manipulating files — the everyday toolkit

| Command | What it does | Example |
|---|---|---|
| `pwd` | print current directory | `pwd` |
| `cd` | change directory | `cd /var/log` |
| `ls -la` | list, including hidden/detailed | `ls -la ~/project` |
| `mkdir -p` | make a directory (and parents) | `mkdir -p a/b/c` |
| `touch` | create an empty file / update its timestamp | `touch notes.txt` |
| `cp -r` | copy (recursive for directories) | `cp -r src/ backup/` |
| `mv` | move or rename | `mv old.txt new.txt` |
| `rm -rf` | remove, recursive+force | `rm -rf build/` — **dangerous, see gotchas below** |
| `find` | search the filesystem by criteria | see below |

`find` is worth its own line because it's the general-purpose search tool,
not just "find by name":

```bash
find . -name "*.log"                    # by name (glob pattern)
find . -type f -mtime +7                # regular files older than 7 days
find . -type d -empty                   # empty directories
find . -name "*.tmp" -delete            # find AND delete in one line
find . -name "*.py" -exec grep -l "TODO" {} \;   # run a command per match
```

**Viewing text:**

```bash
cat file.txt        # dump the whole file
less file.txt        # page through it (q to quit, / to search)
head -n 20 file.txt   # first 20 lines
tail -n 20 file.txt   # last 20 lines
tail -f app.log       # "follow" — keep printing new lines as they're written; the #1 way to watch a live log
```

**The text-processing pipeline tools** — these are what make the shell a
real data-processing environment, not just a file browser:

| Tool | Purpose |
|---|---|
| `grep` | filter lines matching a pattern |
| `sed` | find-and-replace / edit a stream of text |
| `awk` | pull out and process columns/fields |
| `cut` | extract a column by delimiter/position |
| `sort` | sort lines |
| `uniq` | collapse adjacent duplicate lines (needs sorted input) |
| `wc` | count lines/words/bytes |
| `tr` | translate/delete characters |

Chained together, one line answers real questions:

```bash
# "Which 5 IPs hit this server the most, from an access log?"
awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -5

# "How many ERROR lines happened today?"
grep "$(date +%F)" app.log | grep -c ERROR

# "Replace all 'staging' with 'production' in every .yml file, in place"
sed -i 's/staging/production/g' *.yml
```

Read the first one right-to-left in your head as you build it: get column
1 (the IP) from every line → sort so duplicates are adjacent → collapse
duplicates and prefix each with a count → sort numerically, descending →
keep the top 5. That's the whole skill of "Linux tricks": knowing five
small tools well enough to chain them, rather than knowing one big tool
that does everything.

**Turning output into arguments — `xargs`:** many commands (like `rm`)
take arguments, not stdin. `xargs` bridges the gap by taking piped-in
lines and turning each into an argument to another command:

```bash
find . -name "*.tmp" | xargs rm       # delete every .tmp file found
echo "a b c" | xargs -n1 echo         # runs `echo a`, `echo b`, `echo c` separately
```

**Processes:**

```bash
ps aux              # every process on the system, with CPU/mem
ps aux | grep python  # filter to just python processes
top                  # live-updating process viewer (htop is the nicer version)
kill 1234            # send SIGTERM (please stop) to PID 1234
kill -9 1234         # send SIGKILL (stop now, no cleanup) — last resort
some_command &        # run in background, get your prompt back immediately
jobs                  # list background jobs in this shell
fg                    # bring the most recent background job to the foreground
nohup long_task.sh &   # keep running even after you log out / close the terminal
```

**Redirection cheat sheet** (this is idea #2 from the mental model,
spelled out):

```bash
cmd > file        # stdout -> file (overwrite)
cmd >> file       # stdout -> file (append)
cmd < file        # file -> stdin
cmd 2> file       # stderr -> file
cmd > file 2>&1   # both stdout AND stderr -> file (order matters: redirect stdout first, then point stderr at "wherever stdout now points")
cmd &> file       # bash shorthand for the line above
cmd | tee file    # write to file AND still print to the terminal (tee splits the pipe)
```

**Networking / transfer / archives**, briefly, since scripts lean on
these constantly:

```bash
curl -s https://api.example.com/health   # fetch a URL, -s = silent (no progress meter)
wget https://example.com/file.tar.gz     # download to a file
ssh user@host                            # remote shell
scp file.txt user@host:/remote/path/     # copy a file over ssh
tar -czvf out.tar.gz mydir/              # compress a directory (c=create, z=gzip, v=verbose, f=filename)
tar -xzvf out.tar.gz                     # extract it
df -h                                    # disk space, human-readable
du -sh mydir/                            # size of a directory
free -h                                  # memory usage
```

## Terminal productivity tricks (before scripting: working faster interactively)

These don't touch scripts — they're for the minutes you spend typing
commands live, and they compound because you use a shell all day.

**History and repetition** — bash remembers every command you ran, and
gives you shortcuts to reuse it instead of retyping:

```bash
history                 # list past commands, numbered
!!                       # re-run the last command
sudo !!                  # classic pattern: ran a command, forgot sudo, re-run it with sudo prepended
!$                       # the last *argument* of the previous command
vim !$                   # e.g. after `touch config.yml`, edit the file you just created
!grep                    # re-run the most recent command that started with "grep"
Ctrl+R                   # reverse-search history interactively; keep pressing to cycle older matches
```

**Aliases and shell startup files** — a shortcut for a command you type
often, defined once and loaded every time you open a shell:

```bash
alias ll='ls -la'
alias gs='git status'
```

Put lines like these in `~/.bashrc` (interactive non-login shells — what
opens when you launch a terminal) or `~/.bash_profile`/`~/.profile`
(login shells). `source ~/.bashrc` reloads it in your current session
without closing the terminal. `export PATH="$HOME/bin:$PATH"` in one of
these files is how you make your own scripts runnable by name from
anywhere, without typing the full path.

**Navigation shortcuts:**

```bash
cd -                  # jump back to the previous directory (toggles)
pushd /var/log         # cd there, but remember where you came from
popd                   # pop back to it
Tab                    # complete a command/path; press twice to list all matches
```

**Comparing and inspecting:**

```bash
diff file1 file2              # line-by-line differences
diff -u file1 file2            # unified format (what git diff uses)
comm sorted1.txt sorted2.txt   # lines unique to file1 / unique to file2 / in both (three columns) — needs sorted input
column -t data.tsv             # pretty-print tab/space-separated data as aligned columns
watch -n 2 'df -h'             # re-run a command every 2 seconds, screen redrawn in place — great for watching a value change live
time ./script.sh               # how long a command actually took (real/user/sys)
```

**Copying that survives real-world messiness — `rsync` over `cp`/`scp`:**

```bash
rsync -avz src/ user@host:/remote/dst/    # a=archive (preserves perms/times/symlinks), v=verbose, z=compress in transit
rsync -avz --delete src/ dst/              # also remove files in dst/ that no longer exist in src/
```

Unlike `cp -r` or `scp`, `rsync` only transfers what changed, resumes
cleanly if interrupted, and can run repeatedly as a sync rather than a
one-shot copy — this is why deploy scripts and backup jobs use it instead
of `cp`.

**Symlinks** — a pointer to another path, not a copy:

```bash
ln -s /opt/releases/v2.3 /opt/current    # `/opt/current` now resolves to v2.3
```

The classic release pattern: deploy a new version to its own directory,
then flip one symlink to point at it — the "switch" is one atomic
operation instead of overwriting files in place.

**Persistent sessions — `tmux`/`screen`:** a long-running command started
in a plain SSH session dies the instant the connection drops. `tmux`
(or the older `screen`) runs a session on the *server* that keeps going
after you disconnect:

```bash
tmux new -s deploy      # start a named session
# ... run your long command ...
# Ctrl+b then d          # detach, leaving it running
tmux attach -t deploy    # reattach later, from anywhere
```

`nohup cmd &` (already covered above) solves the same disconnect problem
for a single command with no need to reattach; `tmux` is for when you
need to keep interacting with it.

## Shell scripting proper — enough syntax to start writing scripts

### The shebang and making it runnable

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

### Variables

```bash
name="Surendra"          # NO spaces around =. `name = "x"` is a syntax error — bash reads it as running a command called `name`.
echo "$name"              # read it: $name or ${name}
echo "${name}_suffix"     # {} needed here so bash doesn't try to read a variable called name_suffix
```

**Quoting rules — this is the single most important habit in shell
scripting:**

```bash
value="two words"
echo $value       # WRONG for most purposes: expands to two separate arguments, "two" and "words"
echo "$value"      # RIGHT: stays one string, "two words"
echo '$value'      # literal: prints the text $value, no expansion at all
```

Rule of thumb: **always double-quote a variable reference** (`"$var"`)
unless you specifically want word-splitting/globbing to happen. This one
habit prevents the majority of real-world shell script bugs.

**Command substitution** — run a command, capture its stdout as a string:

```bash
today=$(date +%F)
echo "Today is $today"
count=$(ls | wc -l)
```

(`$(...)` is preferred over the older backtick syntax `` `...` `` — it
nests cleanly and is easier to read.)

**Arithmetic:**

```bash
x=5
y=$((x + 3))          # arithmetic context: $(( ... ))
echo $((x * 2))
```

**Special variables bash gives you for free:**

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

### Conditionals

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
| AND / OR | `&&` / `||` |

### Parameter expansion defaults — handling missing input gracefully

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
exactly what the Docker entrypoint pattern referenced later in this doc
uses (`${OPS_SERVER_PORT:-8001}`).

### `case` — cleaner than a chain of `if`/`elif` for matching one value

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

### Loops

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

### Functions

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

### `getopts` — real `-x value` / `--flag` style argument parsing

`$1`, `$2` (positional args) work for a script with one or two fixed
arguments. The moment a script needs *flags* — `-f config.yml -v
--dry-run`, order-independent — reading `$1`/`$2` by hand gets unwieldy
fast. `getopts` is bash's built-in loop for this:

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

### Arrays

```bash
fruits=("apple" "banana" "cherry")
echo "${fruits[0]}"         # apple
echo "${fruits[@]}"         # all elements
echo "${#fruits[@]}"        # length: 3

for fruit in "${fruits[@]}"; do
    echo "$fruit"
done
```

**Associative arrays** (bash 4+) — arrays keyed by string instead of
index, i.e. a dictionary/hash map:

```bash
declare -A env_ports
env_ports[dev]=8000
env_ports[staging]=8001
env_ports[prod]=8002

echo "${env_ports[prod]}"          # 8002
for env in "${!env_ports[@]}"; do   # `!` here means "the keys," not negation
    echo "$env -> ${env_ports[$env]}"
done
```

`declare -A` is mandatory — without it, bash treats the same syntax as a
regular (numeric-indexed) array and silently gives wrong results.

### String manipulation

```bash
s="hello_world.txt"
echo "${#s}"          # length: 15
echo "${s%.txt}"       # strip shortest match from the end: hello_world
echo "${s#hello_}"     # strip shortest match from the start: world.txt
echo "${s/world/there}"  # replace first match: hello_there.txt
echo "${s//o/0}"        # replace all matches: hell0_w0rld.txt
```

### Reading input interactively

```bash
read -p "Enter your name: " name
echo "Hi, $name"
```

### Here-documents (multi-line input inline)

```bash
cat <<EOF > config.txt
host=localhost
port=8080
env=$env_var_expands_here
EOF
```

(Quote the delimiter — `<<'EOF'` — to disable variable expansion inside
the block, useful when writing literal scripts/templates.)

**Here-string** — a one-line shortcut when you just want to hand a single
string to a command's stdin, without a whole heredoc block:

```bash
grep "error" <<< "$log_line"     # equivalent to: echo "$log_line" | grep "error"
```

**Process substitution** — the trick that makes a *command's output*
look like a file, for tools that only accept filenames:

```bash
diff <(sort file1.txt) <(sort file2.txt)   # diff normally takes two files; <(...) fakes one from a command's stdout
while IFS= read -r line; do echo "$line"; done < <(find . -name "*.log")
```

`<(cmd)` runs `cmd` and hands back a path like `/dev/fd/63` in its place
— bash plumbs the command's stdout to something a file-expecting tool can
open. This is also why the `while read` loop in the worked example below
uses `< <(find ...)` instead of piping into the loop: piping into a
`while` runs it in a subshell, so variables set inside the loop vanish
once it ends; `< <(...)` keeps the loop in the current shell.

**Backgrounding and waiting — real parallelism in a script:**

```bash
for host in web1 web2 web3; do
    check_host "$host" &      # & backgrounds this call; the loop doesn't wait for it before starting the next
done
wait                          # block here until every backgrounded job from this shell has finished

# xargs -P: the same idea for a list of inputs, N at a time
cat hosts.txt | xargs -P 4 -I{} curl -sf "https://{}/health"   # -P4 = 4 in parallel, -I{} substitutes each line in
```

`wait` with no arguments blocks until *all* background jobs finish;
`wait "$pid"` (capture a PID with `cmd & pid=$!`) waits for one specific
job — useful when a script needs to know which of several parallel tasks
failed, not just that something did.

### Exit codes and error handling — the difference between a toy script and a production one

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

## A full worked example

The pattern above — shebang, `set -euo pipefail`, argument parsing,
functions, a loop, explicit exit codes, errors to stderr — is exactly what
a real script looks like. A complete, runnable example combining all of
it lives in
[`examples/backup_and_alert.sh`](examples/backup_and_alert.sh): it
archives a directory, checks the result, and reports success/failure with
a proper exit code — the shape of most "housekeeping" scripts you'll
actually write (log rotation, backups, health checks).

A second worked example,
[`examples/parallel_health_check.sh`](examples/parallel_health_check.sh),
puts the tricks from further up this doc into one script: `getopts` for
`-f`/`-t`/`-p` flags, process substitution (`< <(...)`) to read a hosts
file without losing loop state, backgrounded jobs capped with `wait -n`
for bounded parallelism, `trap` on `EXIT` *and* `INT`/`TERM` so Ctrl+C
mid-run still cleans up its temp directory, and a final `[ "$fail_count"
-eq 0 ]` as the script's own exit code — the shape of a fan-out check
script (health checks across N hosts, a parallel deploy verification,
anything "do this same thing to a list of targets and tell me what
failed"). Run it against `examples/sample_hosts.txt` to see it live:

```bash
./examples/parallel_health_check.sh -f examples/sample_hosts.txt -t 5 -p 4
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
  the entrypoint scripts in this repo) links to `dash`, a stricter POSIX
  shell — arrays, `[[ ]]`, and `local` either behave differently or don't
  exist. If a script needs bash-only features, its shebang must say so
  explicitly (`#!/usr/bin/env bash`), or it will fail (or silently behave
  differently) on a system where `/bin/sh` isn't bash.
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

## Working with JSON — `jq` basics

Scripts constantly deal with an API or CLI tool that outputs JSON (a
`curl` response, `kubectl get pod -o json`, `aws ... --output json`).
`grep`/`sed`/`awk` are line-oriented and awkward on JSON's structure;
`jq` is a filter built specifically for it — same "small tool in a
pipeline" idea as `grep`/`sort`, just JSON-shaped instead of line-shaped:

```bash
echo '{"name":"web1","status":"healthy","port":8080}' | jq '.name'        # "web1" (quoted string)
echo '{"name":"web1","status":"healthy","port":8080}' | jq -r '.name'     # web1 (raw, unquoted — what you want in a script variable)

curl -s https://api.example.com/hosts | jq -r '.[] | .name'     # pull a field out of every element of a JSON array
curl -s https://api.example.com/status | jq -e '.status == "ok"'   # -e: exit code reflects the filter's boolean result — usable directly in an `if`
```

The pattern that shows up constantly in real scripts: fetch, filter with
`jq -r`, capture with `$(...)`, use like any other shell variable:

```bash
status=$(curl -s "https://api.example.com/health" | jq -r '.status')
if [ "$status" != "ok" ]; then
    echo "ERROR: service unhealthy (status=$status)" >&2
    exit 1
fi
```

## Scheduling — running a script unattended (cron)

Back in "the problem it solves" at the top: a script's real payoff is
running with no human present. `cron` is the standard Linux scheduler for
that — a background daemon that reads a crontab (a list of "run this at
these times" rules) and executes each script when its time comes.

```bash
crontab -e     # open your crontab in an editor
crontab -l     # list your current scheduled jobs
```

A crontab line has five time fields, then the command:

```
# minute  hour  day-of-month  month  day-of-week   command
   0       2      *            *      *             /home/you/backup_and_alert.sh /data /backups >> /var/log/backup.log 2>&1
  */15     *      *            *      *             /home/you/health_check.sh
   0       9      *            *      1-5            /home/you/weekday_report.sh
```

Read the first one as "at minute 0 of hour 2, every day, every month,
every weekday" — i.e. 2:00 AM daily. `*` means "every value of this
field"; `*/15` means "every 15 units." Two habits matter for any real
cron job: **always redirect output** (`>> logfile 2>&1`) since cron
normally only emails failures and often that's not configured, and
**always use absolute paths** inside the script and for the script
itself — cron runs with a minimal environment, not your interactive
shell's `$PATH` or working directory.

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

## Relationship to other tools/scripts in this repo

This repo already leans on the exact patterns above in real files, which
are worth reading directly once the syntax above makes sense:

- [`genai_lab/aiops_mlops_agent/docker/entrypoint.sh`](../../../../genai_lab/aiops_mlops_agent/docker/entrypoint.sh) —
  a minimal Docker entrypoint: `set -e`, a default-value pattern
  (`${OPS_SERVER_PORT:-8001}` — use the env var if set, else fall back to
  `8001`), and `exec "$@"` at the end, which replaces the shell process
  with whatever command Docker was told to run (instead of running it as
  a child process) so signals like `SIGTERM` reach it directly.
- [`public_docker_images/rust-api/scripts/verify.sh`](../../../../public_docker_images/rust-api/scripts/verify.sh) —
  a full acceptance-test script: `set -uo pipefail`, small reusable
  functions (`ok()`, `bad()`, `assert()`), heavy use of command
  substitution to capture `curl` responses, and an explicit `exit 0` /
  `exit 1` at the end based on an accumulated pass/fail count — the same
  "functions + exit code as the final verdict" shape as the worked
  example above, just applied to HTTP checks instead of file backups.

Both are good next reading once this doc's syntax section feels solid:
same primitives (redirection, `set` flags, functions, `$(...)`, quoting),
applied to a real problem instead of a teaching example.
