"""Working examples of the core cryptographic primitives via `cryptography`
(pyca/cryptography), the standard vetted Python crypto library. Every call
here is "use the library correctly" — never hand-implement the underlying
algorithm math yourself; that's how real vulnerabilities get introduced.

Run: pip install cryptography && python primitives.py
"""
import os

# ---------------------------------------------------------------------------
# AES-GCM (symmetric, AEAD) — encrypts AND authenticates in one call. This is
# the right default over a bare cipher mode (e.g. CBC) plus a bolted-on MAC.
# ---------------------------------------------------------------------------
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

key = AESGCM.generate_key(bit_length=256)      # the one shared secret, both ends
aesgcm = AESGCM(key)
nonce = os.urandom(12)                          # MUST be unique per (key, message) —
                                                 # reuse leaks the authentication key, not just plaintext

ciphertext = aesgcm.encrypt(nonce, b"launch the training run", associated_data=None)
plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
assert plaintext == b"launch the training run"
print("[AES-GCM] round-trip OK")

# AEAD's actual value: decrypt() raises on any tampering — a bare CBC mode
# would silently produce corrupted-but-accepted plaintext instead.
try:
    tampered = ciphertext[:-1] + bytes([ciphertext[-1] ^ 1])
    aesgcm.decrypt(nonce, tampered, associated_data=None)
    raise AssertionError("tampered ciphertext should have been rejected")
except Exception:
    print("[AES-GCM] tampered ciphertext correctly rejected")


# ---------------------------------------------------------------------------
# RSA: encrypt/decrypt — public key encrypts, private key decrypts.
# OAEP padding is not optional: raw/textbook RSA with no padding is broken.
# ---------------------------------------------------------------------------
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes

private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
public_key = private_key.public_key()

message = b"shared AES key goes here"
oaep = padding.OAEP(mgf=padding.MGF1(algorithm=hashes.SHA256()),
                     algorithm=hashes.SHA256(), label=None)
rsa_ciphertext = public_key.encrypt(message, oaep)
rsa_plaintext = private_key.decrypt(rsa_ciphertext, oaep)
assert rsa_plaintext == message
print("[RSA encrypt/decrypt] OK — public encrypts, private decrypts")

# ---------------------------------------------------------------------------
# RSA: sign/verify — the pair run in reverse. Private key signs, public key
# verifies. verify() raises InvalidSignature rather than returning a boolean
# you could forget to check.
# ---------------------------------------------------------------------------
pss = padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH)
signature = private_key.sign(message, pss, hashes.SHA256())
public_key.verify(signature, message, pss, hashes.SHA256())
print("[RSA sign/verify] OK — private signs, public verifies")


# ---------------------------------------------------------------------------
# SHA-256 — one-way, fixed-size digest, no key, not reversible.
# ---------------------------------------------------------------------------
digest = hashes.Hash(hashes.SHA256())
digest.update(b"hello world")
print("[SHA-256]", digest.finalize().hex())


# ---------------------------------------------------------------------------
# HMAC — a keyed hash. Plain hashing alone proves integrity only if you
# already trust the channel; HMAC additionally proves the message came from
# someone holding the shared key.
# ---------------------------------------------------------------------------
from cryptography.hazmat.primitives import hmac

hmac_key = os.urandom(32)                       # shared secret, both sides already hold it

mac = hmac.HMAC(hmac_key, hashes.SHA256())
mac.update(b"a message both sides can authenticate")
tag = mac.finalize()

verifier = hmac.HMAC(hmac_key, hashes.SHA256())
verifier.update(b"a message both sides can authenticate")
verifier.verify(tag)                            # raises InvalidSignature on mismatch
print("[HMAC] tag verified with shared key")


# ---------------------------------------------------------------------------
# Ed25519 — modern EC signature scheme. This exact private.sign()/
# public.verify() pattern is what SSH public-key auth runs under the hood
# (e.g. an AWS EC2 key pair created with type=ed25519).
# ---------------------------------------------------------------------------
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ed_private = Ed25519PrivateKey.generate()
ed_public = ed_private.public_key()
challenge = b"ssh login challenge data"
ed_signature = ed_private.sign(challenge)
ed_public.verify(ed_signature, challenge)
print("[Ed25519] sign/verify OK — same mechanism as SSH pubkey auth")
