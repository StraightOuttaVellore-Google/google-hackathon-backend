"""
Hybrid RAG Manager for Turn-by-Turn Context Retrieval
This module implements manual RAG retrieval before each conversation turn
to work with Gemini Live API WebSocket connections.
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import time

# Google Cloud imports
from google.cloud import aiplatform
import vertexai
from vertexai import rag
from google.genai.types import VertexRagStore, VertexRagStoreRagResource, Tool, Retrieval

# Import dataset processor for corpus management
from dataset_processor import initialize_dataset_processing, process_and_upload_datasets

logger = logging.getLogger(__name__)

class HybridRAGManager:
    """
    Manages turn-by-turn RAG retrieval for Gemini Live API integration.
    This class handles manual context retrieval before each conversation turn.
    """
    
    def __init__(self, project_id: str, location: str = "us-east1"):
        self.project_id = project_id
        self.location = location
        self.corpora = {}  # Store corpus information
        self.retrieval_cache = {}  # Cache for recent retrievals
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
        
        # Initialize Vertex AI
        try:
            vertexai.init(project=self.project_id, location=self.location)
            logger.info(f"✅ Vertex AI initialized for project: {project_id}")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Vertex AI: {e}")
            raise
    
    async def initialize_corpora(self) -> bool:
        """Initialize RAG corpora by processing and uploading datasets"""
        try:
            logger.info("🚀 Initializing RAG corpora...")
            
            # Check if corpora already exist
            existing_corpora = await self._check_existing_corpora()
            if existing_corpora:
                logger.info("✅ Found existing corpora, skipping dataset processing")
                return True
            
            logger.info("📋 No existing corpora found, processing datasets...")
            
            # Initialize dataset processing
            dataset_success = await initialize_dataset_processing(self.project_id, self.location)
            if not dataset_success:
                logger.error("Failed to initialize dataset processing")
                return False
            
            # Process and upload datasets
            corpus_ids = await process_and_upload_datasets()
            if not corpus_ids:
                logger.error("Failed to process and upload datasets")
                return False
            
            # Store corpus information
            for mode, corpus_id in corpus_ids.items():
                corpus_name = f"projects/{self.project_id}/locations/{self.location}/ragCorpora/{corpus_id}"
                self.corpora[mode] = {
                    "corpus_id": corpus_id,
                    "corpus_name": corpus_name,
                    "name": f"{mode}-corpus"
                }
                logger.info(f"✅ {mode.capitalize()} corpus initialized: {corpus_id}")
            
            logger.info("🎉 All RAG corpora initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize corpora: {e}")
            return False
    
    async def _check_existing_corpora(self) -> bool:
        """Check if corpora already exist and populate self.corpora"""
        try:
            # List existing corpora
            corpora = rag.list_corpora()
            
            corpus_found = False
            for corpus in corpora:
                corpus_name = corpus.display_name
                corpus_id = corpus.name.split("/")[-1]
                
                # Check for our expected corpus names
                if "academic-success-corpus" in corpus_name.lower():
                    self.corpora["study"] = {
                        "corpus_id": corpus_id,
                        "corpus_name": corpus.name,
                        "name": corpus_name
                    }
                    corpus_found = True
                    logger.info(f"✅ Found existing study corpus: {corpus_id}")
                
                elif "mental-health-wellness-corpus" in corpus_name.lower():
                    self.corpora["wellness"] = {
                        "corpus_id": corpus_id,
                        "corpus_name": corpus.name,
                        "name": corpus_name
                    }
                    corpus_found = True
                    logger.info(f"✅ Found existing wellness corpus: {corpus_id}")
            
            return corpus_found
            
        except Exception as e:
            logger.warning(f"Could not check for existing corpora: {e}")
            return False
    
    async def retrieve_context(self, query: str, mode: str, top_k: int = 3) -> Tuple[str, List[Dict]]:
        """
        Retrieve relevant context for a given query using Vertex AI RAG Engine.
        
        Args:
            query: The user's query/question
            mode: Agent mode ('study' or 'wellness')
            top_k: Number of top results to retrieve
            
        Returns:
            Tuple of (context_text, retrieved_documents)
        """
        try:
            if mode not in self.corpora:
                logger.warning(f"No corpus available for mode: {mode}")
                return "", []
            
            corpus_info = self.corpora[mode]
            corpus_name = corpus_info["corpus_name"]
            
            # Check cache first
            cache_key = f"{mode}:{hash(query)}"
            if cache_key in self.retrieval_cache:
                cached_result, timestamp = self.retrieval_cache[cache_key]
                if time.time() - timestamp < self.cache_ttl:
                    logger.debug(f"Using cached retrieval for query: {query[:50]}...")
                    return cached_result
            
            logger.info(f"🔍 Retrieving context for {mode} mode query: {query[:100]}...")
            
            # Perform RAG retrieval
            try:
                response = rag.retrieval_query(
                    rag_resources=[
                        rag.RagResource(rag_corpus=corpus_name)
                    ],
                    text=query,
                    rag_retrieval_config=rag.RagRetrievalConfig(
                        top_k=top_k,
                        filter=rag.Filter(vector_distance_threshold=0.7)
                    )
                )
            except Exception as rag_error:
                error_msg = str(rag_error)
                if "quota" in error_msg.lower() or "resourceexhausted" in error_msg.lower():
                    logger.warning(f"⚠️ RAG quota exceeded for {mode} mode - continuing without context")
                    logger.warning(f"⚠️ Quota error details: {error_msg}")
                    return "", []
                else:
                    logger.error(f"❌ RAG retrieval error: {error_msg}")
                    return "", []
            
            # Extract context from response
            contexts = response.contexts.contexts if hasattr(response, 'contexts') else []
            retrieved_docs = []
            context_parts = []
            
            for i, ctx in enumerate(contexts):
                # Clean the content to extract only the meaningful text
                content = ctx.text
                
                # Extract the actual content from the structured format
                cleaned_content = self._extract_meaningful_content(content)
                
                doc_info = {
                    "content": cleaned_content,
                    "score": getattr(ctx, 'score', 0.0),
                    "source": getattr(ctx, 'source', f"document_{i}"),
                    "rank": i + 1
                }
                retrieved_docs.append(doc_info)
                context_parts.append(f"[Context {i+1}]: {cleaned_content}")
            
            # Combine all context
            context_text = "\n\n".join(context_parts)
            
            # Cache the result
            self.retrieval_cache[cache_key] = ((context_text, retrieved_docs), time.time())
            
            # Clean old cache entries
            self._clean_cache()
            
            logger.info(f"✅ Retrieved {len(contexts)} context documents for {mode} mode")
            return context_text, retrieved_docs
            
        except Exception as e:
            error_msg = str(e)
            if "quota" in error_msg.lower() or "resourceexhausted" in error_msg.lower():
                logger.warning(f"⚠️ RAG quota exceeded - continuing without context: {error_msg}")
            else:
                logger.error(f"❌ Failed to retrieve context: {error_msg}")
            return "", []
    
    def _extract_meaningful_content(self, content: str) -> str:
        """Extract meaningful content from structured RAG response"""
        try:
            # Split content into lines
            lines = content.split('\n')
            meaningful_lines = []
            
            # Skip metadata lines and extract actual content
            skip_metadata = True
            for line in lines:
                line = line.strip()
                
                # Skip empty lines
                if not line:
                    continue
                
                # Skip metadata lines
                if line.startswith('metadata ') or line.startswith('title ') or line.startswith('type '):
                    continue
                
                # Start collecting content after we find the actual content
                if line.startswith('content ') or line.startswith('Question:') or line.startswith('Answer:'):
                    skip_metadata = False
                
                # Collect meaningful content
                if not skip_metadata:
                    # Clean up the line
                    if line.startswith('content '):
                        line = line[8:]  # Remove 'content ' prefix
                    meaningful_lines.append(line)
            
            # Join meaningful lines
            cleaned_content = '\n'.join(meaningful_lines)
            
            # If we didn't find structured content, return the original
            if not cleaned_content.strip():
                return content
            
            return cleaned_content.strip()
            
        except Exception as e:
            logger.warning(f"Error cleaning content: {e}")
            return content
    
    def _clean_cache(self):
        """Clean expired cache entries"""
        current_time = time.time()
        expired_keys = [
            key for key, (_, timestamp) in self.retrieval_cache.items()
            if current_time - timestamp > self.cache_ttl
        ]
        for key in expired_keys:
            del self.retrieval_cache[key]
    
    def get_corpus_info(self, mode: str) -> Optional[Dict]:
        """Get corpus information for a given mode"""
        return self.corpora.get(mode)
    
    def is_initialized(self) -> bool:
        """Check if RAG system is initialized"""
        return len(self.corpora) > 0
    
    def get_quota_status(self) -> Dict[str, Any]:
        """Get quota status information"""
        return {
            "corpora_initialized": len(self.corpora),
            "cache_size": len(self.retrieval_cache),
            "available_modes": list(self.corpora.keys())
        }

class ConversationContextManager:
    """
    Manages conversation context and history for RAG-enhanced conversations.
    """
    
    def __init__(self, rag_manager: HybridRAGManager):
        self.rag_manager = rag_manager
        self.conversation_history = {}  # Store conversation history per client
        self.max_history_length = 10  # Keep last 10 exchanges
    
    def add_exchange(self, client_id: str, user_input: str, context: str, response: str):
        """Add a conversation exchange to history"""
        if client_id not in self.conversation_history:
            self.conversation_history[client_id] = []
        
        exchange = {
            "timestamp": datetime.now().isoformat(),
            "user_input": user_input,
            "context": context,
            "response": response
        }
        
        self.conversation_history[client_id].append(exchange)
        
        # Keep only recent history
        if len(self.conversation_history[client_id]) > self.max_history_length:
            self.conversation_history[client_id] = self.conversation_history[client_id][-self.max_history_length:]
    
    def get_conversation_context(self, client_id: str, max_turns: int = 3) -> str:
        """Get recent conversation context for better RAG retrieval"""
        if client_id not in self.conversation_history:
            return ""
        
        recent_exchanges = self.conversation_history[client_id][-max_turns:]  # Last N exchanges
        context_parts = []
        
        for exchange in recent_exchanges:
            context_parts.append(f"User: {exchange['user_input']}")
            context_parts.append(f"Assistant: {exchange['response'][:100]}...")  # Truncate response more aggressively
        
        return "\n".join(context_parts)
    
    def clear_history(self, client_id: str):
        """Clear conversation history for a client"""
        if client_id in self.conversation_history:
            del self.conversation_history[client_id]

class HybridRAGVoiceAgent:
    """
    Hybrid RAG Voice Agent that combines manual retrieval with Gemini Live API.
    """
    
    def __init__(self, project_id: str, location: str = "us-east1"):
        self.project_id = project_id
        self.location = location
        self.rag_manager = HybridRAGManager(project_id, location)
        self.context_manager = ConversationContextManager(self.rag_manager)
        self.is_initialized = False
    
    async def initialize(self) -> bool:
        """Initialize the hybrid RAG system"""
        try:
            logger.info("🚀 Initializing Hybrid RAG Voice Agent...")
            
            success = await self.rag_manager.initialize_corpora()
            if success:
                self.is_initialized = True
                logger.info("✅ Hybrid RAG Voice Agent initialized successfully")
            else:
                logger.error("❌ Failed to initialize Hybrid RAG Voice Agent")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Error initializing Hybrid RAG Voice Agent: {e}")
            return False
    
    async def process_user_input(self, user_input: str, mode: str, client_id: str, input_type: str = "text") -> Tuple[str, List[Dict]]:
        """
        Process user input with RAG context retrieval.
        
        Args:
            user_input: The user's input/query (can be text or transcribed audio)
            mode: Agent mode ('study' or 'wellness')
            client_id: Client identifier for conversation history
            input_type: Type of input ('text', 'audio_transcription', 'audio')
            
        Returns:
            Tuple of (enhanced_input_with_context, retrieved_documents)
        """
        try:
            if not self.is_initialized:
                logger.warning("RAG system not initialized, returning original input")
                return user_input, []
            
            # Get conversation context for better retrieval (limit to recent context for speed)
            conversation_context = self.context_manager.get_conversation_context(client_id, max_turns=2)  # Reduced from 3 to 2
            
            # Enhance query based on input type
            if input_type == "audio_transcription":
                # For audio transcriptions, add context about it being spoken input
                enhanced_query = f"{conversation_context}\n\nSpoken input: {user_input}" if conversation_context else f"Spoken input: {user_input}"
                logger.info(f"🎤 Processing audio transcription with RAG: {user_input[:100]}...")
            elif input_type == "audio":
                # For raw audio, create a descriptive query
                enhanced_query = f"{conversation_context}\n\nAudio input received" if conversation_context else "Audio input received"
                logger.info(f"🎵 Processing audio input with RAG")
            else:
                # For text input
                enhanced_query = f"{conversation_context}\n\nCurrent query: {user_input}" if conversation_context else user_input
                logger.info(f"📝 Processing text input with RAG: {user_input[:100]}...")
            
            # Retrieve relevant context with reduced top_k to limit tokens (optimized for speed)
            context_text, retrieved_docs = await self.rag_manager.retrieve_context(
                enhanced_query, mode, top_k=1  # Reduced from 2 to 1 for faster processing
            )
            
            # Log RAG retrieval if context logger is available
            try:
                from context_logger import get_context_logger
                context_logger = get_context_logger()
                if context_logger:
                    # Get session_id from transcript manager if available
                    from transcript_manager import get_transcript_manager
                    transcript_manager = get_transcript_manager()
                    session_data = transcript_manager.get_active_session(client_id)
                    session_id = session_data.get("session_id") if session_data else None
                    
                    if session_id:
                        await context_logger.log_rag_retrieval(
                            client_id=client_id,
                            session_id=session_id,
                            query=user_input,
                            retrieved_docs=retrieved_docs,
                            mode=mode,
                            input_type=input_type
                        )
            except Exception as log_error:
                logger.debug(f"Could not log RAG retrieval: {log_error}")
            
            # Create enhanced input with context
            if context_text:
                enhanced_input = f"""Context from knowledge base:
{context_text}

