//! The client side, mirroring `server.rs`: same manual record-layer loop,
//! so you can diff the two files and see that a TLS handshake is symmetric
//! at the wire level even though client and server do different crypto work
//! inside `process_new_packets`.

use std::io::Write as _;
use std::net::TcpStream;
use std::sync::Arc;

use rustls::pki_types::{CertificateDer, ServerName};
use rustls::{ClientConfig, ClientConnection, RootCertStore};

pub fn build_config(trusted_cert: &CertificateDer<'static>) -> Arc<ClientConfig> {
    // In real TLS, `root_store` would be the OS/browser's bundle of CA certs.
    // Here we trust exactly one cert: the self-signed one the server just
    // generated for itself — the smallest possible trust store that still
    // makes certificate *verification* real rather than skipped.
    let mut root_store = RootCertStore::empty();
    root_store
        .add(trusted_cert.clone())
        .expect("adding a well-formed cert to the root store");

    let config = ClientConfig::builder()
        .with_root_certificates(root_store)
        .with_no_client_auth();
    Arc::new(config)
}

pub fn connect_and_echo(addr: std::net::SocketAddr, config: Arc<ClientConfig>, message: &str) {
    let server_name = ServerName::try_from("localhost").expect("valid DNS name");
    let mut conn = ClientConnection::new(config, server_name).expect("valid ClientConfig");

    let mut sock = TcpStream::connect(addr).expect("connect to the server's TCP listener");
    println!("[client] opened raw TCP connection to {addr}");

    // --- Phase 1: drive the handshake state machine over the raw socket ---
    let mut round = 0;
    while conn.is_handshaking() {
        round += 1;

        if conn.wants_write() {
            let n = conn.write_tls(&mut sock).expect("write_tls to a live socket");
            println!("[client] round {round}: wrote {n} handshake bytes to the wire");
        }

        if conn.wants_read() {
            let n = conn.read_tls(&mut sock).expect("read_tls from a live socket");
            println!("[client] round {round}: read {n} raw bytes from the wire");
            if n == 0 {
                println!("[client] server closed the connection mid-handshake");
                return;
            }
            // Where the real work happens: parse ServerHello, verify the
            // certificate chain against `root_store`, check the signature
            // over the transcript, derive traffic keys, verify Finished.
            if let Err(e) = conn.process_new_packets() {
                println!("[client] handshake error: {e}");
                return;
            }
        }
    }

    println!(
        "[client] handshake complete: {:?} / {:?}",
        conn.protocol_version(),
        conn.negotiated_cipher_suite().map(|cs| cs.suite())
    );
    println!(
        "[client] server identity verified against our 1-cert trust store — no MITM swapped the cert in transit"
    );

    // --- Phase 2: application data, over the now-encrypted channel ---
    let mut tls_stream = rustls::Stream::new(&mut conn, &mut sock);
    tls_stream
        .write_all(message.as_bytes())
        .expect("write application data");
    println!("[client] sent encrypted application data: {message:?}");

    let mut buf = [0u8; 1024];
    match std::io::Read::read(&mut tls_stream, &mut buf) {
        Ok(0) => println!("[client] server closed the connection"),
        Ok(n) => {
            let reply = String::from_utf8_lossy(&buf[..n]);
            println!("[client] decrypted reply from server: {reply:?}");
        }
        Err(e) => println!("[client] application read error: {e}"),
    }
}
