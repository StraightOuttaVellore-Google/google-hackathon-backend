#!/usr/bin/env python3
"""
Quick test script to verify transcript saving functionality
"""

import asyncio
import logging
from transcript_manager import get_transcript_manager
from context_logger import get_context_logger, EventType, LogLevel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_transcript_saving():
    """Test transcript saving functionality"""
    logger.info("🧪 Testing transcript saving...")
    
    # Get instances
    transcript_manager = get_transcript_manager()
    context_logger = get_context_logger()
    
    if not transcript_manager or not context_logger:
        logger.error("❌ Managers not initialized")
        return
    
    client_id = "test_client_debug"
    mode = "wellness"
    
    # Start session
    session_id = transcript_manager.start_session(client_id, mode)
    logger.info(f"✅ Started session: {session_id}")
    
    # Add some messages
    transcript_manager.add_user_message(client_id, "Hello, I'm testing the transcript system")
    transcript_manager.add_assistant_message(client_id, "Hello! I'm here to help with your test.")
    transcript_manager.add_user_message(client_id, "Can you confirm this conversation is being saved?")
    transcript_manager.add_assistant_message(client_id, "Yes, this conversation should be saved to the transcript.")
    
    # Log events
    await context_logger.log_event(
        client_id=client_id,
        session_id=session_id,
        event_type=EventType.SESSION_START,
        level=LogLevel.INFO,
        message="Test session started"
    )
    
    await context_logger.log_user_input(client_id, session_id, "Hello, I'm testing the transcript system")
    await context_logger.log_assistant_response(client_id, session_id, "Hello! I'm here to help with your test.")
    
    # Get session summary
    summary = transcript_manager.get_session_summary(client_id)
    logger.info(f"📊 Session summary: {summary}")
    
    # Save session
    transcript_id = await transcript_manager.save_session(client_id)
    logger.info(f"💾 Saved transcript: {transcript_id}")
    
    # Verify it was saved
    retrieved_transcript = await transcript_manager.get_transcript_by_id(transcript_id)
    if retrieved_transcript:
        exchanges = retrieved_transcript.get('exchanges', [])
        logger.info(f"✅ Retrieved transcript with {len(exchanges)} exchanges")
        for i, exchange in enumerate(exchanges):
            logger.info(f"  {i+1}. {exchange['role']}: {exchange['content'][:50]}...")
    else:
        logger.error("❌ Failed to retrieve transcript")
    
    # Check stats
    tm_stats = transcript_manager.get_stats()
    cl_stats = context_logger.get_stats()
    logger.info(f"📈 Transcript Manager stats: {tm_stats}")
    logger.info(f"📈 Context Logger stats: {cl_stats}")

if __name__ == "__main__":
    asyncio.run(test_transcript_saving())

