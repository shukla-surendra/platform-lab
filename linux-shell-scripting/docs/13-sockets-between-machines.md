# 13 — Sockets: Talking Between Two Machines

Two computers on the same network can exchange bytes with nothing but the kernel's
socket system calls — no framework, no library. This topic shows the syscalls, then
drives them from the shell: `nc` as the server, bash's built-in `/dev/tcp` as the client.

## The syscalls

A socket is a **file descriptor**, so once it exists you use the same `read`/`write`/`close`
you'd use on a file (idea #1 from
[01 — Introduction and Mental Model](01-introduction-and-mental-model.md): everything is a
file, everything is a stream).

| Syscall | What the kernel does | Who calls it |
|---|---|---|
| `socket(AF_INET, SOCK_STREAM, 0)` | Creates a socket, returns an fd | server and client |
| `bind(fd, {ip, port})` | Attaches the socket to a local IP + port | server |
| `listen(fd, backlog)` | Marks it passive; kernel now completes TCP handshakes and queues clients | server |
| `accept(fd)` | Blocks until a client connects, returns a **new** fd for that one connection | server |
| `connect(fd, {server_ip, port})` | Starts the TCP handshake with the server | client |
| `write(fd, ...)` / `send()` | Copies bytes into the kernel's send buffer; kernel transmits | both |
| `read(fd, ...)` / `recv()` | Copies received bytes out of the kernel's receive buffer | both |
| `close(fd)` | Tears the connection down | both |

```text
Server                          Client
socket()                        socket()
bind(ip, port)
listen()
accept()  ◄──── handshake ────  connect(server_ip, port)
read()/write() ◄────────────►  write()/read()
close()                         close()
```

UDP skips the connection: `socket(AF_INET, SOCK_DGRAM, 0)`, then `sendto()` / `recvfrom()`.

## What the shell can and can't call

Bash cannot call `bind()`, `listen()`, or `accept()` itself — there's no shell syntax for
them. So the work splits like this:

| Side | Tool | Syscalls it makes |
|---|---|---|
| Server | `nc -l PORT` | `socket`, `bind`, `listen`, `accept`, `read`, `write`, `close` |
| Client | bash `/dev/tcp/HOST/PORT` | `socket`, `connect` (then plain fd I/O) |

`/dev/tcp/...` isn't a real file — it's a bash feature. `exec 3<>/dev/tcp/HOST/PORT` makes
bash call `socket()` + `connect()` and gives you the connection as **fd 3**. After that:

```bash
exec 3<>/dev/tcp/192.168.1.20/5000   # socket() + connect()  -> fd 3
echo "hello" >&3                      # write(3, "hello\n")
read -r reply <&3                     # read(3, ...)
exec 3>&-                             # close(3)
```

This is redirection (see [04](04-processes-redirection-networking.md)) pointed at a
network connection instead of a file. It only works in bash — not `sh`/`dash`.

## The example scripts

Runnable, and tested on macOS (both bash 5 and the system bash 3.2):

- [`examples/13_socket_server.sh`](../examples/13_socket_server.sh) — echo server: `nc -l` does the
  syscalls; a named pipe (`mkfifo`) carries replies back into `nc`; a `while true` loop
  re-listens because `nc` serves one connection then exits.
- [`examples/13_socket_client.sh`](../examples/13_socket_client.sh) — reads lines from stdin, sends each
  over `/dev/tcp`, prints the echoed reply.

### On one machine first

```bash
./examples/13_socket_server.sh 5000               # terminal 1
./examples/13_socket_client.sh 127.0.0.1 5000     # terminal 2 — type a line, see it echoed
```

Or skip the client script entirely — `nc` works as both ends, and it's the quickest
smoke test:

```bash
nc -l 5000            # one side
nc 127.0.0.1 5000     # other side — type in either window
```

## Mac ↔ Windows (WSL)

Find each side's IP:

```bash
ipconfig getifaddr en0     # macOS Wi-Fi (try en1 if empty)
hostname -I                # inside WSL — but see the NAT caveat below
```

On WSL, `nc` is already there on Ubuntu/Debian (`netcat-openbsd`); if `nc -l 5000` errors,
you have `netcat-traditional`, which needs `nc -l -p 5000`.

### Easiest: Mac is the server, WSL is the client

Outbound connections from WSL2 need no extra setup.

