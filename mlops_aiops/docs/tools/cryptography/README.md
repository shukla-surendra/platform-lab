# cryptography (pyca/cryptography)

**Category:** cryptography / security (Python library)

## What it is

`cryptography` (the PyPI package is literally named `cryptography`, maintained by the
Python Cryptographic Authority — "pyca") is the standard, vetted Python library for
cryptographic primitives: symmetric encryption, asymmetric encryption/signing, hashing,
MACs, and key exchange. It wraps OpenSSL/BoringSSL for the actual algorithm
implementations, exposed through a Python API split into a high-level "recipes" layer
and a lower-level `hazmat` (hazardous materials) layer for primitives that are easy to
misuse if the caller doesn't already know the pitfalls (padding schemes, nonce/IV
handling, mode of operation choice).

The reason this library specifically, rather than writing crypto code by hand: rolling
your own cryptographic algorithm or protocol is a well-known anti-pattern — unlike most
engineering problems, novelty in crypto design is a liability, not a differentiator. A
design flaw here typically isn't discovered until it's already been exploited. Every
example below is "call a standardized, widely-reviewed primitive correctly," never
"implement AES/RSA from scratch."

## What it's used for

- **AES-GCM (symmetric, AEAD)** — bulk data encryption with built-in tamper detection
  in one call, the modern default over composing a bare cipher mode (CBC/CTR) with a
  separate MAC by hand.
- **RSA encrypt/decrypt** — asymmetric encryption with OAEP padding (raw/textbook RSA
  with no padding is broken and should never be used directly).
- **RSA sign/verify** — digital signatures with PSS padding; `verify()` raises
  `InvalidSignature` rather than returning a boolean that could be silently ignored.
- **SHA-256 hashing** — one-way, fixed-size digests for integrity checks.
- **HMAC** — keyed hashing, proving a message came from a holder of a shared secret
  key, which plain hashing alone cannot do (anyone can hash anything).
- **Ed25519 signing** — the modern elliptic-curve signature scheme; the exact
  `private_key.sign()` / `public_key.verify()` pattern shown here is literally the
  mechanism SSH public-key authentication runs under the hood (e.g. an AWS EC2 key
  pair created with `--key-type ed25519`).

## Alternatives

| Library | Notes |
|---|---|
| `cryptography` | This one — the current standard, actively maintained, wraps OpenSSL/BoringSSL |
| `pycryptodome` | Older, still used in legacy codebases; more primitives implemented in pure Python rather than wrapping OpenSSL for everything |
| `hashlib` / `hmac` (stdlib) | Fine for hashing/HMAC alone (no extra dependency), but has no asymmetric-crypto or AEAD support — `cryptography` is still needed for RSA/EC/AES-GCM |
| `PyNaCl` | Bindings for libsodium — a more opinionated, harder-to-misuse API (fewer padding-scheme footguns), popular when only modern primitives (Ed25519, X25519, XSalsa20-Poly1305) are needed |

## Usage

See [`examples/primitives.py`](examples/primitives.py) for a complete, tested,
runnable script covering all six primitives above (AES-GCM, RSA encrypt/decrypt, RSA
sign/verify, SHA-256, HMAC, Ed25519) with inline comments explaining what each call is
doing and why the specific padding/mode choice matters. Install with
`pip install cryptography`, then `python examples/primitives.py`.

This came up alongside the crypto deep-dive in
`../../../../fundamentals/security/00_foundations/tutorial.md` and its companion
personal notes at
`../../../../fundamentals/security/00_foundations/notes.md` — those cover the
*concepts* (why AEAD over bare CBC, why OAEP padding matters, what HMAC buys over plain
hashing); this doc and its example script are the *"here's the actual Python call"*
companion to that.
