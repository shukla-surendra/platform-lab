# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Create a queue with a retry limit and a dead-letter queue, then send 5 payments (one is broken)."""
import pika

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()

# Where failed messages end up
ch.exchange_declare(exchange="payments.dlx", exchange_type="fanout", durable=True)
ch.queue_declare(queue="payments.dead", durable=True)
ch.queue_bind(exchange="payments.dlx", queue="payments.dead")

# The main queue: a quorum queue (replicated, the recommended type) that gives up after 3 redeliveries
ch.queue_declare(queue="payments", durable=True, arguments={
    "x-queue-type": "quorum",
    "x-delivery-limit": 3,                       # after 3 redeliveries ...
    "x-dead-letter-exchange": "payments.dlx",    # ... send it here instead of retrying forever
})

for body in ["pay-1 $10", "pay-2 $25", "pay-3 BROKEN", "pay-4 $40", "pay-5 $5"]:
    ch.basic_publish(exchange="", routing_key="payments", body=body,
                     properties=pika.BasicProperties(delivery_mode=pika.DeliveryMode.Persistent))
    print("sent", body)
conn.close()
