# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Send N jobs to the 'jobs' queue. Job i pretends to take (i % 3) + 1 seconds."""
import sys
import pika

count = int(sys.argv[1]) if len(sys.argv) > 1 else 10

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
ch.queue_declare(queue="jobs", durable=True)          # survives a broker restart

for i in range(1, count + 1):
    body = f"job-{i} ({i % 3 + 1}s)"
    ch.basic_publish(
        exchange="",                                   # default exchange: routes by queue name
        routing_key="jobs",
        body=body,
        properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent),
    )
    print("sent", body)

conn.close()
