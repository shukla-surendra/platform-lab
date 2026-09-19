# 03 — Files and Text Processing

The everyday toolkit for navigating, viewing, searching, and transforming
files and text streams. This is what makes the shell a real
data-processing environment, not just a file browser.

## Navigating and manipulating files

| Command | What it does | Example |
|---|---|---|
| `pwd` | print current directory | `pwd` |
| `cd` | change directory | `cd /var/log` |
| `ls -la` | list, including hidden/detailed | `ls -la ~/project` |
| `mkdir -p` | make a directory (and parents) | `mkdir -p a/b/c` |
| `touch` | create an empty file / update its timestamp | `touch notes.txt` |
| `cp -r` | copy (recursive for directories) | `cp -r src/ backup/` |
| `mv` | move or rename | `mv old.txt new.txt` |
| `rm -rf` | remove, recursive+force | `rm -rf build/` — **dangerous, see [10 — Error Handling and Debugging](10-error-handling-and-debugging.md)** |
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

## Viewing text

```bash
cat file.txt        # dump the whole file
less file.txt        # page through it (q to quit, / to search)
head -n 20 file.txt   # first 20 lines
tail -n 20 file.txt   # last 20 lines
tail -f app.log       # "follow" — keep printing new lines as they're written; the #1 way to watch a live log
```

## The text-processing pipeline tools

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

## Turning output into arguments — `xargs`

Many commands (like `rm`) take arguments, not stdin. `xargs` bridges the
gap by taking piped-in lines and turning each into an argument to another
command:

```bash
find . -name "*.tmp" | xargs rm       # delete every .tmp file found
echo "a b c" | xargs -n1 echo         # runs `echo a`, `echo b`, `echo c` separately
```

**Run it:** [`examples/03_text_processing_pipeline.sh`](examples/03_text_processing_pipeline.sh)
generates a fake log and runs the pipeline questions above against real
data instead of you copy-pasting them by hand.

```bash
./examples/03_text_processing_pipeline.sh
```

---
**Previous:** [02 — Filesystem and Permissions](02-filesystem-and-permissions.md) · **Next:** [04 — Processes, Redirection, and Networking](04-processes-redirection-networking.md)
