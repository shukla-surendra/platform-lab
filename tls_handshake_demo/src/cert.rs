//! Generates a throwaway self-signed certificate + private key for "localhost",
//! entirely in-memory — no files on disk, no external CA. This is the one part
//! of the demo that is *not* how real TLS works (real certs are signed by a CA
//! the client already trusts); everything downstream of this (the handshake
//! itself) is the real protocol.

use rcgen::{generate_simple_self_signed, CertifiedKey};
use rustls::pki_types::{CertificateDer, PrivateKeyDer, PrivatePkcs8KeyDer};

pub struct LocalhostCert {
    pub cert_der: CertificateDer<'static>,
    pub key_der: PrivateKeyDer<'static>,
}

pub fn generate() -> LocalhostCert {
    let CertifiedKey { cert, key_pair } =
        generate_simple_self_signed(vec!["localhost".to_string()])
            .expect("self-signed cert generation should never fail for a fixed SAN list");

    let cert_der = cert.der().clone();
    let key_der = PrivateKeyDer::Pkcs8(PrivatePkcs8KeyDer::from(key_pair.serialize_der()));

    LocalhostCert { cert_der, key_der }
}
