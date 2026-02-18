#!/usr/bin/env python3
"""
PriusPilot WebSocket Bridge
============================
Bridges flowpilot's ZMQ pub/sub messages to WebSocket for external visualization.

Subscribes to key ZMQ topics on the flowpilot device and rebroadcasts them as
JSON over WebSocket so any browser or app on the local network can consume them.

Usage:
  # On the flowpilot device (Pocophone):
  python bridge_ws.py

  # Or from another machine pointing to the flowpilot device:
  DEVICE_ADDR=192.168.1.100 python bridge_ws.py

  # Custom WebSocket port:
  WS_PORT=8867 python bridge_ws.py

Clients connect to ws://<bridge-ip>:8867 and receive JSON messages like:
  {"topic": "modelV2", "timestamp": 1234567890123, "data": {...}}

Clients can also send a subscription filter:
  {"subscribe": ["modelV2", "carState", "radarState"]}

If no filter is sent, all topics are broadcast to the client.
"""

import os
import sys
import json
import time
import asyncio
import signal
import threading
from collections import defaultdict

# Add flowpilot to path
BASEDIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASEDIR)
os.chdir(BASEDIR)

# Ensure ZMQ TCP protocol
os.environ.setdefault("ZMQ_MESSAGING_PROTOCOL", "TCP")

import cereal.messaging as messaging
from cereal.services import service_list

# WebSocket port - configurable via env
WS_PORT = int(os.environ.get("WS_PORT", "8867"))
WS_HOST = os.environ.get("WS_HOST", "0.0.0.0")

# Topics relevant for visualization - grouped by purpose
VISUALIZATION_TOPICS = [
    # Model output: lane lines, road edges, lead cars, path prediction
    "modelV2",
    # Vehicle state: speed, steering angle, brake, gas, cruise state
    "carState",
    # Radar: lead car tracking, radar objects
    "radarState",
    # Controls: engaged state, alerts, lateral/longitudinal state
    "controlsState",
    # Planning: lateral plan (steering path), longitudinal plan (speed plan)
    "lateralPlan",
    "longitudinalPlan",
    # Calibration: camera-to-road rotation for projection
    "liveCalibration",
    # Car events: warnings, errors, engagement state
    "carEvents",
    # Device state: temps, battery, system health
    "deviceState",
    # Car parameters: car fingerprint, capabilities
    "carParams",
    # Live location: GPS, orientation
    "liveLocationKalman",
    # Driver monitoring
    "driverMonitoringState",
    # Panda state
    "pandaStates",
]


def capnp_to_dict(reader):
    """Convert a capnp reader to a JSON-serializable dict."""
    return _convert(reader)


def _convert(obj):
    """Recursively convert capnp objects to JSON-serializable types."""
    if hasattr(obj, 'to_dict'):
        try:
            return obj.to_dict()
        except Exception:
            pass

    if isinstance(obj, (bool, int, float, str, type(None))):
        return obj

    if isinstance(obj, bytes):
        return None  # skip raw binary blobs

    if isinstance(obj, (list, tuple)):
        return [_convert(item) for item in obj]

    if hasattr(obj, 'items'):
        return {k: _convert(v) for k, v in obj.items()}

    # capnp list-like objects
    if hasattr(obj, '__len__') and hasattr(obj, '__getitem__'):
        try:
            return [_convert(obj[i]) for i in range(len(obj))]
        except Exception:
            pass

    return str(obj)


class ZMQBridgeWorker(threading.Thread):
    """Background thread that subscribes to ZMQ and queues messages."""

    def __init__(self, topics, addr="127.0.0.1"):
        super().__init__(daemon=True)
        self.topics = topics
        self.addr = addr
        self.latest = {}  # topic -> latest JSON-serializable data
        self.lock = threading.Lock()
        self.running = True

    def run(self):
        sm = messaging.SubMaster(self.topics, addr=self.addr)

        while self.running:
            sm.update(100)
            updated = {}

            for topic in self.topics:
                if sm.updated[topic]:
                    try:
                        data = capnp_to_dict(sm[topic])
                        msg = {
                            "topic": topic,
                            "timestamp": sm.logMonoTime[topic],
                            "valid": sm.valid[topic],
                            "data": data,
                        }
                        updated[topic] = msg
                    except Exception as e:
                        print(f"Error converting {topic}: {e}")

            if updated:
                with self.lock:
                    self.latest.update(updated)

    def get_latest(self):
        with self.lock:
            snapshot = dict(self.latest)
        return snapshot

    def stop(self):
        self.running = False


