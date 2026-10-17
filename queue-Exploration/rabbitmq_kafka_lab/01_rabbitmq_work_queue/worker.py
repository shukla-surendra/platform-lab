# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Take jobs from the 'jobs' queue one at a time. Run several of these in separate terminals."""
import sys
import time
import pika

name = sys.argv[1] if len(sys.argv) > 1 else "worker"

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
ch.queue_declare(queue="jobs", durable=True)
ch.basic_qos(prefetch_count=1)    # hold at most 1 unacked job: a busy worker gets no more until it acks

def handle(ch, method, properties, body):
    job = body.decode()
    seconds = int(job.split("(")[1].rstrip("s)"))
    note = "  <- REDELIVERED (a previous worker died before acking)" if method.redelivered else ""
    print(f"[{name}] got  {job}{note}", flush=True)
    time.sleep(seconds)                                # the "work"
    ch.basic_ack(delivery_tag=method.delivery_tag)     # done: RabbitMQ deletes the message now
    print(f"[{name}] done {job}", flush=True)

ch.basic_consume(queue="jobs", on_message_callback=handle)
print(f"[{name}] waiting for jobs. Ctrl+C to stop.", flush=True)
try:
    ch.start_consuming()
except KeyboardInterrupt:
    pass
