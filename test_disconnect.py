#!/usr/bin/env python3
"""
Test WebSocket disconnect handling with immediate cleanup
"""

import asyncio
import json
import logging
import websockets
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_disconnect_handling():
    """Test WebSocket disconnect handling"""
    logger.info("🧪 Testing WebSocket disconnect handling...")
    
    client_id = f"test_disconnect_{int(time.time())}"
    
    try:
        # Connect to WebSocket
        uri = f"ws://localhost:8000/ws/{client_id}"
        logger.info(f"🔌 Connecting to {uri}")
        
        async with websockets.connect(uri) as websocket:
            logger.info("✅ WebSocket connected")
            
            # Send configuration
            config = {
                "type": "config",
                "config": {
                    "mode": "wellness",
                    "voice": "Puck",
                    "vad_enabled": True,
                    "allow_interruptions": False,
                    "client_id": client_id
                }
            }
            
            await websocket.send(json.dumps(config))
            logger.info("📤 Configuration sent")
            
            # Wait for connection confirmation
            response = await websocket.recv()
            response_data = json.loads(response)
            logger.info(f"📨 Received: {response_data}")
            
            if response_data.get("type") == "status" and response_data.get("status") in ["config_received", "connected"]:
                logger.info("✅ Connection confirmed")
            else:
                logger.error(f"❌ Unexpected response: {response_data}")
                return
            
            # Wait for the actual connection status
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5)
                response_data = json.loads(response)
                logger.info(f"📨 Received: {response_data}")
                
                if response_data.get("type") == "status" and response_data.get("status") == "connected":
                    logger.info("✅ Fully connected")
                else:
                    logger.info(f"📨 Status: {response_data.get('status', 'unknown')}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No connection status received, continuing anyway")
            
            # Send a text message
            text_message = {
                "type": "text",
                "text": "Hello, this is a test message for disconnect handling."
            }
            await websocket.send(json.dumps(text_message))
            logger.info("📤 Text message sent")
            
            # Wait a moment
            await asyncio.sleep(1)
            
            # Send explicit disconnect message
            disconnect_message = {
                "type": "disconnect"
            }
            await websocket.send(json.dumps(disconnect_message))
            logger.info("📤 Disconnect message sent")
            
            # Wait for processing
            await asyncio.sleep(2)
            
            logger.info("🔌 WebSocket will close now")
            
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    
    # Wait for cleanup to complete
    logger.info("⏳ Waiting for cleanup to complete...")
    await asyncio.sleep(3)
    
    # Check if transcript was saved
    logger.info("🔍 Checking if transcript was saved...")
    
    from transcript_manager import get_transcript_manager
    transcript_manager = get_transcript_manager()
    
    if transcript_manager:
        transcripts = await transcript_manager.list_transcripts(client_id=client_id, limit=1)
        if transcripts:
            transcript = transcripts[0]
            logger.info(f"✅ Transcript found: {transcript['session_id']}")
            logger.info(f"   - Mode: {transcript['mode']}")
            logger.info(f"   - Exchanges: {transcript['total_exchanges']}")
            logger.info(f"   - Duration: {transcript.get('session_end', 'Ongoing')}")
        else:
            logger.error("❌ No transcript found for client")
    else:
        logger.error("❌ Transcript manager not available")

if __name__ == "__main__":
    asyncio.run(test_disconnect_handling())