class WebSocketBridge:
    """WebSocket server that broadcasts ZMQ data to connected clients."""

    def __init__(self, worker):
        self.worker = worker
        self.clients = {}  # websocket -> set of subscribed topics (empty = all)

    async def handler(self, websocket):
        """Handle a WebSocket client connection."""
        client_addr = websocket.remote_address
        print(f"Client connected: {client_addr}")
        self.clients[websocket] = set()  # empty = subscribe to all

        try:
            # Start sending task
            send_task = asyncio.create_task(self._send_loop(websocket))

            # Listen for client messages (subscription filters)
            async for message in websocket:
                try:
                    msg = json.loads(message)
                    if "subscribe" in msg:
                        topics = set(msg["subscribe"])
                        self.clients[websocket] = topics
                        print(f"Client {client_addr} subscribed to: {topics}")
                        # Send confirmation
                        await websocket.send(json.dumps({
                            "type": "subscribed",
                            "topics": list(topics)
                        }))
                    elif "ping" in msg:
                        await websocket.send(json.dumps({"type": "pong"}))
                    elif msg.get("type") == "get_topics":
                        await websocket.send(json.dumps({
                            "type": "available_topics",
                            "topics": VISUALIZATION_TOPICS,
                            "ports": {t: service_list[t].port for t in VISUALIZATION_TOPICS
                                      if t in service_list}
                        }))
                except json.JSONDecodeError:
                    pass

        except Exception as e:
            print(f"Client {client_addr} error: {e}")
        finally:
            send_task.cancel()
            del self.clients[websocket]
            print(f"Client disconnected: {client_addr}")

    async def _send_loop(self, websocket):
        """Send ZMQ data to a WebSocket client at ~20Hz."""
        prev_timestamps = {}
        while True:
            try:
                latest = self.worker.get_latest()
                subs = self.clients.get(websocket, set())

                batch = []
                for topic, msg in latest.items():
                    # Filter by subscription
                    if subs and topic not in subs:
                        continue
                    # Only send if updated since last send
                    ts = msg["timestamp"]
                    if prev_timestamps.get(topic) == ts:
                        continue
                    prev_timestamps[topic] = ts
                    batch.append(msg)

                if batch:
                    await websocket.send(json.dumps({
                        "type": "batch",
                        "count": len(batch),
                        "messages": batch,
                    }))

                await asyncio.sleep(0.05)  # 20 Hz
            except asyncio.CancelledError:
                return
            except Exception:
                return

    async def serve(self):
        """Start the WebSocket server."""
        import websockets

        print(f"WebSocket bridge starting on ws://{WS_HOST}:{WS_PORT}")
        print(f"Subscribing to {len(VISUALIZATION_TOPICS)} ZMQ topics")
        print(f"ZMQ target: {os.environ.get('DEVICE_ADDR', '127.0.0.1')}")

        async with websockets.serve(self.handler, WS_HOST, WS_PORT):
            print(f"Bridge ready. Connect clients to ws://<this-ip>:{WS_PORT}")
            await asyncio.Future()  # run forever


def main():
    addr = os.environ.get("DEVICE_ADDR", "127.0.0.1")

    # Filter to only topics that exist in service_list
    topics = [t for t in VISUALIZATION_TOPICS if t in service_list]
    print(f"Starting ZMQ subscriber for {len(topics)} topics -> {addr}")

    worker = ZMQBridgeWorker(topics, addr=addr)
    worker.start()

    bridge = WebSocketBridge(worker)

    def signal_handler(sig, frame):
        print("\nShutting down...")
        worker.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    asyncio.run(bridge.serve())


if __name__ == "__main__":
    main()
