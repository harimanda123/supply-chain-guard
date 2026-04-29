"""
In-process SSE event bus.

The pipeline (running in a thread executor) publishes resolution events here.
Connected SSE clients subscribe and receive them in real time.
"""
import asyncio
import json
from typing import AsyncIterator

# event_id -> list of asyncio.Queue subscribers
_subscribers: dict[str, list[asyncio.Queue]] = {}


def publish(event_id: str, payload: dict) -> None:
    """
    Called from a sync context (pipeline thread).
    Puts the payload onto every subscriber queue for this event_id,
    then also onto the wildcard "*" channel for clients watching all events.
    """
    loop = _get_or_create_loop()
    for channel in (event_id, "*"):
        for q in _subscribers.get(channel, []):
            loop.call_soon_threadsafe(q.put_nowait, payload)


def _get_or_create_loop() -> asyncio.AbstractEventLoop:
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop


async def subscribe(channel: str) -> AsyncIterator[str]:
    """
    Async generator — yields SSE-formatted strings for the given channel.
    channel is either a specific event_id or "*" for all events.
    """
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.setdefault(channel, []).append(q)
    try:
        while True:
            payload = await q.get()
            yield f"data: {json.dumps(payload)}\n\n"
    finally:
        _subscribers[channel].remove(q)
        if not _subscribers[channel]:
            del _subscribers[channel]
