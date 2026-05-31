import asyncio
import json
import os

from aiokafka import AIOKafkaConsumer
from redis.asyncio import Redis

from db import get_active_orders_for_driver, init_db


KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "driver-locations")
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
KAFKA_GROUP_ID = os.getenv("KAFKA_GROUP_ID", "tracking-relay")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/delivery.db")


def decode_json(payload: bytes):
    return json.loads(payload.decode("utf-8"))


async def run():
    init_db(DATABASE_PATH)
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=KAFKA_GROUP_ID,
        auto_offset_reset="latest",
        enable_auto_commit=True,
        value_deserializer=decode_json,
    )
    while True:
        try:
            await consumer.start()
            break
        except Exception:
            await asyncio.sleep(2)

    try:
        async for message in consumer:
            event = message.value
            order_id = event.get("orderId")
            if order_id:
                channel = f"order:{order_id}:locations"
                await redis.publish(channel, json.dumps(event))
                continue

            driver_id = event.get("driverId")
            if not driver_id:
                continue

            for order in get_active_orders_for_driver(DATABASE_PATH, driver_id):
                order_event = {
                    **event,
                    "orderId": order["order_id"],
                }
                channel = f"order:{order['order_id']}:locations"
                await redis.publish(channel, json.dumps(order_event))
    finally:
        await consumer.stop()
        await redis.aclose()


if __name__ == "__main__":
    asyncio.run(run())
