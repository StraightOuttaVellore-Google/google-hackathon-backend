from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
import asyncio
import json
import os
import base64
import logging
import time
from datetime import datetime
from dotenv import load_dotenv
from websockets import connect
from typing import Dict
import numpy as np
import torch
# Only import scipy.signal if needed for VAD
try:
    from scipy import signal
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    # Logger will be defined later, so we'll log this warning after logger is initialized

from google.genai.types import GenerateContentConfig
from hybrid_rag_manager import initialize_hybrid_rag_system, get_hybrid_rag_agent
from transcript_manager import get_transcript_manager, initialize_transcript_manager
from context_logger import get_context_logger, initialize_context_logger, EventType, LogLevel
from google import genai

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_agent_backend.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Log scipy availability warning if needed
if not SCIPY_AVAILABLE:
    logger.warning("scipy not available, VAD will be disabled")

router = APIRouter(tags=["VoiceAgent"])

# Audio Format Conversion Functions
def convert_pcm_to_wav(pcm_data: bytes, sample_rate: int = 24000, channels: int = 1) -> bytes:
    """Convert raw PCM audio data to WAV format"""
    import struct
    
    # WAV header parameters
    bits_per_sample = 16
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    
    # Create WAV header
    wav_header = struct.pack('<4sI4s4sIHHIIHH4sI',
        b'RIFF',                    # ChunkID
        len(pcm_data) + 36,         # ChunkSize
        b'WAVE',                    # Format
        b'fmt ',                    # Subchunk1ID
        16,                         # Subchunk1Size
        1,                          # AudioFormat (PCM)
        channels,                   # NumChannels
        sample_rate,                # SampleRate
        byte_rate,                  # ByteRate
        block_align,                # BlockAlign
        bits_per_sample,            # BitsPerSample
        b'data',                    # Subchunk2ID
        len(pcm_data)               # Subchunk2Size
    )
    
    return wav_header + pcm_data

# Audio-to-Text Conversion Function
async def convert_audio_to_text(audio_data_b64: str, mime_type: str = "audio/pcm;rate=24000") -> str:
    """Convert base64 audio data to text using Google's Gemini API"""
    try:
        from google.genai.types import HttpOptions, Part
        import base64
        
        # Create client with v1 API version
        client = genai.Client(http_options=HttpOptions(api_version="v1"))
        
        # Convert base64 to bytes
        audio_bytes = base64.b64decode(audio_data_b64)
        
        logger.info(f"Audio received: {len(audio_bytes)} bytes, format: {mime_type}")
        
        # Convert PCM to WAV format for Gemini API compatibility
        if mime_type.startswith("audio/pcm"):
            # Extract sample rate from mime type
            sample_rate = 24000  # Default
            if "rate=" in mime_type:
                try:
                    sample_rate = int(mime_type.split("rate=")[1])
                except:
                    sample_rate = 24000
            
            # Convert PCM to WAV
            wav_data = convert_pcm_to_wav(audio_bytes, sample_rate)
            logger.info(f"Converted PCM to WAV: {len(audio_bytes)} -> {len(wav_data)} bytes")
            
            # Use WAV format for Gemini API
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash-001",
                    contents=[
                        "Transcribe this audio to text. Only return the transcribed text, nothing else. If no speech is detected, return 'NO_SPEECH'.",
                        Part.from_bytes(data=wav_data, mime_type="audio/wav")
                    ]
                )
                
                if response.text and response.text.strip():
                    transcribed_text = response.text.strip()
                    if transcribed_text.upper() == "NO_SPEECH":
                        return ""
                    logger.info(f"Transcription successful: {transcribed_text[:50]}...")
                    return transcribed_text
                else:
                    logger.debug("No transcription returned from Gemini")
                    return ""
                    
            except Exception as transcription_error:
                logger.warning(f"Gemini transcription failed: {transcription_error}")
                # Fallback to descriptive message for debugging
                return f"[Audio input: {len(audio_bytes)} bytes - transcription failed]"
        else:
            # For non-PCM formats, try direct transcription
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash-001",
                    contents=[
                        "Transcribe this audio to text. Only return the transcribed text, nothing else. If no speech is detected, return 'NO_SPEECH'.",
                        Part.from_bytes(data=audio_bytes, mime_type=mime_type)
                    ]
                )
                
                if response.text and response.text.strip():
                    transcribed_text = response.text.strip()
                    if transcribed_text.upper() == "NO_SPEECH":
                        return ""
                    logger.info(f"Transcription successful: {transcribed_text[:50]}...")
                    return transcribed_text
                else:
                    logger.debug("No transcription returned from Gemini")
                    return ""
                    
            except Exception as transcription_error:
                logger.warning(f"Gemini transcription failed: {transcription_error}")
                return f"[Audio input: {len(audio_bytes)} bytes - transcription failed]"
        
    except Exception as e:
        logger.error(f"Error converting audio to text: {e}")
        return f"[Audio transcription error: {str(e)}]"

# Voice Activity Detector
class VoiceActivityDetector:
    def __init__(self):
        if not SCIPY_AVAILABLE:
            logger.warning("⚠️ VAD disabled - scipy not available")
            self.model = None
            self.is_initialized = False
            return
            
        try:
            self.model, _ = torch.hub.load(repo_or_dir='snakers4/silero-vad',
                                         model='silero_vad',
                                         force_reload=False)
            self.model.eval()
            self.target_sample_rate = 16000
            self.is_initialized = True
            logger.info("VAD model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load VAD model: {e}")
            self.model = None
            self.is_initialized = False

    def resample_audio(self, audio_data: np.ndarray, original_rate: int, target_rate: int) -> np.ndarray:
        """Resample audio data to target sample rate"""
        if original_rate == target_rate:
            return audio_data
        
        # Calculate resampling ratio
        ratio = target_rate / original_rate
        new_length = int(len(audio_data) * ratio)
        
        # Use scipy's resample function
        resampled = signal.resample(audio_data, new_length)
        return resampled.astype(np.float32)

    def is_speech(self, audio_data: bytes, sample_rate: int = 44100) -> bool:
        """Detect if audio contains speech using Silero VAD model"""
        if not self.is_initialized or self.model is None:
            logger.warning("VAD not initialized, assuming speech")
            return True  # Assume speech if VAD is not available
            
        try:
            # Convert raw bytes directly to numpy array of int16
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            
            # Check if we have enough data
            if len(audio_np) == 0:
                return False
            
            # Convert to float32 and normalize to [-1, 1] (VAD model expects float32)
            audio_float = audio_np.astype(np.float32) / 32768.0
            
            # Resample to target sample rate if needed
            if sample_rate != self.target_sample_rate:
                audio_float = self.resample_audio(audio_float, sample_rate, self.target_sample_rate)
            
            # VAD model requires exactly 512 samples for 16kHz
            required_samples = 512
            
            if len(audio_float) < required_samples:
                # Pad with zeros if too short
                padded_audio = np.zeros(required_samples, dtype=np.float32)
                padded_audio[:len(audio_float)] = audio_float
                audio_float = padded_audio
            elif len(audio_float) > required_samples:
                # Take the middle portion if too long
                start_idx = (len(audio_float) - required_samples) // 2
                audio_float = audio_float[start_idx:start_idx + required_samples]
            
            # Convert to torch tensor with proper shape [1, samples] and float32 precision
            audio_tensor = torch.from_numpy(audio_float).unsqueeze(0).float()
            
            # Get speech probability
            with torch.no_grad():
                speech_prob = self.model(audio_tensor, self.target_sample_rate).item()
            
            # Use adaptive threshold based on audio level - make it less aggressive
            rms = np.sqrt(np.mean(audio_float ** 2))
            threshold = 0.2 if rms > 0.005 else 0.3  # Lower threshold for better speech detection
            
            is_speech_detected = speech_prob > threshold
            
            # Debug logging
            if is_speech_detected:
                logger.debug(f"VAD: Speech detected (prob: {speech_prob:.3f}, rms: {rms:.4f})")
            
            return is_speech_detected
            
        except Exception as e:
            logger.error(f"VAD processing error: {e}")
            # Return True (assume speech) if VAD fails to avoid losing audio
            return True

