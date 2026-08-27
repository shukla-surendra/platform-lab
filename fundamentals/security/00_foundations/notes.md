Symmetric key cryptography (SAME key both ends — one shared secret encrypts AND decrypts)

→ AES = the standard. Fast, because it's just one key, no heavy math.
   (wifi WPA2/3, VPN tunnels, messaging app content, disk encryption on laptop — all bulk data)
→ Problem it does NOT solve: how do 2 people who never met agree on that shared key
   without someone snooping the exchange? → this is exactly what asymmetric/DH fixes below.
→ AES isn't just "one algorithm" — the MODE matters:
   - ECB → bad, don't use (same plaintext block → same ciphertext block, patterns leak)
   - CBC → ok, but only confidentiality, no tamper-check on its own
   - GCM → the right default today (AES-GCM) — encrypts AND authenticates in one go (AEAD)

Asymmetric key cryptography (DIFFERENT key each end — a PAIR: public + private) (slower — real math cost, ~100-1000x)
→ RSA and elliptic curve cryptography (ECC/ECDSA) are the two families
→ ECC does the same job as RSA with a MUCH smaller key (256-bit ECC ≈ 3072-bit RSA) → faster, why new stuff defaults to ECC

→ Public key: anyone can have it, anyone can use it to ENCRYPT (or to verify a signature)
→ Private key: only the owner has it, used to DECRYPT (or to CREATE a signature)
   — key rule: public key never decrypts, private key never gets shared. that's the whole model.

→ Digital signature = the pair used BACKWARDS from encryption:
   - Private key SIGNS (owner proves "this came from me, unaltered")
   - Public key VERIFIES the signature — anyone can check it, no secret needed to check
   - in practice you sign a HASH of the message, not the whole message (hash first, then sign the hash — faster)

→ Diffie-Hellman (DH/ECDH): the actual trick that lets 2 strangers build a shared secret
   over a public line without ever sending the secret itself. This is what TLS uses to
   bootstrap — asymmetric math only for this handshake step, then switches to fast
   symmetric (AES) for the actual data. Best of both: solves key exchange, keeps bulk speed.

Hashing (NOT encryption — one-way, no key, can't reverse it)
→ SHA-256 = the safe default today. MD5 and SHA-1 = broken, don't use.
→ used for: integrity check (does file match its checksum), password storage (store hash not password)
→ password hashing needs MORE than plain SHA-256 → salt + slow-on-purpose (bcrypt/Argon2)
   otherwise attacker precomputes a rainbow table and cracks every account at once

<===

PEM = NOT "a public key" — it's a FILE FORMAT/ENCODING (Base64 text with
-----BEGIN .....----- / -----END....----- wrapper). A .pem file can hold:
   - a public key
   - a private key
   - a certificate
   - a whole cert chain
→ what's actually inside is what matters, not the fact that it's ".pem"
→ common real-world extensions: .key (private key), .crt/.cer (certificate), .csr (cert
   signing request — sent TO a CA to get a cert back)

Open questions to come back to:
→ how does a cert chain actually prove trust up to a root CA?
→ HMAC vs signature — when do you use which?

===>

EC2 login via key pair — real-world use of the asymmetric stuff above

