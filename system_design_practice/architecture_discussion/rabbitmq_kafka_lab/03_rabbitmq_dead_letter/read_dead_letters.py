# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Print (and remove) everything in the dead-letter queue, with RabbitMQ's note on why it died."""
import pika

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
while True:
    method, properties, body = ch.basic_get(queue="payments.dead", auto_ack=True)
    if method is None:
        break
    death = (properties.headers or {}).get("x-death", [{}])[0]
    print(f"dead: {body.decode()}  reason={death.get('reason')}  from queue={death.get('queue')}")
conn.close()