User: {user_input}

Please respond based on the provided context while maintaining a conversational, empathetic tone appropriate for {mode} support."""
                logger.info(f"✅ Enhanced input with RAG context for {mode} mode")
            else:
                # Fallback to original input with a note about context
                enhanced_input = f"""User: {user_input}

Note: Knowledge base context is currently unavailable, but please provide helpful, empathetic support appropriate for {mode} mode."""
                logger.info(f"⚠️ Using fallback input without RAG context for {mode} mode")
            
            return enhanced_input, retrieved_docs
            
        except Exception as e:
            logger.error(f"❌ Error processing user input: {e}")
            return user_input, []
    
    def add_conversation_exchange(self, client_id: str, user_input: str, context: str, response: str):
        """Add a conversation exchange to history"""
        self.context_manager.add_exchange(client_id, user_input, context, response)
    
    def clear_conversation_history(self, client_id: str):
        """Clear conversation history for a client"""
        self.context_manager.clear_history(client_id)

# Global instance
hybrid_rag_agent = None

async def initialize_hybrid_rag_system(project_id: str, location: str = "us-east1") -> bool:
    """Initialize the hybrid RAG system"""
    global hybrid_rag_agent
    
    try:
        hybrid_rag_agent = HybridRAGVoiceAgent(project_id, location)
        success = await hybrid_rag_agent.initialize()
        
        if success:
            logger.info("🎉 Hybrid RAG system initialized successfully")
        else:
            logger.error("❌ Failed to initialize hybrid RAG system")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Error initializing hybrid RAG system: {e}")
        return False

def get_hybrid_rag_agent() -> Optional[HybridRAGVoiceAgent]:
    """Get the global hybrid RAG agent instance"""
    return hybrid_rag_agent
