# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Subscribe to the 'orders' exchange with a private queue. Run several with different names."""
import sys
import pika

name = sys.argv[1] if len(sys.argv) > 1 else "subscriber"

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
ch.exchange_declare(exchange="orders", exchange_type="fanout")

# A private queue just for this subscriber. exclusive=True: deleted when this script stops.
q = ch.queue_declare(queue="", exclusive=True).method.queue
ch.queue_bind(exchange="orders", queue=q)

def handle(ch, method, properties, body):
    print(f"[{name}] {body.decode()}", flush=True)

ch.basic_consume(queue=q, on_message_callback=handle, auto_ack=True)
print(f"[{name}] listening on private queue {q}. Ctrl+C to stop.", flush=True)
try:
    ch.start_consuming()
except KeyboardInterrupt:
    pass
