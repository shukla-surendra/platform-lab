# tls_handshake_demo

A real TLS 1.3 handshake, run from **both sides in one process**, so you can
watch what the client does and what the server does at every step of the
same connection.

This uses [`rustls`](https://docs.rs/rustls) (a production TLS
implementation) over a real loopback TCP socket — no cryptography is
hand-rolled here. What *is* hand-rolled is the I/O loop: instead of calling
one `connect()`/`accept()` that hides the handshake inside a library
function, `src/client.rs` and `src/server.rs` each drive the handshake state
machine manually, one record at a time, printing every round trip.

## Run it

```sh
cargo run
```

You'll see a linear transcript like:

```
[client] opened raw TCP connection to 127.0.0.1:46513
[client] round 1: wrote 216 handshake bytes to the wire      # ClientHello
[server] accepted raw TCP connection from Ok(127.0.0.1:46954)
[server] round 1: read 216 raw bytes from the wire
[server] round 2: wrote 662 handshake bytes to the wire      # ServerHello..Finished, one flight
[client] round 1: read 662 raw bytes from the wire
[client] handshake complete: Some(TLSv1_3) / Some(TLS13_AES_256_GCM_SHA384)
[client] sent encrypted application data: "hello over TLS"
[server] round 2: read 80 raw bytes from the wire
[server] handshake complete: Some(TLSv1_3) / Some(TLS13_AES_256_GCM_SHA384)
[server] decrypted application data from client: "hello over TLS"
[server] sent encrypted reply: "echo: hello over TLS"
[client] decrypted reply from server: "echo: hello over TLS"
```

For the itemized play-by-play *inside* those two big "handshake bytes"
blobs — every individual handshake message, decoded — turn on rustls's own
tracing:

```sh
RUST_LOG=trace cargo run 2>&1 | grep TRACE
```

That prints, in order, exactly what TLS 1.3 (RFC 8446) actually sends:

| step | who | message | what it does |
|---|---|---|---|
| 1 | client | `ClientHello` | proposes TLS version, cipher suites, and (crucially, TLS 1.3's speed trick) a Diffie-Hellman key share *guessed* up front, so the server can derive shared secrets without a second round trip |
| 2 | server | `ServerHello` | picks the cipher suite + confirms the key share |
| 3 | server | `EncryptedExtensions` | the rest of the server's negotiation info, now encrypted (TLS 1.3 encrypts everything after ServerHello, unlike TLS 1.2) |
| 4 | server | `Certificate` | the server's cert chain (here: our one self-signed cert) |
| 5 | server | `CertificateVerify` | a signature over the handshake transcript so far, made with the cert's private key — proves the server *holds* the key that matches the cert it just sent |
| 6 | server | `Finished` | a MAC over the whole transcript, proving the server derived the same keys the client will derive |
| 7 | client | *(verifies steps 3-6 against its `RootCertStore`)* | this is where `client.rs`'s "server identity verified" line comes from — real signature + chain-of-trust verification, not a stub |
| 8 | client | `Finished` | client's own MAC over the transcript — server verifies this on its next `process_new_packets()` |
| — | server | `NewSessionTicket` (x2) | out-of-band, post-handshake: session tickets for a future fast resume, not required for this connection |

Steps 2-6 all arrive in the *same* TCP read on the client side (that's the
"round 2: wrote 662 bytes" / "round 1: read 662 bytes" pair above) — TLS
1.3's whole point versus 1.2 is collapsing the server's entire response into
one flight, so a full handshake costs one round trip instead of two.

## Code layout

- `src/cert.rs` — generates a self-signed cert for `"localhost"` in memory (via `rcgen`). This is the one piece that isn't "real" TLS: a real client trusts a CA-signed cert already in its OS/browser trust store, not a cert it just watched the server mint. Everything past this point is the real protocol.
- `src/server.rs` — builds a `ServerConfig` from that cert, then manually drives a `rustls::ServerConnection` over an accepted `TcpStream`.
- `src/client.rs` — builds a `ClientConfig` whose *entire* trust store is that one cert (so verification is genuine, not skipped), then manually drives a `rustls::ClientConnection`.
- `src/main.rs` — wires the two together: binds a loopback listener, runs the server on a background thread, runs the client on the main thread, prints the milestones.

## Why a manual loop instead of `TcpStream` + a one-line `connect()`

`rustls::Stream`/`StreamOwned` (used here only *after* the handshake, for
the echo) would happily drive the handshake invisibly inside the first
`read()`/`write()` call. The manual `while conn.is_handshaking() { ... }`
loop in both `client.rs` and `server.rs` exists purely so the mechanic is
visible: read raw bytes → feed them to the state machine → ask the state
machine what it wants to do next → write out its response → repeat. That
loop *is* the transport-level shape of every TLS handshake, independent of
which specific messages are inside it.
