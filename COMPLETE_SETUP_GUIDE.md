# Complete RAG-Enhanced Voice Agent Setup Guide

## 🎯 Overview

This guide provides step-by-step instructions to set up a comprehensive RAG-enhanced voice agent system using Vertex AI RAG Engine and Gemini Live API. The system includes professional datasets for both academic success and mental health support.

## 📋 Prerequisites

### 1. Google Cloud Project Setup

**Step 1: Create or Select a Google Cloud Project**
```bash
# Install Google Cloud CLI if not already installed
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Login to Google Cloud
gcloud auth login

# Create a new project (optional)
gcloud projects create my-rag-voice-agent-123456 --name="RAG Voice Agent"

# Set your project
gcloud config set project my-rag-voice-agent-123456
```

**Step 2: Enable Required APIs**
```bash
# Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com

# Enable Cloud Storage API
gcloud services enable storage.googleapis.com

# Enable Gemini API
gcloud services enable generativelanguage.googleapis.com

# Verify APIs are enabled
gcloud services list --enabled
```

**Step 3: Set Up Authentication**
```bash
# Create a service account
gcloud iam service-accounts create rag-voice-agent-sa \
    --description="Service account for RAG Voice Agent" \
    --display-name="RAG Voice Agent Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding my-rag-voice-agent-123456 \
    --member="serviceAccount:rag-voice-agent-sa@my-rag-voice-agent-123456.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding my-rag-voice-agent-123456 \
    --member="serviceAccount:rag-voice-agent-sa@my-rag-voice-agent-123456.iam.gserviceaccount.com" \
    --role="roles/storage.admin"

# Create and download service account key
gcloud iam service-accounts keys create ~/rag-voice-agent-key.json \
    --iam-account=rag-voice-agent-sa@my-rag-voice-agent-123456.iam.gserviceaccount.com
```

### 2. Environment Setup

**Step 4: Install Python Dependencies**
```bash
# Navigate to backend directory
cd /home/vatsal/Hackathons/GenAIExchange/FullStackR2/backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

**Step 5: Set Up Environment Variables**
```bash
# Create .env file
cat > .env << EOF
# Google Cloud Configuration
GOOGLE_CLOUD_PROJECT_ID=my-rag-voice-agent-123456
GOOGLE_APPLICATION_CREDENTIALS=/home/vatsal/rag-voice-agent-key.json

# Gemini API Configuration
GEMINI_API_KEY=YOUR_GEMINI_API_KEY

# Database Configuration (if using)
DATABASE_URL=postgresql://username:password@localhost:5432/rag_voice_agent

# Optional: Logging Configuration
LOG_LEVEL=INFO
EOF
```

**Step 6: Get Gemini API Key**
1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Click "Create API Key"
3. Copy the API key and add it to your `.env` file

## 🗂️ Dataset Structure

The system includes three professional datasets:

### 1. Academic Success Knowledge Base
- **File**: `academic_success_knowledge_base.md`
- **Content**: Comprehensive academic guidance including:
  - Executive function and cognitive enhancement
  - Study techniques and learning methodologies
  - Academic stress management and mental health
  - Specialized support for diverse learning needs
  - Advanced study skills and research methods
  - Career development and academic planning
  - Crisis management and support systems

### 2. Mental Health Knowledge Base
- **File**: `mental_health_knowledge_base.md`
- **Content**: Comprehensive mental health support including:
  - Anxiety management and stress reduction
  - Depression and mood management
  - Relationship and social wellbeing
  - Self-care and personal growth
  - Sleep and physical wellbeing
  - Crisis management and professional support
  - Substance use and addiction support
  - Trauma and PTSD support
  - Cultural and identity considerations
  - Mindfulness and spiritual wellbeing

### 3. Counsel Chat Dataset
- **File**: `counsel_chat_250-tokens_full.json`
- **Content**: Real therapy conversations from licensed therapists
- **Format**: JSON with conversation history and responses
- **Size**: 4,000+ therapy Q&A pairs

## 🚀 Installation and Setup

### Step 7: Initialize the RAG System

**Test the Setup:**
```bash
# Run the test script to verify everything is working
python test_rag_integration.py
```

**Expected Output:**
```
🚀 Starting RAG-enhanced Voice Agent Tests
============================================================
📋 System Information:
   Project ID: YOUR_PROJECT_ID
   Gemini API Key: Set
   Google Credentials: Set
📁 Dataset Files:
   Academic Dataset: ✅ Found
   Mental Health Dataset: ✅ Found
   Counsel Chat Dataset: ✅ Found

🧪 Running RAG Initialization test...
✅ RAG system initialized successfully

