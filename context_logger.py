"""
Enhanced Logging System for Voice Agent Context and I/O Monitoring
This module provides comprehensive logging capabilities for tracking conversation context,
input/output processing, and system performance.
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
import time
from contextlib import contextmanager
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

class LogLevel(Enum):
    """Log levels for different types of events"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class EventType(Enum):
    """Types of events to log"""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    USER_INPUT = "user_input"
    ASSISTANT_RESPONSE = "assistant_response"
    RAG_RETRIEVAL = "rag_retrieval"
    CONTEXT_UPDATE = "context_update"
    ERROR = "error"
    PERFORMANCE = "performance"
    SYSTEM_EVENT = "system_event"

@dataclass
class LogEvent:
    """Structured log event"""
    id: str
    timestamp: datetime
    client_id: str
    session_id: str
    event_type: EventType
    level: LogLevel
    message: str
    data: Dict[str, Any]
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

class ContextLogger:
    """
    Enhanced logging system for voice agent context and I/O monitoring.
    Provides structured logging with database storage and real-time monitoring.
    """
    
    def __init__(self, logs_dir: str = "logs", enable_database: bool = True, enable_file: bool = True):
        """
        Initialize the context logger.
        
        Args:
            logs_dir: Directory for storing log files
            enable_database: Enable SQLite database logging
            enable_file: Enable file-based logging
        """
        self.logs_dir = Path(logs_dir)
        self.logs_dir.mkdir(exist_ok=True)
        
        self.enable_database = enable_database
        self.enable_file = enable_file
        
        # Database setup
        if enable_database:
            self.db_path = self.logs_dir / "context_logs.db"
            self._init_database()
        
        # File logging setup
        if enable_file:
            self._setup_file_logging()
        
        # In-memory buffer for recent events
        self.recent_events = []
        self.max_recent_events = 1000
        
        # Performance tracking
        self.performance_metrics = {}
        
        logger.info(f"ContextLogger initialized with database={enable_database}, file={enable_file}")
    
    def _init_database(self):
        """Initialize SQLite database for structured logging"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create events table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS log_events (
                        id TEXT PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        client_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        event_type TEXT NOT NULL,
                        level TEXT NOT NULL,
                        message TEXT NOT NULL,
                        data TEXT NOT NULL,
                        duration_ms REAL,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create performance metrics table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS performance_metrics (
                        id TEXT PRIMARY KEY,
                        timestamp TIMESTAMP NOT NULL,
                        client_id TEXT NOT NULL,
                        session_id TEXT NOT NULL,
                        metric_name TEXT NOT NULL,
                        metric_value REAL NOT NULL,
                        metric_unit TEXT,
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for better performance
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_log_events_client_id ON log_events (client_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_log_events_session_id ON log_events (session_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_log_events_timestamp ON log_events (timestamp)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_log_events_event_type ON log_events (event_type)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_client_id ON performance_metrics (client_id)")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_performance_timestamp ON performance_metrics (timestamp)")
                
                conn.commit()
                logger.info("Context logging database initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize context logging database: {e}")
            raise
    
    def _setup_file_logging(self):
        """Setup file-based logging"""
        # Create separate log files for different event types
        self.log_files = {
            EventType.SESSION_START: self.logs_dir / "sessions.log",
            EventType.SESSION_END: self.logs_dir / "sessions.log",
            EventType.USER_INPUT: self.logs_dir / "user_input.log",
            EventType.ASSISTANT_RESPONSE: self.logs_dir / "assistant_response.log",
            EventType.RAG_RETRIEVAL: self.logs_dir / "rag_retrieval.log",
            EventType.CONTEXT_UPDATE: self.logs_dir / "context_updates.log",
            EventType.ERROR: self.logs_dir / "errors.log",
            EventType.PERFORMANCE: self.logs_dir / "performance.log",
            EventType.SYSTEM_EVENT: self.logs_dir / "system_events.log"
        }
        
        # Create a general log file
        self.general_log_file = self.logs_dir / "general.log"
    
    async def log_event(self, 
                       client_id: str, 
                       session_id: str, 
                       event_type: EventType, 
                       level: LogLevel, 
                       message: str, 
                       data: Dict[str, Any] = None, 
                       duration_ms: float = None,
                       metadata: Dict[str, Any] = None):
        """
        Log a structured event.
        
        Args:
            client_id: Client identifier
            session_id: Session identifier
            event_type: Type of event
            level: Log level
            message: Log message
            data: Event data
            duration_ms: Duration in milliseconds
            metadata: Additional metadata
        """
        event = LogEvent(
            id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            client_id=client_id,
            session_id=session_id,
            event_type=event_type,
            level=level,
            message=message,
            data=data or {},
            duration_ms=duration_ms,
            metadata=metadata or {}
        )
        
        # Add to recent events buffer
        self.recent_events.append(event)
        if len(self.recent_events) > self.max_recent_events:
            self.recent_events = self.recent_events[-self.max_recent_events:]
        
        # Store in database
        if self.enable_database:
            await self._store_event_in_database(event)
        
        # Write to file
        if self.enable_file:
            await self._write_event_to_file(event)
        
        # Also log to standard logger
        log_message = f"[{event_type.value}] {client_id}:{session_id} - {message}"
        if data:
            log_message += f" | Data: {json.dumps(data, default=str)}"
        
        if level == LogLevel.DEBUG:
            logger.debug(log_message)
        elif level == LogLevel.INFO:
            logger.info(log_message)
        elif level == LogLevel.WARNING:
            logger.warning(log_message)
        elif level == LogLevel.ERROR:
            logger.error(log_message)
        elif level == LogLevel.CRITICAL:
            logger.critical(log_message)
    
    async def _store_event_in_database(self, event: LogEvent):
        """Store event in SQLite database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO log_events 
                    (id, timestamp, client_id, session_id, event_type, level, message, data, duration_ms, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event.id,
                    event.timestamp.isoformat(),
                    event.client_id,
                    event.session_id,
                    event.event_type.value,
                    event.level.value,
                    event.message,
                    json.dumps(event.data, default=str),
                    event.duration_ms,
                    json.dumps(event.metadata, default=str) if event.metadata else None
                ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store event in database: {e}")
    
    async def _write_event_to_file(self, event: LogEvent):
        """Write event to appropriate log file"""
        try:
            # Determine log file
            log_file = self.log_files.get(event.event_type, self.general_log_file)
            
            # Format log entry
            log_entry = {
                "timestamp": event.timestamp.isoformat(),
                "client_id": event.client_id,
                "session_id": event.session_id,
                "event_type": event.event_type.value,
                "level": event.level.value,
                "message": event.message,
                "data": event.data,
                "duration_ms": event.duration_ms,
                "metadata": event.metadata
            }
            
            # Write to file
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, default=str) + '\n')
                
        except Exception as e:
            logger.error(f"Failed to write event to file: {e}")
    
    @contextmanager
    def log_performance(self, client_id: str, session_id: str, operation_name: str, metadata: Dict = None):
        """
        Context manager for logging performance metrics.
        
        Usage:
            with context_logger.log_performance(client_id, session_id, "rag_retrieval") as perf:
                # Your operation here
                result = await some_operation()
                perf.add_metric("documents_retrieved", len(result))
        """
        start_time = time.time()
        perf_data = {"operation": operation_name, "metrics": {}}
        
        class PerformanceTracker:
            def add_metric(self, name: str, value: float, unit: str = None):
                perf_data["metrics"][name] = {"value": value, "unit": unit}
        
        tracker = PerformanceTracker()
        
        try:
            yield tracker
        finally:
            duration_ms = (time.time() - start_time) * 1000
            
            # Log performance event
            asyncio.create_task(self.log_event(
                client_id=client_id,
                session_id=session_id,
                event_type=EventType.PERFORMANCE,
                level=LogLevel.INFO,
                message=f"Performance: {operation_name}",
                data=perf_data,
                duration_ms=duration_ms,
                metadata=metadata
            ))
            
            # Store individual metrics
            if self.enable_database:
                asyncio.create_task(self._store_performance_metrics(
                    client_id, session_id, perf_data["metrics"], duration_ms, metadata
                ))
    
    async def _store_performance_metrics(self, client_id: str, session_id: str, metrics: Dict, duration_ms: float, metadata: Dict = None):
        """Store performance metrics in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Store duration metric
                cursor.execute("""
                    INSERT INTO performance_metrics (id, timestamp, client_id, session_id, metric_name, metric_value, metric_unit, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    str(uuid.uuid4()),
                    datetime.now(timezone.utc).isoformat(),
                    client_id,
                    session_id,
                    "duration",
                    duration_ms,
                    "ms",
                    json.dumps(metadata, default=str) if metadata else None
                ))
                
                # Store other metrics
                for metric_name, metric_info in metrics.items():
                    cursor.execute("""
                        INSERT INTO performance_metrics (id, timestamp, client_id, session_id, metric_name, metric_value, metric_unit, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        str(uuid.uuid4()),
                        datetime.now(timezone.utc).isoformat(),
                        client_id,
                        session_id,
                        metric_name,
                        metric_info["value"],
                        metric_info.get("unit"),
                        json.dumps(metadata, default=str) if metadata else None
                    ))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Failed to store performance metrics: {e}")
    
    async def log_user_input(self, client_id: str, session_id: str, input_text: str, input_type: str = "text", metadata: Dict = None):
        """Log user input with context"""
        await self.log_event(
            client_id=client_id,
            session_id=session_id,
            event_type=EventType.USER_INPUT,
            level=LogLevel.INFO,
            message=f"User input received: {input_text[:100]}{'...' if len(input_text) > 100 else ''}",
            data={
                "input_text": input_text,
                "input_type": input_type,
                "input_length": len(input_text)
            },
            metadata=metadata
        )
    
    async def log_assistant_response(self, client_id: str, session_id: str, response_text: str, response_type: str = "text", metadata: Dict = None):
        """Log assistant response with context"""
        await self.log_event(
            client_id=client_id,
            session_id=session_id,
            event_type=EventType.ASSISTANT_RESPONSE,
            level=LogLevel.INFO,
            message=f"Assistant response: {response_text[:100]}{'...' if len(response_text) > 100 else ''}",
            data={
                "response_text": response_text,
                "response_type": response_type,
                "response_length": len(response_text)
            },
            metadata=metadata
        )
    
    async def log_rag_retrieval(self, client_id: str, session_id: str, query: str, retrieved_docs: List[Dict], mode: str, metadata: Dict = None):
        """Log RAG retrieval with context"""
        await self.log_event(
            client_id=client_id,
            session_id=session_id,
            event_type=EventType.RAG_RETRIEVAL,
            level=LogLevel.INFO,
            message=f"RAG retrieval for {mode} mode: {len(retrieved_docs)} documents",
            data={
                "query": query,
                "mode": mode,
                "documents_retrieved": len(retrieved_docs),
                "document_sources": [doc.get("source", "unknown") for doc in retrieved_docs]
            },
            metadata=metadata
        )
    
    async def log_context_update(self, client_id: str, session_id: str, context_type: str, context_data: Dict, metadata: Dict = None):
        """Log context updates"""
        await self.log_event(
            client_id=client_id,
            session_id=session_id,
            event_type=EventType.CONTEXT_UPDATE,
            level=LogLevel.DEBUG,
            message=f"Context updated: {context_type}",
            data={
                "context_type": context_type,
                "context_data": context_data
            },
            metadata=metadata
        )
    
    async def log_error(self, client_id: str, session_id: str, error_message: str, error_type: str = "general", metadata: Dict = None):
        """Log errors with context"""
        await self.log_event(
            client_id=client_id,
            session_id=session_id,
            event_type=EventType.ERROR,
            level=LogLevel.ERROR,
            message=f"Error ({error_type}): {error_message}",
            data={
                "error_message": error_message,
                "error_type": error_type
            },
            metadata=metadata
        )
    
    async def get_recent_events(self, client_id: str = None, session_id: str = None, limit: int = 100) -> List[Dict]:
        """Get recent events from memory buffer"""
        events = self.recent_events
        
        if client_id:
            events = [e for e in events if e.client_id == client_id]
        
        if session_id:
            events = [e for e in events if e.session_id == session_id]
        
        return [asdict(event) for event in events[-limit:]]
    
    async def get_events_from_database(self, 
                                     client_id: str = None, 
                                     session_id: str = None, 
                                     event_type: EventType = None,
                                     start_time: datetime = None,
                                     end_time: datetime = None,
                                     limit: int = 1000) -> List[Dict]:
        """Get events from database with filtering"""
        if not self.enable_database:
            return []
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Build query
                query = "SELECT * FROM log_events WHERE 1=1"
                params = []
                
                if client_id:
                    query += " AND client_id = ?"
                    params.append(client_id)
                
                if session_id:
                    query += " AND session_id = ?"
                    params.append(session_id)
                
                if event_type:
                    query += " AND event_type = ?"
                    params.append(event_type.value)
                
                if start_time:
                    query += " AND timestamp >= ?"
                    params.append(start_time.isoformat())
                
                if end_time:
                    query += " AND timestamp <= ?"
                    params.append(end_time.isoformat())
                
                query += " ORDER BY timestamp DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
                return [dict(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Error retrieving events from database: {e}")
            return []
    
    def get_stats(self) -> Dict[str, Any]:
        """Get logging system statistics"""
        stats = {
            "recent_events_count": len(self.recent_events),
            "logs_directory": str(self.logs_dir),
            "database_enabled": self.enable_database,
            "file_enabled": self.enable_file
        }
        
        if self.enable_database:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT COUNT(*) FROM log_events")
                    stats["total_events"] = cursor.fetchone()[0]
                    
                    cursor.execute("SELECT COUNT(*) FROM performance_metrics")
                    stats["total_performance_metrics"] = cursor.fetchone()[0]
            except Exception as e:
                stats["database_error"] = str(e)
        
        return stats

# Global context logger instance
context_logger = None

def get_context_logger() -> ContextLogger:
    """Get the global context logger instance"""
    global context_logger
    if context_logger is None:
        context_logger = ContextLogger()
    return context_logger

def initialize_context_logger(logs_dir: str = "logs", enable_database: bool = True, enable_file: bool = True) -> ContextLogger:
    """Initialize the global context logger"""
    global context_logger
    context_logger = ContextLogger(logs_dir, enable_database, enable_file)
    return context_logger

