# 01 — Introduction and Mental Model

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

Everything else in this tutorial is vocabulary layered on two ideas:

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

**Run it:** [`examples/01_pipes_and_streams.sh`](examples/01_pipes_and_streams.sh)
demonstrates exit codes, separate stdout/stderr streams, and a pipe, live.

```bash
./examples/01_pipes_and_streams.sh
```

---
**Next:** [02 — Filesystem and Permissions](02-filesystem-and-permissions.md)
