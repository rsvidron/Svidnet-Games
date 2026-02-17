"""
WebSocket endpoints for multiplayer game rooms
Handles real-time game events, buzzer system, live scoring
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import json
import logging

from .manager import manager
from ...db.session import get_async_db
from ...core.security import decode_token
from ...models.user import User
from ...models.game import GameRoom
from sqlalchemy import select

router = APIRouter()
logger = logging.getLogger(__name__)


async def get_user_from_token(token: str, db: AsyncSession) -> Optional[User]:
    """
    Verify WebSocket token and get user

    Args:
        token: JWT token
        db: Database session

    Returns:
        User or None if invalid
    """
    payload = decode_token(token)
    if not payload:
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


@router.websocket("/game/{room_code}")
async def game_room_websocket(
    websocket: WebSocket,
    room_code: str,
    token: str = Query(...),
    db: AsyncSession = Depends(get_async_db)
):
    """
    WebSocket endpoint for game rooms

    Handles:
    - Player connections
    - Game state updates
    - Buzzer system for Jeopardy
    - Live scoring
    - Turn management

    Message format:
    {
        "type": "event_type",
        "data": {...}
    }

    Event types:
    - join: Join room
    - leave: Leave room
    - ready: Mark player as ready
    - answer: Submit answer
    - buzz: Buzz in (Jeopardy mode)
    - chat: Send chat message
    - start_game: Host starts game
    """
    # Authenticate user
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return

    # Verify room exists
    result = await db.execute(
        select(GameRoom).where(GameRoom.room_code == room_code)
    )
    room = result.scalar_one_or_none()

    if not room:
        await websocket.close(code=1008, reason="Room not found")
        return

    # Connect user
    await manager.connect(user.id, websocket)
    manager.join_room(user.id, room_code)

    # Notify room that user joined
    await manager.broadcast_to_room(
        room_code,
        {
            "type": "user_joined",
            "data": {
                "user_id": user.id,
                "username": user.username,
                "avatar_url": user.avatar_url
            }
        },
        exclude_user=user.id
    )

    # Send current room state to user
    room_users = manager.get_room_users(room_code)
    await manager.send_personal_message(
        {
            "type": "room_state",
            "data": {
                "room_code": room_code,
                "room_name": room.room_name,
                "status": room.status,
                "current_players": len(room_users),
                "max_players": room.max_players
            }
        },
        user.id
    )

    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            message = json.loads(data)

            event_type = message.get("type")
            event_data = message.get("data", {})

            logger.info(f"Received event '{event_type}' from user {user.id} in room {room_code}")

            # Handle events
            if event_type == "ready":
                # Player marked as ready
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "player_ready",
                        "data": {
                            "user_id": user.id,
                            "username": user.username
                        }
                    }
                )

            elif event_type == "answer":
                # Player submitted answer
                answer_id = event_data.get("answer_id")
                time_taken = event_data.get("time_taken")

                # Broadcast answer submission (without revealing answer)
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "answer_submitted",
                        "data": {
                            "user_id": user.id,
                            "username": user.username,
                            "time_taken": time_taken
                        }
                    }
                )

                # Process answer server-side (validate, calculate score)
                # This would involve game logic service

            elif event_type == "buzz":
                # Jeopardy buzzer
                # Only first buzz within time window counts
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "player_buzzed",
                        "data": {
                            "user_id": user.id,
                            "username": user.username,
                            "timestamp": event_data.get("timestamp")
                        }
                    }
                )

            elif event_type == "chat":
                # Chat message
                message_text = event_data.get("message", "")
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "chat_message",
                        "data": {
                            "user_id": user.id,
                            "username": user.username,
                            "message": message_text
                        }
                    }
                )

            elif event_type == "start_game":
                # Host starts the game
                if room.host_user_id == user.id:
                    await manager.broadcast_to_room(
                        room_code,
                        {
                            "type": "game_started",
                            "data": {
                                "started_by": user.username
                            }
                        }
                    )

            elif event_type == "score_update":
                # Live score update
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "score_update",
                        "data": event_data
                    }
                )

            elif event_type == "question_reveal":
                # Reveal next question
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "question_revealed",
                        "data": event_data
                    }
                )

            elif event_type == "timer_start":
                # Start countdown timer
                await manager.broadcast_to_room(
                    room_code,
                    {
                        "type": "timer_started",
                        "data": {
                            "duration": event_data.get("duration", 30)
                        }
                    }
                )

            else:
                logger.warning(f"Unknown event type: {event_type}")

    except WebSocketDisconnect:
        logger.info(f"User {user.id} disconnected from room {room_code}")
        manager.disconnect(user.id)

        # Notify room
        await manager.broadcast_to_room(
            room_code,
            {
                "type": "user_left",
                "data": {
                    "user_id": user.id,
                    "username": user.username
                }
            }
        )

    except Exception as e:
        logger.error(f"Error in WebSocket for user {user.id}: {e}", exc_info=True)
        manager.disconnect(user.id)
        await websocket.close(code=1011, reason="Internal error")


@router.websocket("/lobby")
async def lobby_websocket(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_async_db)
):
    """
    WebSocket for game lobby
    Shows available rooms, player counts, etc.
    """
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008, reason="Invalid token")
        return

    await manager.connect(user.id, websocket)

    try:
        while True:
            data = await websocket.receive_text()
            # Handle lobby events

    except WebSocketDisconnect:
        manager.disconnect(user.id)
    except Exception as e:
        logger.error(f"Error in lobby WebSocket: {e}")
        manager.disconnect(user.id)
