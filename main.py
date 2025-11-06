"""
FastAPI backend for Raspberry Pi device communication via WebSocket.

Features:
- POST /send endpoint with API key authentication
- WebSocket endpoint /ws/{device_id} for device connections
- Command forwarding from POST requests to WebSocket clients
- Response handling from devices
"""

import asyncio
import json
import logging
import os
from typing import Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Device Command Server", version="1.0.0")

# CORS middleware for development (adjust as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store active WebSocket connections by device_id
active_connections: Dict[str, WebSocket] = {}

# API Key from environment variable
API_KEY = os.getenv("API_KEY", "your-secret-api-key-change-in-production")


# Pydantic models
class SendCommandRequest(BaseModel):
    device_id: str
    cmd: str


class SendCommandResponse(BaseModel):
    success: bool
    message: str
    device_id: str


# API Key dependency
async def verify_api_key(x_api_key: str = Header(...)):
    """Verify the API key from the x-api-key header."""
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "online",
        "active_connections": len(active_connections),
        "devices": list(active_connections.keys())
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/send", response_model=SendCommandResponse)
async def send_command(
    request: SendCommandRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Send a command to a device via WebSocket.
    
    Requires x-api-key header for authentication.
    """
    device_id = request.device_id
    cmd = request.cmd
    
    logger.info(f"Received command for device {device_id}: {cmd}")
    
    # Check if device is connected
    if device_id not in active_connections:
        logger.warning(f"Device {device_id} is not connected")
        return SendCommandResponse(
            success=False,
            message=f"Device {device_id} is not connected",
            device_id=device_id
        )
    
    websocket = active_connections[device_id]
    
    try:
        # Send command to device via WebSocket
        command_data = {
            "cmd": cmd,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send_text(json.dumps(command_data))
        logger.info(f"Command sent to device {device_id}: {cmd}")
        
        return SendCommandResponse(
            success=True,
            message=f"Command '{cmd}' sent to device {device_id}",
            device_id=device_id
        )
    except Exception as e:
        logger.error(f"Error sending command to device {device_id}: {e}")
        # Remove disconnected connection
        if device_id in active_connections:
            del active_connections[device_id]
        
        return SendCommandResponse(
            success=False,
            message=f"Error sending command: {str(e)}",
            device_id=device_id
        )


@app.websocket("/ws/{device_id}")
async def websocket_endpoint(websocket: WebSocket, device_id: str):
    """
    WebSocket endpoint for device connections.
    
    Each Raspberry Pi connects to /ws/{device_id} and listens for commands.
    """
    await websocket.accept()
    logger.info(f"Device {device_id} connected")
    
    # Store connection
    active_connections[device_id] = websocket
    
    try:
        # Send welcome message
        welcome_msg = {
            "type": "connected",
            "message": f"Device {device_id} connected successfully",
            "device_id": device_id
        }
        await websocket.send_text(json.dumps(welcome_msg))
        
        # Keep connection alive and listen for responses
        while True:
            try:
                # Wait for messages from device (responses, status updates, etc.)
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    logger.info(f"Received message from device {device_id}: {message}")
                    
                    # Handle different message types if needed
                    msg_type = message.get("type", "response")
                    if msg_type == "response":
                        # Device response to a command
                        logger.info(f"Device {device_id} response: {message.get('data', '')}")
                    elif msg_type == "status":
                        # Device status update
                        logger.info(f"Device {device_id} status: {message.get('status', '')}")
                    elif msg_type == "error":
                        # Device error
                        logger.error(f"Device {device_id} error: {message.get('error', '')}")
                        
                except json.JSONDecodeError:
                    # Handle plain text responses
                    logger.info(f"Received plain text from device {device_id}: {data}")
                    
            except WebSocketDisconnect:
                logger.info(f"Device {device_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling message from device {device_id}: {e}")
                break
                
    except Exception as e:
        logger.error(f"WebSocket error for device {device_id}: {e}")
    finally:
        # Clean up connection
        if device_id in active_connections:
            del active_connections[device_id]
        logger.info(f"Device {device_id} connection closed")


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        log_level="info"
    )

