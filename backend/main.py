import asyncio
import json
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from redis.asyncio import Redis

from db import assign_next_order, get_order, init_db


DATABASE_PATH = os.getenv("DATABASE_PATH", "/data/delivery.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
STREAM_IDLE_TIMEOUT_SECONDS = int(os.getenv("STREAM_IDLE_TIMEOUT_SECONDS", "30"))
CORS_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5000,http://127.0.0.1:5000",
    ).split(",")
    if origin.strip()
]


class OrderResponse(BaseModel):
    order_id: str
    assigned_driver: str


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(DATABASE_PATH)
    app.state.redis = Redis.from_url(REDIS_URL, decode_responses=True)
    try:
        yield
    finally:
        await app.state.redis.aclose()


app = FastAPI(title="Delivery Tracking API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/orders", response_model=OrderResponse)
async def create_order():
    order = assign_next_order(DATABASE_PATH)
    return {
        "order_id": order["order_id"],
        "assigned_driver": order["driver_id"],
    }


@app.get("/api/orders/{order_id}")
async def read_order(order_id: str):
    order = get_order(DATABASE_PATH, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(order)


@app.get("/api/stream/{order_id}")
async def stream_locations(order_id: str, request: Request):
    order = get_order(DATABASE_PATH, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    channel = f"order:{order_id}:locations"

    async def event_stream():
        pubsub = app.state.redis.pubsub()
        await pubsub.subscribe(channel)
        loop = asyncio.get_running_loop()
        last_event_at: float | None = None
        try:
            yield f"event: ready\ndata: {json.dumps({'orderId': order_id})}\n\n"
            while True:
                if await request.is_disconnected():
                    break

                message = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=15.0,
                )
                if message and message["type"] == "message":
                    last_event_at = loop.time()
                    yield f"data: {message['data']}\n\n"
                else:
                    if (
                        last_event_at is not None
                        and loop.time() - last_event_at >= STREAM_IDLE_TIMEOUT_SECONDS
                    ):
                        payload = {
                            "orderId": order_id,
                            "reason": "stream_idle_timeout",
                        }
                        yield f"event: complete\ndata: {json.dumps(payload)}\n\n"
                        break
                    yield ": keepalive\n\n"
                    await asyncio.sleep(0.1)

        except asyncio.CancelledError:
            print("client disconnected")
            raise 
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
