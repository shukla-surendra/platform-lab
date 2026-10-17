# /// script
# requires-python = ">=3.12"
# dependencies = ["pika>=1.3"]
# ///
"""Publish N events to the 'orders' fanout exchange. Every bound queue gets a copy."""
import sys
import pika

count = int(sys.argv[1]) if len(sys.argv) > 1 else 5

conn = pika.BlockingConnection(pika.ConnectionParameters("localhost"))
ch = conn.channel()
ch.exchange_declare(exchange="orders", exchange_type="fanout")   # fanout = copy to every bound queue

for i in range(1, count + 1):
    body = f"order-{i} placed"
    ch.basic_publish(exchange="orders", routing_key="", body=body)   # routing key is ignored by fanout
    print("published", body)

conn.close()
