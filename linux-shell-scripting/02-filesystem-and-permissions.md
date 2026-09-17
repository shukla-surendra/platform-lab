# 02 — Filesystem and Permissions

Needed before anything else: every other topic assumes you can read
`ls -la` output and reason about `chmod` without hesitating.

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

**Run it:** [`examples/02_filesystem_and_permissions.sh`](examples/02_filesystem_and_permissions.sh)
does exactly this — creates a practice tree and prints `ls -la` before and
after each `chmod`, so you can watch the permission bits change.

```bash
./examples/02_filesystem_and_permissions.sh
```

---
**Previous:** [01 — Introduction and Mental Model](01-introduction-and-mental-model.md) · **Next:** [03 — Files and Text Processing](03-files-and-text-processing.md)
