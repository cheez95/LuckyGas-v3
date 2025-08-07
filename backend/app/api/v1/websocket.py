import logging
import uuid
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, Query, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.core.config import settings
from app.services.websocket_service import websocket_manager

router = APIRouter()
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


async def get_current_user_ws(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[dict]:
    """
    Authenticate WebSocket connection via query parameter token
    """
    if not token:
        await websocket.close(code=4001, reason="Missing authentication token")
        return None

    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        if not user_id:
            await websocket.close(code=4001, reason="Invalid token")
            return None

        # TODO: Get user from database
        # For now, return mock user data
        return {
            "user_id": user_id,
            "role": payload.get("role", "customer"),
            "email": payload.get("email", ""),
        }

    except jwt.ExpiredSignatureError:
        await websocket.close(code=4001, reason="Token expired")
        return None
    except jwt.InvalidTokenError:
        await websocket.close(code=4001, reason="Invalid token")
        return None


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Main WebSocket endpoint for real - time communication

    Connection URL: ws://localhost:8000 / api / v1 / websocket / ws?token=<JWT_TOKEN>
    """
    # Authenticate user
    user = await get_current_user_ws(websocket, token, db)
    if not user:
        return

    # Generate connection ID
    connection_id = str(uuid.uuid4())

    try:
        # Accept connection
        await websocket_manager.connect(
            websocket, connection_id, user["user_id"], user["role"]
        )

        logger.info(f"WebSocket connection established: {connection_id}")

        # Handle messages
        while True:
            try:
                # Receive message
                message = await websocket.receive_json()

                # Process message
                await websocket_manager.handle_message(connection_id, message)

            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {connection_id}")
                break
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                break

    finally:
        # Clean up connection
        await websocket_manager.disconnect(connection_id)


@router.websocket("/ws / driver")
async def driver_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Dedicated WebSocket endpoint for driver mobile apps
    Optimized for location updates and delivery status
    """
    # Authenticate driver
    user = await get_current_user_ws(websocket, token, db)
    if not user or user["role"] != "driver":
        await websocket.close(code=4003, reason="Driver access only")
        return

    connection_id = f"driver-{str(uuid.uuid4())}"

    try:
        await websocket_manager.connect(
            websocket, connection_id, user["user_id"], "driver"
        )

        # Send initial driver data
        await websocket.send_json(
            {
                "type": "driver.init",
                "driver_id": user["user_id"],
                "active_route": None,  # TODO: Get from database
                "pending_deliveries": [],  # TODO: Get from database
            }
        )

        while True:
            try:
                message = await websocket.receive_json()

                # Handle driver - specific messages
                if message.get("type") == "location.update":
                    # Validate location data
                    if "latitude" in message and "longitude" in message:
                        await websocket_manager.handle_driver_location(
                            user["user_id"], message
                        )
                else:
                    await websocket_manager.handle_message(connection_id, message)

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Driver WebSocket error: {e}")
                break

    finally:
        await websocket_manager.disconnect(connection_id)


@router.websocket("/ws / office")
async def office_websocket_endpoint(
    websocket: WebSocket,
    token: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Office staff WebSocket endpoint with full access to all events
    """
    # Authenticate office staff
    user = await get_current_user_ws(websocket, token, db)
    if not user or user["role"] not in ["office_staf", "manager", "super_admin"]:
        await websocket.close(code=4003, reason="Office access only")
        return

    connection_id = f"office-{str(uuid.uuid4())}"

    try:
        await websocket_manager.connect(
            websocket, connection_id, user["user_id"], "office"
        )

        # Send initial dashboard data
        await websocket.send_json(
            {
                "type": "office.init",
                "user_id": user["user_id"],
                "role": user["role"],
                "active_drivers": [],  # TODO: Get from Redis / database
                "pending_orders": [],  # TODO: Get from database
                "today_routes": [],  # TODO: Get from database
            }
        )

        while True:
            try:
                message = await websocket.receive_json()
                await websocket_manager.handle_message(connection_id, message)
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Office WebSocket error: {e}")
                break

    finally:
        await websocket_manager.disconnect(connection_id)


@router.post("/broadcast/{event_type}")
async def broadcast_event(event_type: str, data: dict, channel: Optional[str] = None):
    """
    HTTP endpoint to broadcast events via WebSocket
    Used by other services to send real - time updates
    """
    await websocket_manager.publish_event(
        channel or "system", {"type": event_type, **data}
    )

    return {"success": True, "event_type": event_type}