1. Launch time: pick/create a key pair in AWS console → AWS generates an RSA
   (or ED25519) PAIR right then.
   → PUBLIC key: AWS keeps it, auto-injects into the instance itself
     (~/.ssh/authorized_keys for ec2-user/ubuntu/admin, via the AMI's boot script)
   → PRIVATE key: AWS gives YOU the .pem file to download ONCE. AWS does not
     keep a copy after that → lose it = locked out, no "forgot password" reset.

   real example — EC2 console "Key Pairs" page only ever shows the PUBLIC half:
     Name: mini-llm-gpu-key       ← label, picked at launch wizard
     Type: ed25519                ← modern EdDSA/ECC, not RSA (fixes ECDSA's
                                     RNG footgun — deterministic signing)
     Fingerprint: DfWjlb3...      ← a HASH of the public key (see Hashing
                                     section above), lets you confirm "is this
                                     the key I think it is" w/o comparing the
                                     whole blob
     ID: key-0ba802106daa677ee    ← just AWS's resource ID for this object
                                     (like an instance/volume ID) — NOT crypto
                                     material, used in CLI/Terraform/IAM refs
   → private key is NOT listed anywhere here — confirms AWS genuinely never
     kept a copy, this page is 100% public-side bookkeeping.

   "Type" = which algorithm family the key's math runs on. Picked ONCE at
   creation, can't be changed after — different type = generate a whole new
   pair, not a setting to flip.
     RSA:     factoring-based, needs 2048-bit for decent security, slower,
              private key file = "-----BEGIN RSA PRIVATE KEY-----"
     ED25519: EC-based (EdDSA/Curve25519), only needs 256-bit for the SAME
              security level → faster math, smaller key. private key file =
              "-----BEGIN OPENSSH PRIVATE KEY-----" (different container,
              PEM/PKCS1 wasn't built for EdDSA)
   → same RSA-vs-ECC trade already in the Asymmetric section above, just
     applied to "which algorithm signs my SSH login" instead of "which
     algorithm signs a TLS cert." AWS now recommends ED25519 as the default
     for new keys; RSA still fully supported, mainly there for
     older-client compatibility.

2. chmod 400 mykey.pem — SSH will straight-up refuse the key if permissions
   are too open (protects it from other local users on your machine).

3. Login: ssh -i mykey.pem ec2-user@<public-ip>
   → this is NOT "decrypt something to prove identity" — modern SSH pubkey auth
     is signature-based, same mechanism as the Digital Signature note above:
     client signs a piece of session data with the PRIVATE key, server checks
     it against the PUBLIC key already sitting in authorized_keys.
   → no password ever goes over the wire.

4. If you lose the .pem: can't SSH in the normal way. Recovery options:
   → detach the root EBS volume, attach to another instance, manually drop a
     new public key into authorized_keys, reattach
   → or just use EC2 Instance Connect / SSM Session Manager instead — browser/CLI
     based, doesn't need the .pem at all (IAM permissions gate access instead)

→ so the whole EC2 key-pair model = the exact public-encrypts/verifies,
  private-decrypts/signs split from the Asymmetric section above, just applied
  to "prove you're allowed to log into this box" instead of "encrypt a message."

===>

How TLS + SSH actually use asymmetric crypto — same 3-part pattern in BOTH

Neither one asymmetrically encrypts the actual data. Asymmetric crypto only
does 2 jobs (identity + key exchange), then both HAND OFF to fast symmetric
(AES/ChaCha20) for the real traffic. 3 steps, always in this order:

1. IDENTITY — prove "you're really talking to who you think," via signature
   → TLS: server sends its CERTIFICATE (its public key + a CA's SIGNATURE
     over it). Client checks the signature chain up to a root CA it already
     trusts → proves this public key really belongs to this domain.
   → SSH: server has its own long-term HOST key pair. First connect =
     "authenticity of host can't be established, fingerprint is X" (that
     fingerprint = the server's public host key). You confirm it once →
     saved to known_hosts. Every later connect, server SIGNS with its private
     host key, your client checks against the saved public key → catches a
     MITM swapping in a fake server.
   → (SSH also does this in the OTHER direction for YOU — see EC2 section
     above: your private key signs, authorized_keys public key verifies.)

2. KEY EXCHANGE — agree on a shared secret w/o ever sending it
   → both use (EC)Diffie-Hellman here (see DH note above) — NOT RSA-encrypt-
     the-session-key like old-school TLS used to. Client + server each throw
     in a public DH value, both independently compute the SAME shared secret.
   → do this with a FRESH (ephemeral) key pair per session = forward secrecy:
     even if the long-term identity key leaks later, past sessions' secrets
     can't be rebuilt from it, because they were never derived from it.

3. SWITCH TO SYMMETRIC — shared secret from step 2 → derives an AES (or
   ChaCha20) key → ALL actual data (the webpage, the SSH terminal session)
   flows through that. This is the ONLY reason TLS/SSH are fast enough to be
   usable — asymmetric math on every byte would be way too slow.

→ one-line version: identity = signature, key exchange = DH, bulk data =
  symmetric. Same 3 moves, TLS and SSH just wrap them differently.

===>

Python examples — the primitives above, actually run (all tested, all pass)
using `cryptography` (pip install cryptography) — the standard vetted lib.
NEVER hand-roll the actual algorithm math yourself (see "rolling your own
crypto" failure mode in tutorial.md) — every example below is "call the
library correctly," not "implement AES."

--- AES-GCM (symmetric, AEAD — the right default from the AES section above) ---

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    import os

    key = AESGCM.generate_key(bit_length=256)   # the ONE shared secret
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)                       # MUST be unique per (key, msg) — reuse = broken, see notes above

    ciphertext = aesgcm.encrypt(nonce, b"launch the training run", associated_data=None)
    plaintext  = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    # tamper the ciphertext and decrypt() raises — THIS is what "authenticated" in
    # AEAD actually buys you: CBC would've silently produced corrupted garbage instead.

--- RSA: encrypt/decrypt (public encrypts, private decrypts) ---

    from cryptography.hazmat.primitives.asymmetric import rsa, padding
    from cryptography.hazmat.primitives import hashes

    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    ct = public_key.encrypt(b"shared AES key goes here",
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    pt = private_key.decrypt(ct,
        padding.OAEP(mgf=padding.MGF1(hashes.SHA256()), algorithm=hashes.SHA256(), label=None))
    # OAEP padding = not optional. raw/textbook RSA with no padding is broken —
    # this is exactly the "misuse pattern" the top of Crypto Essentials warns about.

--- RSA: sign/verify (private signs, public verifies — from Digital Signature note) ---

    signature = private_key.sign(message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    public_key.verify(signature, message,
        padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
        hashes.SHA256())
    # verify() raises InvalidSignature if it doesn't match — no return-True/False to forget to check

--- SHA-256 hashing ---

    from cryptography.hazmat.primitives import hashes
    digest = hashes.Hash(hashes.SHA256())
    digest.update(b"hello world")
    digest.finalize().hex()   # one-way, fixed size, no key — see Hashing section above

--- HMAC (keyed hash — proves WHO sent it, plain hashing alone can't) ---

    from cryptography.hazmat.primitives import hmac, hashes
    import os

    hmac_key = os.urandom(32)                    # SHARED secret both sides already hold
    mac = hmac.HMAC(hmac_key, hashes.SHA256())
    mac.update(b"a message both sides can authenticate")
    tag = mac.finalize()
    # receiver rebuilds HMAC with the SAME key + message, calls .verify(tag) — raises if wrong

--- Ed25519 (same TYPE as your real mini-llm-gpu-key — SSH pubkey auth mechanism) ---

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

    ed_private = Ed25519PrivateKey.generate()
    ed_public = ed_private.public_key()
    signature = ed_private.sign(b"ssh login challenge data")
    ed_public.verify(signature, b"ssh login challenge data")
    # THIS call, private.sign() + public.verify(), is literally what happens (with your
    # actual key, not a random one) every time you `ssh -i mykey.pem ec2-user@...`
