# 09 — Arrays, Strings, and I/O Tricks

## Arrays

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

## String manipulation

```bash
s="hello_world.txt"
echo "${#s}"          # length: 15
echo "${s%.txt}"       # strip shortest match from the end: hello_world
echo "${s#hello_}"     # strip shortest match from the start: world.txt
echo "${s/world/there}"  # replace first match: hello_there.txt
echo "${s//o/0}"        # replace all matches: hell0_w0rld.txt
```

## Reading input interactively

```bash
read -p "Enter your name: " name
echo "Hi, $name"
```

## Here-documents (multi-line input inline)

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

## Process substitution — make a command's output look like a file

```bash
diff <(sort file1.txt) <(sort file2.txt)   # diff normally takes two files; <(...) fakes one from a command's stdout
while IFS= read -r line; do echo "$line"; done < <(find . -name "*.log")
```

`<(cmd)` runs `cmd` and hands back a path like `/dev/fd/63` in its place
— bash plumbs the command's stdout to something a file-expecting tool can
open. This is also why the `while read` loop in the worked example in
[12 — Worked Examples and Real-World References](12-worked-examples-and-real-world.md)
uses `< <(find ...)` instead of piping into the loop: piping into a
`while` runs it in a subshell, so variables set inside the loop vanish
once it ends; `< <(...)` keeps the loop in the current shell.

## Backgrounding and waiting — real parallelism in a script

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

**Run it:** [`examples/09_health_check_ports.sh`](examples/09_health_check_ports.sh)
maps `dev`/`staging`/`prod` to ports with an associative array,
backgrounds a `curl` health check against `localhost:<port>` for each,
then `wait`s for all of them. (Expect `DOWN` for every port unless you
actually have something listening locally — the point is the array +
parallel-check pattern.)

```bash
./examples/09_health_check_ports.sh
```

---
**Previous:** [08 — Functions and Arguments](08-functions-and-arguments.md) · **Next:** [10 — Error Handling and Debugging](10-error-handling-and-debugging.md)
