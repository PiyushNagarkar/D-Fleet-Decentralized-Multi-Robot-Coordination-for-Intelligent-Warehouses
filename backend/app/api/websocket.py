"""Dashboard Telemetry WebSocket Gateway.

CRITICAL ARCHITECTURAL MANDATES:
1. This is the DASHBOARD TELEMETRY channel, architecturally distinct from robot-to-robot P2P.
2. Safety Invariant #9: Dashboard commands CANNOT directly determine robot movement, assign tasks,
   or grant reservations. Any inbound client payloads requesting direct control are rejected.
"""

from __future__ import annotations
import asyncio
import json
from typing import Dict, List, Optional, Set, Any
from fastapi import WebSocket, WebSocketDisconnect


class WebSocketTelemetryHub:
    """Manages connected frontend dashboard WebSocket clients and broadcasts simulation state."""

    def __init__(self):
        self.active_clients: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        async with self._lock:
            self.active_clients.add(websocket)

    async def disconnect(self, websocket: WebSocket) -> None:
        async with self._lock:
            if websocket in self.active_clients:
                self.active_clients.remove(websocket)

    async def broadcast(self, payload: Dict[str, Any]) -> int:
        """Broadcast telemetry snapshot to all connected dashboards."""
        async with self._lock:
            clients = list(self.active_clients)

        sent_count = 0
        message_text = json.dumps(payload)
        for client in clients:
            try:
                await client.send_text(message_text)
                sent_count += 1
            except Exception:
                await self.disconnect(client)

        return sent_count

    async def handle_inbound_message(self, websocket: WebSocket, data: str) -> None:
        """Handle inbound message from dashboard client.

        ENFORCES SAFETY INVARIANT #9:
        Rejects any direct control commands (e.g. move robot, assign task, grant reservation).
        """
        try:
            payload = json.loads(data)
        except Exception:
            await websocket.send_text(json.dumps({
                "type": "ERROR",
                "error": "Invalid JSON format",
            }))
            return

        command = payload.get("command") or payload.get("type") or ""
        command_upper = str(command).upper()

        # Check for forbidden direct-control commands (Safety Invariant #9)
        forbidden_commands = {
            "MOVE_ROBOT", "MOVE", "TELEPORT", "SET_POSITION",
            "ASSIGN_TASK", "CLAIM_TASK_FOR_ROBOT",
            "GRANT_RESERVATION", "FORCE_RESERVATION",
        }

        if command_upper in forbidden_commands:
            # Explicitly reject with Safety Invariant explanation
            await websocket.send_text(json.dumps({
                "type": "COMMAND_REJECTED",
                "command": command,
                "error": "Safety Invariant #9 Violated: Dashboard commands cannot directly determine robot movement, assign tasks, or grant reservations in a decentralized system.",
            }))
            return

        # Handle allowed dashboard control signals (e.g., ping, subscription filter)
        if command_upper == "PING":
            await websocket.send_text(json.dumps({"type": "PONG"}))
        else:
            await websocket.send_text(json.dumps({
                "type": "ACK",
                "received_command": command,
            }))


telemetry_hub = WebSocketTelemetryHub()
