# Hybrid RAG Voice Agent System

## Overview

This system implements a **turn-by-turn hybrid RAG approach** for Gemini Live API integration. Since Gemini Live API (WebSocket) doesn't directly support Vertex AI RAG Engine tools, this implementation manually retrieves relevant context before each conversation turn and injects it into the conversation.

## Key Features

- **Turn-by-turn RAG**: Manual context retrieval before each user input
- **Conversation History**: Maintains conversation context for better retrieval
- **Caching**: Intelligent caching of retrieval results to reduce latency
- **Mode-specific Corpora**: Separate knowledge bases for wellness and study modes
- **Real-time Processing**: Works seamlessly with Gemini Live API WebSocket connections

## Architecture

### Components

1. **HybridRAGManager**: Core RAG functionality with manual retrieval
2. **ConversationContextManager**: Manages conversation history and context
3. **HybridRAGVoiceAgent**: Main agent that combines RAG with voice processing
4. **AwaazConnection**: Updated WebSocket connection handler

### Flow

```
User Input → RAG Retrieval → Enhanced Input → Gemini Live API → Response
     ↓              ↓              ↓              ↓           ↓
Conversation    Context        Context +      Audio/Text    History
History         Retrieval      User Input     Response     Update
```

## Setup

### Prerequisites

1. Google Cloud Project with billing enabled
2. Vertex AI API enabled
3. Required environment variables:
   ```bash
   GOOGLE_CLOUD_PROJECT_ID=your-project-id
   GEMINI_API_KEY=your-gemini-api-key
   ```

### Installation

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Test the system:
   ```bash
   python test_hybrid_rag.py
   ```

3. Start the server:
   ```bash
   uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

## Usage

### WebSocket Connection

Connect to the WebSocket endpoint:
```
ws://localhost:8000/ws/{client_id}
```

### Message Types

#### Configuration Message (First Message)
```json
{
  "type": "config",
  "config": {
    "mode": "wellness",  // or "study"
    "voice": "Puck",
    "vad_enabled": true,
    "allow_interruptions": false
  }
}
```

#### Audio Message
```json
{
  "type": "audio",
  "data": "base64_encoded_audio_data",
  "sampleRate": 16000
}
```

#### Text Message (New - for RAG processing)
```json
{
  "type": "text",
  "text": "I'm feeling stressed about work"
}
```

### Response Messages

#### Audio Response
```json
{
  "type": "audio",
  "data": "base64_encoded_audio_data",
  "mimeType": "audio/opus"
}
```

#### Text Response
```json
{
  "type": "text",
  "text": "I understand you're feeling stressed..."
}
```

#### Status Messages
```json
{
  "type": "status",
  "status": "connected|listening|config_received",
  "text": "Status description"
}
```

## RAG Processing

### How It Works

1. **User Input**: User sends audio or text message
2. **Context Retrieval**: System retrieves relevant context from knowledge base
3. **Enhanced Input**: Context is combined with user input
4. **Gemini Processing**: Enhanced input is sent to Gemini Live API
5. **Response**: Audio/text response is returned to user
6. **History Update**: Conversation is added to history for future context

### Knowledge Bases

- **Wellness Mode**: Mental health support, counseling techniques, wellness strategies
- **Study Mode**: Academic success, study techniques, learning strategies

### Caching

- Retrieval results are cached for 5 minutes
- Cache key includes mode and query hash
- Automatic cleanup of expired cache entries

## Configuration

### Agent Modes

#### Wellness Mode
- **Corpus**: Mental health and wellness support
- **System Prompt**: Empathetic counseling companion
- **Use Case**: Mental health support, emotional wellbeing

#### Study Mode
- **Corpus**: Academic success and study strategies
- **System Prompt**: Academic support companion
- **Use Case**: Study support, academic guidance

### Voice Activity Detection (VAD)

- Enabled by default
- Filters out non-speech audio
- Can be disabled via configuration
- Uses Silero VAD model

## Performance Considerations

### Latency

- **RAG Retrieval**: ~100-500ms per query
- **Caching**: Reduces repeated retrieval latency
- **Conversation History**: Improves context relevance

### Optimization Tips

1. **Selective Retrieval**: Only retrieve when topic changes significantly
2. **Pre-fetching**: Retrieve context for likely follow-up questions
3. **Cache Management**: Monitor cache hit rates and adjust TTL

## Troubleshooting

### Common Issues

1. **RAG System Not Initialized**
   - Check `GOOGLE_CLOUD_PROJECT_ID` environment variable
   - Verify Google Cloud billing is enabled
   - Check Vertex AI API is enabled

2. **No Context Retrieved**
   - Verify corpora are created and populated
   - Check query relevance to knowledge base
   - Adjust vector distance threshold

3. **High Latency**
   - Enable caching (default)
   - Reduce `top_k` parameter
   - Optimize query length

### Debugging

Enable debug logging:
```python
logging.getLogger().setLevel(logging.DEBUG)
```

Check logs for:
- RAG retrieval results
- Cache hit/miss rates
- Conversation history updates

## Migration from Old System

The old RAG integration (`rag_integration.py`) has been deprecated and replaced with this hybrid approach. Key changes:

1. **No RAG Tools**: Removed direct RAG tool integration in Gemini setup
2. **Manual Retrieval**: Context is retrieved before each turn
3. **Enhanced Input**: Context is injected into user input
4. **Conversation History**: Maintains context across turns

## API Reference

### HybridRAGVoiceAgent

#### `process_user_input(query, mode, client_id)`
Processes user input with RAG context retrieval.

**Parameters:**
- `query`: User's input text
- `mode`: Agent mode ("wellness" or "study")
- `client_id`: Client identifier for conversation history

**Returns:**
- `enhanced_input`: Input with RAG context
- `retrieved_docs`: List of retrieved documents

#### `add_conversation_exchange(client_id, user_input, context, response)`
Adds conversation exchange to history.

#### `clear_conversation_history(client_id)`
Clears conversation history for a client.

## Contributing

When making changes to the RAG system:

1. Test with both wellness and study modes
2. Verify conversation history is maintained correctly
3. Check cache performance and hit rates
4. Ensure graceful degradation when RAG is unavailable

## License

This project is part of the Google Hackathon submission.

