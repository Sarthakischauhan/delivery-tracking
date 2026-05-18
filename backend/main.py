import json
import uuid
import random
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from aiokafka import AIOKafkaConsumer

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory database mapping order_id -> driver_id
active_orders = {}

KAFKA_TOPIC = "driver-locations"
KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"

class OrderResponse(BaseModel):
    order_id: str
    assigned_driver: str

@app.post("/api/orders", response_model=OrderResponse)
async def create_order():
    order_id = str(uuid.uuid4())
    assigned_driver = f"driver-{random.randint(1, 5)}"
    active_orders[order_id] = assigned_driver
    return {"order_id": order_id, "assigned_driver": assigned_driver}

async def get_kafka_consumer():
    consumer = AIOKafkaConsumer(
        KAFKA_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest"
    )
    await consumer.start()
    return consumer

@app.get("/api/stream/{order_id}")
async def stream_locations(order_id: str):
    driver_id = active_orders.get(order_id)
    if not driver_id:
        raise HTTPException(status_code=404, detail="Order not found")

    async def event_stream():
        consumer = await get_kafka_consumer()
        try:
            async for msg in consumer:
                print(msg)
                payload = msg.value
                if payload.get("driverId") == driver_id:
                    # Formatting data correctly for Server-Sent Events (SSE)
                    yield f"data: {json.dumps(payload)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            await consumer.stop()

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)