class AwaazConnection:
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            logger.warning("GEMINI_API_KEY environment variable is not set")
            # For testing, we'll continue without the API key
            self.api_key = "test_key"
        else:
            logger.info(f"API Key loaded: {self.api_key[:10]}...{self.api_key[-4:] if len(self.api_key) > 14 else '***'}")
        
        self.model = "gemini-2.0-flash-live-001"
        self.uri = (
            "wss://generativelanguage.googleapis.com/ws/"
            "google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent"
            f"?key={self.api_key}"
        )
        self.ws = None
        self.config = None
        self.running = True
        self.vad = VoiceActivityDetector()
        self.is_playing = False
        self.vad_enabled = True  # Flag to enable/disable VAD
        self.hybrid_rag_agent = None  # Hybrid RAG agent instance
        self.conversation_mode = "wellness"  # Default mode
        
        # Audio buffering for transcription (reduced for smoother conversation)
        self.audio_buffer = b""  # Buffer to accumulate audio chunks
        self.buffer_duration_ms = 0  # Track accumulated duration
        self.min_transcription_duration_ms = 500  # Reduced to 0.5 seconds for faster response
        self.max_buffer_duration_ms = 3000  # Reduced to 3 seconds maximum buffer
        self.last_transcription_time = 0  # Track when we last transcribed
        self.transcription_cooldown_ms = 200  # Reduced to 0.2 seconds between transcriptions
        
        # Audio queue and playback tracking for accurate transcripts
        self.audio_queue = []  # Queue of audio responses waiting to be played
        self.current_playing_audio = None  # Currently playing audio (for transcript recording)
        self.audio_playback_tracking = {}  # Track which audio responses are actually played

    async def connect(self):
        """Initialize connection to Awaaz"""
        try:
            logger.info(f"🔌 AwaazConnection: Starting connection process...")
            logger.info(f"🔌 AwaazConnection: API Key present: {bool(self.api_key)}")
            logger.info(f"🔌 AwaazConnection: API Key preview: {self.api_key[:10]}...{self.api_key[-4:] if len(self.api_key) > 14 else '***'}")
            logger.info(f"🔌 AwaazConnection: Model: {self.model}")
            logger.info(f"🔌 AwaazConnection: URI: {self.uri[:50]}...")
            
            if not self.config:
                logger.error(f"❌ AwaazConnection: No configuration set!")
                raise ValueError("Configuration must be set before connecting")
            
            logger.info(f"🔌 AwaazConnection: Configuration present: {bool(self.config)}")
            logger.info(f"🔌 AwaazConnection: Config details: {self.config}")
            
            logger.info(f"🔌 AwaazConnection: Attempting WebSocket connection...")
            self.ws = await connect(self.uri)
            logger.info("✅ AwaazConnection: WebSocket connection established")

            # Configure generation settings
            generation_config = {
                "response_modalities": ["AUDIO"],
                "speech_config": {
                    "voice_config": {
                        "prebuilt_voice_config": {
                            "voice_name": self.config.get("voice", "Puck")
                        }
                    }
                }
            }
            
            # Prepare setup message (no RAG tools - using hybrid approach)
            setup_message = {
                "setup": {
                    "model": f"models/{self.model}",
                    "generation_config": generation_config,
                    "system_instruction": {
                        "parts": [
                            {
                                "text": self.config.get("systemPrompt", "You are a helpful assistant.")
                            }
                        ]
                    }
                }
            }

            logger.info(f"📤 AwaazConnection: Sending setup message with voice: {self.config.get('voice', 'Puck')}")
            logger.info(f"📤 AwaazConnection: System prompt: {self.config.get('systemPrompt', 'You are a helpful assistant.')[:100]}...")
            logger.info(f"📤 AwaazConnection: Setup message: {json.dumps(setup_message, indent=2)}")

            await self.ws.send(json.dumps(setup_message))
            logger.info("✅ AwaazConnection: Setup message sent, waiting for response...")
            
            # Wait for setup completion with timeout
            try:
                logger.info("⏳ AwaazConnection: Waiting for setup response (10s timeout)...")
                setup_response = await asyncio.wait_for(self.ws.recv(), timeout=10.0)
                logger.info(f"✅ AwaazConnection: Setup response received: {setup_response[:200]}...")
                logger.info(f"✅ AwaazConnection: Full setup response: {setup_response}")
                
                # Connection established successfully
                logger.info("🎉 AwaazConnection: Gemini Live API connection ready!")
                
            except asyncio.TimeoutError:
                logger.warning("⚠️ AwaazConnection: Setup response timeout, continuing anyway")
                
        except Exception as e:
            logger.error(f"❌ AwaazConnection: Error in connection: {e}")
            logger.error(f"❌ AwaazConnection: Error type: {type(e)}")
            import traceback
            logger.error(f"❌ AwaazConnection: Traceback: {traceback.format_exc()}")
            raise

    def set_config(self, config):
        """Set configuration for the connection"""
        self.config = config
        # Check if VAD should be disabled
        self.vad_enabled = config.get("vad_enabled", True)
        
        # Set conversation mode and get hybrid RAG agent
        self.conversation_mode = config.get("mode", "wellness")
        self.hybrid_rag_agent = get_hybrid_rag_agent()
        
        if self.hybrid_rag_agent and self.hybrid_rag_agent.is_initialized:
            logger.info(f"Hybrid RAG system available for mode: {self.conversation_mode}")
        else:
            logger.info(f"Hybrid RAG system not available - running without RAG for mode: {self.conversation_mode}")
        
        logger.info(f"VAD enabled: {self.vad_enabled}")

    async def _get_rag_context_for_mode(self, mode: str) -> str:
        """Get general RAG context for the mode to include in system prompt"""
        try:
            if not self.hybrid_rag_agent or not self.hybrid_rag_agent.is_initialized:
                logger.debug("Hybrid RAG not available")
                return ""
            
            # Get some general context for the mode
            general_queries = {
                "wellness": "mental health support, stress management, emotional wellbeing, counseling techniques",
                "study": "academic success, study strategies, time management, learning techniques"
            }
            
            query = general_queries.get(mode, "")
            if not query:
                return ""
            
            # Retrieve context
            context_text, retrieved_docs = await self.hybrid_rag_agent.process_user_input(
                query, mode, "system_context"
            )
            
            if retrieved_docs:
                logger.info(f"Retrieved {len(retrieved_docs)} context documents for {mode} system prompt")
                # Extract just the content, not the full enhanced input
                context_parts = []
                for doc in retrieved_docs[:2]:  # Limit to 2 most relevant docs
                    context_parts.append(doc['content'][:500] + "...")  # Truncate for system prompt
                
                return "\n\n".join(context_parts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting RAG context for mode: {e}")
            return ""

    async def process_text_with_rag(self, text_input: str, client_id: str, input_type: str = "text") -> str:
        """Process text input with RAG context retrieval"""
        try:
            if not self.hybrid_rag_agent or not self.hybrid_rag_agent.is_initialized:
                logger.debug("Hybrid RAG not available, returning original text")
                return text_input
            
            # Process with RAG context
            enhanced_input, retrieved_docs = await self.hybrid_rag_agent.process_user_input(
                text_input, self.conversation_mode, client_id, input_type
            )
            
            if retrieved_docs:
                logger.info(f"Retrieved {len(retrieved_docs)} context documents for {self.conversation_mode} mode")
            
            return enhanced_input
            
        except Exception as e:
            logger.error(f"Error processing text with RAG: {e}")
            return text_input

    async def send_audio_with_rag_context(self, audio_data: str, sample_rate: int = 16000, client_id: str = None):
        """Send audio data with RAG context processing"""
        try:
            # First, send the audio to get transcription
            await self.send_audio(audio_data, sample_rate)
            
            # Store the audio for potential RAG processing after transcription
            if client_id and hasattr(self, 'hybrid_rag_agent') and self.hybrid_rag_agent and self.hybrid_rag_agent.is_initialized:
                # Store the audio data for later RAG processing
                if not hasattr(self, '_pending_audio_context'):
                    self._pending_audio_context = {}
                
                self._pending_audio_context[client_id] = {
                    'audio_data': audio_data,
                    'sample_rate': sample_rate,
                    'timestamp': time.time()
                }
                
                logger.debug(f"Stored audio context for client {client_id}")
            
        except Exception as e:
            logger.error(f"Error processing audio with RAG context: {e}")
            # Fallback to regular audio processing
            await self.send_audio(audio_data, sample_rate)

    async def process_transcribed_text_with_rag(self, transcribed_text: str, client_id: str) -> str:
        """Process transcribed text with RAG context"""
        try:
            if not self.hybrid_rag_agent or not self.hybrid_rag_agent.is_initialized:
                logger.debug("Hybrid RAG not available, returning original text")
                return transcribed_text
            
            # Process with RAG context
            enhanced_text, retrieved_docs = await self.hybrid_rag_agent.process_user_input(
                transcribed_text, self.conversation_mode, client_id, input_type="audio_transcription"
            )
            
            if retrieved_docs:
                logger.info(f"Retrieved {len(retrieved_docs)} context documents for {self.conversation_mode} mode")
            
            return enhanced_text
            
        except Exception as e:
            logger.error(f"Error processing transcribed text with RAG: {e}")
            return transcribed_text

    async def send_text(self, text_message: dict):
        """Send text message to Gemini Live API"""
        try:
            await self.ws.send(json.dumps(text_message))
            logger.debug("Text message sent successfully to Gemini API")
        except Exception as e:
            logger.error(f"Error sending text message: {e}")

    def add_audio_to_queue(self, audio_data_b64: str, mime_type: str, audio_id: str = None):
        """Add audio response to playback queue with size limit"""
        if audio_id is None:
            audio_id = f"audio_{len(self.audio_queue)}_{int(time.time() * 1000)}"
        
        # Limit queue size to prevent overflow (reduced for faster response)
        max_queue_size = 2  # Reduced from 5 to 2 for faster processing
        if len(self.audio_queue) >= max_queue_size:
            # Remove oldest items to make room
            removed_items = self.audio_queue[:len(self.audio_queue) - max_queue_size + 1]
            self.audio_queue = self.audio_queue[len(self.audio_queue) - max_queue_size + 1:]
            logger.warning(f"Audio queue overflow! Removed {len(removed_items)} old items")
        
        audio_item = {
            "id": audio_id,
            "data": audio_data_b64,
            "mime_type": mime_type,
            "timestamp": time.time(),
            "played": False
        }
        
        self.audio_queue.append(audio_item)
        logger.info(f"Added audio to queue: {audio_id} (queue size: {len(self.audio_queue)})")
        return audio_id

    def mark_audio_as_played(self, audio_id: str):
        """Mark audio as played for transcript recording"""
        self.audio_playback_tracking[audio_id] = True
        logger.info(f"Marked audio as played: {audio_id}")

    def get_next_audio_from_queue(self):
        """Get next audio from queue for playback"""
        if not self.audio_queue:
            return None
        
        audio_item = self.audio_queue.pop(0)
        audio_item["played"] = True
        self.current_playing_audio = audio_item
        logger.info(f"Playing audio from queue: {audio_item['id']} (remaining: {len(self.audio_queue)})")
        return audio_item

    async def process_buffered_audio(self, client_id: str):
        """Process accumulated audio buffer for transcription"""
        import time
        
        current_time = time.time() * 1000  # Convert to milliseconds
        
        # Check if we should transcribe
        should_transcribe = (
            len(self.audio_buffer) > 0 and
            self.buffer_duration_ms >= self.min_transcription_duration_ms and
            (current_time - self.last_transcription_time) >= self.transcription_cooldown_ms
        )
        
        if should_transcribe:
            try:
                # Convert buffer to base64 for transcription
                audio_b64 = base64.b64encode(self.audio_buffer).decode("utf-8")
                
                # Transcribe the buffered audio
                transcribed_text = await convert_audio_to_text(audio_b64, "audio/pcm;rate=24000")
                
                if transcribed_text and transcribed_text.strip() and not transcribed_text.startswith("[Audio"):
                    logger.info(f"🎤 Transcribed buffered audio: {transcribed_text[:100]}...")
                    
                    # Log to transcript manager
                    from transcript_manager import get_transcript_manager
                    transcript_manager = get_transcript_manager()
                    transcript_manager.add_user_message(client_id, transcribed_text, "audio_transcription")
                    
                    # Process with RAG if we have meaningful transcription
                    if len(transcribed_text.strip()) > 5:
                        try:
                            enhanced_text = await self.process_text_with_rag(transcribed_text, client_id, input_type="audio_transcription")
                            logger.info(f"✅ Processed buffered transcription with RAG context")
                            
                            # Send enhanced text to Gemini Live API
                            text_message = {
                                "realtimeInput": {
                                    "text": enhanced_text
                                }
                            }
                            await self.send_text(text_message)
                            logger.info("Enhanced buffered transcription sent to Gemini Live API")
                        except Exception as rag_error:
                            logger.error(f"Error processing buffered transcription with RAG: {rag_error}")
                
                # Clear buffer and update timing
                self.audio_buffer = b""
                self.buffer_duration_ms = 0
                self.last_transcription_time = current_time
                
            except Exception as e:
                logger.error(f"Error processing buffered audio: {e}")
                # Clear buffer on error to prevent accumulation
                self.audio_buffer = b""
                self.buffer_duration_ms = 0

    async def send_audio(self, audio_data: str, sample_rate: int = 16000):
        """Send audio data to Awaaz with voice activity detection"""
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            
            # Only process if we have valid audio data
            if len(audio_bytes) == 0:
                logger.warning("Empty audio data, skipping")
                return
            
            # Calculate audio level for debugging (only log occasionally)
            audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
            rms = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
            # Only log audio level every 100th chunk to reduce spam
            if hasattr(self, '_audio_chunk_count'):
                self._audio_chunk_count += 1
            else:
                self._audio_chunk_count = 1
            
            if self._audio_chunk_count % 100 == 0:
                logger.debug(f"Audio RMS level: {rms:.6f}, samples: {len(audio_np)}, sample_rate: {sample_rate}")
            
            # Apply Voice Activity Detection (if enabled) and buffer audio for transcription
            if self.vad_enabled:
                try:
                    is_speech = self.vad.is_speech(audio_bytes, sample_rate)
                    # Only log VAD results occasionally to reduce spam
                    if self._audio_chunk_count % 50 == 0:
                        logger.debug(f"VAD result: is_speech={is_speech}")
                    
                    if is_speech:
                        # Add audio to buffer for transcription
                        self.audio_buffer += audio_bytes
                        # Estimate duration (assuming 16-bit samples at given sample rate)
                        chunk_duration_ms = (len(audio_bytes) / 2) / sample_rate * 1000  # Convert to milliseconds
                        self.buffer_duration_ms += chunk_duration_ms
                        
                        if self._audio_chunk_count % 50 == 0:
                            logger.debug(f"VAD: Speech detected, buffering audio (buffer: {len(self.audio_buffer)} bytes, {self.buffer_duration_ms:.0f}ms)")
                    else:
                        # No speech detected, send silence to Gemini Live API
                        silence_data = b'\x00' * len(audio_bytes)
                        audio_data = base64.b64encode(silence_data).decode("utf-8")
                        if self._audio_chunk_count % 50 == 0:
                            logger.debug("VAD: No speech detected, sending silence")
                except Exception as vad_error:
                    logger.error(f"VAD error: {vad_error}")
                    # If VAD fails, assume it's speech to avoid losing audio
                    logger.warning("VAD failed, assuming speech")
                    # Add to buffer anyway
                    self.audio_buffer += audio_bytes
                    chunk_duration_ms = (len(audio_bytes) / 2) / sample_rate * 1000
                    self.buffer_duration_ms += chunk_duration_ms
            else:
                # VAD disabled - add all audio to buffer
                self.audio_buffer += audio_bytes
                chunk_duration_ms = (len(audio_bytes) / 2) / sample_rate * 1000
                self.buffer_duration_ms += chunk_duration_ms
                
                # Only log occasionally when VAD is disabled
                if self._audio_chunk_count % 100 == 0:
                    logger.debug(f"VAD disabled - buffering all audio (buffer: {len(self.audio_buffer)} bytes, {self.buffer_duration_ms:.0f}ms)")
            
            # Check if we should process buffered audio for transcription
            if len(self.audio_buffer) > 0 and self.buffer_duration_ms >= self.min_transcription_duration_ms:
                # Process buffered audio (this will be handled in the WebSocket handler with proper client_id)
                logger.debug(f"Audio buffer ready for transcription: {len(self.audio_buffer)} bytes, {self.buffer_duration_ms:.0f}ms")
            
            # Only send audio if not currently playing (unless interruptions are allowed)
            allow_interruptions = self.config.get("allow_interruptions", False)
            should_process = (not self.is_playing) or (self.is_playing and allow_interruptions)
            # Only log processing decision occasionally
            if self._audio_chunk_count % 100 == 0:
                logger.debug(f"Should process audio: {should_process} (is_playing: {self.is_playing}, allow_interruptions: {allow_interruptions})")
            
            if should_process:
                # Convert 16kHz input to 24kHz for Gemini Live API
                if sample_rate == 16000:
                    # Resample audio from 16kHz to 24kHz
                    audio_np = np.frombuffer(audio_bytes, dtype=np.int16)
                    audio_float = audio_np.astype(np.float32) / 32768.0
                    
                    logger.debug(f"Resampling from 16kHz to 24kHz: {len(audio_float)} -> {int(len(audio_float) * 1.5)} samples")
                    
                    # Resample to 24kHz
                    resampled_audio = self.vad.resample_audio(audio_float, 16000, 24000)
                    
                    # Convert back to 16-bit PCM
                    resampled_int16 = (resampled_audio * 32768).astype(np.int16)
                    audio_data = base64.b64encode(resampled_int16.tobytes()).decode("utf-8")
                    sample_rate = 24000
                    
                    # Only log resampling info occasionally
                    if self._audio_chunk_count % 100 == 0:
                        logger.debug(f"Resampled audio: {len(resampled_int16)} samples at {sample_rate}Hz")
                
                realtime_input_msg = {
                    "realtimeInput": {
                        "mediaChunks": [
                            {
                                "data": audio_data,
                                "mimeType": f"audio/pcm;rate={sample_rate}"
                            }
                        ]
                    }
                }
                # Only log sending info occasionally
                if self._audio_chunk_count % 100 == 0:
                    logger.debug(f"Sending to Gemini API: {len(audio_data)} chars")
                
                await self.ws.send(json.dumps(realtime_input_msg))
                # Only log success occasionally
                if self._audio_chunk_count % 100 == 0:
                    logger.info("Audio sent successfully to Gemini API")
                
            else:
                # Only log skipping occasionally
                if self._audio_chunk_count % 100 == 0:
                    logger.debug("Skipping audio - currently playing and interruptions not allowed")
        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            import traceback
            traceback.print_exc()

    async def close(self):
        """Close the connection"""
        self.running = False
        if self.ws:
            await self.ws.close()

# Store active connections
connections: Dict[str, AwaazConnection] = {}

@router.get("/api/voices")
async def get_available_voices():
    """Get available voice options"""
    return {
        "voices": ["Puck", "Charon", "Kore", "Fenrir", "Aoede"],
        "default": "Puck"
    }

@router.get("/api/agent-modes")
async def get_agent_modes():
    """Get available agent modes and their configurations"""
    return {
        "modes": {
            "wellness": {
                "name": "Wellness Journal",
                "description": "A safe space for voice journalling about your daily experiences, emotions, and wellbeing",
                "systemPrompt": "Voice journalling companion for mental wellbeing using CBT and Socratic methods",
                "icon": "🌱",
                "color": "green"
            },
            "study": {
                "name": "Study Journal", 
                "description": "A supportive space for voice journalling about your academic experiences, challenges, and learning journey",
                "systemPrompt": "Voice journalling companion for academic wellbeing using CBT and Socratic methods",
                "icon": "📚",
                "color": "blue"
            }
        }
    }

@router.get("/api/rag-status")
async def get_rag_status():
    """Get RAG system status and quota information"""
    try:
        hybrid_rag = get_hybrid_rag_agent()
        if hybrid_rag and hybrid_rag.is_initialized:
            status = hybrid_rag.rag_manager.get_quota_status()
            return {
                "status": "initialized",
                "rag_system": "hybrid",
                "quota_info": status,
                "message": "Hybrid RAG system is operational"
            }
        else:
            return {
                "status": "not_initialized",
                "rag_system": "hybrid",
                "quota_info": {},
                "message": "Hybrid RAG system is not available"
            }
    except Exception as e:
        return {
            "status": "error",
            "rag_system": "hybrid",
            "quota_info": {},
            "message": f"Error checking RAG status: {str(e)}"
        }

@router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    logger.info(f"🔌 WebSocket connection attempt from client: {client_id}")
    logger.info(f"🔌 WebSocket client info: {websocket.client}")
    await websocket.accept()
    logger.info(f"✅ WebSocket connection accepted for client: {client_id}")
    
    try:
        # Initialize hybrid RAG system
        logger.info("🚀 Initializing hybrid RAG system...")
        try:
            project_id = os.environ.get("GOOGLE_CLOUD_PROJECT_ID")
            if project_id:
                rag_success = await initialize_hybrid_rag_system(project_id)
                if rag_success:
                    logger.info("✅ Hybrid RAG system initialized successfully")
                else:
                    logger.warning("⚠️ Hybrid RAG system initialization failed - continuing without RAG")
            else:
                logger.warning("⚠️ GOOGLE_CLOUD_PROJECT_ID not set - continuing without RAG")
        except Exception as e:
            logger.warning(f"⚠️ Failed to initialize hybrid RAG system: {e}")
        
        logger.info(f"🔧 Creating Awaaz connection for client: {client_id}")
        # Create new Awaaz connection for this client
        awaaz = AwaazConnection()
        awaaz.session_saved = False  # Flag to prevent double cleanup
        awaaz.client_id = client_id  # Store client ID for session management
        connections[client_id] = awaaz
        logger.info(f"✅ Awaaz connection created for client: {client_id}")
        
        # Wait for initial configuration
        logger.info(f"⏳ Waiting for configuration from client: {client_id}")
        config_data = await websocket.receive_json()
        logger.info(f"📨 Received configuration data: {config_data}")
        
        if config_data.get("type") != "config":
            logger.error(f"❌ First message must be configuration, got: {config_data.get('type')}")
            raise ValueError("First message must be configuration")
        
        # Get the configuration and apply mode-specific system prompt
        config = config_data.get("config", {})
        mode = config.get("mode", "wellness")
        logger.info(f"🔧 Processing configuration for mode: {mode}")
        logger.info(f"🔧 Full config: {config}")
        
        # Apply mode-specific system prompt with RAG context
        rag_context = await awaaz._get_rag_context_for_mode(mode)
        
        if mode == "study":
            base_prompt = """You are Awaaz, a compassionate AI study companion specializing in voice journalling for academic wellbeing. Your primary role is to listen actively and help students process their academic experiences through guided reflection.

CORE OBJECTIVES:
- Create a safe, non-judgmental space for students to voice their academic concerns, challenges, and experiences
- Use Socratic questioning to help students explore their study patterns, learning habits, and academic stressors
- Apply evidence-based CBT techniques to help students identify thought patterns affecting their academic performance
- Gather insights about their study routines, productivity levels, social interactions, and academic pressures
- Help students articulate their academic goals, challenges, and areas needing support

APPROACH:
- Listen more than you speak - your primary goal is to understand, not to solve
- Use gentle, open-ended questions that encourage deeper reflection
- Apply CBT techniques to help identify unhelpful thought patterns about studies
- Use Socratic questioning to guide self-discovery about study habits and challenges
- Validate their experiences while gently challenging limiting beliefs
- Focus on understanding their academic journey, not providing immediate solutions

CONVERSATION STYLE:
- Warm, encouraging, and genuinely curious about their academic experience
- Ask questions like: "What was that like for you?" "How did that make you feel?" "What do you think might be contributing to this?"
- Help them explore patterns: "I notice you mentioned feeling overwhelmed when... Can you tell me more about what happens in those moments?"
- Be multilingual (English/Hindi) and culturally sensitive to Indian academic contexts

Remember: You're a listening companion, not a study coach. Your job is to help them process and understand their academic experience through thoughtful conversation."""
        else:  # wellness mode
            base_prompt = """You are Awaaz, a compassionate AI wellness companion specializing in voice journalling for mental wellbeing. Your primary role is to listen actively and help users process their daily experiences through guided reflection.

CORE OBJECTIVES:
- Create a safe, non-judgmental space for users to voice their thoughts, feelings, and daily experiences
- Use Socratic questioning to help users explore their emotional patterns, daily activities, and social interactions
- Apply evidence-based CBT techniques to help users identify thought patterns affecting their wellbeing
- Gather insights about their daily routines, activity levels, social connections, and emotional states
- Help users articulate their feelings, concerns, and areas where they need support

APPROACH:
- Listen more than you speak - your primary goal is to understand, not to fix
- Use gentle, open-ended questions that encourage deeper emotional exploration
- Apply CBT techniques to help identify unhelpful thought patterns
- Use Socratic questioning to guide self-discovery about emotions and behaviors
- Validate their experiences while gently challenging limiting beliefs
- Focus on understanding their emotional journey, not providing immediate solutions

CONVERSATION STYLE:
- Warm, empathetic, and genuinely curious about their daily experience
- Ask questions like: "How are you feeling about that?" "What was that like for you?" "Can you tell me more about what you're experiencing?"
- Help them explore patterns: "I notice you mentioned feeling stressed when... What usually happens in those situations?"
- Be multilingual (English/Hindi) and culturally sensitive to Indian contexts

Remember: You're a listening companion, not a therapist. Your job is to help them process and understand their experiences through thoughtful conversation."""
        
        # Add RAG context to the system prompt
        if rag_context:
            config["systemPrompt"] = f"""{base_prompt}

KNOWLEDGE BASE CONTEXT:
{rag_context}

Use this knowledge base context to provide more informed, evidence-based responses while maintaining your compassionate, listening-focused approach."""
        else:
            config["systemPrompt"] = base_prompt
        
        # Set the configuration
        logger.info(f"🔧 Setting configuration for Awaaz connection...")
        awaaz.set_config(config)
        
        # Create transcript session
        logger.info(f"🚀 Starting transcript session for client: {client_id}")
        transcript_manager = get_transcript_manager()
        if transcript_manager:
            session_id = transcript_manager.start_session(client_id, mode)
            awaaz.session_id = session_id
            logger.info(f"✅ Transcript session started: {session_id}")
        else:
            logger.warning(f"⚠️ Transcript manager not available for client: {client_id}")
        
        # Debug: Log configuration details
        logger.info(f"✅ Configuration applied for client {client_id}:")
        logger.info(f"   - VAD enabled: {awaaz.vad_enabled}")
        logger.info(f"   - Allow interruptions: {config.get('allow_interruptions', False)}")
        logger.info(f"   - Mode: {mode}")
        
        # Send configuration confirmation
        logger.info(f"📤 Sending configuration confirmation to client: {client_id}")
        await websocket.send_json({
            "type": "status",
            "status": "config_received",
            "text": f"Configuration received for {mode} mode"
        })
        logger.info(f"✅ Configuration confirmation sent")
        
        # Initialize Awaaz connection
        logger.info(f"🔌 Attempting to connect to Gemini API for client: {client_id}")
        try:
            await awaaz.connect()
            logger.info(f"✅ Gemini API connection established for client: {client_id}")
            
            # Send connection success message
            logger.info(f"📤 Sending connection success message to client: {client_id}")
            await websocket.send_json({
                "type": "status", 
                "status": "connected",
                "text": "Connected to AI service successfully"
            })
            logger.info(f"✅ Connection success message sent")
        except Exception as e:
            logger.error(f"❌ Failed to connect to Gemini API: {e}")
            logger.error(f"❌ Error details: {str(e)}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            await websocket.send_json({
                "type": "error",
                "text": f"Failed to connect to AI service: {str(e)}"
            })
            logger.info(f"📤 Error message sent to client: {client_id}")
            return
        
        # Handle bidirectional communication
        async def receive_from_client():
            try:
                logger.info("Starting to receive from client...")
                while True:
                    try:
                        message = await websocket.receive()
                        logger.debug(f"Received message from client: {message['type']}")
                        
                        # Check for close message
                        if message["type"] == "websocket.disconnect":
                            logger.info("Received disconnect message")
                            return
                            
                        message_content = json.loads(message["text"])
                        msg_type = message_content["type"]
                        logger.debug(f"Message type: {msg_type}")
                        
                        if msg_type == "audio":
                            sample_rate = message_content.get("sampleRate", 44100)
                            data_length = len(message_content.get("data", ""))
                            audio_data = message_content.get("data", "")
                            
                            # Send audio directly to Gemini Live API for immediate processing (no buffering)
                            try:
                                await awaaz.send_audio(audio_data, sample_rate)
                                logger.debug(f"Audio sent to Gemini Live API: {data_length} chars")
                            except Exception as audio_error:
                                logger.error(f"Error sending audio to Gemini: {audio_error}")
                            
                            # Optional: Process audio for transcription (non-blocking)
                            # This runs in background without blocking the main audio flow
                            try:
                                if len(awaaz.audio_buffer) > 0 and awaaz.buffer_duration_ms >= awaaz.min_transcription_duration_ms:
                                    # Process buffered audio for transcription in background
                                    asyncio.create_task(awaaz.process_buffered_audio(client_id))
                            except Exception as transcription_error:
                                logger.debug(f"Background transcription error: {transcription_error}")
                            
                            # Only log audio message details occasionally
                            if not hasattr(awaaz, '_client_message_count'):
                                awaaz._client_message_count = 0
                            awaaz._client_message_count += 1
                            if awaaz._client_message_count % 100 == 0:
                                logger.debug(f"Audio message: {data_length} chars, sample_rate: {sample_rate}")
                            await awaaz.send_audio(audio_data, sample_rate)
                        elif msg_type == "text":
                            # Handle text input with RAG processing
                            text_input = message_content.get("text", "")
                            if text_input:
                                logger.info(f"Processing text input: {text_input[:100]}...")
                                
                                # Log user text input to transcript
                                transcript_manager = get_transcript_manager()
                                if transcript_manager and hasattr(awaaz, 'session_id') and awaaz.session_id:
                                    transcript_manager.add_user_message(client_id, text_input, "text")
                                    logger.info(f"✅ Added user message to transcript")
                                
                                # Process with RAG context
                                enhanced_text = await awaaz.process_text_with_rag(text_input, client_id)
                                
                                # Send enhanced text to Gemini Live API
                                text_message = {
                                    "realtimeInput": {
                                        "text": enhanced_text
                                    }
                                }
                                await awaaz.ws.send(json.dumps(text_message))
                                logger.info("Enhanced text sent to Gemini Live API")
                        elif msg_type == "audio_played":
                            # Handle audio playback confirmation from frontend
                            audio_id = message_content.get("audioId")
                            if audio_id:
                                logger.info(f"Received audio playback confirmation for: {audio_id}")
                                # The transcript was already recorded when the audio was sent to frontend
                                # This confirmation can be used for analytics or debugging
                            else:
                                logger.warning("Received audio_played message without audioId")
                        elif msg_type == "disconnect":
                            # Handle explicit disconnect message
                            logger.info("Received explicit disconnect message from client")
                            awaaz.running = False  # Signal awaaz to stop
                            
                            # Save session transcript immediately
                            try:
                                transcript_manager = get_transcript_manager()
                                if transcript_manager and hasattr(awaaz, 'session_id') and awaaz.session_id:
                                    session_data = transcript_manager.get_active_session(client_id)
                                    if session_data:
                                        logger.info(f"🔧 Active session found: {session_data['session_id']} with {session_data['metadata']['total_exchanges']} exchanges")
                                    
                                    transcript_id = await transcript_manager.save_session(client_id)
                                    if transcript_id:
                                        logger.info(f"✅ Session transcript saved immediately: {transcript_id}")
                                        awaaz.session_saved = True
                                    else:
                                        logger.warning(f"⚠️ Failed to save session transcript immediately")
                                else:
                                    logger.warning(f"⚠️ No transcript manager or session available for immediate cleanup")
                            except Exception as cleanup_error:
                                logger.error(f"❌ Error in immediate cleanup: {cleanup_error}")
                                import traceback
                                traceback.print_exc()
                            return
                        else:
                            logger.warning(f"Unknown message type: {msg_type}")
                    except json.JSONDecodeError as e:
                        logger.error(f"JSON decode error: {e}")
                        continue
                    except KeyError as e:
                        logger.error(f"Key error in message: {e}")
                        continue
                    except Exception as e:
                        logger.error(f"Error processing client message: {str(e)}")
                        if "disconnect" in str(e).lower() or "closed" in str(e).lower():
                            return
                        continue
                            
            except Exception as e:
                logger.error(f"Fatal error in receive_from_client: {str(e)}")
                return

        async def receive_from_awaaz():
            try:
                logger.info("Starting to receive from Gemini API...")
                logger.debug(f"Awaaz running status: {awaaz.running}")
                logger.debug(f"Awaaz WebSocket status: {awaaz.ws is not None}")
                if awaaz.ws:
                    logger.debug(f"WebSocket state: {awaaz.ws.state}")
                message_count = 0
                
                # Use async for loop like in standalone implementation
                if not awaaz.ws:
                    logger.error("WebSocket is not available")
                    return
                    
                async for msg in awaaz.ws:
                    if not awaaz.running:
                        logger.info("Awaaz stopped, breaking receive loop")
                        break
                        
                    try:
                        message_count += 1
                        logger.debug(f"Raw message from Gemini: {len(msg)} chars")
                        logger.debug(f"Message preview: {msg[:500]}...")
                        
                        response = json.loads(msg)
                        logger.info(f"Parsed response keys: {list(response.keys())}")
                        logger.info(f"Full response structure: {json.dumps(response, indent=2)}")
                        
                        # Process Gemini 2.0 WebSocket response format
                        if "serverContent" in response:
                            server_content = response["serverContent"]
                            logger.debug(f"Server content keys: {list(server_content.keys())}")
                            
                            if "modelTurn" in server_content:
                                model_turn = server_content["modelTurn"]
                                logger.debug(f"Model turn keys: {list(model_turn.keys())}")
                                
                                if "parts" in model_turn:
                                    parts = model_turn["parts"]
                                    logger.info(f"Model turn parts: {len(parts)} parts received")
                                    
                                    for i, part in enumerate(parts):
                                        logger.debug(f"Part {i} keys: {list(part.keys())}")
                                        
                                        if "inlineData" in part:
                                            # This indicates audio data
                                            logger.info("Audio data found in response!")
                                            awaaz.is_playing = True
                                            
                                            # Extract both the audio data and its MIME type
                                            inline_data = part["inlineData"]
                                            audio_data_b64 = inline_data["data"]
                                            mime_type = inline_data.get("mimeType", "audio/opus")  # Default to Opus for Gemini Live API
                                            
                                            logger.info(f"Audio data: {len(audio_data_b64)} chars with MIME type: {mime_type}")
                                            
                                            # Add audio to playback queue instead of immediately recording transcript
                                            audio_id = awaaz.add_audio_to_queue(audio_data_b64, mime_type)
                                            
                                            try:
                                                # Send both data and mimeType to the frontend with audio ID for tracking
                                                await websocket.send_json({
                                                    "type": "audio",
                                                    "data": audio_data_b64,
                                                    "mimeType": mime_type,
                                                    "audioId": audio_id  # Include audio ID for frontend tracking
                                                })
                                                logger.info(f"Audio data sent to frontend successfully with ID: {audio_id}")
                                                
                                                # Mark this audio as played for transcript recording
                                                awaaz.mark_audio_as_played(audio_id)
                                                
                                                # Now record transcript for this played audio
                                                transcript_manager = get_transcript_manager()
                                                if transcript_manager and hasattr(awaaz, 'session_id') and awaaz.session_id:
                                                    try:
                                                        # Convert AI audio to text for transcript logging
                                                        transcribed_text = await convert_audio_to_text(audio_data_b64, mime_type)
                                                        
                                                        # Only record transcript for audio that was actually sent to frontend
                                                        if transcribed_text and transcribed_text != "[Audio transcription failed]" and not transcribed_text.startswith("[Audio transcription error:"):
                                                            transcript_manager.add_assistant_message(client_id, transcribed_text, "audio_transcription")
                                                            logger.info(f"✅ Added played AI audio transcription to transcript: {transcribed_text[:100]}...")
                                                            
                                                            # Add to RAG conversation context for future retrievals
                                                            try:
                                                                awaaz.hybrid_rag_agent.add_conversation_exchange(
                                                                    client_id, 
                                                                    "",  # No user input for AI response
                                                                    "",  # No context for AI response
                                                                    transcribed_text
                                                                )
                                                                logger.info(f"✅ Added played AI audio transcription to RAG conversation context")
                                                            except Exception as rag_error:
                                                                logger.error(f"Error adding AI response to RAG context: {rag_error}")
                                                        else:
                                                            # Fallback for failed transcription
                                                            ai_audio_description = f"[AI Audio response: {len(audio_data_b64)} chars, {mime_type} - transcription failed]"
                                                            transcript_manager.add_assistant_message(client_id, ai_audio_description, "audio")
                                                            logger.info(f"✅ Added played AI audio response to transcript: {ai_audio_description}")
                                                            
                                                    except Exception as transcribe_error:
                                                        logger.error(f"Error transcribing played AI audio: {transcribe_error}")
                                                        # Fallback to descriptive message
                                                        ai_audio_description = f"[AI Audio response: {len(audio_data_b64)} chars, {mime_type} - transcription failed]"
                                                        transcript_manager.add_assistant_message(client_id, ai_audio_description, "audio")
                                                        logger.info(f"✅ Added played AI audio response to transcript: {ai_audio_description}")
                                                
                                            except Exception as send_error:
                                                logger.error(f"Error sending audio to frontend: {send_error}")
                                                # Don't return - continue processing other audio
                                                # Clear the audio queue to prevent further issues
                                                awaaz.audio_queue.clear()
                                                logger.warning("Cleared audio queue due to WebSocket error")
                                                
                                        elif "text" in part:
                                            # If the model also responds with text, forward it
                                            text_content = part["text"]
                                            logger.info(f"Text response: {text_content}")
                                            
                                            # Add to conversation history if hybrid RAG is available
                                            if awaaz.hybrid_rag_agent and awaaz.hybrid_rag_agent.is_initialized:
                                                # Get the last user input from conversation history
                                                conversation_context = awaaz.hybrid_rag_agent.context_manager.get_conversation_context(client_id)
                                                if conversation_context:
                                                    # Extract the last user input (simplified)
                                                    lines = conversation_context.split('\n')
                                                    last_user_input = ""
                                                    for line in reversed(lines):
                                                        if line.startswith("User:"):
                                                            last_user_input = line.replace("User:", "").strip()
                                                            break
                                                    
                                                    if last_user_input:
                                                        awaaz.hybrid_rag_agent.add_conversation_exchange(
                                                            client_id, last_user_input, "", text_content
                                                        )
                                            
                                            try:
                                                await websocket.send_json({
                                                    "type": "text",
                                                    "text": text_content
                                                })
                                                logger.info("Text response sent to frontend")
                                            except Exception as send_error:
                                                logger.error(f"Error sending text to frontend: {send_error}")
                                                return
                                        else:
                                            logger.warning(f"Unknown part type: {part}")
                                else:
                                    logger.warning("No parts in modelTurn")
                            else:
                                logger.warning("No modelTurn in serverContent")
                            
                            # Check if the model ended its turn
                            if server_content.get("turnComplete"):
                                awaaz.is_playing = False
                                logger.info("Turn completed by Gemini")
                                try:
                                    await websocket.send_json({
                                        "type": "status",
                                        "status": "listening"
                                    })
                                    logger.info("Listening status sent to frontend")
                                except Exception as send_error:
                                    logger.error(f"Error sending status: {send_error}")
                                    return
                            else:
                                logger.debug("Turn not complete yet")
                        else:
                            logger.warning(f"Unexpected response format: {response}")
                            # Check if this is a different type of response
                            if "turnComplete" in response:
                                logger.info("Turn completed (direct)")
                                awaaz.is_playing = False
                            elif "error" in response:
                                logger.error(f"Error in response: {response['error']}")
                            elif "candidates" in response:
                                # Handle different response format
                                logger.info("Found candidates in response")
                                candidates = response.get("candidates", [])
                                for candidate in candidates:
                                    if "content" in candidate:
                                        content = candidate["content"]
                                        if "parts" in content:
                                            parts = content["parts"]
                                            for part in parts:
                                                if "inlineData" in part:
                                                    logger.info("Audio data found in candidates!")
                                                    awaaz.is_playing = True
                                                    
                                                    # Extract both the audio data and its MIME type
                                                    inline_data = part["inlineData"]
                                                    audio_data_b64 = inline_data["data"]
                                                    mime_type = inline_data.get("mimeType", "audio/opus")  # Default to Opus for Gemini Live API
                                                    
                                                    # Convert AI audio to text for transcript logging and RAG context (candidates)
                                                    transcript_manager = get_transcript_manager()
                                                    if transcript_manager and hasattr(awaaz, 'session_id') and awaaz.session_id:
                                                        try:
                                                            # Convert AI audio to text
                                                            transcribed_text = await convert_audio_to_text(audio_data_b64, mime_type)
                                                            
                                                            # Log the transcribed text to transcript
                                                            transcript_manager.add_assistant_message(client_id, transcribed_text, "audio_transcription")
                                                            logger.info(f"✅ Added AI audio transcription (candidates) to transcript: {transcribed_text[:100]}...")
                                                            
                                                            # Add to RAG conversation context for future retrievals
                                                            if transcribed_text and transcribed_text != "[Audio transcription failed]" and not transcribed_text.startswith("[Audio transcription error:"):
                                                                try:
                                                                    # Add the AI response to conversation context for better future RAG retrievals
                                                                    awaaz.hybrid_rag_agent.add_conversation_exchange(
                                                                        client_id, 
                                                                        "",  # No user input for AI response
                                                                        "",  # No context for AI response
                                                                        transcribed_text
                                                                    )
                                                                    logger.info(f"✅ Added AI audio transcription (candidates) to RAG conversation context")
                                                                except Exception as rag_error:
                                                                    logger.error(f"Error adding AI response (candidates) to RAG context: {rag_error}")
                                                            
                                                        except Exception as transcribe_error:
                                                            logger.error(f"Error transcribing AI audio (candidates): {transcribe_error}")
                                                            # Fallback to descriptive message
                                                            ai_audio_description = f"[AI Audio response (candidates): {len(audio_data_b64)} chars, {mime_type} - transcription failed]"
                                                            transcript_manager.add_assistant_message(client_id, ai_audio_description, "audio")
                                                            logger.info(f"✅ Added AI audio response (candidates) to transcript: {ai_audio_description}")
                                                    
                                                    try:
                                                        await websocket.send_json({
                                                            "type": "audio",
                                                            "data": audio_data_b64,
                                                            "mimeType": mime_type
                                                        })
                                                        logger.info("Audio data sent to frontend from candidates")
                                                    except Exception as send_error:
                                                        logger.error(f"Error sending audio from candidates: {send_error}")
                            else:
                                logger.debug(f"Full response: {json.dumps(response, indent=2)}")
                            
                    except Exception as receive_error:
                        logger.error(f"Error processing Gemini response: {receive_error}")
                        import traceback
                        traceback.print_exc()
                        # Continue processing other messages
                        continue
                                
            except Exception as e:
                logger.error(f"Fatal error in receive_from_awaaz: {e}")
                import traceback
                traceback.print_exc()
                return
            finally:
                logger.info("Receive from Awaaz loop ended")

        # Run both receiving tasks concurrently
        logger.info("Starting concurrent tasks: receive_from_client and receive_from_awaaz")
        try:
            await asyncio.gather(
                receive_from_client(),
                receive_from_awaaz(),
                return_exceptions=True
            )
        except Exception as gather_error:
            logger.error(f"Error in asyncio.gather: {gather_error}")
            import traceback
            traceback.print_exc()

    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        # Cleanup
        logger.info(f"🔧 Starting cleanup for client: {client_id}")
        if client_id in connections:
            awaaz_connection = connections[client_id]
            logger.info(f"🔧 Found connection for client: {client_id}")
            
            # Save session transcript only if not already saved
            if not getattr(awaaz_connection, 'session_saved', False):
                try:
                    logger.info(f"💾 Attempting to save session transcript for client: {client_id}")
                    transcript_manager = get_transcript_manager()
                    if transcript_manager:
                        transcript_id = await transcript_manager.save_session(client_id)
                        if transcript_id:
                            logger.info(f"✅ Session transcript saved: {transcript_id}")
                            awaaz_connection.session_saved = True
                        else:
                            logger.warning(f"⚠️ Failed to save session transcript for client: {client_id}")
                    else:
                        logger.warning(f"⚠️ Transcript manager not available for client: {client_id}")
                except Exception as e:
                    logger.error(f"❌ Error saving session transcript: {e}")
                    import traceback
                    traceback.print_exc()
            else:
                logger.info(f"✅ Session already saved for client: {client_id}")
            
            # Clear conversation history
            hybrid_rag = get_hybrid_rag_agent()
            if hybrid_rag and hybrid_rag.is_initialized:
                hybrid_rag.clear_conversation_history(client_id)
                logger.info(f"🧹 Cleared conversation history for client: {client_id}")
            
            await awaaz_connection.close()
            del connections[client_id]
            logger.info(f"🔧 Cleanup completed for client: {client_id}")
        else:
            logger.warning(f"⚠️ No connection found for client: {client_id} during cleanup")
