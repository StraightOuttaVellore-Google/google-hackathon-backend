#!/usr/bin/env python3
"""
Full system test for transcript saving on call end
This script simulates a complete voice agent session and verifies transcript saving
"""

import asyncio
import json
import logging
import websockets
import time
from transcript_manager import get_transcript_manager
from context_logger import get_context_logger

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_full_system():
    """Test the full voice agent system with transcript saving"""
    logger.info("🧪 Testing full voice agent system...")
    
    # Get managers
    transcript_manager = get_transcript_manager()
    context_logger = get_context_logger()
    
    if not transcript_manager or not context_logger:
        logger.error("❌ Managers not initialized")
        return
    
    client_id = f"test_client_{int(time.time())}"
    mode = "wellness"
    
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
                    "mode": mode,
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
            
            if response_data.get("type") == "status" and response_data.get("status") == "connected":
                logger.info("✅ Connection confirmed")
            else:
                logger.error(f"❌ Unexpected response: {response_data}")
                return
            
            # Simulate some conversation
            logger.info("🗣️ Simulating conversation...")
            
            # Send a text message
            text_message = {
                "type": "text",
                "text": "Hello, I'm testing the transcript system. Can you hear me?"
            }
            await websocket.send(json.dumps(text_message))
            logger.info("📤 Text message sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                logger.info(f"📨 Received response: {response_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No response received within 10 seconds")
            
            # Send another message
            text_message2 = {
                "type": "text", 
                "text": "This is my second message to test transcript saving."
            }
            await websocket.send(json.dumps(text_message2))
            logger.info("📤 Second text message sent")
            
            # Wait for response
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=10)
                response_data = json.loads(response)
                logger.info(f"📨 Received second response: {response_data.get('type', 'unknown')}")
            except asyncio.TimeoutError:
                logger.warning("⚠️ No second response received within 10 seconds")
            
            # Send explicit disconnect message
            disconnect_message = {
                "type": "disconnect"
            }
            await websocket.send(json.dumps(disconnect_message))
            logger.info("📤 Disconnect message sent")
            
            # Wait a moment for processing
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
    
    # Check transcript manager stats
    tm_stats = transcript_manager.get_stats()
    logger.info(f"📊 Transcript Manager stats: {tm_stats}")
    
    # Check context logger stats
    cl_stats = context_logger.get_stats()
    logger.info(f"📊 Context Logger stats: {cl_stats}")
    
    # Try to find the transcript
    transcripts = await transcript_manager.list_transcripts(client_id=client_id, limit=10)
    logger.info(f"📋 Found {len(transcripts)} transcripts for client {client_id}")
    
    if transcripts:
        transcript = transcripts[0]
        logger.info(f"✅ Transcript found: {transcript['session_id']}")
        logger.info(f"   - Mode: {transcript['mode']}")
        logger.info(f"   - Exchanges: {transcript['total_exchanges']}")
        logger.info(f"   - Duration: {transcript.get('session_end', 'Ongoing')}")
        
        # Get full transcript
        full_transcript = await transcript_manager.get_transcript_by_id(transcript['transcript_id'])
        if full_transcript:
            exchanges = full_transcript.get('exchanges', [])
            logger.info(f"📖 Full transcript has {len(exchanges)} exchanges:")
            for i, exchange in enumerate(exchanges):
                logger.info(f"   {i+1}. {exchange['role']}: {exchange['content'][:50]}...")
    else:
        logger.error("❌ No transcript found for client")
    
    # Check recent events
    recent_events = await context_logger.get_recent_events(client_id=client_id, limit=10)
    logger.info(f"📋 Found {len(recent_events)} recent events for client {client_id}")
    
    for event in recent_events:
        logger.info(f"   - {event['event_type']}: {event['message'][:50]}...")

if __name__ == "__main__":
    asyncio.run(test_full_system())

