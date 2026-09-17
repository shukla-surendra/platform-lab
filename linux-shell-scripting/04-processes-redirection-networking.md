# 04 — Processes, Redirection, and Networking

## Processes

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

## Redirection cheat sheet

This is idea #2 from the mental model in
[01 — Introduction and Mental Model](01-introduction-and-mental-model.md),
spelled out:

```bash
cmd > file        # stdout -> file (overwrite)
cmd >> file       # stdout -> file (append)
cmd < file        # file -> stdin
cmd 2> file       # stderr -> file
cmd > file 2>&1   # both stdout AND stderr -> file (order matters: redirect stdout first, then point stderr at "wherever stdout now points")
cmd &> file       # bash shorthand for the line above
cmd | tee file    # write to file AND still print to the terminal (tee splits the pipe)
```

## Networking / transfer / archives

Briefly, since scripts lean on these constantly:

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

**Run it:** [`examples/04_processes_redirection_networking.sh`](examples/04_processes_redirection_networking.sh)
backgrounds and kills a job, demonstrates `tee`, and builds a `tar`
archive, back to back.

```bash
./examples/04_processes_redirection_networking.sh
```

---
**Previous:** [03 — Files and Text Processing](03-files-and-text-processing.md) · **Next:** [05 — Terminal Productivity](05-terminal-productivity.md)
