"""
Transcript Manager for Voice Agent Conversations
This module handles saving and managing conversation transcripts between users and AI assistants.
"""

import os
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import asyncio
import uuid

logger = logging.getLogger(__name__)

class TranscriptManager:
    """
    Manages conversation transcripts for voice agent sessions.
    Supports both JSON file storage and SQLite database storage.
    """
    
    def __init__(self, storage_type: str = "database", transcripts_dir: str = "transcripts"):
        """
        Initialize the transcript manager.
        
        Args:
            storage_type: "database" for SQLite, "file" for JSON files
            transcripts_dir: Directory for storing transcript files
        """
        self.storage_type = storage_type
        self.transcripts_dir = Path(transcripts_dir)
        self.transcripts_dir.mkdir(exist_ok=True)
        
        # In-memory storage for active sessions
        self.active_transcripts = {}  # client_id -> list of exchanges
        
        # Initialize database if using database storage
        if storage_type == "database":
            self.db_path = self.transcripts_dir / "transcripts.db"
            self._init_database()
        
        logger.info(f"TranscriptManager initialized with {storage_type} storage")
    
    def _init_database(self):
        """Initialize SQLite database for transcript storage"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create transcripts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS transcripts (
                        id TEXT PRIMARY KEY,
                        client_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        mode TEXT NOT NULL,
                        session_start TIMESTAMP NOT NULL,
                        session_end TIMESTAMP,
                        total_exchanges INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create exchanges table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS exchanges (
                        id TEXT PRIMARY KEY,
                        transcript_id TEXT NOT NULL,
                        exchange_order INTEGER NOT NULL,
                        timestamp TIMESTAMP NOT NULL,
                        role TEXT NOT NULL,
                        content TEXT NOT NULL,
                        content_type TEXT DEFAULT 'text',
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (transcript_id) REFERENCES transcripts (id)
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_client_id ON transcripts (client_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_transcripts_session_id ON transcripts (session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchanges_transcript_id ON exchanges (transcript_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_exchanges_timestamp ON exchanges (timestamp)")
                
                conn.commit()
                logger.info("Database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def start_session(self, client_id: str, mode: str = "wellness") -> str:
        """
        Start a new conversation session.
        
        Args:
            client_id: Unique identifier for the client
            mode: Conversation mode (wellness, study, etc.)
            
        Returns:
            session_id: Unique session identifier
        """
        session_id = str(uuid.uuid4())
        session_start = datetime.now(timezone.utc)
        
        # Initialize in-memory storage
        self.active_transcripts[client_id] = {
            "session_id": session_id,
            "mode": mode,
            "session_start": session_start,
            "exchanges": [],
            "metadata": {
                "total_exchanges": 0,
                "last_activity": session_start
            }
        }
        
        logger.info(f"Started new session {session_id} for client {client_id} in {mode} mode")
        return session_id
    
    def add_user_message(self, client_id: str, content: str, content_type: str = "text", metadata: Dict = None):
        """
        Add a user message to the active transcript.
        
        Args:
            client_id: Client identifier
            content: Message content
            content_type: Type of content (text, audio, etc.)
            metadata: Additional metadata
        """
        if client_id not in self.active_transcripts:
            logger.warning(f"No active session for client {client_id}")
            return
        
        exchange = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc),
            "role": "user",
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {}
        }
        
        self.active_transcripts[client_id]["exchanges"].append(exchange)
        self.active_transcripts[client_id]["metadata"]["total_exchanges"] += 1
        self.active_transcripts[client_id]["metadata"]["last_activity"] = exchange["timestamp"]
        
        logger.debug(f"Added user message to session {self.active_transcripts[client_id]['session_id']}")
    
    def add_assistant_message(self, client_id: str, content: str, content_type: str = "text", metadata: Dict = None):
        """
        Add an assistant message to the active transcript.
        
        Args:
            client_id: Client identifier
            content: Message content
            content_type: Type of content (text, audio, etc.)
            metadata: Additional metadata
        """
        if client_id not in self.active_transcripts:
            logger.warning(f"No active session for client {client_id}")
            return
        
        exchange = {
            "id": str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc),
            "role": "assistant",
            "content": content,
            "content_type": content_type,
            "metadata": metadata or {}
        }
        
        self.active_transcripts[client_id]["exchanges"].append(exchange)
        self.active_transcripts[client_id]["metadata"]["total_exchanges"] += 1
        self.active_transcripts[client_id]["metadata"]["last_activity"] = exchange["timestamp"]
        
        logger.debug(f"Added assistant message to session {self.active_transcripts[client_id]['session_id']}")
    
    async def save_session(self, client_id: str, session_end: datetime = None) -> Optional[str]:
        """
        Save the current session to persistent storage.
        
        Args:
            client_id: Client identifier
            session_end: End time of the session (defaults to now)
            
        Returns:
            transcript_id: ID of the saved transcript, or None if failed
        """
        if client_id not in self.active_transcripts:
            logger.warning(f"No active session to save for client {client_id}")
            return None
        
        session_data = self.active_transcripts[client_id]
        session_end = session_end or datetime.now(timezone.utc)
        
        try:
            if self.storage_type == "database":
                transcript_id = await self._save_to_database(client_id, session_data, session_end)
            else:
                transcript_id = await self._save_to_file(client_id, session_data, session_end)
            
            # Clear the active session
            del self.active_transcripts[client_id]
            
            logger.info(f"Saved session {session_data['session_id']} for client {client_id}")
            return transcript_id
            
        except Exception as e:
            logger.error(f"Failed to save session for client {client_id}: {e}")
            return None
    
    async def _save_to_database(self, client_id: str, session_data: Dict, session_end: datetime) -> str:
        """Save session to SQLite database"""
        transcript_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Insert transcript record
            cursor.execute("""
                INSERT INTO transcripts (id, client_id, session_id, mode, session_start, session_end, total_exchanges)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                transcript_id,
                client_id,
                session_data["session_id"],
                session_data["mode"],
                session_data["session_start"].isoformat(),
                session_end.isoformat(),
                session_data["metadata"]["total_exchanges"]
            ))
            
            # Insert exchanges
            for i, exchange in enumerate(session_data["exchanges"]):
                cursor.execute("""
                    INSERT INTO exchanges (id, transcript_id, exchange_order, timestamp, role, content, content_type, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    exchange["id"],
                    transcript_id,
                    i + 1,
                    exchange["timestamp"].isoformat(),
                    exchange["role"],
                    exchange["content"],
                    exchange["content_type"],
                    json.dumps(exchange["metadata"])
                ))
            
            conn.commit()
        
        return transcript_id
    
    async def _save_to_file(self, client_id: str, session_data: Dict, session_end: datetime) -> str:
        """Save session to JSON file"""
        transcript_id = str(uuid.uuid4())
        
        # Prepare transcript data
        transcript_data = {
            "transcript_id": transcript_id,
            "client_id": client_id,
            "session_id": session_data["session_id"],
            "mode": session_data["mode"],
            "session_start": session_data["session_start"].isoformat(),
            "session_end": session_end.isoformat(),
            "total_exchanges": session_data["metadata"]["total_exchanges"],
            "exchanges": session_data["exchanges"]
        }
        
        # Create filename with timestamp
        timestamp_str = session_data["session_start"].strftime("%Y%m%d_%H%M%S")
        filename = f"transcript_{client_id}_{timestamp_str}_{transcript_id[:8]}.json"
        filepath = self.transcripts_dir / filename
        
        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, indent=2, ensure_ascii=False)
        
        return transcript_id
    
    def get_active_session(self, client_id: str) -> Optional[Dict]:
        """Get the active session for a client"""
        return self.active_transcripts.get(client_id)
    
    def get_session_summary(self, client_id: str) -> Optional[Dict]:
        """Get a summary of the active session"""
        session = self.get_active_session(client_id)
        if not session:
            return None
        
        return {
            "session_id": session["session_id"],
            "mode": session["mode"],
            "session_start": session["session_start"].isoformat(),
            "total_exchanges": session["metadata"]["total_exchanges"],
            "last_activity": session["metadata"]["last_activity"].isoformat(),
            "duration_minutes": (datetime.now(timezone.utc) - session["session_start"]).total_seconds() / 60
        }
    
    async def get_transcript_by_id(self, transcript_id: str) -> Optional[Dict]:
        """Get a transcript by its ID"""
        if self.storage_type == "database":
            return await self._get_transcript_from_database(transcript_id)
        else:
            return await self._get_transcript_from_file(transcript_id)
    
    async def _get_transcript_from_database(self, transcript_id: str) -> Optional[Dict]:
        """Get transcript from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Get transcript info
                cursor.execute("SELECT * FROM transcripts WHERE id = ?", (transcript_id,))
                transcript_row = cursor.fetchone()
                
                if not transcript_row:
                    return None
                
                # Get exchanges
                cursor.execute("""
                    SELECT * FROM exchanges 
                    WHERE transcript_id = ? 
                    ORDER BY exchange_order
                """, (transcript_id,))
                exchange_rows = cursor.fetchall()
                
                # Convert to dict format
                transcript_data = dict(transcript_row)
                transcript_data["exchanges"] = [dict(row) for row in exchange_rows]
                
                return transcript_data
                
        except Exception as e:
            logger.error(f"Error retrieving transcript from database: {e}")
            return None
    
    async def _get_transcript_from_file(self, transcript_id: str) -> Optional[Dict]:
        """Get transcript from file"""
        try:
            # Search for file with transcript_id
            for file_path in self.transcripts_dir.glob("*.json"):
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if data.get("transcript_id") == transcript_id:
                        return data
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving transcript from file: {e}")
            return None
    
    async def list_transcripts(self, client_id: str = None, limit: int = 50) -> List[Dict]:
        """List transcripts, optionally filtered by client_id"""
        if self.storage_type == "database":
            return await self._list_transcripts_from_database(client_id, limit)
        else:
            return await self._list_transcripts_from_files(client_id, limit)
    
    async def _list_transcripts_from_database(self, client_id: str = None, limit: int = 50) -> List[Dict]:
        """List transcripts from database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if client_id:
                    cursor.execute("""
                        SELECT * FROM transcripts 
                        WHERE client_id = ? 
                        ORDER BY session_start DESC 
                        LIMIT ?
                    """, (client_id, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM transcripts 
                        ORDER BY session_start DESC 
                        LIMIT ?
                    """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error listing transcripts from database: {e}")
            return []
    
    async def _list_transcripts_from_files(self, client_id: str = None, limit: int = 50) -> List[Dict]:
        """List transcripts from files"""
        try:
            transcripts = []
            
            for file_path in sorted(self.transcripts_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
                if len(transcripts) >= limit:
                    break
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if not client_id or data.get("client_id") == client_id:
                        # Create summary entry
                        summary = {
                            "transcript_id": data.get("transcript_id"),
                            "client_id": data.get("client_id"),
                            "session_id": data.get("session_id"),
                            "mode": data.get("mode"),
                            "session_start": data.get("session_start"),
                            "session_end": data.get("session_end"),
                            "total_exchanges": data.get("total_exchanges")
                        }
                        transcripts.append(summary)
            
            return transcripts
            
        except Exception as e:
            logger.error(f"Error listing transcripts from files: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get transcript manager statistics"""
        stats = {
            "storage_type": self.storage_type,
            "active_sessions": len(self.active_transcripts),
            "transcripts_directory": str(self.transcripts_dir)
        }
        
        if self.storage_type == "database":
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM transcripts")
                    stats["total_transcripts"] = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM exchanges")
                    stats["total_exchanges"] = cursor.fetchone()[0]
            except Exception as e:
                logger.error(f"Error getting database stats: {e}")
                stats["error"] = str(e)
        else:
            # Count files
            json_files = list(self.transcripts_dir.glob("*.json"))
            stats["total_transcripts"] = len(json_files)
        
        return stats

# Global transcript manager instance
transcript_manager = None

def get_transcript_manager() -> TranscriptManager:
    """Get the global transcript manager instance"""
    global transcript_manager
    if transcript_manager is None:
        transcript_manager = TranscriptManager()
    return transcript_manager

def initialize_transcript_manager(storage_type: str = "database", transcripts_dir: str = "transcripts") -> TranscriptManager:
    """Initialize the global transcript manager"""
    global transcript_manager
    transcript_manager = TranscriptManager(storage_type, transcripts_dir)
    return transcript_manager

