"""
WebSocket connection manager for multiplayer games
Handles connections, rooms, and message broadcasting
"""
from typing import Dict, Set, Optional
from fastapi import WebSocket
from collections import defaultdict
import json
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for multiplayer games"""

    def __init__(self):
        # Active connections: {user_id: WebSocket}
        self.active_connections: Dict[int, WebSocket] = {}

        # Room connections: {room_code: Set[user_id]}
        self.room_connections: Dict[str, Set[int]] = defaultdict(set)

        # User to room mapping: {user_id: room_code}
        self.user_rooms: Dict[int, str] = {}

    async def connect(self, user_id: int, websocket: WebSocket):
        """
        Accept a new WebSocket connection

        Args:
            user_id: User ID
            websocket: WebSocket connection
        """
        await websocket.accept()
        self.active_connections[user_id] = websocket
        logger.info(f"User {user_id} connected via WebSocket")

    def disconnect(self, user_id: int):
        """
        Remove a WebSocket connection

        Args:
            user_id: User ID
        """
        # Remove from active connections
        if user_id in self.active_connections:
            del self.active_connections[user_id]

        # Remove from room if in one
        if user_id in self.user_rooms:
            room_code = self.user_rooms[user_id]
            self.leave_room(user_id, room_code)

        logger.info(f"User {user_id} disconnected")

    def join_room(self, user_id: int, room_code: str):
        """
        Add user to a game room

        Args:
            user_id: User ID
            room_code: Room code
        """
        # Leave previous room if in one
        if user_id in self.user_rooms:
            old_room = self.user_rooms[user_id]
            self.leave_room(user_id, old_room)

        # Join new room
        self.room_connections[room_code].add(user_id)
        self.user_rooms[user_id] = room_code
        logger.info(f"User {user_id} joined room {room_code}")

    def leave_room(self, user_id: int, room_code: str):
        """
        Remove user from a game room

        Args:
            user_id: User ID
            room_code: Room code
        """
        if room_code in self.room_connections:
            self.room_connections[room_code].discard(user_id)

            # Clean up empty rooms
            if len(self.room_connections[room_code]) == 0:
                del self.room_connections[room_code]

        if user_id in self.user_rooms:
            del self.user_rooms[user_id]

        logger.info(f"User {user_id} left room {room_code}")

    async def send_personal_message(self, message: dict, user_id: int):
        """
        Send message to a specific user

        Args:
            message: Message data (will be JSON serialized)
            user_id: Target user ID
        """
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)

    async def broadcast_to_room(
        self,
        room_code: str,
        message: dict,
        exclude_user: Optional[int] = None
    ):
        """
        Broadcast message to all users in a room

        Args:
            room_code: Room code
            message: Message data (will be JSON serialized)
            exclude_user: Optional user ID to exclude from broadcast
        """
        if room_code not in self.room_connections:
            return

        disconnected_users = []

        for user_id in self.room_connections[room_code]:
            if exclude_user and user_id == exclude_user:
                continue

            if user_id in self.active_connections:
                try:
                    websocket = self.active_connections[user_id]
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {e}")
                    disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)

    async def broadcast_to_all(self, message: dict):
        """
        Broadcast message to all connected users

        Args:
            message: Message data (will be JSON serialized)
        """
        disconnected_users = []

        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected_users.append(user_id)

        # Clean up disconnected users
        for user_id in disconnected_users:
            self.disconnect(user_id)

    def get_room_users(self, room_code: str) -> Set[int]:
        """
        Get all user IDs in a room

        Args:
            room_code: Room code

        Returns:
            Set of user IDs
        """
        return self.room_connections.get(room_code, set())

    def get_user_room(self, user_id: int) -> Optional[str]:
        """
        Get the room code a user is in

        Args:
            user_id: User ID

        Returns:
            Room code or None
        """
        return self.user_rooms.get(user_id)

    def is_user_connected(self, user_id: int) -> bool:
        """
        Check if user is connected

        Args:
            user_id: User ID

        Returns:
            True if connected
        """
        return user_id in self.active_connections


# Global connection manager instance
manager = ConnectionManager()
