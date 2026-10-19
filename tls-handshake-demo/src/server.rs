//! The server side of the handshake, driven by hand rather than hidden behind
//! a single `accept()` call, so every round trip of the TLS record layer is
//! visible.
//!
//! A TLS connection is two layers:
//!   1. The *record layer*: opaque length-prefixed byte blobs going back and
//!      forth over the raw TCP socket. This is all a plain `TcpStream` ever
//!      sees.
//!   2. The *handshake state machine* (`rustls::ServerConnection`), which
//!      consumes record-layer bytes via `read_tls` + `process_new_packets`,
//!      and produces record-layer bytes to send via `write_tls`.
//!
//! The loop below is exactly that state machine being fed, one record at a
//! time, until it reports the handshake is done.

use std::io::Write as _;
use std::net::TcpStream;
use std::sync::Arc;

use rustls::{ServerConfig, ServerConnection};

use crate::cert::LocalhostCert;

pub fn build_config(cert: &LocalhostCert) -> Arc<ServerConfig> {
    let config = ServerConfig::builder()
        .with_no_client_auth()
        .with_single_cert(vec![cert.cert_der.clone()], cert.key_der.clone_key())
        .expect("cert + key were just generated together, so they must match");
    Arc::new(config)
}

pub fn handle_connection(mut sock: TcpStream, config: Arc<ServerConfig>) {
    println!("[server] accepted raw TCP connection from {:?}", sock.peer_addr());

    let mut conn = ServerConnection::new(config).expect("valid ServerConfig");

    // --- Phase 1: drive the handshake state machine over the raw socket ---
    let mut round = 0;
    while conn.is_handshaking() {
        round += 1;

        if conn.wants_write() {
            let n = conn.write_tls(&mut sock).expect("write_tls to a live socket");
            println!("[server] round {round}: wrote {n} handshake bytes to the wire");
        }

        if conn.wants_read() {
            let n = conn.read_tls(&mut sock).expect("read_tls from a live socket");
            println!("[server] round {round}: read {n} raw bytes from the wire");
            if n == 0 {
                println!("[server] peer closed the connection mid-handshake");
                return;
            }
            // Turns the raw bytes just read into decoded handshake messages,
            // advancing the state machine (parses ClientHello, verifies the
            // Finished MAC, derives keys, etc. — whatever the next expected
            // message is).
            if let Err(e) = conn.process_new_packets() {
                println!("[server] handshake error: {e}");
                // rustls still wants us to flush an alert it queued.
                let _ = conn.write_tls(&mut sock);
                return;
            }
        }
    }

    println!(
        "[server] handshake complete: {:?} / {:?}",
        conn.protocol_version(),
        conn.negotiated_cipher_suite().map(|cs| cs.suite())
    );

    // --- Phase 2: application data, over the now-encrypted channel ---
    // `rustls::Stream` wraps the connection + socket so ordinary read/write
    // calls transparently encrypt/decrypt — this is what real server code
    // uses after the handshake, instead of the manual loop above.
    let mut tls_stream = rustls::Stream::new(&mut conn, &mut sock);

    let mut buf = [0u8; 1024];
    match std::io::Read::read(&mut tls_stream, &mut buf) {
        Ok(0) => println!("[server] client closed the connection"),
        Ok(n) => {
            let msg = String::from_utf8_lossy(&buf[..n]);
            println!("[server] decrypted application data from client: {msg:?}");
            let reply = format!("echo: {msg}");
            tls_stream
                .write_all(reply.as_bytes())
                .expect("write application data");
            println!("[server] sent encrypted reply: {reply:?}");
        }
        Err(e) => println!("[server] application read error: {e}"),
    }

    let _ = conn.send_close_notify();
    let _ = conn.write_tls(&mut sock);
    println!("[server] sent close_notify, connection done");
}