```bash
# Mac
./examples/13_socket_server.sh 5000
# WSL
./examples/13_socket_client.sh <mac-ip> 5000
```

macOS may ask "accept incoming network connections?" for `nc` the first time — click Allow.

### WSL is the server, Mac is the client — one extra step

By default **WSL2 sits behind a NAT** with its own virtual IP (usually `172.x.x.x`). The Mac
can't reach that; it can only reach the Windows host's LAN IP. Pick one:

**Option A — mirrored networking (Windows 11 22H2+).** WSL shares the host's network. In
`%UserProfile%\.wslconfig`:

```ini
[wsl2]
networkingMode=mirrored
```

Then run `wsl --shutdown` in PowerShell and reopen WSL. The Mac connects to the **Windows
machine's LAN IP** (`ipconfig` on Windows). Allow the port through Windows Firewall
(admin PowerShell):

```powershell
New-NetFirewallRule -DisplayName "wsl-socket-test" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

If it's still blocked, mirrored mode also has a separate Hyper-V firewall — check
Microsoft's WSL networking docs for the `Set-NetFirewallHyperVVMSetting` inbound rule.

**Option B — port-forward from Windows into WSL** (older setups). Admin PowerShell, with
`<wsl-ip>` from `hostname -I` inside WSL:

```powershell
netsh interface portproxy add v4tov4 listenport=5000 listenaddress=0.0.0.0 connectport=5000 connectaddress=<wsl-ip>
New-NetFirewallRule -DisplayName "wsl-socket-test" -Direction Inbound -Protocol TCP -LocalPort 5000 -Action Allow
```

The WSL IP changes on restart, so redo the `netsh` line after a reboot (remove the old one
with `netsh interface portproxy delete v4tov4 listenport=5000 listenaddress=0.0.0.0`).
Either way the Mac connects to the **Windows host's LAN IP**, not the WSL one.

*The scripts were run and verified on macOS over loopback. The WSL-side networking steps
above follow Microsoft's documented behavior but weren't exercised from a real
Windows machine while writing this.*

## Watching the raw syscalls

Trace the server and you'll see the sequence from the table above:

```bash
# Linux / WSL
strace -f -e trace=network,read,write nc -l 5000

# macOS (needs sudo; SIP can restrict it)
sudo dtruss -f nc -l 5000
```

Expect `socket(...)`, `bind(...)`, `listen(...)`, then `accept(...)` blocking until a client
connects, then `read`/`write` as data flows. (`strace` doesn't exist on macOS; `dtruss` is its
closest equivalent.) `lsof -i :5000` (macOS) / `ss -ltnp` (Linux) shows who is holding the port.

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| `Connection refused` | Nothing listening on that IP:port — server not running, wrong port, or (WSL server) NAT/portproxy not set up |
| Hangs, then `timed out` | A firewall is silently dropping packets, or the machines aren't on the same subnet (guest Wi-Fi and some routers isolate clients) |
| `Address already in use` on the server | Something already holds the port — check with `lsof -i :5000` / `ss -ltnp` |
| Works on `127.0.0.1`, not from the other machine | Firewall, or you're targeting the WSL2 NAT address instead of the Windows host IP |
| `nc -l 5000` errors or doesn't listen on WSL | You likely have `netcat-traditional` — use `nc -l -p 5000` |

## Things worth noticing

- The server holds **two kinds of fd**: the listening one (only `accept`s) and one new fd per connection.
- TCP is a **byte stream**, not messages: one `write` of N bytes can arrive over several `read`s.
  The scripts sidestep that by using newline-terminated lines (`read -r` reads up to a newline) —
  real protocols need explicit framing (a delimiter or a length prefix).
- The kernel does the network work — handshake, retransmits, ACKs, routing. Your process only makes these calls.
- These scripts serve one client at a time; real servers use `fork`/threads/`epoll`.
- Plain TCP is unencrypted and unauthenticated — fine for a lab on your own LAN, not for anything sensitive.

Deeper reading: *The Linux Programming Interface*, chapters 56–61.

## Try it yourself

Write a UDP version using only `nc` and `/dev/udp`: `nc -u -l 5000` as the receiver, and
`echo hi > /dev/udp/HOST/5000` as the sender. Which syscalls disappear compared to the TCP
version, and why?

---
**Previous:** [12 — Worked Examples and Real-World References](12-worked-examples-and-real-world.md) · **Back to:** [README](README.md)
