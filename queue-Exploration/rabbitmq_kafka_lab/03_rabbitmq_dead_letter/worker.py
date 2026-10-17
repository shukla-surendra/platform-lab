# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Process payments. A BROKEN payment fails every time and is requeued until RabbitMQ gives up on it."""
import time
import pika

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
ch.basic_qos(prefetch_count=1)

def handle(ch, method, properties, body):
    msg = body.decode()
    tries = (properties.headers or {}).get("x-delivery-count", 0)   # set by quorum queues on redelivery
    if "BROKEN" in msg:
        print(f"FAIL {msg}  (redelivery #{tries}) -> nack, requeue", flush=True)
        time.sleep(0.5)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # "couldn't do it, put it back"
    else:
        print(f"ok   {msg}", flush=True)
        ch.basic_ack(delivery_tag=method.delivery_tag)

ch.basic_consume(queue="payments", on_message_callback=handle)
print("processing payments. Ctrl+C to stop.", flush=True)
try:
    ch.start_consuming()
except KeyboardInterrupt:
    pass