🧪 Running Dataset Processing test...
✅ Datasets processed successfully. Corpus IDs: {'study': 'corpus_id_1', 'wellness': 'corpus_id_2'}

🧪 Running RAG Configuration test...
✅ Study mode RAG configuration retrieved
✅ Wellness mode RAG configuration retrieved

🧪 Running Voice Agent Integration test...
✅ Study voice agent can use RAG tools
✅ Wellness voice agent can use RAG tools

📊 Test Results Summary:
============================================================
   RAG Initialization: ✅ PASSED
   Dataset Processing: ✅ PASSED
   RAG Configuration: ✅ PASSED
   Voice Agent Integration: ✅ PASSED

🎯 Overall: 4/4 tests passed
🎉 All tests passed! RAG-enhanced voice agent is ready to use.
```

### Step 8: Start the Application

**Start the Backend Server:**
```bash
# Start the FastAPI server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Will watch for changes in these directories: ['/path/to/backend']
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [12345] using StatReload
INFO:     Started server process [12346]
INFO:     Waiting for application startup.
INFO:     Initializing RAG system for project: YOUR_PROJECT_ID
INFO:     Dataset processing system initialized successfully
INFO:     Processed academic dataset into 7 sections
INFO:     Processed mental health dataset into 10 sections
INFO:     Processed counsel chat JSON dataset into 80 batches
INFO:     Created RAG corpus: academic-success-corpus with ID: corpus_id_1
INFO:     Created RAG corpus: mental-health-wellness-corpus with ID: corpus_id_2
INFO:     Successfully processed datasets and created corpora: {'study': 'corpus_id_1', 'wellness': 'corpus_id_2'}
INFO:     RAG system initialized successfully
INFO:     Application startup complete.
```

## 🔧 Configuration

### Voice Agent Modes

**Study Mode Configuration:**
```javascript
const studyConfig = {
  type: 'config',
  config: {
    mode: 'study',
    voice: 'Puck',
    vad_enabled: true,
    allow_interruptions: false,
    systemPrompt: 'You are Awaaz, a compassionate AI study companion...'
  }
};
```

**Wellness Mode Configuration:**
```javascript
const wellnessConfig = {
  type: 'config',
  config: {
    mode: 'wellness',
    voice: 'Puck',
    vad_enabled: true,
    allow_interruptions: true,
    systemPrompt: 'You are Awaaz, a compassionate AI wellness companion...'
  }
};
```

### RAG Configuration

The system automatically configures RAG tools based on the mode:

**Study Mode RAG Tools:**
```json
{
  "retrieval": {
    "vertex_rag_store": {
      "rag_resources": {
        "rag_corpus": "projects/YOUR_PROJECT_ID/locations/us-central1/ragCorpora/academic-success-corpus"
      }
    }
  }
}
```

**Wellness Mode RAG Tools:**
```json
{
  "retrieval": {
    "vertex_rag_store": {
      "rag_resources": {
        "rag_corpus": "projects/YOUR_PROJECT_ID/locations/us-central1/ragCorpora/mental-health-wellness-corpus"
      }
    }
  }
}
```

## 🎮 Usage Examples

### Frontend Integration

**WebSocket Connection:**
```javascript
// Connect to voice agent
const ws = new WebSocket('ws://localhost:8000/ws/client-id');

// Configure for study mode
ws.send(JSON.stringify({
  type: 'config',
  config: {
    mode: 'study',
    voice: 'Puck',
    vad_enabled: true
  }
}));

// Handle responses
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'audio') {
    // Play audio response
    const audio = new Audio('data:audio/opus;base64,' + data.data);
    audio.play();
  } else if (data.type === 'text') {
    // Display text response
    console.log('AI Response:', data.text);
  }
};

// Send audio data
const sendAudio = (audioBlob) => {
  const reader = new FileReader();
  reader.onload = () => {
    const base64 = reader.result.split(',')[1];
    ws.send(JSON.stringify({
      type: 'audio',
      data: base64,
      sampleRate: 44100
    }));
  };
  reader.readAsDataURL(audioBlob);
};
```

### API Endpoints

**Get Available Voices:**
```bash
curl http://localhost:8000/api/voices
```

**Get Agent Modes:**
```bash
curl http://localhost:8000/api/agent-modes
```

**Health Check:**
```bash
curl http://localhost:8000/health-de1f4b3133627b2cacac9aad5ddfe07c
```

## 🔍 Monitoring and Debugging

### Log Files

**Backend Logs:**
```bash
# View real-time logs
tail -f voice_agent_backend.log

