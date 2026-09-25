# Learning Log

A running, chronological log of concepts covered in Claude Code sessions —
appended to after each topic, not edited into a polished writeup. Newest
entries at the bottom.

---

## 2026-09-22 — Transformer internals: Q/K/V order, MLOps vs MLP, GELU

**Q/K/V projection order is an implementation choice, not a semantic one.**
Two files in `pytorch_exploration/` demonstrate this:
- `qkv_demo.py` uses three *separate* `nn.Linear` layers (`W_q`, `W_k`, `W_v`) — no shared weight matrix, so there's no "order" at all.
- `mini_llm.py` fuses them into one `nn.Linear(n_embd, 3*n_embd)` (`qkv_proj`) and splits the output into three chunks via `.split(C, dim=-1)`. The split order is arbitrary — the network learns whichever segment is used as "query" to behave as a query — as long as it's internally consistent (whatever chunk is used in `q @ k.T` as the query side stays the query side downstream). The only place order stops being optional: loading *pretrained* weights, where the checkpoint's fused matrix has a specific slice order baked in already.

**MLOps vs MLP** — homophone mixup, not a real overlap:
- **MLOps** = Machine Learning Operations. Practices for running ML in production: data/experiment versioning, CI/CD for models, model registries, serving, drift monitoring, retraining loops. Repo notes already exist at `mlops/docs/mlops-aiops-llmops.md` and `system_design_foundation/01_ml_system_design/11_llmops.md`.
- **MLP** = Multi-Layer Perceptron, the feed-forward sublayer of a transformer block (`mini_llm.py:160-174`). Two Linear layers with a nonlinearity between them (`E -> 4E -> E`), holding most of a transformer's parameters/FLOPs.

**Why GELU (or any nonlinearity) is required in the MLP:** stacking two Linear layers with nothing between them collapses algebraically into one Linear layer — `fc_out(fc_in(x))` is just another single `E x E` matrix, so the model would gain zero expressive power over one layer no matter how many parameters were added. GELU (`x * Φ(x)`, a smooth approximation of "pass positive values through, zero out negative ones") breaks that collapse and is what gives the MLP the capacity to approximate non-linear functions. GPT-2-style models use plain GELU; the repo's `custom-gpt-200m/350m` (Llama-style) use SiLU inside a *gated* SwiGLU MLP instead.

**Architecture survey of `llm-engineering/from_scratch/*`:** all variants are dense decoders (no MoE, no GQA/MQA — every variant has `num_heads == num_kv_heads`). Two architecture generations exist side by side:
- GPT-2-style (`custom-gpt-6m/10m/50m/153m/nano/word/distill-10m`): learned absolute position embeddings, LayerNorm, 2-matrix GELU MLP.
- Llama-style (`custom-gpt-200m/350m/350m-ddp`): RoPE, RMSNorm, 3-matrix SwiGLU MLP (`8/3 E` hidden), no biases. This is the more "current-trend" architecture of the two, though it's still one generation behind the very latest frontier open models (which add GQA and often MoE on top of this same RoPE+RMSNorm+SwiGLU base).

---

## 2026-09-23 — TLS handshake, from both sides, and how self-signed certs work

Built a standalone project, `tls_handshake_demo/` (repo root), to see a real
TLS 1.3 handshake end-to-end: a `rustls` client and server running in one
process over a real loopback TCP socket, each driving its handshake state
machine by hand (`while conn.is_handshaking() { read_tls / process_new_packets / write_tls }`)
instead of hiding it behind one `connect()` call, so every round trip and
milestone prints. Full writeup of the wire-level message sequence is in
`tls_handshake_demo/README.md`; running `RUST_LOG=trace cargo run` surfaces
rustls's own internal per-message log lines (decoded ClientHello,
ServerHello, Certificate, CertificateVerify, Finished, NewSessionTicket).

**How a certificate actually gets created — the key pair comes first, always:**
1. **Generate the key pair as one unit.** A private key is a random number; the public key is *derived* from it in one deterministic step (e.g. ECDSA: `Q = d * G`). There's no independent "generate a public key" step — you can't have one without its private key existing first (or already possessed).
2. **Build the to-be-signed body**: that public key + identity claims (`CN=localhost`, SAN) + validity dates + extensions. Just structured data so far, not yet trusted by anyone.
3. **Sign it** — this is the entire self-signed vs CA-signed distinction:
   - *CA-signed*: you send a CSR (public key + identity, unsigned) to a CA, who signs the body with **its own** long-lived private key. Result is trusted by anyone who already trusts that CA (browsers/OSes ship CA public keys pre-installed).
   - *Self-signed*: you sign the body with **your own** private key — the same key pair whose public half is embedded in the cert. `issuer == subject`; the signature verifies against the cert's own embedded public key. Same crypto operation either way — the only difference is nobody outside you is vouching for it, so a client needs your specific cert in its trust store beforehand (exactly what `client.rs`'s `RootCertStore` does).

`tls_handshake_demo/src/cert.rs` does exactly this: `rcgen::generate_simple_self_signed` generates the key pair, builds the cert body with `SAN=localhost`, and signs it with that same key — one call standing in for all three steps above.

**Separate long-term identity key vs per-connection key exchange:** the key pair inside the certificate (identity key, long-lived, used for `CertificateVerify`'s signature) is a different key pair from the ephemeral X25519 key share exchanged fresh in every `ClientHello`/`ServerHello` for that connection's actual encryption keys — that ephemeral part is what gives TLS forward secrecy even if the identity private key is ever compromised later.

**What creating a certificate actually requires from the requester, and what tools do it:**
- Always: a self-generated key pair (algorithm choice: RSA 2048/4096, ECDSA P-256/384, or Ed25519), the subject's identity fields (CN, O, OU, L, ST, C), the Subject Alternative Names (SAN — the field browsers actually check now, not CN), and a CSR (public key + identity, signed by your own private key to prove possession) if someone else is going to sign it.
- Only for a publicly-trusted CA-signed cert: proof of control over the domain (DV: DNS TXT record or HTTP challenge; OV/EV: business paperwork), plus a relationship/account with that CA.
- Tooling landscape: `openssl`/LibreSSL/BoringSSL (general CLI); `mkcert` (local dev — auto-installs its own CA into the OS/browser trust store so localhost certs show as trusted); Certbot/`acme.sh`/`lego` (ACME clients that automate free public certs from Let's Encrypt/ZeroSSL, including renewal); `step-ca`/`cfssl`/HashiCorp Vault PKI (run your own private CA, often issuing short-lived certs); `cert-manager` (Kubernetes automation); AWS ACM/GCP/Azure Key Vault (cloud-managed CAs tied to their load balancers); language libraries (`rcgen` in Rust, Python `cryptography`, Go `crypto/x509`, Java `keytool`) for generating certs programmatically instead of via a CLI step; commercial CAs (DigiCert, GlobalSign, Sectigo) for OV/EV certs needing manual identity vetting.
