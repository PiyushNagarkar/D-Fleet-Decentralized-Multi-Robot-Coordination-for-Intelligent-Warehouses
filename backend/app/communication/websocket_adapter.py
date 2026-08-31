"""WebSocket Transport Adapter for Peer-to-Peer Robot Communication.

Provides a pass-through asynchronous gateway allowing distributed robot instances
to exchange peer-to-peer envelopes over WebSockets.

CRITICAL ARCHITECTURAL MANDATE:
- This is purely passive communication infrastructure.
- It NEVER decides routes, priorities, tasks, or conflict resolutions.
- It simply routes envelopes between connected peer endpoints.
"""

from __future__ import annotations
import asyncio
import json
from typing import Dict, List, Optional, Set, Any
from fastapi import WebSocket, WebSocketDisconnect

from app.robots.message import Message, MessageType


class P2PWebSocketAdapter:
    """Manages direct WebSocket peer connections for autonomous robots."""

    def __init__(self):
        # Active peer sockets: robot_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, robot_id: str, websocket: WebSocket) -> None:
        """Register a connected robot peer."""
        await websocket.accept()
        async with self._lock:
            self.active_connections[robot_id] = websocket

    async def disconnect(self, robot_id: str) -> None:
        """Unregister a disconnected robot peer."""
        async with self._lock:
            if robot_id in self.active_connections:
                del self.active_connections[robot_id]

    async def send_direct_message(self, message: Message) -> bool:
        """Send message directly to recipient robot over WebSocket."""
        recipient = message.recipient
        async with self._lock:
            ws = self.active_connections.get(recipient)

        if ws:
            try:
                await ws.send_text(json.dumps(message.to_dict()))
                return True
            except Exception:
                await self.disconnect(recipient)
                return False
        return False

    async def broadcast_message(self, message: Message) -> int:
        """Broadcast message to all connected peers except sender."""
        sender = message.sender
        async with self._lock:
            peers = [(r_id, ws) for r_id, ws in self.active_connections.items() if r_id != sender]

        sent_count = 0
        for r_id, ws in peers:
            try:
                await ws.send_text(json.dumps(message.to_dict()))
                sent_count += 1
            except Exception:
                await self.disconnect(r_id)

        return sent_count


# Global singleton adapter for FastAPI routing
p2p_ws_adapter = P2PWebSocketAdapter()