# View specific log levels
grep "ERROR" voice_agent_backend.log
grep "RAG" voice_agent_backend.log
```

**Application Logs:**
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug
```

### Key Metrics to Monitor

1. **RAG Retrieval Performance**
   - Response time for RAG queries
   - Number of documents retrieved per query
   - Relevance scores of retrieved content

2. **Voice Agent Performance**
   - Audio processing latency
   - Voice activity detection accuracy
   - WebSocket connection stability

3. **Dataset Processing**
   - Number of documents processed
   - Corpus creation success rate
   - Document upload completion

### Common Issues and Solutions

**Issue: RAG Initialization Fails**
```bash
# Check Google Cloud credentials
gcloud auth list
gcloud config get-value project

# Verify API enablement
gcloud services list --enabled | grep aiplatform
```

**Issue: Dataset Processing Errors**
```bash
# Check file permissions
ls -la rag_dataset/

# Verify file encoding
file rag_dataset/academic_success_knowledge_base.md
```

**Issue: Voice Agent Connection Problems**
```bash
# Check Gemini API key
echo $GEMINI_API_KEY

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/test-client
```

## 🚀 Advanced Configuration

### Custom Dataset Integration

**Adding New Datasets:**
1. Create your dataset file in `rag_dataset/`
2. Add processing method to `DatasetProcessor` class
3. Update `process_and_upload_datasets()` function
4. Test with `test_rag_integration.py`

**Example:**
```python
def process_custom_dataset(self, dataset_path: str) -> List[str]:
    """Process custom dataset and upload to GCS"""
    # Your custom processing logic here
    pass
```

### Performance Optimization

**RAG Optimization:**
- Adjust chunk sizes based on content type
- Implement response caching for common queries
- Use latest embedding models for better retrieval

**Voice Agent Optimization:**
- Tune VAD sensitivity for your environment
- Optimize audio sample rates and compression
- Implement progressive response delivery

### Security Considerations

**Data Privacy:**
- All user interactions are processed securely
- No personal data is stored in RAG corpora
- Implement proper access controls

**API Security:**
- Use environment variables for sensitive data
- Implement rate limiting
- Monitor for unusual usage patterns

## 📊 Dataset Statistics

### Academic Success Knowledge Base
- **Size**: 390 lines of comprehensive content
- **Sections**: 7 major categories
- **Content**: Evidence-based academic strategies
- **Coverage**: Executive function, study techniques, stress management, neurodivergent support

### Mental Health Knowledge Base
- **Size**: 461 lines of comprehensive content
- **Sections**: 10 major categories
- **Content**: Evidence-based mental health support
- **Coverage**: Anxiety, depression, relationships, self-care, crisis management

### Counsel Chat Dataset
- **Size**: 4,000+ therapy conversations
- **Format**: JSON with conversation history
- **Source**: Licensed therapists from counselchat.com
- **Integration**: Supplemented with mental health knowledge base

## 🎯 Next Steps

### Immediate Actions
1. **Test the System**: Run `python test_rag_integration.py`
2. **Start the Server**: `uvicorn main:app --reload`
3. **Connect Frontend**: Implement WebSocket connection
4. **Monitor Performance**: Check logs and metrics

### Future Enhancements
1. **Multi-language Support**: Expand datasets for different languages
2. **Personalization**: User-specific RAG corpora
3. **Real-time Learning**: Continuous dataset updates
4. **Advanced Analytics**: Detailed usage metrics
5. **Integration**: Connect with external resources

## 🆘 Support and Troubleshooting

### Getting Help
1. **Check Logs**: Review error messages in log files
2. **Run Tests**: Use `test_rag_integration.py` to diagnose issues
3. **Verify Setup**: Ensure all prerequisites are met
4. **Check Documentation**: Review Google Cloud and Gemini API docs

### Common Commands
```bash
# Restart the application
pkill -f uvicorn
uvicorn main:app --reload

# Clear logs
> voice_agent_backend.log

# Test RAG system
python test_rag_integration.py

# Check Google Cloud status
gcloud auth list
gcloud config get-value project
```

## 🎉 Success Indicators

You'll know the system is working correctly when:

✅ **RAG Initialization**: All tests pass in `test_rag_integration.py`
✅ **Dataset Processing**: Corpora are created successfully
✅ **Voice Agent**: WebSocket connections work without errors
✅ **Audio Processing**: Voice input is processed and responses are generated
✅ **RAG Integration**: Responses include relevant retrieved content
✅ **Logging**: No critical errors in log files

**Congratulations! Your RAG-enhanced voice agent is ready to provide intelligent, context-aware support for both academic success and mental health! 🚀**
