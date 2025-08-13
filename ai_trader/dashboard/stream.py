from __future__ import annotations

"""Event streaming utilities (WebSocket + Server Sent Events)."""

import json
import queue
from flask import Response

_event_q: queue.Queue[dict] = queue.Queue(maxsize=10000)

# Optional Socket.IO support -------------------------------------------------
socketio = None
try:  # pragma: no cover
    from flask_socketio import SocketIO

    socketio = SocketIO(message_queue=None, cors_allowed_origins="*")
except Exception:  # pragma: no cover - optional dependency
    socketio = None


def attach_socketio(sio) -> None:
    """Attach a SocketIO instance created by the caller."""

    global socketio
    socketio = sio


def publish_event(kind: str, data: dict) -> None:
    """Publish an event to the internal queue and broadcast via WS if possible."""

    payload = {"kind": kind, "data": data}
    try:
        _event_q.put_nowait(payload)
    except Exception:  # queue full - drop silently
        pass
    if socketio:
        try:
            socketio.emit(f"{kind}_event", payload, namespace="/ws")
        except Exception:  # pragma: no cover - network issues shouldn't crash
            pass


def sse_stream() -> Response:
    """Return a streaming response for Server Sent Events."""

    def gen():
        while True:
            item = _event_q.get()
            yield f"event: {item['kind']}\n"
            yield f"data: {json.dumps(item['data'])}\n\n"

    return Response(gen(), mimetype="text/event-stream")
