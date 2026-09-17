# 05 — Terminal Productivity Tricks

These don't touch scripts — they're for the minutes you spend typing
commands live, and they compound because you use a shell all day.

## History and repetition

Bash remembers every command you ran, and gives you shortcuts to reuse it
instead of retyping:

```bash
history                 # list past commands, numbered
!!                       # re-run the last command
sudo !!                  # classic pattern: ran a command, forgot sudo, re-run it with sudo prepended
!$                       # the last *argument* of the previous command
vim !$                   # e.g. after `touch config.yml`, edit the file you just created
!grep                    # re-run the most recent command that started with "grep"
Ctrl+R                   # reverse-search history interactively; keep pressing to cycle older matches
```

## Aliases and shell startup files

A shortcut for a command you type often, defined once and loaded every
time you open a shell:

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

## Navigation shortcuts

```bash
cd -                  # jump back to the previous directory (toggles)
pushd /var/log         # cd there, but remember where you came from
popd                   # pop back to it
Tab                    # complete a command/path; press twice to list all matches
```

## Comparing and inspecting

```bash
diff file1 file2              # line-by-line differences
diff -u file1 file2            # unified format (what git diff uses)
comm sorted1.txt sorted2.txt   # lines unique to file1 / unique to file2 / in both (three columns) — needs sorted input
column -t data.tsv             # pretty-print tab/space-separated data as aligned columns
watch -n 2 'df -h'             # re-run a command every 2 seconds, screen redrawn in place — great for watching a value change live
time ./script.sh               # how long a command actually took (real/user/sys)
```

## Copying that survives real-world messiness — `rsync` over `cp`/`scp`

```bash
rsync -avz src/ user@host:/remote/dst/    # a=archive (preserves perms/times/symlinks), v=verbose, z=compress in transit
rsync -avz --delete src/ dst/              # also remove files in dst/ that no longer exist in src/
```

Unlike `cp -r` or `scp`, `rsync` only transfers what changed, resumes
cleanly if interrupted, and can run repeatedly as a sync rather than a
one-shot copy — this is why deploy scripts and backup jobs use it instead
of `cp`.

## Symlinks

A pointer to another path, not a copy:

```bash
ln -s /opt/releases/v2.3 /opt/current    # `/opt/current` now resolves to v2.3
```

The classic release pattern: deploy a new version to its own directory,
then flip one symlink to point at it — the "switch" is one atomic
operation instead of overwriting files in place.

## Persistent sessions — `tmux`/`screen`

A long-running command started in a plain SSH session dies the instant
the connection drops. `tmux` (or the older `screen`) runs a session on
the *server* that keeps going after you disconnect:

```bash
tmux new -s deploy      # start a named session
# ... run your long command ...
# Ctrl+b then d          # detach, leaving it running
tmux attach -t deploy    # reattach later, from anywhere
```

`nohup cmd &` (covered in
[04 — Processes, Redirection, and Networking](04-processes-redirection-networking.md))
solves the same disconnect problem for a single command with no need to
reattach; `tmux` is for when you need to keep interacting with it.

**Run it:** [`examples/05_terminal_productivity.sh`](examples/05_terminal_productivity.sh)
covers the scriptable half of this topic — `diff`, `comm`, `column`,
`time`, `rsync`, and symlinks. (History, aliases, and `tmux` are
interactive-only — try those by hand in your terminal.)

```bash
./examples/05_terminal_productivity.sh
```

---
**Previous:** [04 — Processes, Redirection, and Networking](04-processes-redirection-networking.md) · **Next:** [06 — Scripting Basics](06-scripting-basics.md)
